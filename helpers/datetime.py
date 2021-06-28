from datetime import datetime, date


def time_to_timedelta(time):
    return datetime.combine(date.min, time) - datetime.min


def timedelta_to_str(delta):
    total = int(delta.total_seconds())
    if total < 0:
        total = -total
        value = '-'
    else:
        value = '+'

    total, seconds = divmod(total, 60)
    total, minutes = divmod(total, 60)
    days, hours = divmod(total, 60)
    if days > 0:
        value += "{:d}d ".format(days)
    value += "{:d}:{:02d}:{:02d}".format(hours, minutes, seconds)
    return value
