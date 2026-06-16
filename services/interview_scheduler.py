from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config.settings import settings


def generate_interview_slots(days_ahead=3, slots_per_day=3):
    slots = []
    now = datetime.now(ZoneInfo(settings.timezone))
    base_time = now + timedelta(days=1)

    for day in range(days_ahead):
        day_start = base_time + timedelta(days=day)
        for hour in [10, 14, 16][:slots_per_day]:
            slot = day_start.replace(hour=hour, minute=0, second=0, microsecond=0)
            slots.append(slot)

    return slots


def allocate_interview_time(index: int):
    slots = generate_interview_slots()
    if index >= len(slots):
        raise ValueError("No interview slots available")

    return slots[index]
