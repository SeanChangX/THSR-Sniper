#!/usr/bin/env python3

import sys
import time
from thsr_py.cli import parse_args
from thsr_py.flows import run, show_station, show_time_table


def _preload_ocr_if_needed(args) -> None:
    """Preload OCR model if booking functionality will be used."""
    # Only preload for booking operations (not for info queries or API mode)
    if (not args.no_ocr and 
        not args.times and 
        not args.stations and 
        not args.start_api and 
        not args.list_tasks and 
        not args.task_status and 
        not args.cancel_task):
        
        start_time = time.time()
        
        try:
            # Import and initialize OCR to warm up the model
            import os
            from pathlib import Path
            
            # Set TensorFlow to be quiet
            os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
            
            # Try to load model path
            if getattr(sys, 'frozen', False):
                # Running in PyInstaller bundle
                bundle_dir = Path(sys._MEIPASS)
                model_path = str(bundle_dir / "thsr_ocr" / "thsr_prediction_model_250827.keras")
            else:
                # Running in development
                model_path = str(Path(__file__).parent / "thsr_ocr" / "thsr_prediction_model_250827.keras")
            
            if os.path.exists(model_path):
                # Add OCR path to sys.path
                if getattr(sys, 'frozen', False):
                    sys.path.append(str(bundle_dir / "thsr_ocr"))
                else:
                    sys.path.append(str(Path(__file__).parent / "thsr_ocr"))
                
                from test_model import CaptchaModelTester
                
                # Initialize model (this takes the most time)
                tester = CaptchaModelTester(model_path)
                
                print(f"OCR Model Loaded")
            else:
                print("OCR Model Not Found, Falling Back to Manual Input")

        except Exception as e:
            print(f"OCR Preload Failed: {e}")

def main() -> None:
    args = parse_args()
    
    # Preload OCR model for better user experience
    _preload_ocr_if_needed(args)

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
