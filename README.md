# GE Appointment Finder

Polls the CBP Trusted Traveler Programs scheduler for new Global Entry interview
slots at the enrollment centers you choose and pushes a notification to an
[ntfy](https://ntfy.sh) topic the moment something opens up. Each slot is
reported once, so you only get pinged for genuinely new openings.

No third-party runtime dependencies; Python 3.12+ standard library only.

## Install

With [uv](https://docs.astral.sh/uv/):

```sh
uv tool install git+https://github.com/iQlusi0n/GE-Appointment-Finder
```

Or run it straight from a clone:

```sh
git clone https://github.com/iQlusi0n/GE-Appointment-Finder
cd GE-Appointment-Finder
uv run ge-appointment-finder --help
```

## Usage

1. Find the IDs of the enrollment centers you want to watch:

   ```sh
   ge-appointment-finder locations --state OH --state MI
   ```

2. Point it at an ntfy topic by exporting the variables (or put them in a file
   like `.env.example` and run via `uv run --env-file .env ...`):

   ```sh
   export NTFY_URL=https://ntfy.sh/your-secret-topic
   # optional auth, if your topic/server needs it:
   export NTFY_TOKEN=tk_...          # or NTFY_USER / NTFY_PASS
   ```

3. Watch:

   ```sh
   ge-appointment-finder watch -l 5023 -l 7680 --before 2026-12-01
   ```

   Options:

   | Flag | Meaning |
   | --- | --- |
   | `-l`, `--location ID` | Enrollment center to watch (repeatable) |
   | `--before YYYY-MM-DD` | Ignore slots on or after this date |
   | `--interval SEC` | Seconds between polls (default 300) |
   | `--state-file PATH` | Where already-reported slots are remembered (default `.slots.json`) |
   | `--once` | Poll once and exit (handy under cron/systemd timers) |
   | `--no-notify` | Log new slots instead of pushing to ntfy |

Subscribe to the topic in the ntfy app and you're done. Slots are remembered in
the state file so each is reported once; a failed push is retried on the next
poll, and past slots are pruned automatically. Delete the state file to
re-notify about everything.

Enrollment center names and IDs are fetched live from CBP, so new or renamed
centers show up in `locations` without an update. Restart `watch` with new
`-l` flags to add a center.

## Running as a service

Two options:

**Long-running (systemd):** `contrib/ge-appointment-finder.service` is a user
unit that runs `watch` with `Restart=on-failure`, reads `NTFY_*` from
`~/.config/ge-appointment-finder/env`, and keeps the state file in
`~/.local/state/ge-appointment-finder/`. Install steps are in the file's
header; adjust the `-l` / `--before` arguments to your centers.

```sh
systemctl --user status ge-appointment-finder
journalctl --user -u ge-appointment-finder -f
```

**Periodic (cron / systemd timer):** run `watch --once` on a schedule. State
lives in `--state-file`, so each invocation only reports slots the previous
ones haven't.

```cron
*/5 * * * * cd ~/ge && NTFY_URL=https://ntfy.sh/your-topic ~/.local/bin/ge-appointment-finder watch --once -l 5023 >> ge.log 2>&1
```

## Development

```sh
uv sync
uv run ruff check . && uv run ruff format --check .
uv run pytest
```

## License

[MIT](LICENSE)
