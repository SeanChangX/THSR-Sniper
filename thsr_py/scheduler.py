from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
import logging
import threading
import json
from pathlib import Path
import fcntl
import os

from .flows import run as run_booking_flow
from .schema import STATION_MAP, TIME_TABLE, TicketType, is_ticket_sales_open, get_taiwan_now


class BookingStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    DELETED = "deleted"
    WAITING = "waiting"


@dataclass
class BookingTask:
    id: str
    from_station: int
    to_station: int
    date: str
    user_id: Optional[str] = None
    adult_cnt: Optional[int] = None
    student_cnt: Optional[int] = None
    child_cnt: Optional[int] = None
    senior_cnt: Optional[int] = None
    disabled_cnt: Optional[int] = None
    time: Optional[int] = None
    train_index: Optional[int] = None
    seat_prefer: Optional[int] = None
    class_type: Optional[int] = None
    personal_id: Optional[str] = None
    use_membership: Optional[bool] = None
    no_ocr: bool = False
    
    # Scheduler settings
    interval_minutes: int = 5
    max_attempts: Optional[int] = None  # None means unlimited until expired
    
    # Status tracking
    status: BookingStatus = BookingStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_attempt: Optional[datetime] = None
    attempts: int = 0
    success_pnr: Optional[str] = None
    error_message: Optional[str] = None
    
    def is_expired(self) -> bool:
        """Check if the booking date has passed."""
        try:
            booking_date = datetime.strptime(self.date, "%Y/%m/%d")
            return datetime.now(timezone.utc).date() > booking_date.date()
        except ValueError:
            return False
    
    def should_stop(self) -> bool:
        """Check if task should stop (expired or max attempts reached)."""
        if self.is_expired():
            return True
        if self.max_attempts and self.attempts >= self.max_attempts:
            return True
        return False
    
    def to_args_namespace(self):
        """Convert to argparse.Namespace for compatibility with existing booking flow."""
        from argparse import Namespace
        return Namespace(
            from_=self.from_station,
            to=self.to_station,
            date=self.date,
            adult_cnt=self.adult_cnt,
            student_cnt=self.student_cnt,
            time=self.time,
            train_index=self.train_index,
            seat_prefer=self.seat_prefer,
            class_type=self.class_type,
            personal_id=self.personal_id,
            use_membership=self.use_membership,
            no_ocr=self.no_ocr,
            stations=False,
            times=False
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "from_station": self.from_station,
            "to_station": self.to_station,
            "date": self.date,
            "user_id": self.user_id,
            "adult_cnt": self.adult_cnt,
            "student_cnt": self.student_cnt,
            "child_cnt": self.child_cnt,
            "senior_cnt": self.senior_cnt,
            "disabled_cnt": self.disabled_cnt,
            "time": self.time,
            "train_index": self.train_index,
            "seat_prefer": self.seat_prefer,
            "class_type": self.class_type,
            "personal_id": self.personal_id,
            "use_membership": self.use_membership,
            "no_ocr": self.no_ocr,
            "interval_minutes": self.interval_minutes,
            "max_attempts": self.max_attempts,
            "status": self.status.value,
            "created_at": self.created_at.isoformat().replace('+00:00', 'Z'),
            "last_attempt": self.last_attempt.isoformat().replace('+00:00', 'Z') if self.last_attempt else None,
            "attempts": self.attempts,
            "success_pnr": self.success_pnr,
            "error_message": self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BookingTask":
        """Create from dictionary (JSON deserialization)."""
        task = cls(
            id=data["id"],
            from_station=data["from_station"],
            to_station=data["to_station"],
            date=data["date"],
            user_id=data.get("user_id"),
            adult_cnt=data.get("adult_cnt"),
            student_cnt=data.get("student_cnt"),
            child_cnt=data.get("child_cnt"),
            senior_cnt=data.get("senior_cnt"),
            disabled_cnt=data.get("disabled_cnt"),
            time=data.get("time"),
            train_index=data.get("train_index"),
            seat_prefer=data.get("seat_prefer"),
            class_type=data.get("class_type"),
            personal_id=data.get("personal_id"),
            use_membership=data.get("use_membership"),
            no_ocr=data.get("no_ocr", False),
            interval_minutes=data.get("interval_minutes", 5),
            max_attempts=data.get("max_attempts"),
            status=BookingStatus(data.get("status", "pending")),
            attempts=data.get("attempts", 0),
            success_pnr=data.get("success_pnr"),
            error_message=data.get("error_message")
        )
        
        if data.get("created_at"):
            created_at_str = data["created_at"]
            # Handle both Z format and raw format (assume UTC if no timezone)
            if created_at_str.endswith('Z'):
                created_at_str = created_at_str.replace('Z', '+00:00')
            elif '+' not in created_at_str and 'Z' not in created_at_str:
                # No timezone info, assume it's already UTC
                created_at_str += '+00:00'
            task.created_at = datetime.fromisoformat(created_at_str)
        if data.get("last_attempt"):
            last_attempt_str = data["last_attempt"]
            # Handle both Z format and raw format (assume UTC if no timezone)
            if last_attempt_str.endswith('Z'):
                last_attempt_str = last_attempt_str.replace('Z', '+00:00')
            elif '+' not in last_attempt_str and 'Z' not in last_attempt_str:
                # No timezone info, assume it's already UTC
                last_attempt_str += '+00:00'
            task.last_attempt = datetime.fromisoformat(last_attempt_str)
            
        return task


class BookingScheduler:
    """Main scheduler class that manages multiple booking tasks."""
    
    def __init__(self, storage_path: str = None, enable_persistence: bool = True):
        self.enable_persistence = enable_persistence
        
        if storage_path is None and enable_persistence:
            # Auto-detect storage location
            data_dir = Path("/app/data")
            if data_dir.exists():
                # Running in Docker container - use shared volume
                storage_path = "/app/data/thsr_scheduler.json"
            else:
                # Running locally - create .thsr directory in user's home
                home_dir = Path.home() / ".thsr"
                home_dir.mkdir(exist_ok=True)
                storage_path = str(home_dir / "scheduler.json")
        
        self.storage_path = Path(storage_path) if storage_path else None
        self.tasks: Dict[str, BookingTask] = {}
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.logger = self._setup_logger()
        
        # Initialize file modification time tracking
        self._last_file_mtime: Optional[float] = None
        
        # Load existing tasks if persistence is enabled
        if self.enable_persistence:
            self._load_tasks()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for the scheduler."""
        logger = logging.getLogger("thsr_scheduler")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _should_reload_tasks(self) -> bool:
        """Check if tasks should be reloaded based on file modification time."""
        if not self.enable_persistence or not self.storage_path or not self.storage_path.exists():
            return False
            
        try:
            current_mtime = self.storage_path.stat().st_mtime
            if self._last_file_mtime is None or current_mtime > self._last_file_mtime:
                self._last_file_mtime = current_mtime
                return True
            return False
        except Exception as e:
            self.logger.debug(f"Error checking file mtime: {e}")
            return True  # Reload on error to be safe

    def _load_tasks(self, force: bool = False) -> None:
        """Load tasks from storage file."""
        if not self.enable_persistence or not self.storage_path:
            return
        
        # If not forcing and we already have tasks, don't reload unless file changed
        if not force and self.tasks and not self._should_reload_tasks():
            return
            
        if self.storage_path.exists():
            # Use file locking to prevent concurrent access during read
            lock_path = self.storage_path.with_suffix('.lock')
            
            # Try to acquire lock with timeout (shorter timeout for reads)
            lock_acquired = False
            lock_fd = None
            for attempt in range(5):  # Try for up to 0.5 seconds
                try:
                    lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                    lock_acquired = True
                    break
                except FileExistsError:
                    time.sleep(0.1)  # Wait 100ms before retry
            
            try:
                # If we can't get lock, proceed without it (read operations are safer)
                if not lock_acquired:
                    self.logger.debug("Could not acquire read lock, proceeding anyway")
                
                # Check if file is empty
                if self.storage_path.stat().st_size == 0:
                    self.logger.debug("Storage file is empty, starting with no tasks")
                    return
                
                # Clear existing tasks before loading
                self.tasks.clear()
                
                with open(self.storage_path, 'r') as f:
                    content = f.read().strip()
                    if not content:
                        self.logger.debug("Storage file is empty, starting with no tasks")
                        return
                    
                    data = json.loads(content)
                    for task_data in data.get("tasks", []):
                        task = BookingTask.from_dict(task_data)
                        self.tasks[task.id] = task
                    
                self.logger.info(f"Loaded {len(self.tasks)} tasks from {self.storage_path}")
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON from storage file: {e}")
                self.logger.info("Creating backup of corrupted file and starting fresh")
                # Backup corrupted file
                backup_path = self.storage_path.with_suffix('.corrupted')
                self.storage_path.replace(backup_path)
                self.logger.info(f"Corrupted file backed up to {backup_path}")
                
            except Exception as e:
                self.logger.error(f"Failed to load tasks from storage: {e}")
                import traceback
                self.logger.debug(f"Load error traceback: {traceback.format_exc()}")
            
            finally:
                # Always release lock if acquired
                if lock_acquired and lock_fd is not None:
                    try:
                        os.close(lock_fd)
                        lock_path.unlink()
                    except:
                        pass
        else:
            self.logger.debug(f"No storage file found at {self.storage_path}, starting with empty task list")
    
    def _save_tasks(self) -> None:
        """Save tasks to storage file with simplified locking."""
        if not self.enable_persistence or not self.storage_path:
            return
            
        try:
            # Ensure parent directory exists
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "tasks": [task.to_dict() for task in self.tasks.values()],
                "last_updated": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
            
            # Write to temporary file first, then move to final location (atomic write)
            temp_path = self.storage_path.with_suffix('.tmp')
            
            # Simplified locking - try once, if fails, log warning but continue
            lock_path = self.storage_path.with_suffix('.lock')
            lock_acquired = False
            
            try:
                lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                lock_acquired = True
            except FileExistsError:
                self.logger.debug("File is locked by another process, skipping save")
                return
            
            try:
                with open(temp_path, 'w') as f:
                    json.dump(data, f, indent=2)
                
                # Atomic move
                temp_path.replace(self.storage_path)
                
                # Update our tracked modification time
                if self.storage_path.exists():
                    self._last_file_mtime = self.storage_path.stat().st_mtime
                    
                self.logger.debug(f"Tasks saved successfully to {self.storage_path}")
                
            finally:
                # Always release lock
                if lock_acquired:
                    try:
                        os.close(lock_fd)
                        lock_path.unlink()
                    except:
                        pass
                    
        except Exception as e:
            self.logger.error(f"Failed to save tasks to storage: {e}")
            import traceback
            self.logger.debug(f"Save error traceback: {traceback.format_exc()}")
    
    def add_task(self, task: BookingTask) -> str:
        """Add a new booking task."""
        if not task.id:
            task.id = str(uuid.uuid4())
        
        self.tasks[task.id] = task
        self._save_tasks()
        self.logger.info(f"Added new booking task: {task.id}")
        return task.id
    
    def get_task(self, task_id: str) -> Optional[BookingTask]:
        """Get a specific task by ID."""
        # Only reload if we don't have the task in memory
        if task_id not in self.tasks:
            self._load_tasks()
        return self.tasks.get(task_id)
    
    def list_tasks(self, force_reload: bool = False, include_deleted: bool = False) -> List[BookingTask]:
        """List all tasks, optionally excluding deleted tasks."""
        # Only reload if we have no tasks in memory, to avoid overwriting
        if not self.tasks or force_reload:
            self._load_tasks()
        
        tasks = list(self.tasks.values())
        
        # Filter out deleted tasks unless specifically requested
        if not include_deleted:
            tasks = [task for task in tasks if task.status != BookingStatus.DELETED]
        
        return tasks
    
    def cancel_task(self, task_id: str, user_id: Optional[str] = None) -> bool:
        """Cancel a specific task."""
        # Reload to get latest state
        self._load_tasks()
        if task_id in self.tasks:
            task = self.tasks[task_id]
            
            # Check user ownership if user_id is provided
            if user_id is not None and task.user_id != user_id:
                self.logger.warning(f"User {user_id} attempted to cancel task {task_id} owned by {task.user_id}")
                return False
            
            task.status = BookingStatus.CANCELLED
            self._save_tasks()
            self.logger.info(f"Cancelled task: {task_id}")
            return True
        return False
    
    def remove_task(self, task_id: str, user_id: Optional[str] = None) -> bool:
        """Mark a task as deleted instead of removing it completely."""
        # Reload to get latest state
        self._load_tasks()
        if task_id in self.tasks:
            task = self.tasks[task_id]
            
            # Check user ownership if user_id is provided
            if user_id is not None and task.user_id != user_id:
                self.logger.warning(f"User {user_id} attempted to remove task {task_id} owned by {task.user_id}")
                return False
            
            # Mark as deleted instead of removing
            task.status = BookingStatus.DELETED
            self._save_tasks()
            self.logger.info(f"Marked task as deleted: {task_id}")
            return True
        return False
    
    def start_scheduler(self) -> None:
        """Start the scheduler in a background thread."""
        if self.running:
            self.logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        self.logger.info("Scheduler started")
    
    def stop_scheduler(self) -> None:
        """Stop the scheduler."""
        self.running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        self.logger.info("Scheduler stopped")
    
    def _scheduler_loop(self) -> None:
        """Main scheduler loop that runs in background."""
        while self.running:
            try:
                self._process_tasks()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _process_tasks(self) -> None:
        """Process all pending tasks."""
        current_time = datetime.now(timezone.utc)
        
        for task in list(self.tasks.values()):
            if task.status in [BookingStatus.SUCCESS, BookingStatus.CANCELLED, BookingStatus.DELETED]:
                continue
            
            # Check if task is expired
            if task.is_expired():
                task.status = BookingStatus.EXPIRED
                self.logger.info(f"Task {task.id} expired")
                continue
            
            # Check if task should stop
            if task.should_stop():
                task.status = BookingStatus.FAILED
                task.error_message = "Maximum attempts reached"
                self.logger.info(f"Task {task.id} stopped after {task.attempts} attempts")
                continue
            
            # Check if ticket sales are open for future booking dates
            if not is_ticket_sales_open(task.date):
                if task.status != BookingStatus.WAITING:
                    task.status = BookingStatus.WAITING
                    self.logger.info(f"Task {task.id} waiting for ticket sales to open at 00:00 Taiwan time")
                continue
            
            # If task was waiting and ticket sales are now open, change to pending
            if task.status == BookingStatus.WAITING:
                task.status = BookingStatus.PENDING
                self.logger.info(f"Task {task.id} ticket sales now open, resuming booking attempts")
            
            # Check if it's time to run this task
            if task.last_attempt is None:
                should_run = True
            else:
                # Ensure both datetimes are timezone-aware for comparison
                task_last_attempt = task.last_attempt
                if task_last_attempt.tzinfo is None:
                    task_last_attempt = task_last_attempt.replace(tzinfo=timezone.utc)
                
                time_since_last = current_time - task_last_attempt
                should_run = time_since_last >= timedelta(minutes=task.interval_minutes)
            
            if should_run:
                self._execute_booking_task(task)
        
        # Periodically clean up old deleted tasks (every hour)
        self._cleanup_deleted_tasks(current_time)
        
        # Only save if there were any changes in this cycle
        # _execute_booking_task already saves its changes, so we don't need to save again
        # This prevents unnecessary merge conflicts
        # self._save_tasks_safe()  # Commented out to prevent SUCCESS status overwrites
    
    def _cleanup_deleted_tasks(self, current_time: datetime) -> None:
        """Clean up tasks that have been marked as deleted for more than 1 hour."""
        if not hasattr(self, '_last_cleanup_time'):
            self._last_cleanup_time = current_time
            return
        
        # Only run cleanup once per hour
        if current_time - self._last_cleanup_time < timedelta(hours=1):
            return
        
        self._last_cleanup_time = current_time
        
        # Remove tasks that have been deleted for more than 1 hour
        deleted_cutoff = current_time - timedelta(hours=1)
        tasks_to_remove = []
        
        for task_id, task in self.tasks.items():
            if (task.status == BookingStatus.DELETED and 
                task.last_attempt and task.last_attempt < deleted_cutoff):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            self.logger.debug(f"Permanently removed deleted task: {task_id}")
        
        if tasks_to_remove:
            self.logger.info(f"Cleaned up {len(tasks_to_remove)} old deleted tasks")
    
    def _save_tasks_safe(self) -> None:
        """Save tasks with conflict detection."""
        if not self.enable_persistence or not self.storage_path:
            return
            
        # Check if file was modified by another process since our last load
        if self._should_reload_tasks():
            self.logger.debug("File was modified by another process, merging changes before save")
            # Load the latest state
            current_tasks = dict(self.tasks)  # Save our current state
            self._load_tasks(force=True)      # Load latest from file
            
            # Merge our changes back - prioritize completed tasks and recent updates
            for task_id, task in current_tasks.items():
                if task_id in self.tasks:
                    existing_task = self.tasks[task_id]
                    
                    # ALWAYS preserve completed tasks (SUCCESS, CANCELLED, DELETED)
                    if task.status in [BookingStatus.SUCCESS, BookingStatus.CANCELLED, BookingStatus.DELETED]:
                        self.tasks[task_id] = task
                        self.logger.debug(f"Preserved completed task {task_id} status: {task.status.value}")
                    # For other tasks, keep our version if it's more recent or has more attempts
                    elif (task.last_attempt and existing_task.last_attempt and 
                        task.last_attempt > existing_task.last_attempt) or \
                       task.attempts > existing_task.attempts:
                        self.tasks[task_id] = task
                else:
                    # Add new task that doesn't exist in file
                    self.tasks[task_id] = task
        
        self._save_tasks()
    
    def _execute_booking_task(self, task: BookingTask) -> None:
        """Execute a single booking task."""
        # Store original values for rollback if needed
        original_status = task.status
        original_attempts = task.attempts
        original_last_attempt = task.last_attempt
        
        # Update task status and attempt info with timezone-aware datetime
        task.status = BookingStatus.RUNNING
        task.last_attempt = datetime.now(timezone.utc)
        task.attempts += 1
        
        self.logger.info(f"Executing task {task.id} (attempt {task.attempts})")
        
        # Save immediately after updating attempt count
        try:
            self._save_tasks()
        except Exception as save_error:
            self.logger.error(f"Failed to save task state before execution: {save_error}")

        # Store environment variable for restoration
        original_non_interactive = None
        
        try:
            # Convert task to args namespace
            args = task.to_args_namespace()
            
            # Capture the booking flow output to detect success
            import io
            import sys
            import os
            from contextlib import redirect_stdout, redirect_stderr
            
            # Set environment variable to indicate non-interactive mode
            original_non_interactive = os.environ.get('THSR_NON_INTERACTIVE')
            os.environ['THSR_NON_INTERACTIVE'] = '1'
            
            # Create string buffers to capture output
            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()
            
            # Redirect stdout and stderr to capture output
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                run_booking_flow(args)
            
            # Check if booking was successful by looking for PNR in output
            output = stdout_buffer.getvalue()
            stderr_output = stderr_buffer.getvalue()
            
            self.logger.debug(f"Task {task.id} output length: stdout={len(output)}, stderr={len(stderr_output)}")
            
            if "PNR Code:" in output:
                # Extract PNR code
                lines = output.split('\n')
                for line in lines:
                    if "PNR Code:" in line:
                        pnr = line.split("PNR Code:")[-1].strip()
                        # Clean ANSI color codes from PNR
                        import re
                        pnr = re.sub(r'\033\[[0-9;]*m', '', pnr).strip()
                        task.success_pnr = pnr
                        break
                
                task.status = BookingStatus.SUCCESS
                self.logger.info(f"Task {task.id} completed successfully! PNR: {task.success_pnr}")
                self.logger.info(f"Task {task.id} STATUS SET TO SUCCESS - about to save...")
            else:
                # Check for error messages in output
                if stderr_output:
                    task.error_message = stderr_output.strip()[:500]  # Limit error message length
                elif "Error" in output or "error" in output.lower():
                    # Look for error patterns in stdout
                    error_lines = [line for line in output.split('\n') if 'error' in line.lower() or 'Error' in line]
                    if error_lines:
                        task.error_message = '; '.join(error_lines[:3])[:500]
                    else:
                        task.error_message = "Booking failed - no PNR code found"
                else:
                    task.error_message = "Booking failed - no PNR code found"
                
                # Only set to PENDING if task is not already SUCCESS (shouldn't happen but safety check)
                if task.status != BookingStatus.SUCCESS:
                    task.status = BookingStatus.PENDING  # Will retry on next cycle
                self.logger.warning(f"Task {task.id} attempt {task.attempts} failed: {task.error_message}")
            
        except Exception as e:
            # Only override status if it's not already SUCCESS
            if task.status != BookingStatus.SUCCESS:
                task.error_message = f"Booking execution error: {str(e)}"[:500]
                task.status = BookingStatus.PENDING  # Will retry on next cycle
            self.logger.error(f"Task {task.id} failed with exception: {e}")
            import traceback
            self.logger.debug(f"Task {task.id} traceback: {traceback.format_exc()}")
        
        finally:
            # Restore original environment variable
            if original_non_interactive is None:
                os.environ.pop('THSR_NON_INTERACTIVE', None)
            else:
                os.environ['THSR_NON_INTERACTIVE'] = original_non_interactive
                
            # Always save the final state
            try:
                self.logger.info(f"Task {task.id} FINAL SAVE - status={task.status.value}, pnr={task.success_pnr}")
                # Save the task state
                self._save_tasks()
                self.logger.info(f"Task {task.id} SAVE COMPLETED - status={task.status.value}, attempts={task.attempts}")
            except Exception as save_error:
                self.logger.error(f"Failed to save task state after execution: {save_error}")


# Global scheduler instance
_scheduler_instance: Optional[BookingScheduler] = None


def get_scheduler() -> BookingScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        # Check if we're running in the API service
        # API service should only read, not write to avoid conflicts
        import os
        is_api_service = os.environ.get('THSR_API_MODE') == '1'
        
        if is_api_service:
            # API service uses read-write mode with shared storage
            _scheduler_instance = BookingScheduler(enable_persistence=True)
            # Load tasks from shared storage
            _scheduler_instance._load_tasks(force=True)
        else:
            # Normal scheduler service with full read/write
            _scheduler_instance = BookingScheduler()
        
        # Tasks are already loaded in __init__ or above
    # Don't reload automatically - let individual methods decide
    return _scheduler_instance


def create_booking_task(
    from_station: int,
    to_station: int,
    date: str,
    personal_id: str,
    use_membership: bool,
    user_id: Optional[str] = None,
    adult_cnt: Optional[int] = None,
    student_cnt: Optional[int] = None,
    child_cnt: Optional[int] = None,
    senior_cnt: Optional[int] = None,
    disabled_cnt: Optional[int] = None,
    time: Optional[int] = None,
    train_index: Optional[int] = None,
    seat_prefer: Optional[int] = None,
    class_type: Optional[int] = None,
    interval_minutes: int = 5,
    max_attempts: Optional[int] = None,
    no_ocr: bool = False,  # Default to False to enable OCR for automated booking
    **kwargs
) -> BookingTask:
    """Create a new booking task with validation for real booking scenarios."""
    
    # Validate required parameters for real booking
    if not personal_id or not personal_id.strip():
        raise ValueError("Personal ID is required for booking")
    
    if use_membership is None:
        raise ValueError("Membership preference must be specified (True/False)")
    
    # Validate stations
    if not 1 <= from_station <= len(STATION_MAP):
        raise ValueError(f"Invalid from_station: {from_station} (must be 1-{len(STATION_MAP)})")
    if not 1 <= to_station <= len(STATION_MAP):
        raise ValueError(f"Invalid to_station: {to_station} (must be 1-{len(STATION_MAP)})")
    
    if from_station == to_station:
        raise ValueError("Departure and arrival stations cannot be the same")
    
    # Validate date format and future date
    try:
        booking_date = datetime.strptime(date, "%Y/%m/%d")
        if booking_date.date() < datetime.now(timezone.utc).date():
            raise ValueError(f"Booking date must be in the future: {date}")
    except ValueError as e:
        if "does not match format" in str(e):
            raise ValueError(f"Invalid date format (use YYYY/MM/DD): {date}")
        raise e
    
    # Validate ticket counts - require at least one ticket
    total_tickets = (adult_cnt or 0) + (student_cnt or 0) + (child_cnt or 0) + (senior_cnt or 0) + (disabled_cnt or 0)
    if total_tickets == 0:
        raise ValueError("At least one ticket must be specified")
    if total_tickets > 10:
        raise ValueError("Total ticket count cannot exceed 10")
    
    if adult_cnt is not None and not 0 <= adult_cnt <= 10:
        raise ValueError(f"Adult ticket count must be 0-10: {adult_cnt}")
    if student_cnt is not None and not 0 <= student_cnt <= 10:
        raise ValueError(f"Student ticket count must be 0-10: {student_cnt}")
    if child_cnt is not None and not 0 <= child_cnt <= 10:
        raise ValueError(f"Child ticket count must be 0-10: {child_cnt}")
    if senior_cnt is not None and not 0 <= senior_cnt <= 10:
        raise ValueError(f"Senior ticket count must be 0-10: {senior_cnt}")
    if disabled_cnt is not None and not 0 <= disabled_cnt <= 10:
        raise ValueError(f"Disabled ticket count must be 0-10: {disabled_cnt}")
    
    # Validate optional parameters
    if time is not None and not 1 <= time <= len(TIME_TABLE):
        raise ValueError(f"Invalid time slot: {time} (must be 1-{len(TIME_TABLE)})")
    
    if train_index is not None and train_index < 1:
        raise ValueError(f"Invalid train index: {train_index} (must be >= 1)")
    
    if seat_prefer is not None and seat_prefer not in [0, 1, 2]:
        raise ValueError(f"Invalid seat preference: {seat_prefer} (must be 0, 1, or 2)")
    
    if class_type is not None and class_type not in [0, 1]:
        raise ValueError(f"Invalid class type: {class_type} (must be 0 or 1)")
    
    # Validate interval
    if interval_minutes < 1:
        raise ValueError(f"Interval must be at least 1 minute: {interval_minutes}")
    if interval_minutes > 60:
        raise ValueError(f"Interval should not exceed 60 minutes: {interval_minutes}")
    
    # Validate personal ID format (basic check)
    personal_id = personal_id.strip().upper()
    if len(personal_id) != 10:
        raise ValueError("Personal ID must be 10 characters long")
    
    task = BookingTask(
        id=str(uuid.uuid4()),
        from_station=from_station,
        to_station=to_station,
        date=date,
        user_id=user_id,
        personal_id=personal_id,
        use_membership=use_membership,
        adult_cnt=adult_cnt,
        student_cnt=student_cnt,
        child_cnt=child_cnt,
        senior_cnt=senior_cnt,
        disabled_cnt=disabled_cnt,
        time=time,
        train_index=train_index,
        seat_prefer=seat_prefer,
        class_type=class_type,
        interval_minutes=interval_minutes,
        max_attempts=max_attempts,
        no_ocr=no_ocr,  # Force no OCR for automated execution
        **kwargs
    )
    
    return task
