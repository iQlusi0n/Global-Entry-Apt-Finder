"""Command-line interface."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import date
from pathlib import Path

from ge_appointment_finder import __version__, cbp
from ge_appointment_finder.notify import Notifier, NotifierConfigError
from ge_appointment_finder.store import SeenSlots

log = logging.getLogger("ge_appointment_finder")

DEFAULT_INTERVAL = 300
DEFAULT_STATE_FILE = Path(".slots.json")


def format_message(slots: list[cbp.Slot], names: dict[int, str]) -> str:
    lines = []
    for slot in sorted(slots):
        name = names.get(slot.location_id, str(slot.location_id))
        lines.append(f"{name:<32} {slot.start:%a %b %d %H:%M}")
    return "\n".join(lines)


def cmd_locations(args: argparse.Namespace) -> int:
    locations = cbp.fetch_locations()
    if args.state:
        wanted = {s.upper() for s in args.state}
        locations = [loc for loc in locations if loc.state.upper() in wanted]
    if not locations:
        log.error("no locations returned")
        return 1
    for loc in locations:
        print(f"{loc.id:>6}  {loc.state:<2}  {loc.name} ({loc.city})")
    return 0


def resolve_names(location_ids: list[int]) -> dict[int, str]:
    names = {loc.id: loc.name for loc in cbp.fetch_locations()}
    for location_id in location_ids:
        if location_id not in names:
            log.warning("location %d is not a known enrollment center", location_id)
    return {lid: names.get(lid, str(lid)) for lid in location_ids}


def check_once(
    location_ids: list[int],
    names: dict[int, str],
    before: date | None,
    seen: SeenSlots,
    notifier: Notifier | None,
) -> list[cbp.Slot]:
    slots: list[cbp.Slot] = []
    for location_id in location_ids:
        slots.extend(cbp.fetch_slots(location_id))
    if before is not None:
        slots = [slot for slot in slots if slot.start.date() < before]
    fresh = seen.unseen(slots)
    if not fresh:
        log.info("no new slots")
        return fresh
    message = format_message(fresh, names)
    log.info("new slots:\n%s", message)
    if notifier is not None:
        try:
            notifier.send(message, title="Global Entry slots available")
        except OSError as e:
            # Not remembered: the next poll will retry the notification.
            log.error("push notification failed, will retry next poll: %s", e)
            return []
    seen.remember(fresh)
    return fresh


def cmd_watch(args: argparse.Namespace) -> int:
    notifier: Notifier | None = None
    if not args.no_notify:
        try:
            notifier = Notifier.from_env()
        except NotifierConfigError as e:
            log.error("%s (set it, or pass --no-notify to only log)", e)
            return 2

    names = resolve_names(args.location)
    seen = SeenSlots(args.state_file)
    log.info(
        "watching %s every %ds%s",
        ", ".join(names.values()),
        args.interval,
        f" for slots before {args.before}" if args.before else "",
    )
    try:
        while True:
            check_once(args.location, names, args.before, seen, notifier)
            if args.once:
                return 0
            time.sleep(args.interval)
    except KeyboardInterrupt:
        log.info("interrupted")
        return 130


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ge-appointment-finder",
        description="Watch CBP Global Entry enrollment centers for new interview slots.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    p_loc = sub.add_parser("locations", help="list enrollment centers and their IDs")
    p_loc.add_argument(
        "--state", action="append", metavar="ST", help="only show this state (repeatable)"
    )
    p_loc.set_defaults(func=cmd_locations)

    p_watch = sub.add_parser("watch", help="poll for new slots and send notifications")
    p_watch.add_argument(
        "-l",
        "--location",
        action="append",
        type=int,
        required=True,
        metavar="ID",
        help="enrollment center ID to watch (repeatable; see `locations`)",
    )
    p_watch.add_argument(
        "--before",
        type=date.fromisoformat,
        metavar="YYYY-MM-DD",
        help="ignore slots on or after this date",
    )
    p_watch.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL,
        metavar="SEC",
        help=f"seconds between polls (default: {DEFAULT_INTERVAL})",
    )
    p_watch.add_argument(
        "--state-file",
        type=Path,
        default=DEFAULT_STATE_FILE,
        metavar="PATH",
        help=f"where already-reported slots are remembered (default: {DEFAULT_STATE_FILE})",
    )
    p_watch.add_argument("--once", action="store_true", help="poll a single time and exit")
    p_watch.add_argument(
        "--no-notify", action="store_true", help="log new slots instead of pushing to ntfy"
    )
    p_watch.set_defaults(func=cmd_watch)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    return args.func(args)
