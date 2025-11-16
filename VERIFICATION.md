# Build Verification & Transparency

This document explains how PrioTag ensures transparency and allows users to verify that the deployed application matches the open source code.

## Overview

PrioTag implements a multi-layered verification system to ensure that what you see running is exactly what's in the public source code:

1. **Signed Docker Images** - All production images are cryptographically signed
2. **SLSA Provenance** - Build attestations link source code to artifacts
3. **SBOM (Software Bill of Materials)** - Complete dependency lists for transparency
4. **Build Metadata Injection** - Running apps expose their exact Git commit
5. **Public CI/CD** - All builds happen in auditable GitHub Actions workflows

## Quick Verification

### For End Users

Visit the verification page on any PrioTag deployment:
```
https://your-priotag-instance.com/verify
```

This page shows:
- The exact Git commit SHA of the running code
- Link to view that commit on GitHub
- Build date and version
- Instructions for advanced verification

### For Technical Users

Verify the backend API directly:
```bash
curl https://your-priotag-instance.com/api/v1/build-info
```

Response:
```json
{
  "version": "v1.2.3",
  "commit": "abc123def456...",
  "build_date": "2025-11-16T12:34:56Z",
  "source_url": "https://github.com/DomiDre/priotag/tree/abc123def456..."
}
```

## Docker Image Verification

### Prerequisites

