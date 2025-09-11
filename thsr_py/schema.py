from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

STATION_MAP = [
    "Nangang",
    "Taipei",
    "Banqiao",
    "Taoyuan",
    "Hsinchu",
    "Miaoli",
    "Taichung",
    "Changhua",
    "Yunlin",
    "Chiayi",
    "Tainan",
    "Zuouing",
]

TIME_TABLE = [
    "1201A",
    "1230A",
    "600A",
    "630A",
    "700A",
    "730A",
    "800A",
    "830A",
    "900A",
    "930A",
    "1000A",
    "1030A",
    "1100A",
    "1130A",
    "1200N",
    "1230P",
    "100P",
    "130P",
    "200P",
    "230P",
    "300P",
    "330P",
    "400P",
    "430P",
    "500P",
    "530P",
    "600P",
    "630P",
    "700P",
    "730P",
    "800P",
    "830P",
    "900P",
    "930P",
    "1000P",
    "1030P",
    "1100P",
    "1130P",
]

class TicketType:
    Adult = "F"
    Child = "H"
    Disabled = "W"
    Elder = "E"
    College = "P"


# Taiwan timezone utilities
TAIWAN_TZ = timezone(timedelta(hours=8))


def get_taiwan_now() -> datetime:
    """Get current time in Taiwan timezone."""
    return datetime.now(TAIWAN_TZ)


def is_ticket_sales_open(booking_date: str) -> bool:
    """
    Check if ticket sales are open for the given booking date.
    Taiwan High Speed Rail ticket sales open 28 days in advance at 00:00 Taiwan time.
    We allow some flexibility for early sales due to holidays or special promotions.
    """
    try:
        # Parse booking date
        booking_date_obj = datetime.strptime(booking_date, "%Y/%m/%d").date()
        taiwan_now = get_taiwan_now()
        
        # Calculate the date when ticket sales should open (28 days before booking date)
        sales_open_date = booking_date_obj - timedelta(days=28)
        
        # Allow more flexibility: start trying 4 days before official opening
        # This handles cases where sales open early due to holidays or promotions
        flexible_open_date = sales_open_date - timedelta(days=4)
        
        # Check if we're past the flexible open date
        return taiwan_now.date() >= flexible_open_date
    except ValueError:
        return False


def parse_time_string(time_str: str) -> Optional[datetime]:
    """
    Parse time string from train data (e.g., "0800", "1430", "07:58") to datetime object.
    Returns None if parsing fails.
    """
    try:
        # Handle HH:MM format (e.g., "07:58")
        if ':' in time_str:
            hour, minute = time_str.split(':')
            hour = int(hour)
            minute = int(minute)
            return datetime.now(TAIWAN_TZ).replace(hour=hour, minute=minute, second=0, microsecond=0)
        # Handle HHMM format (e.g., "0800")
        elif len(time_str) == 4:
            hour = int(time_str[:2])
            minute = int(time_str[2:])
            return datetime.now(TAIWAN_TZ).replace(hour=hour, minute=minute, second=0, microsecond=0)
    except (ValueError, IndexError):
        pass
    return None


def find_closest_train_within_range(trains: List[Dict[str, str]], target_time_idx: int, tolerance_hours: float = 0.5) -> Optional[Dict[str, str]]:
    """
    Find the closest train within ±tolerance_hours of the target time.
    Returns the train closest to the target time, or None if no trains are within range.
    """
    if not trains or target_time_idx < 1 or target_time_idx > len(TIME_TABLE):
        return None
    
    target_time_str = TIME_TABLE[target_time_idx - 1]
    target_time = _parse_time_table_to_datetime(target_time_str)
    if not target_time:
        return None
    
    valid_trains = []
    
    for train in trains:
        depart_time_str = train.get('depart', '')
        if not depart_time_str:
            continue
            
        train_time = parse_time_string(depart_time_str)
        if not train_time:
            continue
        
        # Calculate time difference in hours
        time_diff = abs((train_time - target_time).total_seconds()) / 3600
        
        if time_diff <= tolerance_hours:
            valid_trains.append((train, time_diff))
    
    if not valid_trains:
        return None
    
    # Return the train with the smallest time difference
    valid_trains.sort(key=lambda x: x[1])
    return valid_trains[0][0]


def _parse_time_table_to_datetime(time_str: str) -> Optional[datetime]:
    """
    Parse time string from TIME_TABLE (e.g., "800A", "200P") to datetime object.
    Returns None if parsing fails.
    """
    try:
        # Remove the last character (A/P/N)
        time_part = time_str[:-1]
        period = time_str[-1]
        
        # Convert to integer
        time_int = int(time_part)
        
        # Handle special cases
        if period == 'A' and time_int // 100 == 12:
            # 1201A, 1230A -> 00:01, 00:30
            time_int = time_int % 1200
        elif period == 'P' and time_int != 1230:
            # PM times (except 1230P which is noon)
            time_int += 1200
        elif period == 'N':
            # 1200N is noon
            time_int = 1200
        
        hour = time_int // 100
        minute = time_int % 100
        
        return datetime.now(TAIWAN_TZ).replace(hour=hour, minute=minute, second=0, microsecond=0)
    except (ValueError, IndexError):
        return None
