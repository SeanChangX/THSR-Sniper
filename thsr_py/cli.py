from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta


def _get_colored_banner() -> str:
    """Get colored ASCII art banner for the CLI."""
    # Check if we're in a terminal that supports colors
    if os.environ.get('TERM') and '256' in os.environ.get('TERM', ''):
        # ANSI color codes for 256-color terminals - using THSR theme color #ca4f0f
        thsr_red = '\033[38;5;166m'  # Close to #ca4f0f
        thsr_dark = '\033[38;5;124m'  # Darker variant
        accent = '\033[38;5;220m'     # Yellow accent
        reset = '\033[0m'
        
        banner = f"""{thsr_red}╔══════════════════════════════════════════════════════════════════════════════╗{reset}
{thsr_red}║       ________  _______ ____              _____       _                      ║{reset}
{thsr_red}║      /_  __/ / / / ___// __ \\            / ___/____  (_)___  ___  _____      ║{reset}
{thsr_red}║       / / / /_/ /\\__ \\/ /_/ /  ______    \\__ \\/ __ \\/ / __ \\/ _ \\/ ___/      ║{reset}
{thsr_red}║      / / / __  /___/ / _, _/  /_____/   ___/ / / / / / /_/ /  __/ /          ║{reset}
{thsr_red}║     /_/ /_/ /_//____/_/ |_|            /____/_/ /_/_/ .___/\\___/_/           ║{reset}
{thsr_red}║                                                    /_/                       ║{reset}
{thsr_red}║                                                                              ║{reset}
{thsr_red}║                    Taiwan High Speed Rail Ticket Sniper                      ║{reset}
{thsr_red}║                                                                              ║{reset}
{thsr_red}║    A modern CLI tool for booking THSR tickets with intelligent automation.   ║{reset}
{thsr_red}║    Features automatic captcha recognition and comprehensive booking flow.    ║{reset}
{thsr_red}║                                                                              ║{reset}
{thsr_red}╚══════════════════════════════════════════════════════════════════════════════╝{reset}
        """
    else:
        # Fallback for terminals without color support
        banner = r"""
╔══════════════════════════════════════════════════════════════════════════════╗
║       ________  _______ ____              _____       _                      ║
║      /_  __/ / / / ___// __ \            / ___/____  (_)___  ___  _____      ║
║       / / / /_/ /\__ \/ /_/ /  ______    \__ \/ __ \/ / __ \/ _ \/ ___/      ║
║      / / / __  /___/ / _, _/  /_____/   ___/ / / / / / /_/ /  __/ /          ║
║     /_/ /_/ /_//____/_/ |_|            /____/_/ /_/_/ .___/\___/_/           ║
║                                                    /_/                       ║
║                                                                              ║
║                    Taiwan High Speed Rail Ticket Sniper                      ║
║                                                                              ║
║    A modern CLI tool for booking THSR tickets with intelligent automation.   ║
║    Features automatic captcha recognition and comprehensive booking flow.    ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """
    
    return banner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="thsr",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=_get_colored_banner(),
        epilog="""
Examples:
  # Interactive mode
  python main.py

  # Quick booking (immediate)
  python main.py --from 2 --to 11 --adult 1 --date 2026/01/01

  # Scheduled booking (requires API server running)
  python main.py --schedule --from 2 --to 11 --adult 1 --date +1 \
                 --id A123456789 --member n --interval 5

  # Task management (requires API server running)
  python main.py --list-tasks
  python main.py --task-status TASK_ID
  python main.py --cancel-task TASK_ID

  # View options
  python main.py --stations
  python main.py --times

  # Start API server
  python main.py --start-api --api-port 8000

  # Advanced booking
  python main.py --from 1 --to 12 --date 2026/01/01 --time 10
                 --adult 1 --seat 1 --class 0 --train 1
                 --id A123456789 --member n

  # Watchdog service (standalone)
  python watchdog.py
        """
    )

    # Personal information
    personal_group = parser.add_argument_group("Personal Information")
    personal_group.add_argument(
        "--id", "-i", 
        dest="personal_id", 
        help="Personal ID number (required for booking)"
    )
    personal_group.add_argument(
        "--member", "-m", 
        dest="use_membership", 
        help="Use membership (y/n, true/false, 1/0)"
    )

    # Journey details
    journey_group = parser.add_argument_group("Journey Details")
    journey_group.add_argument(
        "--from", "-f", 
        dest="from_", 
        type=int, 
        help="Departure station ID (use --stations to see list)"
    )
    journey_group.add_argument(
        "--to", "-t", 
        dest="to", 
        type=int, 
        help="Arrival station ID (use --stations to see list)"
    )
    journey_group.add_argument(
        "--date", "-d", 
        help="Departure date (YYYY/MM/DD, YYYY-MM-DD, or relative: +1, +2, tomorrow)"
    )
    journey_group.add_argument(
        "--time", "-T", 
        dest="time", 
        type=int, 
        help="Departure time ID (use --times to see list)"
    )
    journey_group.add_argument(
        "--train", "-r",
        dest="train_index",
        type=int,
        help="Train selection index (1, 2, 3...) from the available trains list"
    )

    # Ticket configuration
    ticket_group = parser.add_argument_group("Ticket Configuration")
    ticket_group.add_argument(
        "--adult", "-a", 
        dest="adult_cnt", 
        type=int, 
        help="Number of adult tickets (0-10)"
    )
    ticket_group.add_argument(
        "--student", "-s", 
        dest="student_cnt", 
        type=int, 
        help="Number of student tickets (0-10)"
    )
    ticket_group.add_argument(
        "--seat",
        "-p",
        dest="seat_prefer",
        type=int,
        choices=[0, 1, 2],
        help="Seat preference: 0=any, 1=window, 2=aisle"
    )
    ticket_group.add_argument(
        "--class",
        "-c",
        dest="class_type",
        type=int,
        choices=[0, 1],
        help="Class type: 0=standard, 1=business"
    )

    # Scheduler options (via API)
    scheduler_group = parser.add_argument_group("Scheduler Options")
    scheduler_group.add_argument(
        "--schedule",
        action="store_true",
        help="Schedule booking for periodic execution (via API)"
    )
    scheduler_group.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Booking attempt interval in minutes (default: 5)"
    )
    scheduler_group.add_argument(
        "--max-attempts",
        dest="max_attempts",
        type=int,
        help="Maximum number of booking attempts (unlimited if not specified)"
    )
    scheduler_group.add_argument(
        "--list-tasks",
        action="store_true",
        help="List all scheduled booking tasks (via API)"
    )
    scheduler_group.add_argument(
        "--task-status",
        dest="task_status",
        help="Show status of a specific task by ID (via API)"
    )
    scheduler_group.add_argument(
        "--cancel-task",
        dest="cancel_task",
        help="Cancel a scheduled task by ID (via API)"
    )

    # API Server options
    api_group = parser.add_argument_group("API Server Options")
    api_group.add_argument(
        "--start-api",
        action="store_true",
        help="Start the API server for web interface and task scheduling"
    )
    api_group.add_argument(
        "--api-host",
        dest="api_host",
        default="0.0.0.0",
        help="API server host (default: 0.0.0.0)"
    )
    api_group.add_argument(
        "--api-port",
        dest="api_port",
        type=int,
        default=8000,
        help="API server port (default: 8000)"
    )

    # Information and utilities
    info_group = parser.add_argument_group("Information & Utilities")
    info_group.add_argument(
        "--stations", 
        action="store_true", 
        help="List all available stations with IDs"
    )
    info_group.add_argument(
        "--times", 
        action="store_true", 
        help="List all available departure times with IDs"
    )
    info_group.add_argument(
        "--no-ocr",
        action="store_true",
        help="Disable automatic captcha OCR recognition, use manual input only"
    )

    args = parser.parse_args()

    # Process date input for modern CLI format
    if args.date:
        args.date = _parse_date_input(args.date)

    # Normalize membership values
    if isinstance(args.use_membership, str):
        lm = args.use_membership.strip().lower()
        if lm in ("true", "1", "y", "yes"):
            args.use_membership = True
        elif lm in ("false", "0", "n", "no"):
            args.use_membership = False
        else:
            args.use_membership = None

    return args


def _parse_date_input(date_input: str) -> str:
    """Parse modern CLI date formats including relative dates."""
    date_input = date_input.strip()
    
    # Handle relative dates
    if date_input.startswith("+"):
        try:
            days = int(date_input[1:])
            target_date = datetime.now() + timedelta(days=days)
            return target_date.strftime("%Y/%m/%d")
        except ValueError:
            pass
    elif date_input.lower() in ["tomorrow", "tmr"]:
        target_date = datetime.now() + timedelta(days=1)
        return target_date.strftime("%Y/%m/%d")
    elif date_input.lower() in ["today", "now"]:
        return datetime.now().strftime("%Y/%m/%d")
    
    # Handle various date formats
    date_formats = [
        "%Y/%m/%d", "%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d",
        "%m/%d/%Y", "%m-%d-%Y", "%d/%m/%Y", "%d-%m-%Y"
    ]
    
    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(date_input, fmt)
            return parsed_date.strftime("%Y/%m/%d")
        except ValueError:
            continue
    
    # If no format matches, return as-is (will be validated later)
    return date_input
