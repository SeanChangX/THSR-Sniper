from __future__ import annotations

import os
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from .schema import STATION_MAP, TIME_TABLE, TicketType

BASE_URL = "https://irs.thsrc.com.tw"
BOOKING_PAGE_URL = f"{BASE_URL}/IMINT/?locale=tw"
SUBMIT_FORM_URL = (
    "https://irs.thsrc.com.tw/IMINT/;jsessionid={}?wicket:interface=:0:BookingS1Form::IFormSubmitListener"
)
CONFIRM_TRAIN_URL = (
    "https://irs.thsrc.com.tw/IMINT/?wicket:interface=:1:BookingS2Form::IFormSubmitListener"
)
CONFIRM_TICKET_URL = (
    "https://irs.thsrc.com.tw/IMINT/?wicket:interface=:2:BookingS3Form::IFormSubmitListener"
)


def _print_header(title: str) -> None:
    """Print a formatted header with THSR banner."""
    if title == "THSR-Sniper":
        # Display full THSR banner like in CLI
        _print_thsr_banner()
    else:
        # Regular header for other sections
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")


def _print_thsr_banner() -> None:
    """Print the THSR-Sniper banner with colors."""
    # Check if we're in a terminal that supports colors
    if os.environ.get('TERM') and '256' in os.environ.get('TERM', ''):
        # ANSI color codes for 256-color terminals - using THSR theme color #ca4f0f
        thsr_red = '\033[38;5;166m'  # Close to #ca4f0f
        reset = '\033[0m'
        
        banner = f"""{thsr_red}╔══════════════════════════════════════════════════════════════════════════════╗{reset}
{thsr_red}║       ________  _______ ____              _____       _                      ║{reset}
{thsr_red}║      /_  __/ / / / ___// __ \\            / ___/____  (_)___  ___  _____      ║{reset}
{thsr_red}║       / / / /_/ /\\__ \\/ /_/ /  ______    \\__ \\/ __ \\/ / __ \\/ _ \\/ ___/      ║{reset}
{thsr_red}║      / / / __  /___/ / _, _/  /_____/   ___/ / / / / / /_/ /  __/ /          ║{reset}
{thsr_red}║     /_/ /_/ /_//____/_/ |_|            /____/_/ /_/_/ .___/\\___/_/           ║{reset}
{thsr_red}║                                                    /_/                       ║{reset}
{thsr_red}║                                                                              ║{reset}
{thsr_red}║                    Taiwan High Speed Rail Ticket Sniper                      ║{reset}
{thsr_red}║                                                                              ║{reset}
{thsr_red}║    A modern CLI tool for booking THSR tickets with intelligent automation.   ║{reset}
{thsr_red}║    Features automatic captcha recognition and comprehensive booking flow.    ║{reset}
{thsr_red}║                                                                              ║{reset}
{thsr_red}╚══════════════════════════════════════════════════════════════════════════════╝{reset}
        """
        print(banner)
    else:
        # Fallback for terminals without color support
        banner = r"""
╔══════════════════════════════════════════════════════════════════════════════╗
║       ________  _______ ____              _____       _                      ║
║      /_  __/ / / / ___// __ \            / ___/____  (_)___  ___  _____      ║
║       / / / /_/ /\__ \/ /_/ /  ______    \__ \/ __ \/ / __ \/ _ \/ ___/      ║
║      / / / __  /___/ / _, _/  /_____/   ___/ / / / / / /_/ /  __/ /          ║
║     /_/ /_/ /_//____/_/ |_|            /____/_/ /_/_/ .___/\___/_/           ║
║                                                    /_/                       ║
║                                                                              ║
║                    Taiwan High Speed Rail Ticket Sniper                      ║
║                                                                              ║
║    A modern CLI tool for booking THSR tickets with intelligent automation.   ║
║    Features automatic captcha recognition and comprehensive booking flow.    ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """
        print(banner)


def _print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'-'*40}")
    print(f"  {title}")
    print(f"{'-'*40}")


def _headers() -> Dict[str, str]:
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


