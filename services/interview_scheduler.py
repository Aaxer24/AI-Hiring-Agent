from datetime import datetime, timedelta

"""This function creates a list of available interview time slots for the next few days and then assigns one slot to a candidate in a predictable way. It helps automate interview scheduling and avoids manual coordination."""

def generate_interview_slots(days_ahead=3, slots_per_day=3):
    slots = []
    base_time = datetime.now() + timedelta(days=1)

    for day in range(days_ahead):
        day_start = base_time + timedelta(days=day)
        for hour in [10, 14, 16]:  # 10AM, 2PM, 4PM
            slot = day_start.replace(hour=hour, minute=0, second=0)
            slots.append(slot)

    return slots


#deterministic allocator (uses slots list)
def allocate_interview_time(index: int):
    slots = generate_interview_slots()
    if index >= len(slots):
        raise ValueError("No interview slots available")

    return slots[index]

# interview_scheduler is responsible for deciding and allocating unique interview time slots, while calendar_agent is responsible for creating the actual Google Calendar event. Separating them keeps time allocation logic independent from API execution logic.