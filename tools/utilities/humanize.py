import datetime
from datetime import timedelta

import humanize
from dateutil.relativedelta import relativedelta

from .text import Plural, human_join


def human_timedelta(
    dt: datetime.datetime,
    *,
    source: datetime.datetime | None = None,
    accuracy: int | None = 3,
    brief: bool = False,
    suffix: bool = True,
) -> str:
    if isinstance(dt, datetime.timedelta):
        dt = datetime.datetime.utcfromtimestamp(dt.total_seconds())

    now = source or datetime.datetime.now(datetime.UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.UTC)

    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime.UTC)

    now = now.replace(microsecond=0)
    dt = dt.replace(microsecond=0)

    if dt < now:  # Change > to <
        delta = relativedelta(now, dt)
        output_suffix = " ago" if suffix else ""
    else:
        delta = relativedelta(dt, now)
        output_suffix = ""

    attrs = [
        ("year", "y"),
        ("month", "mo"),
        ("day", "d"),
        ("hour", "h"),
        ("minute", "m"),
        ("second", "s"),
    ]

    output = []
    for attr, brief_attr in attrs:
        elem = getattr(delta, f"{attr}s")
        if not elem:
            continue

        if attr == "day":
            if weeks := delta.weeks:
                elem -= weeks * 7
                if not brief:
                    output.append(format(Plural(weeks), "week"))
                else:
                    output.append(f"{weeks}w")

        if elem <= 0:
            continue

        if brief:
            output.append(f"{elem}{brief_attr}")
        else:
            output.append(format(Plural(elem), attr))

    if accuracy is not None:
        output = output[:accuracy]

    if len(output) == 0:
        return "now"
    if not brief:
        return human_join(output, final="and") + output_suffix
    return "".join(output) + output_suffix


def size(value: int):
    return humanize.naturalsize(value).replace(" ", "")


def time(value: timedelta, short: bool = False):
    value = (
        humanize.precisedelta(value, format="%0.f")
        .replace("ago", "")
        .replace("from now", "")
    )
    if value.endswith("s") and value[:-1].isdigit() and int(value[:-1]) == 1:
        value = value[:-1]

    if short:
        value = " ".join(value.split(" ", 2)[:2])
        return value.removesuffix(",")
    return value


def ordinal(value: int):
    return humanize.ordinal(value)


def comma(value: int):
    return humanize.intcomma(value)


def percentage(small: int, big: int = 100):
    return f"{int((small / big) * 100)}%"