def _get_input(prompt: str, default, choices: Optional[List] = None) -> any:
    """Get user input with modern formatting and validation."""
    if choices:
        print(f"\n{prompt}")
        # print(f"Available options: {', '.join(map(str, choices))}")
        # print(f"Default: {default}")
    else:
        print(f"\n{prompt}")
        # if default is not None:
        #     print(f"Default: {default}")
    
    try:
        val = input("> ").strip()
    except EOFError:
        val = ""
    
    if val == "":
        return default
    
    # Try to convert to the same type as default
    try:
        if default is not None:
            return type(default)(val)
        return val
    except (ValueError, TypeError):
        return val


def _parse_error(soup: BeautifulSoup) -> Optional[str]:
    errors = [e.get_text(strip=True) for e in soup.select("span.feedbackPanelERROR")]
    return "\n".join(errors) if errors else None


def show_station() -> None:
    """Display all available stations in a modern format."""
    _print_header("Available Stations")
    print("ID  | Station Name")
    print("----|-------------")
    for idx, name in enumerate(STATION_MAP, start=1):
        print(f"{idx:2d}  | {name}")
    # print(f"\nTotal: {len(STATION_MAP)} stations")


def show_time_table() -> None:
    """Display all available departure times in a modern format."""
    _print_header("Available Departure Times")
    print("ID  | Time  | ID  | Time  | ID  | Time  | ID  | Time")
    print("----|-------|-----|-------|-----|-------|-----|------")
    
    for i in range(0, len(TIME_TABLE), 4):
        row = []
        for j in range(4):
            idx = i + j
            if idx < len(TIME_TABLE):
                t_str = TIME_TABLE[idx]
                t_int = int(t_str[:-1])
                if t_str.endswith("A") and t_int // 100 == 12:
                    t_int %= 1200
                elif t_int != 1230 and t_str.endswith("P"):
                    t_int += 1200
                formatted_time = f"{t_int:04d}"
                time_str = f"{formatted_time[:-2]}:{formatted_time[-2:]}"
                row.append(f"{idx+1:2d}  | {time_str}")
            else:
                row.append("    |      ")
        print(" | ".join(row))
    
    # print(f"\nTotal: {len(TIME_TABLE)} time slots")


def run(args) -> None:
    """Main booking flow with modern interface."""
    _print_header("THSR-Sniper")
    
    session = requests.Session()
    session.headers.update(_headers())
    session.max_redirects = 20

    # First page
    _print_section("Step 1: Initializing Booking Session")
    print("Connecting to THSR booking system...")
    
    try:
        r = session.get(BOOKING_PAGE_URL, timeout=60)
        r.raise_for_status()
        print("✓ Connected successfully")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return

    # Parse JSESSIONID
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
    if not jsession:
        print("✗ Error: Cannot establish session")
        return

    print("✓ Session established")

    soup = BeautifulSoup(r.text, "html.parser")

    # Security code image
    _print_section("Step 2: Security Verification")
    img_src = soup.select_one("#BookingS1Form_homeCaptcha_passCode").get("src")
    img_url = f"{BASE_URL}{img_src}"
    
    try:
        img_r = session.get(img_url, timeout=60)
        img_r.raise_for_status()
        print("✓ Captcha image downloaded")
    except Exception as e:
        print(f"✗ Failed to download captcha: {e}")
        return

    _show_image(img_r.content)

    # Build payload
    _print_section("Step 3: Journey Configuration")
    payload = _BookingPayload.default()
    payload.search_by = _parse_search_by(soup)
    payload.types_of_trip = _parse_types_of_trip_value(soup)
    
    payload.select_start_station(getattr(args, "from_", None))
    payload.select_dest_station(getattr(args, "to", None))
    
    start_date, end_date = _parse_avail_start_end_date(soup)
    payload.select_date(start_date, end_date, getattr(args, "date", None))
    payload.select_time(getattr(args, "time", None))

    # Handle ticket selection logic properly
    adult_cnt = getattr(args, "adult_cnt", None)
    student_cnt = getattr(args, "student_cnt", None)
    
    if adult_cnt is None and student_cnt is None:
        # No tickets specified, default to 1 adult ticket
        payload.select_ticket_num(TicketType.Adult, None)
    else:
        # Tickets specified, use explicit counts
        if adult_cnt is not None:
            payload.select_ticket_num(TicketType.Adult, adult_cnt)
        elif student_cnt is not None:
            # If only student tickets specified, set adult tickets to 0
            payload.select_ticket_num(TicketType.Adult, 0)
        
        if student_cnt is not None:
            payload.select_ticket_num(TicketType.College, student_cnt)

    payload.select_seat_prefer(getattr(args, "seat_prefer", None))
    payload.select_class_type(getattr(args, "class_type", None))

    payload.input_security_code(img_r.content, not getattr(args, "no_ocr", False))

    # Submit booking request
    _print_section("Step 4: Submitting Booking Request")
    print("Sending booking request...")
    
    try:
        r = session.post(
            SUBMIT_FORM_URL.format(jsession),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=payload.to_form(),
            timeout=60,
        )
        r.raise_for_status()
        print("✓ Booking request submitted")
    except Exception as e:
        print(f"✗ Booking request failed: {e}")
        return

    soup = BeautifulSoup(r.text, "html.parser")
    err = _parse_error(soup)
    if err:
        print(f"✗ Booking error: {err}")
        return

    # Second page
    _print_section("Step 5: Train Selection")
    train_index = getattr(args, "train_index", None)
    soup = _confirm_train_flow(session, soup, train_index)
    if soup is None:
        return

    # Final page
    _print_section("Step 6: Final Confirmation")
    soup = _confirm_ticket_flow(session, soup, args)
    if soup is None:
        return

    _print_section("Booking Complete")
    _show_result(soup)


