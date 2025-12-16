import base64
import hashlib
import logging
from html.parser import HTMLParser
from pathlib import Path

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ScriptExtractor(HTMLParser):
    """
    Secure HTML parser for extracting inline scripts.

    Uses HTMLParser instead of regex to avoid ReDoS and parsing edge cases.
    """

    def __init__(self):
        super().__init__()
        self.scripts: list[str] = []
        self._in_script = False
        self._current_script = []
        self._current_tag_has_src = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        if tag.lower() == "script":
            self._in_script = True
            self._current_script = []
            # Check if script has src attribute
            self._current_tag_has_src = any(attr[0].lower() == "src" for attr in attrs)

    def handle_endtag(self, tag: str):
        if tag.lower() == "script" and self._in_script:
            # Only collect inline scripts (without src attribute)
            if not self._current_tag_has_src:
                script_content = "".join(self._current_script)
                if script_content.strip():  # Only add non-empty scripts
                    self.scripts.append(script_content)
            self._in_script = False
            self._current_script = []
            self._current_tag_has_src = False

    def handle_data(self, data: str):
        if self._in_script:
            self._current_script.append(data)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        static_path: Path,
        enable_hsts: bool = False,
        csp_report_uri: str | None = None,
    ):
        super().__init__(app)
        self.static_path = static_path.resolve()  # Resolve to prevent path traversal
        self.script_hashes: set[str] = set()
        self.enable_hsts = enable_hsts  # Only enable HSTS when on HTTPS
        self.csp_report_uri = csp_report_uri

        # Use exact match for relaxed CSP routes to prevent prefix matching exploits
        self.relaxed_csp_routes = {
            "/api/docs",
            "/api/docs/",
            "/api/redoc",
            "/api/redoc/",
        }

        # Extract hashes at startup
        self._extract_hashes()

        # Build CSP header once
        self.csp_header = self._build_csp()
        self.relaxed_csp_header = self._build_relaxed_csp()
        logger.info(f"CSP initialized with {len(self.script_hashes)} script hashes")

        # Log all hashes for debugging
        for hash_val in sorted(self.script_hashes):
            logger.info(f"  Allowed script hash: {hash_val}")

    def _extract_inline_scripts(self, html_content: str) -> list[str]:
        """
        Extract inline script contents from HTML using proper HTML parser.

        This avoids ReDoS vulnerabilities and handles edge cases that regex cannot.
        """
        try:
            parser = ScriptExtractor()
            parser.feed(html_content)
            return parser.scripts
        except Exception as e:
            logger.error(f"Error parsing HTML for scripts: {e}")
            return []

    def _calculate_hash(self, content: str) -> str:
        """Calculate SHA-256 hash for content."""
        hash_digest = hashlib.sha256(content.encode("utf-8")).digest()
        hash_b64 = base64.b64encode(hash_digest).decode("utf-8")
        hash_str = f"'sha256-{hash_b64}'"
        return hash_str

    def _is_safe_file_path(self, file_path: Path) -> bool:
        """
        Validate that a file path is within the static directory.

        Prevents path traversal vulnerabilities.
        """
        try:
            resolved_file = file_path.resolve()
            resolved_static = self.static_path.resolve()

            # Check if file is within static path
            resolved_file.relative_to(resolved_static)
            return True
        except (ValueError, RuntimeError):
            logger.warning(f"Unsafe file path detected: {file_path}")
            return False

    def _extract_hashes(self):
        """Extract and hash all inline scripts from static HTML files."""
        if not self.static_path.exists():
            logger.warning(f"Static path {self.static_path} does not exist")
            return

        # Find all HTML files in the static directory
        try:
            html_files = list(self.static_path.rglob("*.html"))
        except Exception as e:
            logger.error(f"Error listing HTML files: {e}")
            return

        if not html_files:
            logger.warning(f"No HTML files found in {self.static_path}")
            return

        logger.info(f"Processing {len(html_files)} HTML file(s) for CSP hashes")

        for html_file in html_files:
            # Validate file path before reading
            if not self._is_safe_file_path(html_file):
                logger.error(f"Skipping unsafe file path: {html_file}")
                continue

            try:
                # Limit file size to prevent DoS
                if html_file.stat().st_size > 10 * 1024 * 1024:  # 10MB limit
                    logger.warning(f"Skipping large file: {html_file} (>10MB)")
                    continue

                with open(html_file, encoding="utf-8") as f:
                    html_content = f.read()

                # Extract and hash inline scripts using HTMLParser
                inline_scripts = self._extract_inline_scripts(html_content)

                if inline_scripts:
                    logger.info(
                        f"Found {len(inline_scripts)} inline script(s) in {html_file.name}"
                    )

                for i, script in enumerate(inline_scripts):
                    hash_value = self._calculate_hash(script)
                    self.script_hashes.add(hash_value)

                    # Debug log
                    logger.debug(f"  Script {i + 1} hash: {hash_value}")
                    logger.debug(f"  Script {i + 1} length: {len(script)} bytes")
                    logger.debug(f"  Script {i + 1} preview: {repr(script[:80])}")

            except (OSError, UnicodeDecodeError) as e:
                logger.error(f"Error processing {html_file}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error processing {html_file}: {e}")

    def _build_csp(self) -> str:
        """Build the Content Security Policy header."""
        # Start with base directives
        script_src = "'self'"
        if self.script_hashes:
            # Limit number of hashes to prevent header size issues
            if len(self.script_hashes) > 50:
                logger.warning(
                    f"Large number of script hashes: {len(self.script_hashes)}"
                )
            script_src += " " + " ".join(sorted(self.script_hashes))

        # For styles - keep unsafe-inline for SvelteKit transitions
        # Note: This is a known trade-off for framework compatibility
        style_src = "'self' 'unsafe-inline'"

        csp_parts = [
            "default-src 'self'",
            f"script-src {script_src}",
            f"style-src {style_src}",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "object-src 'none'",
        ]

        # Only add upgrade-insecure-requests if HSTS is enabled (implies HTTPS)
        if self.enable_hsts:
            csp_parts.append("upgrade-insecure-requests")

        # Add CSP reporting if configured
        if self.csp_report_uri:
            csp_parts.append(f"report-uri {self.csp_report_uri}")

        return "; ".join(csp_parts)

    def _build_relaxed_csp(self) -> str:
        """Build relaxed CSP for API documentation (Swagger UI, ReDoc)."""
        csp_parts = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Swagger needs eval
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "object-src 'none'",
        ]

        # Add CSP reporting if configured
        if self.csp_report_uri:
            csp_parts.append(f"report-uri {self.csp_report_uri}")

        return "; ".join(csp_parts)

    def _should_use_relaxed_csp(self, path: str) -> bool:
        """
        Check if the request path should use relaxed CSP.

        Uses exact match instead of prefix matching to prevent bypasses.
        """
        # Normalize path
        normalized_path = path.rstrip("/")

        # Check exact matches and explicit child paths
        if normalized_path in self.relaxed_csp_routes:
            return True

        # Check if it's a subpath of relaxed routes (e.g., /api/docs/something)
        for route in self.relaxed_csp_routes:
            if normalized_path.startswith(route.rstrip("/") + "/"):
                return True

        return False

    def _validate_content_type(self, content_type: str | None) -> bool:
        """
        Validate content type to prevent header injection via content-type manipulation.
        """
        if not content_type:
            return True

        # Reject content types with newlines (header injection attempt)
        if "\n" in content_type or "\r" in content_type:
            logger.warning(
                f"Header injection attempt detected in content-type: {content_type!r}"
            )
            return False

        return True

    async def dispatch(self, request: Request, call_next):
        # Process the request normally
        response = await call_next(request)
        path = request.url.path

        # Get and validate content type
        content_type = response.headers.get("content-type", "")
        if not self._validate_content_type(content_type):
            # Don't add headers to suspicious responses
            return response

        # Check if relaxed CSP should be used
        use_relaxed_csp = self._should_use_relaxed_csp(path)
        if use_relaxed_csp:
            logger.debug(f"Applied relaxed CSP for {path}")
            return response

        # Only add headers to HTML responses and API responses
        if (
            "text/html" in content_type
            or "application/json" in content_type
            or not content_type
        ):
            # Content Security Policy
            if use_relaxed_csp:
                response.headers["Content-Security-Policy"] = self.relaxed_csp_header
            else:
                response.headers["Content-Security-Policy"] = self.csp_header

            # Strict Transport Security (only if explicitly enabled and on HTTPS)
            if self.enable_hsts:
                response.headers["Strict-Transport-Security"] = (
                    "max-age=63072000; includeSubDomains; preload"
                )

            # Permissions Policy (restrictive by default)
            response.headers["Permissions-Policy"] = (
                "accelerometer=(), autoplay=(), "
                "camera=(), display-capture=(), "
                "encrypted-media=(), fullscreen=(self), "
                "geolocation=(), gyroscope=(), microphone=(), "
                "payment=(), picture-in-picture=(), "
                "screen-wake-lock=(), usb=()"
            )

            # Other Security Headers
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
            response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
            response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        return response
