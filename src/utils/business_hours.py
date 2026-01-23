"""
Business Hours Utility

Provides functions to check if current time is within business hours.
Supports flexible configuration formats:
- Day ranges: "Mon-Fri: 09:00-18:00"
- Individual days: "Monday: 09:00-17:00, Saturday: 10:00-14:00"
- Multiple time slots: "Mon-Fri: 09:00-12:00,14:00-18:00"
- Timezone-aware (defaults to UTC)
"""
from datetime import datetime, time, timedelta
from typing import Optional, Dict, Tuple
import re
import logging

logger = logging.getLogger(__name__)


# Mapping para normalizar nomes de dias
DAY_NAMES = {
    # English full
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
    # English short
    "mon": 0, "tue": 1, "wed": 2, "thu": 3,
    "fri": 4, "sat": 5, "sun": 6,
    # Portuguese full
    "segunda": 0, "terça": 1, "quarta": 2, "quinta": 3,
    "sexta": 4, "sábado": 5, "domingo": 6,
    # Portuguese short
    "seg": 0, "ter": 1, "qua": 2, "qui": 3,
    "sex": 4, "sáb": 5, "dom": 6,
}


def normalize_day_name(day: str) -> Optional[int]:
    """
    Convert day name to weekday number (0=Monday, 6=Sunday).
    
    Args:
        day: Day name (English or Portuguese, full or abbreviated)
        
    Returns:
        Weekday number (0-6) or None if not recognized
    """
    day_clean = day.lower().strip().replace("-feira", "")
    return DAY_NAMES.get(day_clean)