def _parse_avail_start_end_date(soup: BeautifulSoup) -> Tuple[str, str]:
    elem = soup.select_one("#toTimeInputField")
    return elem.get("date"), elem.get("limit")


def _parse_types_of_trip_value(soup: BeautifulSoup) -> int:
    elem = soup.select_one("#BookingS1Form_tripCon_typesoftrip")
    sel = elem.select_one("[selected='selected']")
    return int(sel.get("value"))


def _parse_search_by(soup: BeautifulSoup) -> str:
    for tag in soup.select("input[name='bookingMethod']"):
        if tag.has_attr("checked"):
            return tag.get("value")
    return "1"


@dataclass
class _BookingPayload:
    start_station: int = 1
    dest_station: int = 12
    search_by: str = "1"
    types_of_trip: int = 0
    outbound_date: str = "2023/10/01"
    outbound_time: str = "08:00"
    security_code: str = "1234"
    seat_prefer: int = 0
    form_mark: str = ""
    class_type: int = 0
    inbound_date: Optional[str] = None
    inbound_time: Optional[str] = None
    to_train_id: Optional[int] = None
    back_train_id: Optional[int] = None
    adult_ticket_num: str = "0F"
    child_ticket_num: str = "0H"
    disabled_ticket_num: str = "0W"
    elder_ticket_num: str = "0E"
    college_ticket_num: str = "0P"

    @staticmethod
    def default() -> "_BookingPayload":
        return _BookingPayload()

    def to_form(self) -> Dict[str, str]:
        d = {
            "selectStartStation": str(self.start_station),
            "selectDestinationStation": str(self.dest_station),
            "bookingMethod": self.search_by,
            "tripCon:typesoftrip": str(self.types_of_trip),
            "toTimeInputField": self.outbound_date,
            "toTimeTable": self.outbound_time,
            "homeCaptcha:securityCode": self.security_code,
            "seatCon:seatRadioGroup": str(self.seat_prefer),
            "BookingS1Form:hf:0": self.form_mark,
            "trainCon:trainRadioGroup": str(self.class_type),
            "ticketPanel:rows:0:ticketAmount": self.adult_ticket_num,
            "ticketPanel:rows:1:ticketAmount": self.child_ticket_num,
            "ticketPanel:rows:2:ticketAmount": self.disabled_ticket_num,
            "ticketPanel:rows:3:ticketAmount": self.elder_ticket_num,
            "ticketPanel:rows:4:ticketAmount": self.college_ticket_num,
        }
        if self.inbound_date:
            d["backTimeInputField"] = self.inbound_date
        if self.inbound_time:
            d["backTimeTable"] = self.inbound_time
        if self.to_train_id is not None:
            d["toTrainIDInputField"] = str(self.to_train_id)
        if self.back_train_id is not None:
            d["backTrainIDInputField"] = str(self.back_train_id)
        return d

    def select_start_station(self, from_idx: Optional[int]) -> None:
        if from_idx is not None:
            self.start_station = int(from_idx)
            return
        show_station()
        inp = _get_input("Select departure station (default: 1):", 1, list(range(1, len(STATION_MAP) + 1)))
        self.start_station = inp if 1 <= inp <= len(STATION_MAP) else 1

    def select_dest_station(self, to_idx: Optional[int]) -> None:
        if to_idx is not None:
            self.dest_station = int(to_idx)
            return
        show_station()
        inp = _get_input("Select arrival station (default: 12):", 12, list(range(1, len(STATION_MAP) + 1)))
        self.dest_station = inp if 1 <= inp <= len(STATION_MAP) else 12

    def _normalize_date(self, s: str) -> Optional[str]:
        try:
            y, m, d = s.split("/")
            y = f"{int(y):04d}"
            m = f"{int(m):02d}"
            d = f"{int(d):02d}"
            return f"{y}/{m}/{d}"
        except Exception:
            return None

    def select_date(self, start_date: str, end_date: str, date_value: Optional[str]) -> None:
        if date_value is None:
                    inp = _get_input(
            f"Select departure date (range: {start_date} to {end_date}, default: {start_date}):",
            start_date,
        )
        else:
            inp = date_value

        norm = self._normalize_date(inp)
        if not norm:
            print(f"Invalid date format, defaulting to {start_date}")
            self.outbound_date = start_date
            return
        if start_date <= norm <= end_date:
            self.outbound_date = norm
        else:
            print(f"Invalid date, defaulting to {start_date}")
            self.outbound_date = start_date

    def select_time(self, time_idx: Optional[int]) -> None:
        if time_idx is None:
            show_time_table()
            time_idx = _get_input("Select departure time (default: 10):", 10, list(range(1, len(TIME_TABLE) + 1)))
        if time_idx > len(TIME_TABLE):
            print("Invalid input, defaulting to 10.")
            self.outbound_time = TIME_TABLE[9]
        else:
            self.outbound_time = TIME_TABLE[time_idx - 1]

    def select_ticket_num(self, ticket_type: str, val: Optional[int]) -> None:
        if val is None:
                    val = _get_input(
            f"Select number of {ticket_type} tickets (0-10, default: 1)",
            1,
            list(range(0, 11))
        )
        if val > 10:
            print("Invalid input, defaulting to 1.")
            val = 1
        encoded = f"{val}{ticket_type}"
        if ticket_type == TicketType.Adult:
            self.adult_ticket_num = encoded
        elif ticket_type == TicketType.Child:
            self.child_ticket_num = encoded
        elif ticket_type == TicketType.Disabled:
            self.disabled_ticket_num = encoded
        elif ticket_type == TicketType.Elder:
            self.elder_ticket_num = encoded
        elif ticket_type == TicketType.College:
            self.college_ticket_num = encoded

    def select_seat_prefer(self, prefer: Optional[int]) -> None:
        if prefer is None:
                    prefer = _get_input(
            "Select seat preference (0: any, 1: window, 2: aisle, default: 0):",
            0,
            [0, 1, 2]
        )
        self.seat_prefer = prefer if prefer in (0, 1, 2) else 0

    def select_class_type(self, class_type: Optional[int]) -> None:
        if class_type is None:
                    class_type = _get_input(
            "Select class type (0: standard, 1: business, default: 0):",
            0,
            [0, 1]
        )
        self.class_type = class_type if class_type in (0, 1) else 0

    def input_security_code(self, img_bytes: Optional[bytes] = None, use_ocr: bool = True) -> None:
        """Input security code with OCR auto-recognition and manual fallback."""
        if img_bytes and use_ocr:
            # Try OCR first
            print("\nAttempting automatic captcha recognition...")
            ocr_result = _try_ocr_captcha(img_bytes)
            if ocr_result:
                self.security_code = ocr_result
                return
        
        # Fallback to manual input
        print("\nEnter the security code from the captcha image:")
        code = input("> ").strip()
        self.security_code = code


