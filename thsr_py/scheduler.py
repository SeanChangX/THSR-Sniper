from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
import logging
import threading
import json
from pathlib import Path

from .flows import run as run_booking_flow
from .schema import STATION_MAP, TIME_TABLE, TicketType


class BookingStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class BookingTask:
    id: str
    from_station: int
    to_station: int
    date: str
    adult_cnt: Optional[int] = None
    student_cnt: Optional[int] = None
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
    created_at: datetime = field(default_factory=datetime.now)
    last_attempt: Optional[datetime] = None
    attempts: int = 0
    success_pnr: Optional[str] = None
    error_message: Optional[str] = None
    
    def is_expired(self) -> bool:
        """Check if the booking date has passed."""
        try:
            booking_date = datetime.strptime(self.date, "%Y/%m/%d")
            return datetime.now().date() > booking_date.date()
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
            "adult_cnt": self.adult_cnt,
            "student_cnt": self.student_cnt,
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
            "created_at": self.created_at.isoformat(),
            "last_attempt": self.last_attempt.isoformat() if self.last_attempt else None,
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
            adult_cnt=data.get("adult_cnt"),
            student_cnt=data.get("student_cnt"),
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
            task.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("last_attempt"):
            task.last_attempt = datetime.fromisoformat(data["last_attempt"])
            
        return task


