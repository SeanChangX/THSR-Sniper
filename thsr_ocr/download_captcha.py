#!/usr/bin/env python3
"""
Script to automatically download specified number of captcha images (tmp_code.jpg)
from THSR booking system and save them to a folder.
"""

import os
import time
import requests
from bs4 import BeautifulSoup
import argparse
from pathlib import Path


def _headers() -> dict:
    """Get headers similar to flows.py"""
    return {
        "Host": "irs.thsrc.com.tw",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": "https://irs.thsrc.com.tw/IMINT/",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "no-cors",
    }


def download_captcha_images(count: int, output_dir: str = "captcha_images", delay: float = 1.0, also_save_to_tmp: bool = True):
    """
    Download specified number of captcha images from THSR booking system.
    
    Args:
        count: Number of images to download
        output_dir: Directory to save images (will be created if not exists)
        delay: Delay between requests in seconds
        also_save_to_tmp: Also save each image to /tmp/tmp_code.jpg (like flows.py)
    """
    BASE_URL = "https://irs.thsrc.com.tw"
    BOOKING_PAGE_URL = f"{BASE_URL}/IMINT/?locale=tw"
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    print(f"Output directory: {output_path.absolute()}")
    
    if also_save_to_tmp:
        print("Also saving to /tmp/tmp_code.jpg (like flows.py)")
    
    # Create session for persistent cookies
    session = requests.Session()
    session.headers.update(_headers())
    session.max_redirects = 20
    
    print(f"Starting download of {count} captcha images...")
    
    for i in range(1, count + 1):
        try:
            print(f"\n--- Downloading image {i}/{count} ---")
            
            # Step 1: Get the booking page to establish session
            print(f"  Step 1: Accessing booking page...")
            r = session.get(BOOKING_PAGE_URL, timeout=30)
            r.raise_for_status()
            print(f"  ✓ Booking page loaded successfully")
            
            # Parse JSESSIONID from cookies (similar to flows.py)
            jsession = None
            for c in session.cookies:
                if c.name == "JSESSIONID":
                    jsession = c.value
                    break
            if not jsession:
                # Fallback try from response cookies
                for c in r.cookies:
                    if c.name == "JSESSIONID":
                        jsession = c.value
                        break
            
            if jsession:
                print(f"  ✓ Session ID: {jsession[:20]}...")
            else:
                print(f"  ⚠ Warning: No session ID found")
            
            # Step 2: Parse the page to get captcha image source
            print(f"  Step 2: Parsing page for captcha image...")
            soup = BeautifulSoup(r.text, 'html.parser')
            img_src = soup.select_one("#BookingS1Form_homeCaptcha_passCode")
            
            if not img_src:
                print(f"  ✗ Failed to find captcha image source on attempt {i}")
                print(f"  Page content preview: {r.text[:200]}...")
                continue
                
            img_url = f"{BASE_URL}{img_src.get('src')}"
            print(f"  ✓ Found captcha image URL: {img_url}")
            
            # Step 3: Download the captcha image
            print(f"  Step 3: Downloading captcha image...")
            img_r = session.get(img_url, timeout=30)
            img_r.raise_for_status()
            print(f"  ✓ Captcha image downloaded ({len(img_r.content)} bytes)")
            
            # Step 4: Save the image to both locations
            print(f"  Step 4: Saving image...")
            
            # Save to numbered file in output directory
            filename = f"captcha_{i:03d}.jpg"
            filepath = output_path / filename
            
            with open(filepath, 'wb') as f:
                f.write(img_r.content)
            
            print(f"  ✓ Successfully saved: {filename}")
            print(f"  ✓ File size: {len(img_r.content)} bytes")
            
            # Also save to /tmp/tmp_code.jpg (like flows.py)
            if also_save_to_tmp:
                try:
                    tmp_file = "/tmp/tmp_code.jpg"
                    with open(tmp_file, 'wb') as f:
                        f.write(img_r.content)
                    print(f"  ✓ Also saved to: {tmp_file}")
                except Exception as e:
                    print(f"  ⚠ Warning: Could not save to {tmp_file}: {e}")
            
            # Add delay between requests to be respectful
            if i < count:
                print(f"  Waiting {delay} seconds before next request...")
                time.sleep(delay)
                
        except requests.exceptions.Timeout:
            print(f"  ✗ Timeout error on attempt {i} - request took too long")
            continue
        except requests.exceptions.ConnectionError as e:
            print(f"  ✗ Connection error on attempt {i}: {e}")
            print(f"  Waiting 5 seconds before retry...")
            time.sleep(5)
            continue
        except requests.exceptions.RequestException as e:
            print(f"  ✗ Request error on attempt {i}: {e}")
            continue
        except Exception as e:
            print(f"  ✗ Unexpected error on attempt {i}: {e}")
            continue
    
    print(f"\n--- Download Summary ---")
    print(f"Total images requested: {count}")
    print(f"Images saved to: {output_path.absolute()}")
    
    if also_save_to_tmp:
        print(f"Last image also saved to: /tmp/tmp_code.jpg")
    
    # Count actual downloaded files
    actual_count = len(list(output_path.glob("captcha_*.jpg")))
    print(f"Actual images downloaded: {actual_count}")
    
    if actual_count < count:
        print(f"Warning: Only {actual_count}/{count} images were successfully downloaded")


def main():
    parser = argparse.ArgumentParser(
        description="Download captcha images from THSR booking system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 download_captcha.py 10                    # Download 10 images to default folder
  python3 download_captcha.py 50 -o my_images      # Download 50 images to 'my_images' folder
  python3 download_captcha.py 100 -d 2.0           # Download 100 images with 2 second delay
  python3 download_captcha.py 5 --no-tmp           # Download 5 images without saving to /tmp
        """
    )
    
    parser.add_argument(
        'count',
        type=int,
        help='Number of captcha images to download'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='captcha_images',
        help='Output directory for images (default: captcha_images)'
    )
    
    parser.add_argument(
        '-d', '--delay',
        type=float,
        default=1.0,
        help='Delay between requests in seconds (default: 1.0)'
    )
    
    parser.add_argument(
        '--no-tmp',
        action='store_true',
        help='Do not save to /tmp/tmp_code.jpg (default: saves to both locations)'
    )
    
    args = parser.parse_args()
    
    if args.count <= 0:
        print("Error: Count must be a positive number")
        return 1
    
    if args.delay < 0:
        print("Error: Delay must be non-negative")
        return 1
    
    try:
        download_captcha_images(args.count, args.output, args.delay, not args.no_tmp)
        return 0
    except KeyboardInterrupt:
        print("\nDownload interrupted by user")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
