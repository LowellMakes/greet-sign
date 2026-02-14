#!/usr/bin/env python3

from datetime import datetime, time

now = datetime.now()


# ---------------- NORMAL DEFAULT ----------------

DEFAULT_FRAMES = [
    "Welcome to Lowell Makes",
    "HACK - BUILD - LEARN",
]


# ---------------- HOLIDAY RULES ----------------

def is_thanksgiving():
    if now.month != 11:
        return False

    # 4th Thursday
    first = datetime(now.year, 11, 1)
    first_thu = first + timedelta((3 - first.weekday()) % 7)
    fourth = first_thu + timedelta(weeks=3)

    return now.date() == fourth.date()


def is_open_house():
    return (
        now.weekday() == 2 and
        time(18, 30) <= now.time() <= time(20, 0)
    )


# ---------------- OUTPUT ----------------

# Entire December → Christmas cartoon takeover
if now.month == 12:
    print("--cartoon christmas")
    exit()

# July 4
if now.month == 7 and now.day == 4:
    print("--cartoon july4th")
    exit()

# NYE / NYD
if (now.month, now.day) in [(12, 31), (1, 1)]:
    print("--cartoon newyears")
    exit()

# Thanksgiving (text only)
if is_thanksgiving():
    print('"HAPPY THANKSGIVING"')
    exit()

# Pi Day example
if now.month == 3 and now.day == 14:
    print('"HAPPY PI DAY"')
    exit()

# Open house time override
if is_open_house():
    print('"Welcome open house guests!!!!"')
    exit()


# ---------------- DEFAULT ----------------

for frame in DEFAULT_FRAMES:
    print(frame)
    print("-n")