def _confirm_train_flow(session: requests.Session, soup: BeautifulSoup, train_index: Optional[int] = None) -> Optional[BeautifulSoup]:
    alerts = [e.get_text(strip=True) for e in soup.select("ul.alert-body > li")]
    if alerts:
        print("\n".join(alerts))

    trains = _parse_trains(soup)
    if not trains:
        print("✗ Error: No trains available for the selected criteria")
        return None
    
    if train_index:
        # Use the specified train index
        if train_index < 1 or train_index > len(trains):
            print(f"✗ Error: Train index {train_index} is out of range (1-{len(trains)})")
            return None
        selected_train = trains[train_index - 1]["form_value"]
        train_id = trains[train_index - 1]["id"]
        print(f"✓ Selected train {train_id} (index {train_index}) automatically")
    else:
        # Manual selection
        selected_train = _select_train(trains)
    
    payload = {"TrainQueryDataViewPanel:TrainGroup": selected_train, "BookingS2Form:hf:0": ""}
    r = session.post(
        CONFIRM_TRAIN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=payload,
        timeout=60,
    )
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    err = _parse_error(soup)
    if err:
        print(f"✗ Error: {err}")
        return None
    return soup


def _parse_trains(soup: BeautifulSoup) -> List[Dict[str, str]]:
    items = []
    for label in soup.select("label.result-item"):
        inp = label.select_one("input")
        items.append(
            {
                "id": inp.get("querycode"),
                "depart": inp.get("querydeparture"),
                "arrive": inp.get("queryarrival"),
                "travel_time": inp.get("queryestimatedtime"),
                "form_value": inp.get("value"),
                "discount": _parse_discount(label),
            }
        )
    return items


