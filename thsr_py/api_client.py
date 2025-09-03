#!/usr/bin/env python3
"""
API client for THSR-Sniper scheduling functionality.
Provides CLI interface that calls the API backend.
"""

import json
import sys
from typing import Optional, Dict, Any
import requests
from datetime import datetime


class THSRApiClient:
    """Client for interacting with THSR-Sniper API."""
    
    def __init__(self, base_url: str = None, use_cli_auth: bool = True):
        # Auto-detect API URL based on environment
        if base_url is None:
            import os
            # Check if running in Docker (presence of /.dockerenv or hostname matching container pattern)
            if os.path.exists('/.dockerenv') or os.environ.get('HOSTNAME', '').startswith('thsr-sniper'):
                base_url = "http://thsr-sniper-api:8000"  # Docker internal network
            else:
                base_url = "http://localhost:8000"  # Local development
        
        self.base_url = base_url.rstrip('/')
        self.use_cli_auth = use_cli_auth
        
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to API."""
        url = f"{self.base_url}{endpoint}"
        
        # Add CLI internal authentication header
        headers = {}
        if self.use_cli_auth:
            headers["X-Internal-CLI"] = "thsr-cli-internal"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.ConnectionError:
            print(f"× Error: Cannot connect to API server at {self.base_url}")
            print("   Make sure the API server is running:")
            print("   docker compose up -d api")
            sys.exit(1)
        except requests.exceptions.Timeout:
            print("× Error: Request timeout. API server may be overloaded.")
            sys.exit(1)
        except requests.exceptions.HTTPError as e:
            print(f"× API Error: {e}")
            if hasattr(e.response, 'text'):
                try:
                    error_detail = json.loads(e.response.text)
                    print(f"   Details: {error_detail.get('detail', 'Unknown error')}")
                except:
                    print(f"   Response: {e.response.text}")
            sys.exit(1)
            
    def create_scheduled_task(
        self,
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
        max_attempts: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new scheduled booking task."""
        
        payload = {
            "from_station": from_station,
            "to_station": to_station,
            "date": date,
            "personal_id": personal_id,
            "use_membership": use_membership,
            "interval_minutes": interval_minutes
        }
        
        # Add optional parameters
        if adult_cnt is not None:
            payload["adult_cnt"] = adult_cnt
        if student_cnt is not None:
            payload["student_cnt"] = student_cnt
        if time is not None:
            payload["time"] = time
        if train_index is not None:
            payload["train_index"] = train_index
        if seat_prefer is not None:
            payload["seat_prefer"] = seat_prefer
        if class_type is not None:
            payload["class_type"] = class_type
        if max_attempts is not None:
            payload["max_attempts"] = max_attempts
            
        return self._make_request("POST", "/schedule", payload)
    
    def list_tasks(self) -> list:
        """List all scheduled tasks."""
        return self._make_request("GET", "/tasks")
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a specific task."""
        return self._make_request("GET", f"/tasks/{task_id}")
    
    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancel a specific task."""
        return self._make_request("DELETE", f"/tasks/{task_id}")
    
    def get_stations(self) -> Dict[str, Any]:
        """Get list of available stations."""
        return self._make_request("GET", "/stations")
    
    def get_times(self) -> Dict[str, Any]:
        """Get list of available time slots."""
        return self._make_request("GET", "/times")


