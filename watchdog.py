#!/usr/bin/env python3
"""
Standalone watchdog service for THSR-Sniper scheduler.
This script can be run independently to monitor scheduled booking tasks.
"""

from thsr_py.watchdog import run_watchdog_service

if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description="THSR-Sniper Scheduler Watchdog Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start watchdog with default settings
  python watchdog.py
  
  # Start with custom monitoring interval and log file
  python watchdog.py --interval 30 --log-file /var/log/thsr-watchdog.log
  
  # Show current status only
  python watchdog.py --status
        """
    )
    
    parser.add_argument(
        "--log-file", 
        help="Log file path for watchdog output"
    )
    parser.add_argument(
        "--interval", 
        type=int, 
        default=60,
        help="Monitoring interval in seconds (default: 60)"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current status and exit"
    )
    
    args = parser.parse_args()
    
    if args.status:
        from thsr_py.watchdog import SchedulerWatchdog
        watchdog = SchedulerWatchdog()
        watchdog.status()
        sys.exit(0)
    
    try:
        print("Starting THSR-Sniper Scheduler Watchdog...")
        if args.log_file:
            print(f"Logging to: {args.log_file}")
        print(f"Monitoring interval: {args.interval} seconds")
        print("Press Ctrl+C to stop\n")
        
        run_watchdog_service(
            log_file=args.log_file,
            monitor_interval=args.interval
        )
    except KeyboardInterrupt:
        print("\nWatchdog stopped by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
