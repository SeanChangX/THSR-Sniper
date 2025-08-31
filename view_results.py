#!/usr/bin/env python3
"""
Results viewer for THSR-Sniper scheduled tasks.
Uses API to fetch and display task results.
"""

import sys
import json
from typing import Optional
import requests
from datetime import datetime


def get_api_data(endpoint: str, base_url: str = "http://localhost:8000") -> Optional[list]:
    """Fetch data from API endpoint."""
    try:
        response = requests.get(f"{base_url}{endpoint}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        print("× Error: Cannot connect to THSR-Sniper API")
        print("   Make sure the API server is running:")
        print("   docker compose up -d api")
        return None
    except Exception as e:
        print(f"× Error fetching data: {e}")
        return None


def format_task_details(task: dict) -> None:
    """Format and display detailed task information."""
    print(f"\n{'='*80}")
    print(f"Task ID: {task['id']}")
    print(f"{'='*80}")
    
    # Basic info
    status_symbol = "✓" if task['status'].lower() == 'success' else "○" if task['status'].lower() == 'running' else "×" if task['status'].lower() in ['failed', 'error'] else "•"
    print(f"Status: {status_symbol} {task['status'].upper()}")
    print(f"Route: Station {task['from_station']} -> Station {task['to_station']}")
    print(f"Date: {task['date']}")
    print(f"Created: {datetime.fromisoformat(task['created_at'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Progress info
    print(f"Attempts: {task['attempts']}")
    print(f"Interval: {task['interval_minutes']} minutes")
    
    if task.get('last_attempt'):
        last_attempt = datetime.fromisoformat(task['last_attempt'].replace('Z', '+00:00'))
        print(f"Last Attempt: {last_attempt.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Result info
    if task['status'] == 'success' and task.get('success_pnr'):
        print(f"✓ SUCCESS!")
        print(f"PNR Code: {task['success_pnr']}")
    elif task.get('error_message'):
        print(f"× Last Error: {task['error_message']}")


def display_summary(tasks: list) -> None:
    """Display summary statistics."""
    if not tasks:
        print("\n>> No tasks found")
        return
    
    # Calculate statistics
    total = len(tasks)
    status_counts = {}
    total_attempts = 0
    successful_pnrs = []
    
    for task in tasks:
        status = task['status']
        status_counts[status] = status_counts.get(status, 0) + 1
        total_attempts += task.get('attempts', 0)
        
        if status == 'success' and task.get('success_pnr'):
            successful_pnrs.append(task['success_pnr'])
    
    print(f"\n>> Task Summary")
    print(f"{'='*60}")
    print(f"Total Tasks: {total}")
    print(f"Total Attempts: {total_attempts}")
    print(f"Success Rate: {len(successful_pnrs)}/{total} ({len(successful_pnrs)/total*100:.1f}%)")
    
    print(f"\nStatus Breakdown:")
    for status, count in status_counts.items():
        percentage = count / total * 100
        status_symbol = "✓" if status.lower() == 'success' else "○" if status.lower() == 'running' else "×" if status.lower() in ['failed', 'error'] else "•"
        print(f"  {status_symbol} {status.upper()}: {count} ({percentage:.1f}%)")
    
    if successful_pnrs:
        print(f"\n>> Successful Bookings:")
        for pnr in successful_pnrs:
            print(f"  ✓ PNR: {pnr}")


def main():
    """Main results viewer."""
    import argparse
    
    parser = argparse.ArgumentParser(description="THSR-Sniper Results Viewer")
    parser.add_argument("--details", action="store_true", help="Show detailed task information")
    parser.add_argument("--task-id", help="Show specific task details")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API server URL")
    
    args = parser.parse_args()
    
    print(">> THSR-Sniper Results Viewer")
    print("=" * 50)
    
    if args.task_id:
        # Show specific task
        task = get_api_data(f"/tasks/{args.task_id}", args.api_url)
        if task:
            format_task_details(task)
    else:
        # Show all tasks
        tasks = get_api_data("/tasks", args.api_url)
        if tasks is None:
            sys.exit(1)
        
        display_summary(tasks)
        
        if args.details and tasks:
            print(f"\n>> Detailed Task Information:")
            for task in tasks:
                format_task_details(task)


if __name__ == "__main__":
    main()
