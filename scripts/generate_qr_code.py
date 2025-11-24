#!/usr/bin/env python3
"""
QR Code Generator for Priotag Registration

This script generates QR codes for the all-in-one registration flow.
Users can scan the QR code within the institute to register without manually entering the magic word.

Requirements:
    pip install qrcode[pil]

Usage:
    # Generate QR code with magic word and institution
    python generate_qr_code.py "MyMagicWord123" "MIT"

    # Generate QR code with URL containing magic word and institution
    python generate_qr_code.py "MyMagicWord123" "MIT" --url "https://priotag.example.com"

    # Specify output file
    python generate_qr_code.py "MyMagicWord123" "MIT" --output mit_registration_qr.png

    # Customize QR code size and error correction
    python generate_qr_code.py "MyMagicWord123" "MIT" --size 10 --error-correction H
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Literal

try:
    import qrcode
    from qrcode.image.pure import PyPNGImage
except ImportError:
    print("Error: qrcode library not installed")
    print("Please install it with: pip install qrcode[pil]")
    sys.exit(1)


ErrorCorrectionLevel = Literal["L", "M", "Q", "H"]


def generate_qr_code(
    magic_word: str,
    institution_short_code: str,
    output_file: str = "registration_qr.png",
    base_url: str | None = None,
    box_size: int = 10,
    border: int = 4,
    error_correction: ErrorCorrectionLevel = "M",
) -> None:
    """
    Generate a QR code for registration.

    Args:
        magic_word: The magic word for registration
        institution_short_code: The institution short code (e.g., 'MIT', 'STANFORD')
        output_file: Path to save the QR code image
        base_url: Optional base URL for the frontend. If provided, creates a URL with magic word parameter
        box_size: Size of each box in pixels (default: 10)
        border: Border size in boxes (default: 4)
        error_correction: Error correction level - L (7%), M (15%), Q (25%), H (30%)
    """
    # Determine error correction level
    error_levels = {
        "L": qrcode.constants.ERROR_CORRECT_L,
        "M": qrcode.constants.ERROR_CORRECT_M,
        "Q": qrcode.constants.ERROR_CORRECT_Q,
        "H": qrcode.constants.ERROR_CORRECT_H,
    }

    qr = qrcode.QRCode(
        version=1,  # Auto-adjust version based on data size
        error_correction=error_levels[error_correction],
        box_size=box_size,
        border=border,
    )

    # Determine what to encode in the QR code
    if base_url:
        # Option 1: Encode a full URL with magic word and institution as parameters
        # This allows direct navigation to registration page
        base_url = base_url.rstrip("/")
        qr_data = f"{base_url}/register?magic={magic_word}&institution={institution_short_code}"
        print(f"Generating QR code with URL: {qr_data}")
    else:
        # Option 2: Encode JSON with magic word and institution
        # Users can use this in the registration form
        qr_data = json.dumps({
            "magic": magic_word,
            "institution": institution_short_code
        })
        print(f"Generating QR code with magic word: {magic_word}")
        print(f"                   and institution: {institution_short_code}")

    qr.add_data(qr_data)
    qr.make(fit=True)

    # Create and save the image
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(output_file)

    print(f"✓ QR code saved to: {output_file}")
    print(f"  Box size: {box_size}px")
    print(f"  Border: {border} boxes")
    print(f"  Error correction: {error_correction}")

    # Also save metadata
    metadata_file = Path(output_file).with_suffix(".json")
    metadata = {
        "magic_word": magic_word,
        "institution_short_code": institution_short_code,
        "url": qr_data if base_url else None,
        "output_file": output_file,
        "box_size": box_size,
        "border": border,
        "error_correction": error_correction,
    }

    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"✓ Metadata saved to: {metadata_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate QR codes for Priotag registration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage - magic word and institution
  %(prog)s "MyMagicWord123" "MIT"

  # With URL for direct navigation
  %(prog)s "MyMagicWord123" "MIT" --url "https://priotag.example.com"

  # Custom output file
  %(prog)s "MyMagicWord123" "MIT" -o mit_registration.png

  # Large QR code with high error correction
  %(prog)s "MyMagicWord123" "STANFORD" --size 20 --error-correction H
        """,
    )

    parser.add_argument(
        "magic_word",
        help="The magic word for registration",
    )

    parser.add_argument(
        "institution",
        help="Institution short code (e.g., 'MIT', 'STANFORD')",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="registration_qr.png",
        help="Output file path (default: registration_qr.png)",
    )

    parser.add_argument(
        "-u",
        "--url",
        help="Base URL of the frontend (e.g., https://priotag.example.com). "
        "If provided, the QR code will contain a full URL to the registration page.",
    )

    parser.add_argument(
        "-s",
        "--size",
        type=int,
        default=10,
        help="Size of each box in pixels (default: 10)",
    )

    parser.add_argument(
        "-b",
        "--border",
        type=int,
        default=4,
        help="Border size in boxes (default: 4)",
    )

    parser.add_argument(
        "-e",
        "--error-correction",
        choices=["L", "M", "Q", "H"],
        default="M",
        help="Error correction level: L (7%%), M (15%%), Q (25%%), H (30%%) (default: M)",
    )

    args = parser.parse_args()

    generate_qr_code(
        magic_word=args.magic_word,
        institution_short_code=args.institution,
        output_file=args.output,
        base_url=args.url,
        box_size=args.size,
        border=args.border,
        error_correction=args.error_correction,
    )


if __name__ == "__main__":
    main()