def _parse_discount(label) -> str:
    discounts = []
    p = label.select_one("p.early-bird span")
    if p:
        discounts.append(p.get_text(strip=True))
    p = label.select_one("p.student span")
    if p:
        discounts.append(p.get_text(strip=True))
    return f"({', '.join(discounts)})" if discounts else ""


def _select_train(trains: List[Dict[str, str]]) -> str:
    for idx, tr in enumerate(trains, start=1):
        print(
            f"{idx:>2}. {int(tr['id']):>4} {tr['depart']:>3}~{tr['arrive']} {tr['travel_time']:>3} {tr['discount']}"
        )
    sel = _get_input("Select a train (default: 1):", 1)
    sel = max(1, min(sel, len(trains)))
    return trains[sel - 1]["form_value"]


def _confirm_ticket_flow(session: requests.Session, soup: BeautifulSoup, args) -> Optional[BeautifulSoup]:
    payload = _ConfirmTicketPayload.default()
    personal_id = payload.input_personal_id(getattr(args, "personal_id", None))
    radio_value, additional_payload = _process_membership(soup, personal_id, getattr(args, "use_membership", None))
    payload.member_radio = radio_value

    form_data = payload.to_form()
    eb = _process_early_bird(soup, personal_id)
    if eb:
        form_data.update(eb)
    if additional_payload:
        form_data.update(additional_payload)

    print("Processing final confirmation...")
    r = session.post(
        CONFIRM_TICKET_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=form_data,
        timeout=60,
    )
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    err = _parse_error(soup)
    if err:
        print(f"✗ Error: {err}")
        return None
    return soup


@dataclass
class _ConfirmTicketPayload:
    personal_id: str = ""
    phone_num: str = ""
    member_radio: str = "0"
    form_mark: str = ""
    id_input_radio: int = 0
    diff_over: int = 1
    email: str = ""
    agree: str = "on"
    go_back_m: str = ""
    back_home: str = ""
    tgo_error: int = 1

    @staticmethod
    def default() -> "_ConfirmTicketPayload":
        return _ConfirmTicketPayload()

    def to_form(self) -> Dict[str, str]:
        return {
            "dummyId": self.personal_id,
            "dummyPhone": self.phone_num,
            "TicketMemberSystemInputPanel:TakerMemberSystemDataView:memberSystemRadioGroup": self.member_radio,
            "BookingS3FormSP:hf:0": self.form_mark,
            "idInputRadio": str(self.id_input_radio),
            "diffOver": str(self.diff_over),
            "email": self.email,
            "agree": self.agree,
            "isGoBackM": self.go_back_m,
            "backHome": self.back_home,
            "TgoError": str(self.tgo_error),
        }

    def input_personal_id(self, personal_id: Optional[str]) -> str:
        if personal_id is None:
            print("\nEnter your personal ID number:")
            personal_id = input("> ").strip()
        self.personal_id = personal_id.strip()
        return self.personal_id


