from datetime import datetime, timedelta, timezone


def sm2_calculate(
    quality: int, repetition_level: int, easiness_factor: float, interval: int
):
    """
    SM-2 Algorithm Implementation.
    :param quality: 1-5 (as per spec: 1=forgot, 3=hard, 5=perfect)
    :param repetition_level: how many times the card has been successfully reviewed
    :param easiness_factor: easiness factor of the card (default 2.5)
    :param interval: current interval in days
    :return: (new_repetition_level, new_easiness_factor, new_interval, next_review_date)
    """
    if quality >= 3:
        if repetition_level == 0:
            new_interval = 1
        elif repetition_level == 1:
            new_interval = 6
        else:
            new_interval = round(interval * easiness_factor)

        new_repetition_level = repetition_level + 1
    else:
        new_repetition_level = 0
        new_interval = 1

    new_easiness_factor = easiness_factor + (
        0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    )
    if new_easiness_factor < 1.3:
        new_easiness_factor = 1.3

    next_review = datetime.now(timezone.utc) + timedelta(days=new_interval)

    return new_repetition_level, new_easiness_factor, new_interval, next_review
