
# THSR-Sniper

```

        ________  _______ ____              _____       _                
       /_  __/ / / / ___// __ \            / ___/____  (_)___  ___  _____
        / / / /_/ /\__ \/ /_/ /  ______    \__ \/ __ \/ / __ \/ _ \/ ___/
       / / / __  /___/ / _, _/  /_____/   ___/ / / / / / /_/ /  __/ /    
      /_/ /_/ /_//____/_/ |_|            /____/_/ /_/_/ .___/\___/_/     
                                                     /_/                 

# A comprehensive automated ticket booking system for Taiwan High Speed Rail (THSR)
# Features intelligent automation, OCR captcha recognition, API server, task scheduling,
# and multi-service architecture with Docker deployment support.
```

## Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/SeanChangX/THSR-Sniper.git
cd THSR-Sniper

# Build the services (optional)
docker compose build
```

### Three Operation Modes

#### 1. Immediate Booking (CLI Mode)
Direct booking with immediate execution:
```bash
# Interactive mode (guided experience)
docker compose run --rm thsr-sniper python main.py

# Command line mode (all parameters specified)
docker compose run --rm thsr-sniper python main.py \
  --from 2 --to 11 --date 2026/01/01 --time 20 \
  --adult 1 --seat 0 --class 0 --train 1 --id A123456789 --member n
```

#### 2. Scheduled Booking (API + Scheduler)
Automated periodic booking attempts with task management:
```bash
# Start the complete system (API + Scheduler + Watchdog)
docker compose up -d

# Schedule a booking task
docker compose exec thsr-sniper python main.py --schedule \
  --from 2 --to 11 --adult 1 --date +1 --id A123456789 --member n \
  --interval 5 --max-attempts 50

# Manage tasks
docker compose exec thsr-sniper python main.py --list-tasks
docker compose exec thsr-sniper python main.py --task-status TASK_ID
docker compose exec thsr-sniper python main.py --cancel-task TASK_ID
```

#### 3. API Server Mode
RESTful API for integration and web interfaces:
```bash
# Start only the API server
docker compose up -d api

# API will be available at http://localhost:8000
# Documentation at http://localhost:8000/docs
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

### Scheduler Options (API Mode)
- `--schedule` - Schedule booking for periodic execution (requires API server)
- `--interval` - Booking attempt interval in minutes (default: 5)
- `--max-attempts` - Maximum number of booking attempts (unlimited if not specified)
- `--list-tasks` - List all scheduled booking tasks
- `--task-status TASK_ID` - Show status of a specific task
- `--cancel-task TASK_ID` - Cancel a scheduled task

### API Server Options
- `--start-api` - Start the API server for web interface and task scheduling
- `--api-host` - API server host (default: 0.0.0.0)
- `--api-port` - API server port (default: 8000)

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

## Docker Services

The system consists of three Docker services:

### `thsr-sniper` (Main CLI)
Interactive CLI for immediate booking and task management:
```bash
docker compose run --rm thsr-sniper python main.py [options]
```

### `api` (RESTful API Server)
Web API server with OpenAPI documentation:
```bash
docker compose up -d api
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### `scheduler` (Background Watchdog)
Monitors and executes scheduled booking tasks:
```bash
docker compose up -d scheduler
# Automatically manages periodic booking attempts
```

## API Endpoints

The REST API provides programmatic access to all booking features:

### Information Endpoints
- `GET /` - API information and status
- `GET /stations` - List all available stations
- `GET /times` - List all available time slots
- `GET /scheduler/status` - Scheduler status and statistics

### Booking Endpoints
- `POST /book` - Execute immediate booking (single attempt)
- `POST /schedule` - Schedule periodic booking task

### Task Management Endpoints
- `GET /tasks` - List all scheduled tasks
- `GET /tasks/{task_id}` - Get specific task status
- `DELETE /tasks/{task_id}` - Cancel a task
- `DELETE /tasks/{task_id}/remove` - Remove a task completely

### Results and Analytics
- `GET /results` - Get booking results with filtering
- `GET /results/stats` - Get booking statistics
- `GET /results/{task_id}` - Get detailed task result

## Usage Examples

### Immediate Booking Examples

#### Basic Booking
```bash
# Book one adult ticket from Taipei to Tainan
docker compose run --rm thsr-sniper python main.py \
  --from 2 --to 11 --adult 1 --id A123456789 --member n
```

#### Advanced Booking with All Options
```bash
# Book with specific train, seat preference, and business class
docker compose run --rm thsr-sniper python main.py \
  --from 1 --to 12 --date 2026/01/01 --time 10 \
  --adult 1 --seat 1 --class 1 --train 1 \
  --id A123456789 --member n
```

#### Student Tickets with Relative Dates
```bash
# Book student tickets for tomorrow
docker compose run --rm thsr-sniper python main.py \
  --from 5 --to 7 --student 2 --date +1 \
  --id A123456789 --member n
```

### Scheduled Booking Examples

#### Start the Complete System
```bash
# Start all services (API + Scheduler + Watchdog)
docker compose up -d
```

#### Schedule a Booking Task
```bash
# Schedule booking attempts every 5 minutes
docker compose exec thsr-sniper python main.py --schedule \
  --from 2 --to 11 --adult 1 --date +3 \
  --id A123456789 --member n --interval 5
