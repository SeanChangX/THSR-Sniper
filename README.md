
# THSR-Sniper

```

        ________  _______ ____              _____       _                
       /_  __/ / / / ___// __ \            / ___/____  (_)___  ___  _____
        / / / /_/ /\__ \/ /_/ /  ______    \__ \/ __ \/ / __ \/ _ \/ ___/
       / / / __  /___/ / _, _/  /_____/   ___/ / / / / / /_/ /  __/ /    
      /_/ /_/ /_//____/_/ |_|            /____/_/ /_/_/ .___/\___/_/     
                                                     /_/                 

# A modern Python-based automated ticket booking system for Taiwan High Speed Rail (THSR).
# Features intelligent automation, modern CLI interface, and comprehensive booking capabilities.
```

## Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/SeanChangX/THSR-Sniper.git
cd THSR-Sniper

# Build and run
docker compose build
docker compose run --rm thsr-sniper python main.py --help
```

### Interactive Mode
Run without parameters for a guided experience:
```bash
docker compose run --rm thsr-sniper python main.py
```

### Command Line Mode
Specify all parameters directly:
```bash
docker compose run --rm thsr-sniper python main.py \
  --from 2 --to 11 --adult 1 --date 2026/01/01
```

## Command Line Options

### Personal Information
- `--id, -i` - Personal ID number (required for booking)
- `--member, -m` - Use THSR membership (y/n, true/false, 1/0)

### Journey Details
- `--from, -f` - Departure station ID (use `--stations` to see list)
- `--to, -t` - Arrival station ID (use `--stations` to see list)
- `--date, -d` - Departure date (YYYY/MM/DD, YYYY-MM-DD, or relative: +1, +2, tomorrow)
- `--time, -T` - Departure time ID (use `--times` to see list)
- `--train, -r` - Train selection index (1, 2, 3...) from available trains list

### Ticket Configuration
- `--adult, -a` - Number of adult tickets (0-10)
- `--student, -s` - Number of student tickets (0-10)
- `--seat, -p` - Seat preference: 0=any, 1=window, 2=aisle
- `--class, -c` - Class type: 0=standard, 1=business

### Information & Utilities
- `--stations` - List all available stations with IDs
- `--times` - List all available departure times with IDs
- `--no-ocr` - Disable automatic captcha OCR recognition, use manual input only

## Date Format Support

The system supports multiple date input formats:

### Absolute Dates
- `2026/01/15` (YYYY/MM/DD)
- `2026-01-15` (YYYY-MM-DD)
- `01/15/2026` (MM/DD/YYYY)
- `15/01/2026` (DD/MM/YYYY)

### Relative Dates
- `+1` - Tomorrow
- `+2` - Day after tomorrow
- `+7` - Next week
- `tomorrow` or `tmr` - Tomorrow
- `today` or `now` - Today

## Station Reference

| ID | Station | ID | Station |
|----|---------|----|---------|
| 1  | Nangang | 7  | Taichung |
| 2  | Taipei  | 8  | Changhua |
| 3  | Banqiao | 9  | Yunlin  |
| 4  | Taoyuan | 10 | Chiayi  |
| 5  | Hsinchu | 11 | Tainan  |
| 6  | Miaoli  | 12 | Zuoying |

## Time Slots

The system provides 38 time slots throughout the day, from 00:01 to 23:30. Use `--times` to see the complete list with IDs.

## Usage Examples

### Basic Booking
```bash
# Book one adult ticket from Taipei to Kaohsiung
docker compose run --rm thsr-sniper python main.py \
  --from 2 --to 11 --adult 1
```

### Advanced Booking with Train Selection
```bash
# Book with specific train index and all preferences
docker compose run --rm thsr-sniper python main.py \
  --from 1 --to 12 --date 2026/01/01 --time 10 \
  --adult 1 --seat 1 --class 0 --train 1 \
  --id A123456789 --member n
```

### Student Tickets
```bash
# Book student tickets for next week
docker compose run --rm thsr-sniper python main.py \
  --from 5 --to 7 --student 2 --date +7
```

### View Available Options
```bash
# List all stations
docker compose run --rm thsr-sniper python main.py --stations

# List all time slots
docker compose run --rm thsr-sniper python main.py --times
```

## Development

### Project Structure
```
THSR-Sniper/
├── thsr_py/                 # Core Python package
│   ├── __init__.py          # Package initialization
│   ├── cli.py               # Command line interface with colored banner
│   ├── flows.py             # Main booking logic and automation
│   └── schema.py            # Data models and constants
├── thsr_ocr/                # OCR module for captcha recognition
│   ├── captcha_ocr.py       # Captcha OCR training
│   ├── download_captcha.py  # Download captcha images
│   ├── prediction_model.py  # Convert full model to prediction-only model (without CTC layer)
│   ├── test_model.py        # Test OCR recognition flow
│   ├── datasets/            # Image processing utilities
│   └── *.keras              # Trained OCR models
├── main.py                  # Entry point
├── requirements.txt         # Python dependencies
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile               # Container definition
└── README.md                
```

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python main.py --help
```

## Technical Details

### Captcha OCR Overview

- Automatically recognizes THSR captchas, up to 3 attempts before manual input
- Uses a deep learning model (CNN+LSTM+CTC) tailored for THSR captchas
- Supports THSR-specific alphanumeric characters, input size 160x50 grayscale

## Disclaimer

**This software is provided for academic research and educational purposes only.**

- This is an unofficial implementation and is not affiliated with Taiwan High Speed Railway (THSR)
- Use at your own risk and discretion
- Users are responsible for compliance with applicable laws and regulations
- The developers assume no liability for any damages or legal issues arising from the use of this software
- This tool is intended for educational and research purposes in the field of web automation and CLI development
