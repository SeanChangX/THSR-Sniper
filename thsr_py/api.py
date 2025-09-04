from __future__ import annotations

import requests
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator, model_validator
import uvicorn

from .scheduler import (
    BookingTask, BookingStatus, 
    get_scheduler, create_booking_task
)
from .schema import STATION_MAP, TIME_TABLE
from .flows import run as run_booking_flow

# Utility function to clean ANSI color codes
def clean_ansi_codes(text: Optional[str]) -> Optional[str]:
    """Remove ANSI color codes from text."""
    if not text:
        return text
    import re
    return re.sub(r'\033\[[0-9;]*m', '', text).strip()

# Authentication dependency
async def get_current_user(authorization: str = Header(None), x_internal_cli: str = Header(None)) -> Optional[str]:
    """Extract user ID from authorization header or allow CLI internal access."""
    
    # Check for internal CLI access (only when running in same Docker network)
    if x_internal_cli == "thsr-cli-internal":
        # Return a special CLI user ID to indicate internal access
        return "cli-internal"
    
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization.split(" ")[1]
    
    # Verify token with auth service
    try:
        auth_service_url = "http://thsr-sniper-auth:8001"
        response = requests.get(
            f"{auth_service_url}/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        
        if response.status_code == 200:
            user_data = response.json()
            return user_data.get("id")
    except Exception as e:
        print(f"Auth verification failed: {e}")
    
    return None


# Pydantic models for API request/response
class BookingRequest(BaseModel):
    from_station: int = Field(..., ge=1, le=12, description="Departure station ID (1-12)")
    to_station: int = Field(..., ge=1, le=12, description="Arrival station ID (1-12)")
    date: str = Field(..., description="Departure date in YYYY/MM/DD format")
    personal_id: str = Field(..., description="Personal ID number (required)")
    use_membership: bool = Field(..., description="Use THSR membership (required)")
    adult_cnt: Optional[int] = Field(None, ge=0, le=10, description="Number of adult tickets (0-10)")
    student_cnt: Optional[int] = Field(None, ge=0, le=10, description="Number of student tickets (0-10)")
    child_cnt: Optional[int] = Field(None, ge=0, le=10, description="Number of child tickets (0-10)")
    senior_cnt: Optional[int] = Field(None, ge=0, le=10, description="Number of senior tickets (0-10)")
    disabled_cnt: Optional[int] = Field(None, ge=0, le=10, description="Number of disabled tickets (0-10)")
    time: Optional[int] = Field(None, ge=1, le=38, description="Departure time ID (1-38)")
    train_index: Optional[int] = Field(None, ge=1, description="Train selection index")
    seat_prefer: Optional[int] = Field(None, ge=0, le=2, description="Seat preference: 0=any, 1=window, 2=aisle")
    class_type: Optional[int] = Field(None, ge=0, le=1, description="Class type: 0=standard, 1=business")
    no_ocr: bool = Field(False, description="Disable automatic captcha OCR recognition (default: False to enable OCR)")
    
    @validator('date')
    def validate_date(cls, v):
        try:
            booking_date = datetime.strptime(v, "%Y/%m/%d")
            if booking_date.date() < datetime.now().date():
                raise ValueError("Booking date must be in the future")
            return v
        except ValueError as e:
            raise ValueError(f"Invalid date format or past date: {e}")
    
    @validator('personal_id')
    def validate_personal_id(cls, v):
        if not v or not v.strip():
            raise ValueError("Personal ID is required")
        v = v.strip().upper()
        if len(v) != 10:
            raise ValueError("Personal ID must be 10 characters long")
        return v
    
    @model_validator(mode='after')
    def validate_ticket_counts(self):
        """Validate that at least one ticket is selected and total doesn't exceed 10"""
        adult_cnt = self.adult_cnt or 0
        student_cnt = self.student_cnt or 0
        child_cnt = self.child_cnt or 0
        senior_cnt = self.senior_cnt or 0
        disabled_cnt = self.disabled_cnt or 0
        
        total_tickets = adult_cnt + student_cnt + child_cnt + senior_cnt + disabled_cnt
        
        if total_tickets == 0:
            raise ValueError("At least one ticket must be specified")
        
        if total_tickets > 10:
            raise ValueError("Total tickets cannot exceed 10")
        
        return self


class ScheduledBookingRequest(BookingRequest):
    interval_minutes: int = Field(5, ge=1, description="Booking attempt interval in minutes")
    max_attempts: Optional[int] = Field(None, ge=1, description="Maximum number of attempts (unlimited if null)")


class BookingResponse(BaseModel):
    success: bool
    message: str
    pnr_code: Optional[str] = None
    task_id: Optional[str] = None


class TaskStatusResponse(BaseModel):
    id: str
    status: str
    from_station: int
    to_station: int
    date: str
    adult_cnt: Optional[int] = None
    student_cnt: Optional[int] = None
    child_cnt: Optional[int] = None
    senior_cnt: Optional[int] = None
    disabled_cnt: Optional[int] = None
    time: Optional[int] = None
    train_index: Optional[int] = None
    interval_minutes: int
    attempts: int
    last_attempt: Optional[str]
    success_pnr: Optional[str]
    error_message: Optional[str]
    created_at: str


class StationInfo(BaseModel):
    id: int
    name: str


class TimeSlotInfo(BaseModel):
    id: int
    time: str
    formatted_time: str


# Create FastAPI app
app = FastAPI(
    title="THSR-Sniper API",
    description="Taiwan High Speed Rail Ticket Booking API with Scheduling",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize scheduler on startup."""
    scheduler = get_scheduler()
    scheduler.start_scheduler()


@app.on_event("shutdown") 
async def shutdown_event():
    """Stop scheduler on shutdown."""
    scheduler = get_scheduler()
    scheduler.stop_scheduler()


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "THSR-Sniper API",
        "description": "Taiwan High Speed Rail Ticket Booking API with Scheduling",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/stations", response_model=List[StationInfo])
async def get_stations():
    """Get all available stations."""
    return [
        StationInfo(id=idx + 1, name=name) 
        for idx, name in enumerate(STATION_MAP)
    ]


@app.get("/times", response_model=List[TimeSlotInfo])
async def get_time_slots():
    """Get all available departure time slots."""
    time_slots = []
    for idx, time_str in enumerate(TIME_TABLE):
        t_int = int(time_str[:-1])
        if time_str.endswith("A") and t_int // 100 == 12:
            t_int %= 1200
        elif t_int != 1230 and time_str.endswith("P"):
            t_int += 1200
        formatted_time = f"{t_int:04d}"
        formatted = f"{formatted_time[:-2]}:{formatted_time[-2:]}"
        
        time_slots.append(TimeSlotInfo(
            id=idx + 1,
            time=time_str,
            formatted_time=formatted
        ))
    
    return time_slots


@app.post("/book", response_model=BookingResponse)
async def immediate_booking(request: BookingRequest):
    """Execute immediate booking (single attempt)."""
    try:
        # Convert request to args namespace
        from argparse import Namespace
        args = Namespace(
            from_=request.from_station,
            to=request.to_station,
            date=request.date,
            personal_id=request.personal_id,
            use_membership=request.use_membership,
            adult_cnt=request.adult_cnt if request.adult_cnt is not None else 0,
            student_cnt=request.student_cnt if request.student_cnt is not None else 0,
            child_cnt=request.child_cnt if request.child_cnt is not None else 0,
            senior_cnt=request.senior_cnt if request.senior_cnt is not None else 0,
            disabled_cnt=request.disabled_cnt if request.disabled_cnt is not None else 0,
            time=request.time,
            train_index=request.train_index,
            seat_prefer=request.seat_prefer,
            class_type=request.class_type,
            no_ocr=request.no_ocr,
            stations=False,
            times=False
        )
        
        # Execute booking flow
        import io
        import sys
        import os
        from contextlib import redirect_stdout, redirect_stderr
        
        # Set environment variable to indicate API mode (non-interactive)
        original_api_mode = os.environ.get('THSR_API_MODE')
        os.environ['THSR_API_MODE'] = '1'
        
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        
        try:
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                run_booking_flow(args)
            
            output = stdout_buffer.getvalue()
            
            if "PNR Code:" in output:
                # Extract PNR code
                lines = output.split('\n')
                pnr_code = None
                for line in lines:
                    if "PNR Code:" in line:
                        pnr_code = line.split("PNR Code:")[-1].strip()
                        break
                
                return BookingResponse(
                    success=True,
                    message="Booking completed successfully!",
                    pnr_code=pnr_code
                )
            else:
                error_output = stderr_buffer.getvalue()
                error_msg = error_output if error_output else "Booking failed - no PNR code found"
                
                return BookingResponse(
                    success=False,
                    message=f"Booking failed: {error_msg}"
                )
        
        except Exception as e:
            return BookingResponse(
                success=False,
                message=f"Booking execution failed: {str(e)}"
            )
        finally:
            # Restore original environment variable
            if original_api_mode is None:
                os.environ.pop('THSR_API_MODE', None)
            else:
                os.environ['THSR_API_MODE'] = original_api_mode
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")


@app.post("/schedule", response_model=BookingResponse)
async def schedule_booking(
    request: ScheduledBookingRequest,
    current_user_id: Optional[str] = Depends(get_current_user)
):
    """Schedule a booking task for periodic execution."""
    try:
        # Determine user_id for task association
        # CLI internal access gets a special user_id, regular users get their actual user_id
        task_user_id = "cli-user" if current_user_id == "cli-internal" else current_user_id
        
        # Create booking task
        task = create_booking_task(
            from_station=request.from_station,
            to_station=request.to_station,
            date=request.date,
            personal_id=request.personal_id,
            use_membership=request.use_membership,
            user_id=task_user_id,  # Associate task with appropriate user
            adult_cnt=request.adult_cnt,
            student_cnt=request.student_cnt,
            child_cnt=request.child_cnt,
            senior_cnt=request.senior_cnt,
            disabled_cnt=request.disabled_cnt,
            interval_minutes=request.interval_minutes,
            max_attempts=request.max_attempts,
            time=request.time,
            train_index=request.train_index,
            seat_prefer=request.seat_prefer,
            class_type=request.class_type,
            no_ocr=request.no_ocr
        )
        
        # Add to scheduler
        scheduler = get_scheduler()
        task_id = scheduler.add_task(task)
        
        return BookingResponse(
            success=True,
            message=f"Booking scheduled successfully! Task will run every {request.interval_minutes} minutes.",
            task_id=task_id
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to schedule booking: {str(e)}")


@app.get("/tasks", response_model=List[TaskStatusResponse])
async def list_tasks(current_user_id: Optional[str] = Depends(get_current_user)):
    """List scheduled booking tasks for the authenticated user."""
    # Require authentication for task access
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Authentication required to access tasks")
    
    scheduler = get_scheduler()
    tasks = scheduler.list_tasks(force_reload=False)
    
    # CLI internal access sees all tasks, regular users see only their own
    if current_user_id != "cli-internal":
        tasks = [task for task in tasks if task.user_id == current_user_id]
    
    return [
        TaskStatusResponse(
            id=task.id,
            status=task.status.value,
            from_station=task.from_station,
            to_station=task.to_station,
            date=task.date,
            adult_cnt=task.adult_cnt,
            student_cnt=task.student_cnt,
            child_cnt=task.child_cnt,
            senior_cnt=task.senior_cnt,
            disabled_cnt=task.disabled_cnt,
            time=task.time,
            train_index=task.train_index,
            interval_minutes=task.interval_minutes,
            attempts=task.attempts,
            last_attempt=task.last_attempt.isoformat() if task.last_attempt else None,
            success_pnr=clean_ansi_codes(task.success_pnr),
            error_message=task.error_message,
            created_at=task.created_at.isoformat()
        )
        for task in tasks
    ]


@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user_id: Optional[str] = Depends(get_current_user)
):
    """Get status of a specific task."""
    # Require authentication for task access
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Authentication required to access tasks")
    
    scheduler = get_scheduler()
    task = scheduler.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check task ownership (CLI internal access bypasses this check)
    if current_user_id != "cli-internal" and task.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied: You can only view your own tasks")
    
    return TaskStatusResponse(
        id=task.id,
        status=task.status.value,
        from_station=task.from_station,
        to_station=task.to_station,
        date=task.date,
        adult_cnt=task.adult_cnt,
        student_cnt=task.student_cnt,
        child_cnt=task.child_cnt,
        senior_cnt=task.senior_cnt,
        disabled_cnt=task.disabled_cnt,
        time=task.time,
        train_index=task.train_index,
        interval_minutes=task.interval_minutes,
        attempts=task.attempts,
        last_attempt=task.last_attempt.isoformat() if task.last_attempt else None,
        success_pnr=clean_ansi_codes(task.success_pnr),
        error_message=task.error_message,
        created_at=task.created_at.isoformat()
    )


@app.delete("/tasks/{task_id}", response_model=BookingResponse)
async def cancel_task(
    task_id: str,
    current_user_id: Optional[str] = Depends(get_current_user)
):
    """Cancel a scheduled booking task."""
    # Require authentication for task access
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Authentication required to access tasks")
    
    scheduler = get_scheduler()
    task = scheduler.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check task ownership (CLI internal access bypasses this check)
    if current_user_id != "cli-internal" and task.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied: You can only cancel your own tasks")
    
    # For CLI internal access, pass None as user_id to bypass user checks
    user_check_id = None if current_user_id == "cli-internal" else current_user_id
    if scheduler.cancel_task(task_id, user_check_id):
        return BookingResponse(
            success=True,
            message=f"Task {task_id} cancelled successfully"
        )
    else:
        raise HTTPException(status_code=404, detail="Task not found")


@app.delete("/tasks/{task_id}/remove", response_model=BookingResponse)
async def remove_task(
    task_id: str,
    current_user_id: Optional[str] = Depends(get_current_user)
):
    """Remove a task completely."""
    # Require authentication for task access
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Authentication required to access tasks")
    
    scheduler = get_scheduler()
    task = scheduler.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check task ownership (CLI internal access bypasses this check)
    if current_user_id != "cli-internal" and task.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied: You can only remove your own tasks")
    
    # For CLI internal access, pass None as user_id to bypass user checks
    user_check_id = None if current_user_id == "cli-internal" else current_user_id
    if scheduler.remove_task(task_id, user_check_id):
        return BookingResponse(
            success=True,
            message=f"Task {task_id} removed successfully"
        )
    else:
        raise HTTPException(status_code=404, detail="Task not found")


@app.get("/scheduler/status")
async def get_scheduler_status():
    """Get scheduler status information."""
    scheduler = get_scheduler()
    tasks = scheduler.list_tasks(force_reload=False)
    
    status_counts = {}
    for status in BookingStatus:
        status_counts[status.value] = sum(1 for task in tasks if task.status == status)
    
    # THSR website connectivity check disabled
    # thsr_status = await test_thsr_connectivity()
    
    return {
        "running": scheduler.running,
        "total_tasks": len(tasks),
        "status_breakdown": status_counts,
        "storage_path": str(scheduler.storage_path),
        # "thsr_connectivity": thsr_status
    }





# Cache for THSR connectivity status to avoid frequent external requests
_thsr_connectivity_cache = {
    "status": None,
    "last_checked": 0,
    "cache_duration": 60  # Cache for 60 seconds
}

@app.get("/health/thsr")
async def test_thsr_connectivity():
    """Test connectivity to THSR official website with caching and async optimization."""
    import time
    import asyncio
    import aiohttp
    import random
    from .flows import _headers
    
    # Check cache first
    current_time = time.time()
    if (_thsr_connectivity_cache["status"] is not None and 
        current_time - _thsr_connectivity_cache["last_checked"] < _thsr_connectivity_cache["cache_duration"]):
        return _thsr_connectivity_cache["status"]
    
    try:
        # Generate random session-like parameters to simulate different users/devices
        session_params = {
            'user_agent_suffix': f"_{random.randint(1000, 9999)}",
            'timestamp': str(int(current_time)),
            'random_id': random.randint(100000, 999999)
        }
        
        headers = _headers()
        headers['User-Agent'] += session_params['user_agent_suffix']
        headers['X-Requested-With'] = 'XMLHttpRequest'
        headers['X-Session-ID'] = f"session_{session_params['random_id']}_{session_params['timestamp']}"
        
        # Use async HTTP client with shorter timeout and HEAD request for faster response
        start_time = time.time()
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            # First try HEAD request for faster response
            try:
                async with session.head(
                    "https://irs.thsrc.com.tw/IMINT/?locale=tw",
                    headers=headers,
                    allow_redirects=True
                ) as response:
                    response_time = round((time.time() - start_time) * 1000, 2)
                    
                    if response.status == 200:
                        result = {
                            "status": "online",
                            "response_time_ms": response_time,
                            "message": "高鐵官網連線正常",
                            "tested_at": current_time,
                            "session_info": f"Session ID: {session_params['random_id']}"
                        }
                    else:
                        result = {
                            "status": "error",
                            "response_time_ms": response_time,
                            "message": f"高鐵官網連線失敗 (HTTP {response.status})",
                            "tested_at": current_time
                        }
            except asyncio.TimeoutError:
                result = {
                    "status": "timeout",
                    "response_time_ms": None,
                    "message": "高鐵官網連線逾時",
                    "tested_at": current_time
                }
            except aiohttp.ClientConnectorError:
                result = {
                    "status": "offline",
                    "response_time_ms": None,
                    "message": "無法連線至高鐵官網，請檢查網路連線",
                    "tested_at": current_time
                }
            except Exception as e:
                result = {
                    "status": "error",
                    "response_time_ms": None,
                    "message": f"高鐵官網連線測試發生錯誤: {str(e)}",
                    "tested_at": current_time
                }
        
        # Update cache
        _thsr_connectivity_cache["status"] = result
        _thsr_connectivity_cache["last_checked"] = current_time
        
        return result
            
    except Exception as e:
        error_result = {
            "status": "error",
            "response_time_ms": None,
            "message": f"高鐵官網連線測試發生錯誤: {str(e)}",
            "tested_at": current_time
        }
        # Don't cache errors
        return error_result


@app.get("/results")
async def get_results(
    status: Optional[str] = Query(None, description="Filter by status (pending/running/success/failed/cancelled/expired)"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user_id: Optional[str] = Depends(get_current_user)
):
    """Get booking results with optional filtering."""
    try:
        # Require authentication for task access
        if not current_user_id:
            raise HTTPException(status_code=401, detail="Authentication required to access tasks")
        
        scheduler = get_scheduler()
        tasks = scheduler.list_tasks(force_reload=False)
        
        # Filter by user
        tasks = [task for task in tasks if task.user_id == current_user_id]
        
        # Filter by status if specified
        if status:
            tasks = [task for task in tasks if task.status.value == status.lower()]
        
        # Sort by creation time (newest first)
        tasks.sort(key=lambda x: x.created_at, reverse=True)
        
        # Apply pagination
        total = len(tasks)
        tasks = tasks[offset:offset + limit]
        
        # Convert to response format
        results = []
        for task in tasks:
            result = {
                "id": task.id,
                "status": task.status.value,
                "from_station": task.from_station,
                "to_station": task.to_station,
                "date": task.date,
                "adult_cnt": task.adult_cnt,
                "student_cnt": task.student_cnt,
                "child_cnt": task.child_cnt,
                "senior_cnt": task.senior_cnt,
                "disabled_cnt": task.disabled_cnt,
                "personal_id": task.personal_id,
                "use_membership": task.use_membership,
                "interval_minutes": task.interval_minutes,
                "max_attempts": task.max_attempts,
                "attempts": task.attempts,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "last_attempt": task.last_attempt.isoformat() if task.last_attempt else None,
                "time": task.time,
                "seat_prefer": task.seat_prefer,
                "class_type": task.class_type,
                "no_ocr": task.no_ocr,
                "result": getattr(task, 'result', None),
                "success_pnr": getattr(task, 'success_pnr', None),
                "error": getattr(task, 'error', None)
            }
            results.append(result)
        
        return {
            "success": True,
            "total": total,
            "offset": offset,
            "limit": limit,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/results/stats")
async def get_results_stats(current_user_id: Optional[str] = Depends(get_current_user)):
    """Get booking results statistics."""
    try:
        # Require authentication for stats access
        if not current_user_id:
            raise HTTPException(status_code=401, detail="Authentication required to access task statistics")
        
        scheduler = get_scheduler()
        tasks = scheduler.list_tasks(force_reload=False)
        
        # Filter by user
        tasks = [task for task in tasks if task.user_id == current_user_id]
        
        if not tasks:
            return {
                "success": True,
                "total_tasks": 0,
                "total_attempts": 0,
                "average_attempts": 0,
                "status_breakdown": {},
                "success_rate": 0
            }
        
        # Calculate statistics
        status_count = {}
        total_attempts = 0
        
        for task in tasks:
            status = task.status.value
            status_count[status] = status_count.get(status, 0) + 1
            total_attempts += task.attempts
        
        success_count = status_count.get('success', 0)
        completed_count = sum(status_count.get(s, 0) for s in ['success', 'failed', 'cancelled', 'expired'])
        success_rate = (success_count / completed_count * 100) if completed_count > 0 else 0
        
        return {
            "success": True,
            "total_tasks": len(tasks),
            "total_attempts": total_attempts,
            "average_attempts": round(total_attempts / len(tasks), 2),
            "status_breakdown": status_count,
            "success_rate": round(success_rate, 2),
            "completed_tasks": completed_count,
            "active_tasks": status_count.get('pending', 0) + status_count.get('running', 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/results/{task_id}")
async def get_task_result(
    task_id: str,
    current_user_id: Optional[str] = Depends(get_current_user)
):
    """Get detailed result for a specific task."""
    try:
        # Require authentication for task access
        if not current_user_id:
            raise HTTPException(status_code=401, detail="Authentication required to access tasks")
        
        scheduler = get_scheduler()
        task = scheduler.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Check task ownership
        if task.user_id != current_user_id:
            raise HTTPException(status_code=403, detail="Access denied: You can only view your own tasks")
        
        # Detailed task information
        result = {
            "id": task.id,
            "status": task.status.value,
            "from_station": task.from_station,
            "to_station": task.to_station,
            "date": task.date,
            "adult_cnt": task.adult_cnt,
            "student_cnt": task.student_cnt,
            "child_cnt": task.child_cnt,
            "senior_cnt": task.senior_cnt,
            "disabled_cnt": task.disabled_cnt,
            "personal_id": task.personal_id,
            "use_membership": task.use_membership,
            "interval_minutes": task.interval_minutes,
            "max_attempts": task.max_attempts,
            "attempts": task.attempts,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "last_attempt": task.last_attempt.isoformat() if task.last_attempt else None,
            "time": task.time,
            "seat_prefer": task.seat_prefer,
            "class_type": task.class_type,
            "no_ocr": task.no_ocr,
            "result": getattr(task, 'result', None),
            "success_pnr": getattr(task, 'success_pnr', None),
            "error": getattr(task, 'error', None)
        }
        
        # Calculate next attempt time if task is active
        if task.status.value in ['pending', 'running'] and task.last_attempt:
            from datetime import timedelta
            next_attempt = task.last_attempt + timedelta(minutes=task.interval_minutes)
            result["next_attempt"] = next_attempt.isoformat()
        
        return {"success": True, "task": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run_api_server(host: str = "0.0.0.0", port: int = 8000, log_level: str = "info"):
    """Run the FastAPI server."""
    uvicorn.run(
        "thsr_py.api:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=False
    )


if __name__ == "__main__":
    run_api_server()
