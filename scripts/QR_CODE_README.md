# QR Code Registration

This directory contains a script to generate QR codes for simplified user registration within the institute.

## Overview

The QR code registration system allows users to register without manually entering the magic word. This is useful when users are physically present at the institute and can scan a displayed QR code.

### How It Works

1. **Admin generates a QR code** containing the magic word using the `generate_qr_code.py` script
2. **QR code is displayed** at the institute (printed poster, digital display, etc.)
3. **User scans the QR code** with their phone
4. **User is directed to the registration page** (if URL mode is used) or gets the magic word
5. **User completes registration** using the new `/auth/register-qr` endpoint

## Installation

First, install the required Python package:

```bash
pip install qrcode[pil]
```

## Usage

### Basic Usage (Magic Word Only)

Generate a simple QR code containing just the magic word:

```bash
python scripts/generate_qr_code.py "YourMagicWord123"
```

This creates `registration_qr.png` in the current directory.

### Advanced Usage (URL with Magic Word)

Generate a QR code with a full URL to your registration page:

```bash
python scripts/generate_qr_code.py "YourMagicWord123" --url "https://priotag.example.com"
```

This creates a QR code that, when scanned, opens: `https://priotag.example.com/register?magic=YourMagicWord123`

### Customize Output

```bash
# Custom output filename
python scripts/generate_qr_code.py "YourMagicWord123" --output institute_qr.png

# Larger QR code with high error correction
python scripts/generate_qr_code.py "YourMagicWord123" --size 20 --error-correction H

# All options combined
python scripts/generate_qr_code.py "YourMagicWord123" \
    --url "https://priotag.example.com" \
    --output registration_poster.png \
    --size 15 \
    --border 6 \
    --error-correction H
```

## Script Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--output` | `-o` | Output file path | `registration_qr.png` |
| `--url` | `-u` | Base URL of frontend (optional) | None |
| `--size` | `-s` | Size of each box in pixels | 10 |
| `--border` | `-b` | Border size in boxes | 4 |
| `--error-correction` | `-e` | Error correction level (L/M/Q/H) | M |

### Error Correction Levels

- **L**: ~7% - Use for small QR codes in good conditions
- **M**: ~15% - Good balance (recommended)
- **Q**: ~25% - Better error recovery
- **H**: ~30% - Best for codes that may be damaged or partially obscured

## Backend API Endpoint

The new `/auth/register-qr` endpoint accepts:

```json
{
  "identity": "username",
  "password": "password",
  "passwordConfirm": "password",
  "name": "Child's Name",
  "magic_word": "YourMagicWord123",
  "keep_logged_in": false
}
```

This endpoint:
1. ✓ Validates the magic word
2. ✓ Applies rate limiting (10 attempts per IP per hour)
3. ✓ Creates the user account
4. ✓ Auto-logs in the user
5. ✓ Sets authentication cookies
6. ✓ Returns success response

## Frontend Integration

### Option 1: Manual Entry

If using magic word only mode, users can:
1. Scan the QR code
2. Copy the magic word
3. Paste it into the registration form

### Option 2: URL with Query Parameter (Recommended)

The frontend can be updated to:
1. Read the `magic` query parameter from the URL
2. Auto-fill the magic word field
3. Call the `/auth/register-qr` endpoint instead of the two-step process

Example URL structure:
```
https://priotag.example.com/register?magic=YourMagicWord123
```

## Example Workflow

1. Admin updates the magic word via admin panel
2. Admin generates a new QR code:
   ```bash
   python scripts/generate_qr_code.py "NewMagicWord456" \
       --url "https://priotag.example.com" \
       --output qr_codes/current_registration.png \
       --size 15 \
       --error-correction H
   ```
3. QR code is displayed on a poster/screen at the institute
4. Users scan and register easily

## Security Considerations

- The QR code should only be displayed in secure, controlled locations (within the institute)
- Consider regenerating the magic word and QR code periodically
- The same rate limiting applies as the normal magic word verification
- QR codes are saved with metadata files (`.json`) for your records

## Metadata Files

The script automatically saves metadata alongside the QR code:

```json
{
  "magic_word": "YourMagicWord123",
  "url": "https://priotag.example.com/register?magic=YourMagicWord123",
  "output_file": "registration_qr.png",
  "box_size": 10,
  "border": 4,
  "error_correction": "M"
}
```

This helps you track which QR codes were generated and with what settings.

## Tips

- **Print Size**: For posters, use `--size 20` or higher
- **Digital Displays**: Standard size (`--size 10`) works well
- **Damaged Codes**: Use `--error-correction H` if the code might be partially obscured
- **File Format**: The script generates PNG files which work well for both print and digital use