def format_task_summary(task: Dict[str, Any], detailed: bool = False) -> None:
    """Format and print task summary."""
    from .schema import STATION_MAP
    
    # Get station names
    from_name = STATION_MAP[task["from_station"] - 1] if task["from_station"] <= len(STATION_MAP) else f"Station {task['from_station']}"
    to_name = STATION_MAP[task["to_station"] - 1] if task["to_station"] <= len(STATION_MAP) else f"Station {task['to_station']}"
    
    print(f"\n{'='*60}")
    print(f"  Task Details: {task['id'][:8]}...")
    print(f"{'='*60}")
    status_symbol = "✓" if task['status'].lower() in ['completed', 'success'] else "○" if task['status'].lower() == 'running' else "×" if task['status'].lower() in ['failed', 'error'] else "•"
    print(f"Status: {status_symbol} {task['status'].upper()}")
    print(f"Route: {from_name} ({task['from_station']}) -> {to_name} ({task['to_station']})")
    print(f"Date: {task['date']}")
    
    # Ticket info
    tickets = []
    if task.get('adult_cnt'):
        tickets.append(f"{task['adult_cnt']} adult")
    if task.get('student_cnt'):
        tickets.append(f"{task['student_cnt']} student")
    if tickets:
        print(f"Tickets: {', '.join(tickets)}")
    
    print(f"Interval: {task['interval_minutes']} minutes")
    print(f"Attempts: {task['attempts']}")
    
    if task.get('last_attempt'):
        last_attempt = datetime.fromisoformat(task['last_attempt'].replace('Z', '+00:00'))
        print(f"Last Attempt: {last_attempt.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if task.get('success_pnr'):
        print(f"✓ SUCCESS - PNR: {task['success_pnr']}")
    elif task.get('error_message'):
        print(f"× Error: {task['error_message'][:100]}...")
    
    if detailed:
        print(f"Created: {datetime.fromisoformat(task['created_at'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Full Task ID: {task['id']}")


def print_task_list(tasks: list) -> None:
    """Print formatted list of tasks."""
    if not tasks:
        print("\nNo scheduled booking tasks found.")
        return
    
    # Group by status
    status_groups = {}
    for task in tasks:
        status = task['status'].upper()
        if status not in status_groups:
            status_groups[status] = []
        status_groups[status].append(task)
    
    print(f"\n{'='*80}")
    print(f"  >> Scheduled Booking Tasks ({len(tasks)} total)")
    print(f"{'='*80}")
    
    for status, group_tasks in status_groups.items():
        status_symbol = "✓" if status.lower() in ['completed', 'success'] else "○" if status.lower() == 'running' else "×" if status.lower() in ['failed', 'error'] else "•"
        print(f"\n{status_symbol} {status} ({len(group_tasks)} tasks)")
        print("-" * 60)
        
        for task in group_tasks:
            from .schema import STATION_MAP
            
            # Get station names (shortened)
            from_short = STATION_MAP[task["from_station"] - 1][:3] if task["from_station"] <= len(STATION_MAP) else f"S{task['from_station']}"
            to_short = STATION_MAP[task["to_station"] - 1][:3] if task["to_station"] <= len(STATION_MAP) else f"S{task['to_station']}"
            
            # Ticket summary
            tickets = []
            if task.get('adult_cnt') and task['adult_cnt'] > 0:
                tickets.append(f"{task['adult_cnt']}A")
            if task.get('student_cnt') and task['student_cnt'] > 0:
                tickets.append(f"{task['student_cnt']}S")
            if task.get('child_cnt') and task['child_cnt'] > 0:
                tickets.append(f"{task['child_cnt']}C")
            if task.get('senior_cnt') and task['senior_cnt'] > 0:
                tickets.append(f"{task['senior_cnt']}Sr")
            if task.get('disabled_cnt') and task['disabled_cnt'] > 0:
                tickets.append(f"{task['disabled_cnt']}D")
            ticket_str = f"[{','.join(tickets)}]" if tickets else "[1A]"  # Default to 1 adult if none specified
            
            # Time info
            time_info = ""
            if task.get('time'):
                from .schema import TIME_TABLE
                if task['time'] <= len(TIME_TABLE):
                    time_info = f" @{TIME_TABLE[task['time']-1]}"
                else:
                    time_info = f" @T{task['time']}"
            elif task.get('train_index'):
                time_info = f" #{task['train_index']}"
            
            # Success info
            extra_info = ""
            if task.get('success_pnr'):
                extra_info = f" | ✓ PNR: {task['success_pnr']}"
            elif task.get('error_message'):
                extra_info = f" | × Error: {task['error_message'][:30]}..."
            
            task_symbol = "✓" if task['status'].lower() in ['completed', 'success'] else "○" if task['status'].lower() == 'running' else "×" if task['status'].lower() in ['failed', 'error'] else "•"
            print(f"  {task_symbol} {task['id'][:8]}... | {status:<7} | {from_short}->{to_short} {task['date']} {ticket_str}{time_info} | Attempts: {task['attempts']} | Interval: {task['interval_minutes']}m{extra_info}")


def show_task_status(client: THSRApiClient, task_id: str) -> None:
    """Show detailed status of a specific task."""
    try:
        task = client.get_task_status(task_id)
        format_task_summary(task, detailed=True)
    except SystemExit:
        print(f"× Task '{task_id}' not found or API error.")


def cancel_task_interactive(client: THSRApiClient, task_id: str) -> None:
    """Cancel a task with confirmation."""
    try:
        # Get task details first
        task = client.get_task_status(task_id)
        print(f"Task to cancel: {task['id'][:8]}... ({task['status']})")
        
        # Confirm cancellation
        try:
            confirm = input("Are you sure you want to cancel this task? (y/N): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            confirm = 'n'  # Default to no in non-interactive environments
            
        if confirm in ['y', 'yes']:
            result = client.cancel_task(task_id)
            print(f"✓ Task cancelled successfully")
        else:
            print("× Cancellation aborted")
            
    except SystemExit:
        print(f"× Task '{task_id}' not found or API error.")


def schedule_booking_via_api(args) -> None:
    """Schedule a booking task via API (called from main.py)."""
    client = THSRApiClient()
    
    try:
        # Validate required parameters
        if not hasattr(args, 'from_') or args.from_ is None:
            print("× Error: --from station is required for scheduled booking")
            print("   Use --stations to see available stations")
            return
        if not hasattr(args, 'to') or args.to is None:
            print("× Error: --to station is required for scheduled booking")
            print("   Use --stations to see available stations")
            return
        if not hasattr(args, 'date') or args.date is None:
            print("× Error: --date is required for scheduled booking")
            print("   Example: --date 2025/09/10 or --date +1")
            return
        if not hasattr(args, 'personal_id') or not args.personal_id:
            print("× Error: --id (Personal ID) is required for scheduled booking")
            print("   Example: --id A123456789")
            return
        if not hasattr(args, 'use_membership') or args.use_membership is None:
            print("× Error: --member (membership preference) is required for scheduled booking")
            print("   Example: --member y or --member n")
            return
        
        # Check that at least one ticket type is specified
        adult_cnt = getattr(args, 'adult_cnt', None)
        student_cnt = getattr(args, 'student_cnt', None)
        if adult_cnt is None and student_cnt is None:
            print("× Error: At least one ticket type must be specified")
            print("   Example: --adult 1 or --student 2")
            return
        
        # Create the scheduled task
        result = client.create_scheduled_task(
            from_station=args.from_,
            to_station=args.to,
            date=args.date,
            personal_id=args.personal_id,
            use_membership=args.use_membership,
            adult_cnt=adult_cnt,
            student_cnt=student_cnt,
            interval_minutes=getattr(args, 'interval', 5),
            max_attempts=getattr(args, 'max_attempts', None),
            time=getattr(args, 'time', None),
            train_index=getattr(args, 'train_index', None),
            seat_prefer=getattr(args, 'seat_prefer', None),
            class_type=getattr(args, 'class_type', None)
        )
        
        print(f"\n✓ Booking task scheduled successfully!")
        print(f"Task ID: {result['task_id']}")
        print(f"Message: {result['message']}")
        
        # Get and show task details
        task = client.get_task_status(result['task_id'])
        format_task_summary(task, detailed=True)
        
        print(f"\n>> Use the following commands to manage your task:")
        print(f"   • python main.py --task-status {result['task_id']}")
        print(f"   • python main.py --cancel-task {result['task_id']}")
        print(f"   • python main.py --list-tasks")
        
    except Exception as e:
        print(f"× Error scheduling booking: {e}")


def list_tasks_via_api() -> None:
    """List all tasks via API."""
    client = THSRApiClient()
    tasks = client.list_tasks()
    
    print(f"\n>> Scheduler Status")
    print(f"Total Tasks: {len(tasks)}")
    print(f"API Endpoint: {client.base_url}")
    
    print_task_list(tasks)


if __name__ == "__main__":
    # Simple CLI for testing
    import argparse
    
    parser = argparse.ArgumentParser(description="THSR API Client")
    parser.add_argument("--list", action="store_true", help="List all tasks")
    parser.add_argument("--status", help="Show task status")
    parser.add_argument("--cancel", help="Cancel task")
    
    args = parser.parse_args()
    
    client = THSRApiClient()
    
    if args.list:
        list_tasks_via_api()
    elif args.status:
        show_task_status(client, args.status)
    elif args.cancel:
        cancel_task_interactive(client, args.cancel)
    else:
        print("Use --list, --status TASK_ID, or --cancel TASK_ID")
