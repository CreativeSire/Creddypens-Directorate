from __future__ import annotations

import random
from datetime import datetime, timedelta


class SchedulingTool:
    """Mock scheduling system for elite agents like Jessica."""

    def check_availability(self, *, date_str: str | None = None) -> dict:
        # Mock availability for the next few days
        slots = [
            "09:00 AM", "10:30 AM", "01:00 PM", "02:30 PM", "04:00 PM"
        ]
        target_date = date_str or datetime.now().strftime("%Y-%m-%d")
        
        # Randomly pick 2-3 available slots
        available = random.sample(slots, k=random.randint(2, 4))
        available.sort()
        
        return {
            "date": target_date,
            "available_slots": available,
            "timezone": "EST"
        }

    def book_meeting(self, *, name: str, email: str, slot: str, date_str: str) -> dict:
        # Mock booking confirmation
        return {
            "status": "confirmed",
            "meeting_id": f"mtg_{random.getrandbits(32)}",
            "details": {
                "attendee": name,
                "email": email,
                "time": slot,
                "date": date_str,
                "link": "https://meet.creddypens.com/jessica-intake"
            }
        }

scheduling_tool = SchedulingTool()
