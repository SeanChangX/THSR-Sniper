from __future__ import annotations

import signal
import sys
import time
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .scheduler import get_scheduler, BookingStatus


class SchedulerWatchdog:
    """
    Watchdog service that monitors and manages the booking scheduler.
    Provides a daemon-like service with status monitoring and automatic restart.
    """
    
    def __init__(self, log_file: Optional[str] = None):
        self.scheduler = get_scheduler()
        self.running = False
        self.log_file = log_file
        self.logger = self._setup_logger()
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for the watchdog service."""
        logger = logging.getLogger("thsr_watchdog")
        logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler if log file specified
        if self.log_file:
            try:
                file_handler = logging.FileHandler(self.log_file)
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)
                logger.info(f"Logging to file: {self.log_file}")
            except Exception as e:
                logger.warning(f"Failed to setup file logging: {e}")
        
        return logger
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def start(self, monitor_interval: int = 60) -> None:
        """
        Start the watchdog service.
        
        Args:
            monitor_interval: Interval in seconds between status checks
        """
        if self.running:
            self.logger.warning("Watchdog is already running")
            return
        
        self.running = True
        self.logger.info("Starting THSR Scheduler Watchdog")
        
        # Start the scheduler if not already running
        if not self.scheduler.running:
            self.scheduler.start_scheduler()
            self.logger.info("Started booking scheduler")
        
        # Display initial status
        self._print_startup_status()
        
        # Main monitoring loop
        last_status_time = datetime.now()
        status_report_interval = timedelta(minutes=30)  # Report status every 30 minutes
        
        try:
            while self.running:
                current_time = datetime.now()
                
                # Monitor scheduler health
                if not self.scheduler.running:
                    self.logger.warning("Scheduler appears to be stopped, restarting...")
                    self.scheduler.start_scheduler()
                
                # Periodic status report
                if current_time - last_status_time >= status_report_interval:
                    self._report_status()
                    last_status_time = current_time
                
                # Check for expired tasks and cleanup
                self._cleanup_expired_tasks()
                
                # Sleep for the monitoring interval
                time.sleep(monitor_interval)
                
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Watchdog error: {e}")
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop the watchdog service gracefully."""
        if not self.running:
            return
        
        self.running = False
        self.logger.info("Stopping watchdog service...")
        
        # Stop the scheduler
        if self.scheduler.running:
            self.scheduler.stop_scheduler()
            self.logger.info("Stopped booking scheduler")
        
        self.logger.info("Watchdog service stopped")
    
    def _print_startup_status(self) -> None:
        """Print startup status information."""
        tasks = self.scheduler.list_tasks()
        active_tasks = [t for t in tasks if t.status in [BookingStatus.PENDING, BookingStatus.RUNNING]]
        
        print(f"\n{'='*60}")
        print(f"  THSR Scheduler Watchdog Started")
        print(f"{'='*60}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Tasks: {len(tasks)}")
        print(f"Active Tasks: {len(active_tasks)}")
        print(f"Storage: {self.scheduler.storage_path}")
        
        if active_tasks:
            print(f"\nActive Booking Tasks:")
            for task in active_tasks[:5]:  # Show first 5
                from .schema import STATION_MAP
                route = f"{STATION_MAP[task.from_station-1]} -> {STATION_MAP[task.to_station-1]}"
                print(f"  {task.id[:8]}... | {route} | {task.date} | Every {task.interval_minutes}m")
            
            if len(active_tasks) > 5:
                print(f"  ... and {len(active_tasks) - 5} more")
        
        print(f"\nWatchdog is monitoring scheduler...")
        print(f"Press Ctrl+C to stop")
        print(f"{'='*60}\n")
    
    def _report_status(self) -> None:
        """Generate periodic status report."""
        tasks = self.scheduler.list_tasks()
        
        # Count tasks by status
        status_counts = {}
        for status in BookingStatus:
            count = sum(1 for task in tasks if task.status == status)
            if count > 0:
                status_counts[status.value] = count
        
        # Find recent activity
        recent_cutoff = datetime.now() - timedelta(hours=1)
        # Ensure timezone compatibility for comparison
        recent_tasks = []
        for t in tasks:
            if t.last_attempt:
                task_last_attempt = t.last_attempt
                # Make timezone-aware if needed
                if task_last_attempt.tzinfo is None:
                    task_last_attempt = task_last_attempt.replace(tzinfo=timezone.utc)
                # Make cutoff timezone-aware 
                if recent_cutoff.tzinfo is None:
                    recent_cutoff = recent_cutoff.replace(tzinfo=timezone.utc)
                if task_last_attempt > recent_cutoff:
                    recent_tasks.append(t)
        
        self.logger.info(f"Status Report - Total: {len(tasks)}, Status: {status_counts}, Recent activity: {len(recent_tasks)} tasks")
        
        # Log successful bookings
        successful_tasks = [t for t in tasks if t.status == BookingStatus.SUCCESS and t.success_pnr]
        if successful_tasks:
            self.logger.info(f"Successful bookings: {len(successful_tasks)} tasks with PNR codes")
    
    def _cleanup_expired_tasks(self) -> None:
        """Automatically mark expired tasks."""
        tasks = self.scheduler.list_tasks()
        expired_count = 0
        
        for task in tasks:
            if task.status in [BookingStatus.PENDING, BookingStatus.RUNNING] and task.is_expired():
                task.status = BookingStatus.EXPIRED
                expired_count += 1
                self.logger.info(f"Marked task {task.id[:8]}... as expired (date: {task.date})")
        
        if expired_count > 0:
            self.scheduler._save_tasks()  # Save the status changes
    
    def status(self) -> None:
        """Display current status (non-blocking)."""
        tasks = self.scheduler.list_tasks()
        print(f"Scheduler Status: {'RUNNING' if self.scheduler.running else 'STOPPED'}")
        print(f"Total Tasks: {len(tasks)}")
        print(f"Storage: {self.scheduler.storage_path}")
        
        if tasks:
            status_counts = {}
            for status in BookingStatus:
                count = sum(1 for task in tasks if task.status == status)
                if count > 0:
                    status_counts[status.value] = count
            print(f"Status Breakdown: {status_counts}")
        else:
            print("No scheduled tasks found.")


def run_watchdog_service(
    log_file: Optional[str] = None,
    monitor_interval: int = 60
) -> None:
    """
    Run the watchdog service as a standalone daemon.
    
    Args:
        log_file: Optional log file path
        monitor_interval: Monitoring interval in seconds
    """
    watchdog = SchedulerWatchdog(log_file=log_file)
    
    try:
        watchdog.start(monitor_interval=monitor_interval)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        watchdog.logger.error(f"Watchdog service failed: {e}")
        sys.exit(1)


def start_background_watchdog() -> None:
    """Start watchdog in background mode (non-blocking)."""
    import threading
    
    def background_watchdog():
        watchdog = SchedulerWatchdog()
        watchdog.start(monitor_interval=120)  # Check every 2 minutes in background
    
    watchdog_thread = threading.Thread(target=background_watchdog, daemon=True)
    watchdog_thread.start()
    print("✓ Background watchdog started")


if __name__ == "__main__":
    # Simple command line interface for the watchdog
    import argparse
    
    parser = argparse.ArgumentParser(description="THSR Scheduler Watchdog Service")
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
        watchdog = SchedulerWatchdog()
        watchdog.status()
    else:
        run_watchdog_service(
            log_file=args.log_file,
            monitor_interval=args.interval
        )