def _process_membership(soup: BeautifulSoup, membership_id: str, to_use_membership: Optional[bool]):
    if to_use_membership is None:
        ask = _get_input("Use THSR membership? (y/n, default: n):", "n", ["y", "n", "yes", "no"])
        to_use_membership = str(ask).lower() == "y"

    sel = "#memberSystemRadio1" if to_use_membership else "#memberSystemRadio3"
    elem = soup.select_one(sel)
    membership_radio = elem.get("value")

    add = {}
    if to_use_membership:
        add[
            "TicketMemberSystemInputPanel:TakerMemberSystemDataView:memberSystemRadioGroup:memberShipNumber"
        ] = membership_id
        add[
            "TicketMemberSystemInputPanel:TakerMemberSystemDataView:memberSystemRadioGroup:memberSystemShipCheckBox"
        ] = "on"
    return membership_radio, add


def _process_early_bird(soup: BeautifulSoup, personal_id: str) -> Dict[str, str]:
    items = [e.get_text(strip=True) for e in soup.select(".superEarlyBird")]
    if not items:
        return {}

    def _ask_pid(i: int) -> str:
        while True:
            pid = _get_input(
                f"Enter passenger {i + 1} ID number (cannot be changed later):",
                "",
            )
            if pid:
                return pid
            print("ID should not be empty!")

    early_type = soup.select_one(
        "input[name='TicketPassengerInfoInputPanel:passengerDataView:0:passengerDataView2:passengerDataTypeName']"
    ).get("value")

    form: Dict[str, str] = {
        "TicketPassengerInfoInputPanel:passengerDataView:0:passengerDataView2:passengerDataLastName": "",
        "TicketPassengerInfoInputPanel:passengerDataView:0:passengerDataView2:passengerDataFirstName": "",
        "TicketPassengerInfoInputPanel:passengerDataView:0:passengerDataView2:passengerDataTypeName": early_type,
        "TicketPassengerInfoInputPanel:passengerDataView:0:passengerDataView2:passengerDataIdNumber": _get_input(
            f"Enter passenger ID number (default: {personal_id}):",
            personal_id,
        ),
        "TicketPassengerInfoInputPanel:passengerDataView:0:passengerDataView2:passengerDataInputChoice": "0",
    }

    for i in range(1, len(items)):
        pid = _ask_pid(i)
        prefix = f"TicketPassengerInfoInputPanel:passengerDataView:{i}:passengerDataView2:"
        form[prefix + "passengerDataLastName"] = ""
        form[prefix + "passengerDataFirstName"] = ""
        form[prefix + "passengerDataTypeName"] = early_type
        form[prefix + "passengerDataIdNumber"] = pid
        form[prefix + "passengerDataInputChoice"] = "0"
    return form


def _show_result(soup: BeautifulSoup) -> None:
    """Display booking result in a modern, formatted way."""
    _print_header("Booking Successful!")
    
    # PNR Code
    pnr = soup.select_one("p.pnr-code span").get_text(strip=True)
    
    # Use bright colors for PNR code
    if os.environ.get('TERM') and '256' in os.environ.get('TERM', ''):
        # ANSI color codes for highlighting
        bright_green = '\033[38;5;46m'  # Bright green
        bright_yellow = '\033[38;5;226m'  # Bright yellow
        bold = '\033[1m'
        reset = '\033[0m'
        
        print(f"\n{bold}{bright_yellow}PNR Code: {bright_green}{pnr}{reset}")
        print("   Use this code for payment and ticket pickup")
    else:
        # Fallback without colors
        print(f"\nPNR Code: {pnr}")
        print("   Use this code for payment and ticket pickup")
    
    # Price and Payment
    price = soup.select_one("#setTrainTotalPriceValue").get_text(strip=True)
    payment_exp = soup.select_one("span.status-unpaid span:nth-child(3)").get_text(strip=True)
    print(f"\nPrice: {price}")
    print(f"   Payment due by: {payment_exp}")
    
    # Journey Details
    print(f"\nJourney Details:")
    print("   " + "─" * 40)
    
    date = soup.select_one("span.date span").get_text(strip=True)
    print(f"   Date: {date}")
    
    depart = soup.select_one("#setTrainDeparture0").get_text(strip=True)
    arrive = soup.select_one("#setTrainArrival0").get_text(strip=True)
    print(f"   Time: {depart} ~ {arrive}")
    
    depart_name = soup.select_one("p.departure-stn span").get_text(strip=True)
    arrive_name = soup.select_one("p.arrival-stn span").get_text(strip=True)
    print(f"   From: {depart_name}")
    print(f"   To: {arrive_name}")
    
    # Ticket Details
    seats = [s.get_text(strip=True) for s in soup.select("div.seat-label span")]
    passenger_count = soup.select_one("div.uk-accordion-content span").get_text(strip=True)
    seat_type = soup.select_one("p.info-data span").get_text(strip=True)
    print(f"   Class: {seat_type}")
    print(f"   Passengers: {passenger_count}")
    print(f"   Seats: {', '.join(seats)}")
    
    print("\n" + "─" * 50)
    print("Next Steps:")
    print("   1. Complete payment using the PNR code")
    print("   2. Collect your ticket at the station or phone app")
    print("   3. Enjoy your journey!")


