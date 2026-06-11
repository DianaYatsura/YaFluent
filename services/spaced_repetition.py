from datetime import datetime, timedelta, timezone


def calculate_next_review(current_level: int):
    intervals = {
        0: timedelta(minutes=1),
        1: timedelta(days=1),
        2: timedelta(days=3),
        3: timedelta(days=7),
        4: timedelta(days=14),
        5: timedelta(days=30),
    }

    interval = intervals.get(current_level, timedelta(days=30))
    return datetime.now(timezone.utc) + interval