class BookingScheduler:
    """Main scheduler class that manages multiple booking tasks."""
    
    def __init__(self, storage_path: str = None, enable_persistence: bool = True):
        self.enable_persistence = enable_persistence
        
        if storage_path is None and enable_persistence:
            # Auto-detect storage location
            data_dir = Path("/app/data")
            if data_dir.exists():
                # Running in Docker container
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
    
    def _load_tasks(self) -> None:
        """Load tasks from storage file."""
        if not self.enable_persistence or not self.storage_path:
            return
            
        if self.storage_path.exists():
            try:
                # Check if file is empty
                if self.storage_path.stat().st_size == 0:
                    self.logger.debug("Storage file is empty, starting with no tasks")
                    return
                
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
        else:
            self.logger.debug(f"No storage file found at {self.storage_path}, starting with empty task list")
    
    def _save_tasks(self) -> None:
        """Save tasks to storage file."""
        if not self.enable_persistence or not self.storage_path:
            return
            
        try:
            # Ensure parent directory exists
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "tasks": [task.to_dict() for task in self.tasks.values()],
                "last_updated": datetime.now().isoformat()
            }
            
            # Write to temporary file first, then move to final location (atomic write)
            temp_path = self.storage_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Atomic move
            temp_path.replace(self.storage_path)
            self.logger.debug(f"Tasks saved successfully to {self.storage_path}")
            
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
    
    def list_tasks(self) -> List[BookingTask]:
        """List all tasks."""
        # Only reload if we have no tasks in memory, to avoid overwriting
        if not self.tasks:
            self._load_tasks()
        return list(self.tasks.values())
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a specific task."""
        # Reload to get latest state
        self._load_tasks()
        if task_id in self.tasks:
            self.tasks[task_id].status = BookingStatus.CANCELLED
            self._save_tasks()
            self.logger.info(f"Cancelled task: {task_id}")
            return True
        return False
    
    def remove_task(self, task_id: str) -> bool:
        """Remove a task completely."""
        # Reload to get latest state
        self._load_tasks()
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._save_tasks()
            self.logger.info(f"Removed task: {task_id}")
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
        current_time = datetime.now()
        
        for task in list(self.tasks.values()):
            if task.status in [BookingStatus.SUCCESS, BookingStatus.CANCELLED]:
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
            
            # Check if it's time to run this task
            if task.last_attempt is None:
                should_run = True
            else:
                time_since_last = current_time - task.last_attempt
                should_run = time_since_last >= timedelta(minutes=task.interval_minutes)
            
            if should_run:
                self._execute_booking_task(task)
        
        self._save_tasks()
    
    def _execute_booking_task(self, task: BookingTask) -> None:
        """Execute a single booking task."""
        # Store original values for rollback if needed
        original_status = task.status
        original_attempts = task.attempts
        original_last_attempt = task.last_attempt
        
        # Update task status and attempt info
        task.status = BookingStatus.RUNNING
        task.last_attempt = datetime.now()
        task.attempts += 1
        
        self.logger.info(f"Executing task {task.id} (attempt {task.attempts})")
        
        # Save immediately after updating attempt count
        try:
            self._save_tasks()
        except Exception as save_error:
            self.logger.error(f"Failed to save task state before execution: {save_error}")
        
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
            
            try:
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
                            task.success_pnr = pnr
                            break
                    
                    task.status = BookingStatus.SUCCESS
                    self.logger.info(f"Task {task.id} completed successfully! PNR: {task.success_pnr}")
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
                    
                    task.status = BookingStatus.PENDING  # Will retry on next cycle
                    self.logger.warning(f"Task {task.id} attempt {task.attempts} failed: {task.error_message}")
            
            except Exception as e:
                task.error_message = f"Booking execution error: {str(e)}"[:500]
                task.status = BookingStatus.PENDING  # Will retry on next cycle
                self.logger.error(f"Task {task.id} failed with booking exception: {e}")
                import traceback
                self.logger.debug(f"Task {task.id} traceback: {traceback.format_exc()}")
        
        except Exception as e:
            # Critical error - restore original state except for attempt count
            task.status = BookingStatus.PENDING
            task.error_message = f"Critical execution error: {str(e)}"[:500]
            self.logger.error(f"Critical failure in task {task.id}: {e}")
            import traceback
            self.logger.debug(f"Critical error traceback: {traceback.format_exc()}")
        
        finally:
            # Restore original environment variable
            if original_non_interactive is None:
                os.environ.pop('THSR_NON_INTERACTIVE', None)
            else:
                os.environ['THSR_NON_INTERACTIVE'] = original_non_interactive
                
            # Always save the final state
            try:
                self._save_tasks()
                self.logger.debug(f"Task {task.id} final state saved: status={task.status.value}, attempts={task.attempts}")
            except Exception as save_error:
                self.logger.error(f"Failed to save task state after execution: {save_error}")


# Global scheduler instance
_scheduler_instance: Optional[BookingScheduler] = None


def get_scheduler() -> BookingScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = BookingScheduler()
        # Tasks are already loaded in __init__
    # Don't reload automatically - let individual methods decide
    return _scheduler_instance


def create_booking_task(
    from_station: int,
    to_station: int,
    date: str,
    personal_id: str,
    use_membership: bool,
    adult_cnt: Optional[int] = None,
    student_cnt: Optional[int] = None,
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
        if booking_date.date() < datetime.now().date():
            raise ValueError(f"Booking date must be in the future: {date}")
    except ValueError as e:
        if "does not match format" in str(e):
            raise ValueError(f"Invalid date format (use YYYY/MM/DD): {date}")
        raise e
    
    # Validate ticket counts - require at least one ticket
    if adult_cnt is None and student_cnt is None:
        raise ValueError("At least one ticket type (adult or student) must be specified")
    
    total_tickets = (adult_cnt or 0) + (student_cnt or 0)
    if total_tickets == 0:
        raise ValueError("Total ticket count must be greater than 0")
    if total_tickets > 10:
        raise ValueError("Total ticket count cannot exceed 10")
    
    if adult_cnt is not None and not 0 <= adult_cnt <= 10:
        raise ValueError(f"Adult ticket count must be 0-10: {adult_cnt}")
    if student_cnt is not None and not 0 <= student_cnt <= 10:
        raise ValueError(f"Student ticket count must be 0-10: {student_cnt}")
    
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
        personal_id=personal_id,
        use_membership=use_membership,
        adult_cnt=adult_cnt,
        student_cnt=student_cnt,
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