def parse_time_range(time_str: str) -> Optional[Tuple[time, time]]:
    """
    Parse time range string into (start_time, end_time) tuple.
    
    Supports formats:
    - "09:00-18:00"
    - "9:00-18:00"
    - "09:00 - 18:00"
    
    Args:
        time_str: Time range string
        
    Returns:
        Tuple of (start_time, end_time) or None if invalid
    """
    try:
        # Clean and split
        time_str = time_str.strip()
        match = re.match(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", time_str)
        
        if not match:
            return None
            
        start_hour, start_min, end_hour, end_min = match.groups()
        
        start = time(int(start_hour), int(start_min))
        end = time(int(end_hour), int(end_min))
        
        return (start, end)
        
    except (ValueError, AttributeError) as e:
        logger.warning(f"Failed to parse time range '{time_str}': {e}")
        return None


def parse_business_hours(hours_config: Dict[str, str]) -> Dict[int, list[Tuple[time, time]]]:
    """
    Parse business hours configuration into structured format.
    
    Supports multiple formats:
    
    Format 1 - Simple day range:
    {
        "Mon-Fri": "09:00-18:00",
        "Sat": "10:00-14:00"
    }
    
    Format 2 - Multiple time slots:
    {
        "Mon-Fri": "09:00-12:00,14:00-18:00"
    }
    
    Format 3 - Text description (fallback to always open):
    {
        "description": "Segunda a Sexta: 9h às 18h"
    }
    
    Args:
        hours_config: Business hours configuration dictionary
        
    Returns:
        Dictionary mapping weekday (0-6) to list of (start_time, end_time) tuples
    """
    schedule: Dict[int, list[Tuple[time, time]]] = {}
    
    for day_spec, time_spec in hours_config.items():
        # Parse day specification
        days = parse_day_spec(day_spec)
        
        if not days:
            # Could be a text description, skip
            logger.debug(f"Could not parse day spec: {day_spec}")
            continue
            
        # Parse time specification (can have multiple slots separated by comma)
        time_slots = []
        for slot in time_spec.split(","):
            time_range = parse_time_range(slot.strip())
            if time_range:
                time_slots.append(time_range)
                
        if not time_slots:
            logger.warning(f"No valid time slots for {day_spec}: {time_spec}")
            continue
            
        # Assign time slots to all days in range
        for day in days:
            if day not in schedule:
                schedule[day] = []
            schedule[day].extend(time_slots)
    
    return schedule


def parse_day_spec(day_spec: str) -> list[int]:
    """
    Parse day specification into list of weekday numbers.
    
    Supports:
    - Single day: "Mon", "Monday", "Segunda"
    - Day range: "Mon-Fri", "Seg-Sex"
    - Multiple days: Not yet supported (can be added)
    
    Args:
        day_spec: Day specification string
        
    Returns:
        List of weekday numbers (0-6)
    """
    days = []
    
    # Check for range (e.g., "Mon-Fri")
    if "-" in day_spec:
        parts = day_spec.split("-", 1)
        if len(parts) == 2:
            start_day = normalize_day_name(parts[0])
            end_day = normalize_day_name(parts[1])
            
            if start_day is not None and end_day is not None:
                # Handle wrapping (e.g., Fri-Mon)
                if start_day <= end_day:
                    days = list(range(start_day, end_day + 1))
                else:
                    days = list(range(start_day, 7)) + list(range(0, end_day + 1))
    else:
        # Single day
        day = normalize_day_name(day_spec)
        if day is not None:
            days = [day]
    
    return days


def is_within_business_hours(
    hours_config: Optional[Dict[str, str]],
    current_time: Optional[datetime] = None
) -> bool:
    """
    Check if current time is within business hours.
    
    Args:
        hours_config: Business hours configuration (from CompanyConfig.business_hours)
        current_time: Time to check (defaults to datetime.now())
        
    Returns:
        True if within business hours, False otherwise
        
    Note:
        - If hours_config is None or empty, returns True (always open)
        - If hours_config cannot be parsed, returns True (fail-open)
        - Times are assumed to be in the same timezone as current_time
    """
    # Default to always open if no config
    if not hours_config:
        return True
        
    # Parse schedule
    schedule = parse_business_hours(hours_config)
    
    # If no valid schedule parsed, fail open
    if not schedule:
        logger.warning("Could not parse business hours config, assuming always open")
        return True
        
    # Get current time
    if current_time is None:
        current_time = datetime.now()
        
    current_weekday = current_time.weekday()  # 0=Monday, 6=Sunday
    current_time_of_day = current_time.time()
    
    # Check if current weekday has hours defined
    if current_weekday not in schedule:
        # Day not in schedule = closed
        return False
        
    # Check if current time falls within any time slot
    for start, end in schedule[current_weekday]:
        # Handle overnight slots (e.g., 22:00-02:00)
        if start <= end:
            # Normal slot within same day
            if start <= current_time_of_day <= end:
                return True
        else:
            # Overnight slot (end is next day)
            if current_time_of_day >= start or current_time_of_day <= end:
                return True
                
    return False


def format_business_hours(hours_config: Optional[Dict[str, str]]) -> str:
    """
    Format business hours for display to users.
    
    Args:
        hours_config: Business hours configuration
        
    Returns:
        Human-readable string (e.g., "Mon-Fri: 09:00-18:00, Sat: 10:00-14:00")
    """
    if not hours_config:
        return "24/7"
        
    # Try to format nicely
    lines = []
    for day_spec, time_spec in hours_config.items():
        lines.append(f"{day_spec}: {time_spec}")
        
    return ", ".join(lines) if lines else "Not specified"


def get_next_opening_time(
    hours_config: Optional[Dict[str, str]],
    current_time: Optional[datetime] = None
) -> Optional[datetime]:
    """
    Get the next opening time.
    
    Args:
        hours_config: Business hours configuration
        current_time: Current time (defaults to datetime.now())
        
    Returns:
        Datetime of next opening, or None if always open/cannot determine
        
    Note:
        This is a simplified implementation that checks the next 7 days.
        A full implementation would handle complex schedules better.
    """
    if not hours_config:
        return None  # Always open
        
    schedule = parse_business_hours(hours_config)
    if not schedule:
        return None  # Cannot parse = always open
        
    if current_time is None:
        current_time = datetime.now()
        
    # Check next 7 days
    for days_ahead in range(8):
        check_time = datetime(
            current_time.year,
            current_time.month,
            current_time.day,
            0, 0, 0
        ) + timedelta(days=days_ahead)
        
        weekday = check_time.weekday()
        
        if weekday in schedule:
            # Get first opening time of the day
            first_slot = schedule[weekday][0]
            opening_time = datetime.combine(check_time.date(), first_slot[0])
            
            # Only return if it's in the future
            if opening_time > current_time:
                return opening_time
                
    return None  # No opening found in next 7 days


# Convenience function for use in telegram_bot.py
def check_business_hours(
    hours_config: Optional[Dict[str, str]],
    current_time: Optional[datetime] = None
) -> Tuple[bool, str]:
    """
    Check business hours and return user-friendly status.
    
    Args:
        hours_config: Business hours configuration
        current_time: Current time (defaults to datetime.now())
        
    Returns:
        Tuple of (is_open: bool, hours_display: str)
        
    Example:
        >>> is_open, hours_str = check_business_hours(config.business_hours)
        >>> if not is_open:
        >>>     print(f"We're closed. Hours: {hours_str}")
    """
    is_open = is_within_business_hours(hours_config, current_time)
    hours_display = format_business_hours(hours_config)
    
    return is_open, hours_display


# For testing/debugging
if __name__ == "__main__":
    # Test examples
    import sys
    
    # Example 1: Mon-Fri 9-18
    config1 = {
        "Mon-Fri": "09:00-18:00"
    }
    
    # Example 2: Multiple time slots
    config2 = {
        "Mon-Fri": "09:00-12:00,14:00-18:00",
        "Sat": "10:00-14:00"
    }
    
    # Example 3: Portuguese
    config3 = {
        "Seg-Sex": "09:00-18:00",
        "Sábado": "10:00-14:00"
    }
    
    # Test with different times
    test_times = [
        datetime(2026, 1, 27, 10, 0),  # Monday 10:00 (should be open)
        datetime(2026, 1, 27, 8, 0),   # Monday 08:00 (should be closed)
        datetime(2026, 1, 25, 10, 0),  # Saturday 10:00 (depends on config)
        datetime(2026, 1, 26, 10, 0),  # Sunday 10:00 (should be closed)
    ]
    
    for config_name, config in [("Simple", config1), ("Multiple slots", config2), ("Portuguese", config3)]:
        print(f"\n=== {config_name} ===")
        print(f"Config: {config}")
        print(f"Display: {format_business_hours(config)}")
        
        for test_time in test_times:
            is_open = is_within_business_hours(config, test_time)
            day_name = test_time.strftime("%A")
            time_str = test_time.strftime("%H:%M")
            status = "✅ OPEN" if is_open else "❌ CLOSED"
            print(f"  {day_name} {time_str}: {status}")
