#!/usr/bin/env python3

from thsr_py.cli import parse_args
from thsr_py.flows import run, show_station, show_time_table


def main() -> None:
    args = parse_args()

    # Information queries
    if args.times:
        show_time_table()
        return

    if args.stations:
        show_station()
        return

    # API server mode
    if args.start_api:
        from thsr_py.api import run_api_server
        print(f"Starting THSR-Sniper API server on {args.api_host}:{args.api_port}")
        print(f"API documentation available at: http://{args.api_host}:{args.api_port}/docs")
        run_api_server(host=args.api_host, port=args.api_port)
        return

    # Scheduler task management (via API)
    if args.list_tasks:
        from thsr_py.api_client import list_tasks_via_api
        list_tasks_via_api()
        return

    if args.task_status:
        from thsr_py.api_client import THSRApiClient, show_task_status
        client = THSRApiClient()
        show_task_status(client, args.task_status)
        return

    if args.cancel_task:
        from thsr_py.api_client import THSRApiClient, cancel_task_interactive
        client = THSRApiClient()
        cancel_task_interactive(client, args.cancel_task)
        return

    # Scheduled booking mode (via API)
    if args.schedule:
        from thsr_py.api_client import schedule_booking_via_api
        schedule_booking_via_api(args)
        return

    # Default: immediate booking
    run(args)


if __name__ == "__main__":
    main()