```

#### Advanced Scheduled Booking
```bash
# Schedule with maximum attempts and specific preferences
docker compose exec thsr-sniper python main.py --schedule \
  --from 1 --to 12 --date 2026/01/01 --time 15 \
  --adult 2 --seat 1 --class 0 \
  --id A123456789 --member y \
  --interval 3 --max-attempts 100
```

### Task Management Examples

#### List All Tasks
```bash
docker compose exec thsr-sniper python main.py --list-tasks
```

#### Check Task Status
```bash
docker compose exec thsr-sniper python main.py --task-status abc12345-...
```

#### Cancel a Task
```bash
docker compose exec thsr-sniper python main.py --cancel-task abc12345-...
```

### API Usage Examples

#### Schedule Booking via API
```bash
curl -X POST "http://localhost:8000/schedule" \
  -H "Content-Type: application/json" \
  -d '{
    "from_station": 2,
    "to_station": 11,
    "date": "2026/01/01",
    "personal_id": "A123456789",
    "use_membership": false,
    "adult_cnt": 1,
    "interval_minutes": 5
  }'
```

#### Get Task Status via API
```bash
curl "http://localhost:8000/tasks/abc12345-..."
```

#### View Results and Statistics
```bash
# Get all results
curl "http://localhost:8000/results"

# Get statistics
curl "http://localhost:8000/results/stats"

# Filter successful bookings
curl "http://localhost:8000/results?status=success"
```

### Information and Utilities

#### View Available Options
```bash
# List all stations
docker compose run --rm thsr-sniper python main.py --stations

# List all time slots
docker compose run --rm thsr-sniper python main.py --times
```

### Results Viewer
```bash
# View booking results
python view_results.py

# View detailed results
python view_results.py --details

# View specific task result
python view_results.py --task-id abc12345-...
```

## Development

### Project Structure
```
THSR-Sniper/
├── thsr_py/                 # Core Python package
│   ├── __init__.py          # Package initialization with all modules
│   ├── api.py               # FastAPI server with RESTful endpoints
│   ├── api_client.py        # API client for CLI task management
│   ├── cli.py               # Command line interface with modern banner
│   ├── flows.py             # Main booking logic and automation flow
│   ├── scheduler.py         # Task scheduling and execution engine
│   ├── schema.py            # Data models and constants
│   └── watchdog.py          # Background service monitoring
├── thsr_ocr/                # OCR module for captcha recognition
│   ├── captcha_ocr.py       # Captcha OCR training pipeline
│   ├── download_captcha.py  # Download captcha images
│   ├── prediction_model.py  # Convert full model to prediction-only
│   ├── test_model.py        # Test OCR recognition accuracy
│   ├── datasets/            # Image processing and dataset tools
│   │   ├── image_processor.py # Image preprocessing utilities
│   │   ├── label_*.sh       # Dataset management scripts
│   │   └── 20250825*/       # Training datasets
│   └── *.keras              # Trained OCR models
├── main.py                  # Main entry point and mode router
├── watchdog.py              # Standalone watchdog service
├── view_results.py          # Results viewer and analytics tool
├── requirements.txt         # Python dependencies
├── docker-compose.yml       # Multi-service Docker configuration
├── Dockerfile               # Container definition with all dependencies
└── README.md                # This comprehensive documentation
```

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (immediate booking)
python main.py --help

# Start API server locally
python main.py --start-api

# Run watchdog service locally
python watchdog.py
```

## Technical Details

### Captcha OCR System

- **Deep Learning Architecture**: CNN+LSTM+CTC model tailored for THSR captchas
- **Automatic Recognition**: Up to 3 attempts before manual input fallback
- **Model Specifications**: 160x50 grayscale input, THSR-specific character set
- **Training Pipeline**: Includes dataset management and model conversion tools
- **Integration**: Seamlessly integrated into booking flow with error handling

### Task Scheduling Engine

- **Persistent Storage**: JSON-based task serialization with atomic writes
- **Status Tracking**: Six task states (pending/running/success/failed/expired/cancelled)
- **Retry Logic**: Configurable intervals and maximum attempt limits
- **Concurrent Execution**: Thread-safe task processing with proper locking
- **Health Monitoring**: Watchdog service with automatic restart capabilities

### API Architecture

- **FastAPI Framework**: Modern Python web framework with automatic OpenAPI docs
- **RESTful Design**: Standard HTTP methods and status codes
- **Request Validation**: Pydantic models with comprehensive input validation
- **Error Handling**: Structured error responses with detailed messages
- **CORS Support**: Cross-origin resource sharing for web integration

## Disclaimer

**This software is provided for academic research and educational purposes only.**

- This is an unofficial implementation and is not affiliated with Taiwan High Speed Railway (THSR)
- Use at your own risk and discretion
- Users are responsible for compliance with applicable laws and regulations
- The developers assume no liability for any damages or legal issues arising from the use of this software
- This tool is intended for educational and research purposes in the field of web automation and CLI development
