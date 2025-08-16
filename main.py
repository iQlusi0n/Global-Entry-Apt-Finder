#!/usr/bin/env python3

import urllib.request
import json
import sys
import base64
import pickle
import urllib.error
import socket
import os

from dataclasses import dataclass, asdict
from datetime import datetime
import time

@dataclass
class AppointmentSlot:
    locationId: int
    startTimestamp: str
    endTimestamp: str
    active: bool
    duration: int
    remoteInd: bool

    def __lt__(self, other):
        return datetime.fromisoformat(self.startTimestamp) < datetime.fromisoformat(other.startTimestamp)

    def __hash__(self):
        return hash((self.locationId, self.startTimestamp))

Locations = {
    5023: "Detroit",
    7680: "Cincinnati",
    9200: "Pittsburgh",
    16242: "Dayton",
    16802: "Columbus",
    16816: "Toledo",
    16903: "Mason",
}

EndDate = AppointmentSlot(
    locationId=0,
    startTimestamp="2025-08-22T00:00",
    endTimestamp="2025-08-22T00:00",
    active=True,
    duration=10,
    remoteInd=False
)

Username = os.environ["NTFY_USER"]
Password = os.environ["NTFY_PASS"]

AppointmentSlotUrl = "https://ttp.cbp.dhs.gov/schedulerapi/slots?orderBy=soonest&limit=10&locationId={}&minimum=1"
BaseUrl = os.environ["NTFY_URL"]


def send_push(msg):
    print("sending push notification")
    user_pass = base64.b64encode(f"{Username}:{Password}".encode('utf-8')).decode()
    auth_hdr = f"Basic {user_pass}".encode('utf-8')
    auth_param = base64.b64encode(auth_hdr).rstrip(b'=').decode()
    url = f"{BaseUrl}?auth={auth_param}"

    req = urllib.request.Request(url, data=msg.encode('utf-8') , method='POST')
    with urllib.request.urlopen(req) as response:
        result = response.read().decode('utf-8')


def attempt_fetch(url, retries=3, backoff_factor=2):
    delay = 1  # initial delay in seconds
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=15) as response:
                if response.status == 200:
                    return json.loads(response.read())
                else:
                    print(f"Non-200 status from {url}: {response.status}")
                    return None
        except (urllib.error.URLError, socket.timeout) as e:
            print(f"Attempt {attempt} failed for {url}: {e}")
            if attempt < retries:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= backoff_factor
            else:
                print(f"Giving up on {url} after {retries} attempts.")
                return None


def get_slots():
    print("fetching potential slots")
    urls = [AppointmentSlotUrl.format(location) for location in Locations.keys()]

    slots = []
    for url in urls:
        jslots = attempt_fetch(url)
        if not jslots:
            continue

        for jslot in jslots:
            slot = AppointmentSlot(**jslot)
            slots.append(slot)
    slots.sort()

    return slots


def save_slots(slots):
    with open(".slots.db", "wb") as f:
        pickle.dump(slots, f)


def load_slots():
    try:
        with open(".slots.db", "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        return []


def filter_slots(slots):
    print("filtering potential slots")
    new_slots = set([slot for slot in slots if slot < EndDate]) # Removes all past end date
    saved_slots = set(load_slots())
    save_slots(new_slots | saved_slots)

    return new_slots - saved_slots


def build_msg(slots):
    print("building push message body")
    body = "{:<15}@ {}"

    slots = sorted(slots)
    msg = ""
    for slot in slots:
        location = Locations[slot.locationId]
        dt = datetime.fromisoformat(slot.startTimestamp)
        hr_dt = dt.strftime("%b %d: %H:%M")
        line = body.format(location, hr_dt)
        print(line)
        msg += line + "\n"

    return msg


def main():
    try:
        while True:
            slots = get_slots()
            slots = filter_slots(slots)
            if slots:
                msg = build_msg(slots)
                send_push(msg)
            print("sleeping")
            time.sleep(300)

    except KeyboardInterrupt:
        print("Interrupted by user. Exiting.")

    return 0


if __name__ == "__main__":
    sys.exit(main())