Install [Cosign](https://docs.sigstore.dev/cosign/installation/):

```bash
# Linux
curl -O -L "https://github.com/sigstore/cosign/releases/latest/download/cosign-linux-amd64"
sudo mv cosign-linux-amd64 /usr/local/bin/cosign
sudo chmod +x /usr/local/bin/cosign

# macOS
brew install cosign

# Windows
choco install cosign
```

### Verify Image Signatures

All PrioTag Docker images are signed using keyless OIDC signing with Sigstore:

```bash
# Verify backend image
cosign verify \
  --certificate-identity-regexp='https://github.com/DomiDre/priotag' \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
  ghcr.io/domidre/priotag-backend:latest

# Verify admin UI image
cosign verify \
  --certificate-identity-regexp='https://github.com/DomiDre/priotag' \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
  ghcr.io/domidre/priotag-admin-ui:latest

# Verify frontend image
cosign verify \
  --certificate-identity-regexp='https://github.com/DomiDre/priotag' \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
  ghcr.io/domidre/priotag-frontend:latest
```

Successful verification output:
```
Verification for ghcr.io/domidre/priotag-backend:latest --
The following checks were performed on each of these signatures:
  - The cosign claims were validated
  - Existence of the claims in the transparency log was verified offline
  - The code-signing certificate was verified using trusted certificate authority certificates
```

### Verify SBOM Attestations

View the Software Bill of Materials to see all dependencies:

```bash
# Verify and display SBOM for backend
cosign verify-attestation \
  --type spdxjson \
  --certificate-identity-regexp='https://github.com/DomiDre/priotag' \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
  ghcr.io/domidre/priotag-backend:latest | jq -r '.payload' | base64 -d | jq
```

This shows every package, version, and license included in the image.

## Build Process Verification

### GitHub Actions Workflows

All builds are performed in public GitHub Actions:

1. **Location**: `.github/workflows/build-and-sign.yml`
2. **Trigger**: Automatically on push to `main` or version tags
3. **View Runs**: https://github.com/DomiDre/priotag/actions

### Build Steps (Transparent & Auditable)

Each build:
1. ✅ Starts from a clean Ubuntu runner
2. ✅ Checks out the exact commit
3. ✅ Builds Docker images with injected metadata
4. ✅ Generates SBOM with Syft
5. ✅ Signs images with Cosign (keyless OIDC)
6. ✅ Attests SBOMs to images
7. ✅ Pushes to GitHub Container Registry
8. ✅ Creates release artifacts

### Reproducible Builds

While not byte-for-byte reproducible, our builds are:
- **Deterministic**: Same source → same behavior
- **Transparent**: All steps logged in CI
- **Verifiable**: Signatures prove authenticity
- **Documented**: Complete SBOM shows all inputs

## SLSA Provenance

Our builds generate [SLSA](https://slsa.dev/) provenance metadata:

- **Build Platform**: GitHub Actions
- **Source Repository**: github.com/DomiDre/priotag
- **Build Definition**: Public workflow file
- **Build Parameters**: Commit SHA, version, date

Docker's built-in provenance is enabled via `provenance: true` in the build workflow.

## Security Benefits

### What This Prevents

✅ **Supply Chain Attacks**: Signatures ensure images come from our CI
✅ **Malicious Modifications**: Any tampering breaks the signature
✅ **Dependency Confusion**: SBOM shows exact dependencies
✅ **Backdoored Builds**: Public CI logs prove build process
✅ **Impersonation**: Only our GitHub Actions can sign our images

### Trust Anchors

The verification chain relies on:
1. **GitHub**: Trusted to run Actions securely
2. **Sigstore**: Trusted transparency log and CA
3. **Source Code**: Publicly auditable on GitHub

## Verification for Self-Hosting

If you're self-hosting PrioTag:

### Option 1: Use Official Signed Images

```bash
# Pull verified images
docker pull ghcr.io/domidre/priotag-backend:latest
docker pull ghcr.io/domidre/priotag-admin-ui:latest
docker pull ghcr.io/domidre/priotag-frontend:latest

# Verify signatures (as shown above)
cosign verify ...

# Run with docker-compose
docker-compose up -d
```

### Option 2: Build From Source

```bash
# Clone repository
git clone https://github.com/DomiDre/priotag.git
cd priotag

# Checkout specific verified version
git checkout v1.2.3

# Build locally
just build

# The build will still inject metadata
# Check: docker run --rm ghcr.io/domidre/priotag-backend:latest cat /app/build_info.json
```

## FAQ

### How do I know the signature is legitimate?

Cosign uses keyless signing, which means:
- No secret keys to manage or leak
- Identity comes from GitHub's OIDC token
- Certificate includes workflow details
- Everything is logged in Sigstore's transparency log

### Can you sign a malicious image?

Technically yes, if our GitHub repository is compromised. However:
- Repository changes are public and visible
- Commit history is preserved
- Community can audit all changes
- Signatures only prove "built by our CI", not "is safe"

### What about dependencies?

- SBOM lists all dependencies with versions
- You can audit each package
- Use `npm audit`, `pip-audit`, etc. on the SBOM
- We run security scans in CI (see `.github/workflows/ci.yml`)

### Is this better than trusting a binary?

Yes, because:
- You can read the source code
- You can verify the source → binary link
- Build process is transparent
- Community can audit everything

### How often are images rebuilt?

- On every push to `main`
- On every version tag (releases)
- You can see build dates in `/api/v1/build-info`

## Advanced: Verify Build Reproducibility

While not byte-for-byte reproducible, you can verify behavioral equivalence:

```bash
# Build twice from the same commit
git checkout abc123

# First build
docker build -t test1 ./backend
docker run --rm test1 cat /app/build_info.json > build1.json

# Second build (clean cache)
docker build --no-cache -t test2 ./backend
docker run --rm test2 cat /app/build_info.json > build2.json

# Compare (should be identical except timestamps)
diff build1.json build2.json
```

## Resources

- **Cosign Documentation**: https://docs.sigstore.dev/cosign/
- **SLSA Framework**: https://slsa.dev/
- **SBOM Guide**: https://www.ntia.gov/sbom
- **Supply Chain Security**: https://security.googleblog.com/2021/05/introducing-slsa-end-to-end-framework.html

## Contributing

If you have suggestions for improving our verification process:
1. Open an issue on GitHub
2. Propose changes via pull request
3. All changes will be publicly visible and verifiable

## Support

Questions about verification?
- Open an issue: https://github.com/DomiDre/priotag/issues
- Check discussions: https://github.com/DomiDre/priotag/discussions