def _try_ocr_captcha(img_bytes: bytes, max_attempts: int = 3) -> Optional[str]:
    """Try to recognize captcha using OCR model with retry mechanism."""
    try:
        # Suppress TensorFlow logging for cleaner output
        import logging
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TF messages
        logging.getLogger('tensorflow').setLevel(logging.ERROR)
        
        # Try to import OCR dependencies
        sys.path.append(str(Path(__file__).parent.parent / "thsr_ocr"))
        from test_model import CaptchaModelTester
        from datasets.image_processor import process_image
        
        # Create temporary file for the captcha image
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            temp_file.write(img_bytes)
            temp_image_path = temp_file.name
        
        try:
            # Initialize OCR model
            model_path = str(Path(__file__).parent.parent / "thsr_ocr" / "thsr_prediction_model_250827.keras")
            if not os.path.exists(model_path):
                print("[ OCR model not found, falling back to manual input ]")
                return None
            
            # print("Loading OCR model...")
            tester = CaptchaModelTester(model_path)
            
            for attempt in range(max_attempts):
                try:
                    if attempt == 0:
                        # print("Recognizing captcha...")
                        pass
                    else:
                        print(f"[ Retry attempt {attempt + 1}/{max_attempts} ]")
                    
                    # Process image using the same processor as training  
                    # Suppress image processing output for cleaner CLI
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        processed_img = process_image(
                            temp_image_path,
                            target_size=(160, 50),  # Model input size
                            mode='balanced',  # Use balanced processing mode
                            preview=False
                        )
                    
                    # Save processed image for prediction
                    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as processed_file:
                        processed_img.save(processed_file.name, 'JPEG', quality=95)
                        processed_path = processed_file.name
                    
                    try:
                        # Predict using OCR model
                        prediction = tester.predict_image(processed_path)
                        
                        if prediction and len(prediction.strip()) >= 3:  # Basic validation
                            print(f"✓ OCR success: [{prediction}]")
                            return prediction.strip()
                        else:
                            print(f"✗ OCR failed, result too short: [{prediction}]")
                    
                    finally:
                        # Clean up processed image
                        try:
                            os.unlink(processed_path)
                        except:
                            pass
                            
                except Exception as e:
                    print(f"✗ OCR attempt {attempt + 1} failed: {e}")
                    if attempt == max_attempts - 1:
                        print("✗ All OCR attempts failed, fallback to manual input")
            
            return None
            
        finally:
            # Clean up temporary image
            try:
                os.unlink(temp_image_path)
            except:
                pass
                
    except ImportError as e:
        print(f"   OCR dependencies unavailable, fallback to manual input")
        return None
    except Exception as e:
        print(f"   OCR initialization failed, fallback to manual input")
        return None


def _show_image(img_bytes: bytes) -> None:
    """Save and display captcha image information."""
    # Use platform-independent temporary directory
    temp_dir = tempfile.gettempdir()
    file_name = os.path.join(temp_dir, "thsr_captcha.jpg")
    
    with open(file_name, "wb") as f:
        f.write(img_bytes)
    
    print(f"\n[ Security Verification Required ]")
    print(f"Captcha image saved to: {file_name}")
