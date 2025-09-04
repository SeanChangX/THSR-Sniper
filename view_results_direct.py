#!/usr/bin/env python3
"""
Direct database viewer for THSR-Sniper scheduled tasks.
Bypasses API authentication by directly accessing storage files and database.
For use inside Docker containers or local server environment.
"""

import sys
import json
import os
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import argparse


def load_tasks_from_storage(storage_path: str = "/app/data/thsr_scheduler.json") -> List[Dict[str, Any]]:
    """Load tasks directly from scheduler storage file."""
    try:
        if not Path(storage_path).exists():
            print(f"× Task storage file not found: {storage_path}")
            # Try alternative locations
            alt_paths = [
                "./data/thsr_scheduler.json",
                "./thsr_scheduler.json",
                str(Path.home() / ".thsr" / "scheduler.json")
            ]
            
            for alt_path in alt_paths:
                if Path(alt_path).exists():
                    print(f"✓ Found alternative storage: {alt_path}")
                    storage_path = alt_path
                    break
            else:
                return []
        
        with open(storage_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        tasks = data.get('tasks', [])
        print(f"✓ Loaded {len(tasks)} tasks from {storage_path}")
        return tasks
        
    except json.JSONDecodeError as e:
        print(f"× Error parsing task storage file: {e}")
        return []
    except Exception as e:
        print(f"× Error loading tasks: {e}")
        return []


def load_users_from_db() -> Dict[str, Dict[str, Any]]:
    """Load user information from MySQL database."""
    try:
        # Try to import database dependencies
        try:
            import pymysql
            from sqlalchemy import create_engine, text
        except ImportError:
            print("× Warning: Database dependencies not available. User info will be limited.")
            return {}
        
        # Database configuration from environment
        db_config = {
            'host': os.getenv("MYSQL_HOST", "mysql"),
            'port': int(os.getenv("MYSQL_PORT", "3306")),
            'database': os.getenv("MYSQL_DATABASE", "thsr_sniper"),
            'user': os.getenv("MYSQL_USER", "user"),
            'password': os.getenv("MYSQL_PASSWORD", "password")
        }
        
        # Create database connection
        database_url = f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
        engine = create_engine(database_url)
        
        # Query users
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, username, email, full_name, created_at FROM users"))
            users = {}
            for row in result:
                users[str(row.id)] = {
                    'id': row.id,
                    'username': row.username,
                    'email': row.email,
                    'full_name': row.full_name,
                    'created_at': row.created_at
                }
        
        print(f"✓ Loaded {len(users)} users from database")
        return users
        
    except Exception as e:
        print(f"× Warning: Could not load user data from database: {e}")
        return {}


def format_task_details(task: Dict[str, Any], users: Dict[str, Dict[str, Any]] = None) -> None:
    """Format and display detailed task information."""
    print(f"\n{'='*80}")
    print(f"Task ID: {task['id']}")
    print(f"{'='*80}")
    
    # User info
    user_id = task.get('user_id')
    if user_id and users and user_id in users:
        user = users[user_id]
        print(f"User: {user.get('full_name', user.get('username', 'Unknown'))} ({user.get('email', 'No email')})")
    elif user_id:
        print(f"User ID: {user_id}")
    else:
        print("User: Not specified")
    
    # Basic info
    status_icons = {
        'success': '✓',
        'running': '○',
        'pending': '⏳',
        'failed': '×',
        'error': '×',
        'expired': '⏰',
        'cancelled': '🚫'
    }
    status = task.get('status', 'unknown').lower()
    status_icon = status_icons.get(status, '•')
    print(f"Status: {status_icon} {status.upper()}")
    
    # Route info
    from_station = task.get('from_station', 'Unknown')
    to_station = task.get('to_station', 'Unknown')
    print(f"Route: Station {from_station} -> Station {to_station}")
    print(f"Date: {task.get('date', 'Not specified')}")
    
    # Passenger info
    passengers = []
    adult_cnt = task.get('adult_cnt') or 0
    student_cnt = task.get('student_cnt') or 0
    child_cnt = task.get('child_cnt') or 0
    senior_cnt = task.get('senior_cnt') or 0
    disabled_cnt = task.get('disabled_cnt') or 0
    
    if adult_cnt > 0:
        passengers.append(f"成人 {adult_cnt}")
    if student_cnt > 0:
        passengers.append(f"學生 {student_cnt}")
    if child_cnt > 0:
        passengers.append(f"兒童 {child_cnt}")
    if senior_cnt > 0:
        passengers.append(f"敬老 {senior_cnt}")
    if disabled_cnt > 0:
        passengers.append(f"愛心 {disabled_cnt}")
    
    if passengers:
        print(f"Passengers: {' + '.join(passengers)}")
    
    # Timing info
    if task.get('created_at'):
        try:
            created = datetime.fromisoformat(task['created_at'].replace('Z', '+00:00'))
            print(f"Created: {created.strftime('%Y-%m-%d %H:%M:%S')}")
        except:
            print(f"Created: {task['created_at']}")
    
    # Progress info
    attempts = task.get('attempts', 0)
    max_attempts = task.get('max_attempts')
    max_str = f"/{max_attempts}" if max_attempts else "/∞"
    print(f"Attempts: {attempts}{max_str}")
    print(f"Interval: {task.get('interval_minutes', 5)} minutes")
    
    if task.get('last_attempt'):
        try:
            last_attempt = datetime.fromisoformat(task['last_attempt'].replace('Z', '+00:00'))
            print(f"Last Attempt: {last_attempt.strftime('%Y-%m-%d %H:%M:%S')}")
        except:
            print(f"Last Attempt: {task['last_attempt']}")
    
    # Result info
    if status == 'success' and task.get('success_pnr'):
        print(f"✓ SUCCESS!")
        pnr = task['success_pnr']
        # Clean ANSI color codes
        if isinstance(pnr, str):
            pnr = pnr.replace('\u001b[38;5;46m', '').replace('\u001b[0m', '').strip()
        print(f"PNR Code: {pnr}")
    elif task.get('error_message'):
        print(f"× Last Error: {task['error_message']}")


def display_summary(tasks: List[Dict[str, Any]], users: Dict[str, Dict[str, Any]] = None) -> None:
    """Display summary statistics."""
    if not tasks:
        print("\n>> No tasks found")
        return
    
    # Calculate statistics
    total = len(tasks)
    status_counts = {}
    total_attempts = 0
    successful_pnrs = []
    user_stats = {}
    
    for task in tasks:
        # Status stats
        status = task.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
        total_attempts += task.get('attempts', 0)
        
        # Success stats
        if status == 'success' and task.get('success_pnr'):
            pnr = task['success_pnr']
            if isinstance(pnr, str):
                pnr = pnr.replace('\u001b[38;5;46m', '').replace('\u001b[0m', '').strip()
            successful_pnrs.append(pnr)
        
        # User stats
        user_id = task.get('user_id')
        if user_id:
            if user_id not in user_stats:
                user_stats[user_id] = {'tasks': 0, 'success': 0}
            user_stats[user_id]['tasks'] += 1
            if status == 'success':
                user_stats[user_id]['success'] += 1
    
    print(f"\n>> Task Summary")
    print(f"{'='*50}")
    print(f"Total Tasks: {total}")
    print(f"Total Attempts: {total_attempts}")
    success_count = len(successful_pnrs)
    success_rate = success_count / total * 100 if total > 0 else 0
    print(f"Success Rate: {success_count}/{total} ({success_rate:.1f}%)")
    
    print(f"\nStatus Breakdown:")
    status_icons = {
        'success': '✓',
        'running': '○',
        'pending': '⏳',
        'failed': '×',
        'error': '×',
        'expired': '⏰',
        'cancelled': '🚫'
    }
    
    for status, count in status_counts.items():
        percentage = count / total * 100
        icon = status_icons.get(status.lower(), '•')
        print(f"  {icon} {status.upper()}: {count} ({percentage:.1f}%)")
    
    # User statistics
    if user_stats and users:
        print(f"\nUser Statistics:")
        for user_id, stats in user_stats.items():
            user = users.get(user_id, {})
            username = user.get('full_name', user.get('username', f'User {user_id}'))
            user_success_rate = stats['success'] / stats['tasks'] * 100 if stats['tasks'] > 0 else 0
            print(f"  {username}: {stats['success']}/{stats['tasks']} ({user_success_rate:.1f}%)")
    
    if successful_pnrs:
        print(f"\n>> Successful Bookings:")
        for pnr in successful_pnrs:
            print(f"  ✓ PNR: {pnr}")


def main():
    """Main CLI viewer."""
    parser = argparse.ArgumentParser(description="THSR-Sniper Direct Results Viewer")
    parser.add_argument("--details", action="store_true", help="Show detailed task information")
    parser.add_argument("--task-id", help="Show specific task details")
    parser.add_argument("--storage-path", help="Path to scheduler storage file")
    parser.add_argument("--no-db", action="store_true", help="Skip database user lookup")
    parser.add_argument("--user", help="Filter tasks by user ID")
    parser.add_argument("--status", help="Filter tasks by status")
    
    args = parser.parse_args()
    
    print(">> THSR-Sniper Direct Results Viewer")
    print("=" * 50)
    
    # Load tasks from storage
    storage_path = args.storage_path or "/app/data/thsr_scheduler.json"
    tasks = load_tasks_from_storage(storage_path)
    
    if not tasks:
        print(">> No tasks found in storage.")
        print("   This is normal if no booking tasks have been created yet.")
        print("   Create tasks through the web interface or API first.")
        return  # Exit successfully with exit code 0
    
    # Load users from database if available
    users = {} if args.no_db else load_users_from_db()
    
    # Show initial task count for debugging
    print(f"✓ Found {len(tasks)} total tasks before filtering")
    
    # Filter tasks
    if args.task_id:
        tasks = [task for task in tasks if task.get('id') == args.task_id]
        if not tasks:
            print(f"Task with ID '{args.task_id}' not found.")
            sys.exit(1)
    
    if args.user:
        original_count = len(tasks)
        # Convert user argument to string for comparison since user_id is stored as string
        user_filter = str(args.user)
        tasks = [task for task in tasks if str(task.get('user_id', '')) == user_filter]
        print(f"✓ Filtered by user '{user_filter}': {len(tasks)} tasks (from {original_count} total)")
        if not tasks:
            print(f"No tasks found for user '{args.user}'.")
            print("Available user IDs in tasks:")
            all_user_ids = set(str(task.get('user_id', 'None')) for task in load_tasks_from_storage(args.storage_path or "/app/data/thsr_scheduler.json"))
            for uid in sorted(all_user_ids):
                print(f"  - {uid}")
            sys.exit(1)
    
    if args.status:
        original_count = len(tasks)
        tasks = [task for task in tasks if task.get('status', '').lower() == args.status.lower()]
        print(f"✓ Filtered by status '{args.status}': {len(tasks)} tasks (from {original_count} total)")
        if not tasks:
            print(f"No tasks found with status '{args.status}'.")
            sys.exit(1)
    
    # Display results
    if args.task_id:
        # Show specific task
        format_task_details(tasks[0], users)
    else:
        # Show summary and optionally details
        display_summary(tasks, users)
        
        if args.details:
            print(f"\n>> Detailed Task Information:")
            for task in tasks:
                format_task_details(task, users)


if __name__ == "__main__":
    main()
