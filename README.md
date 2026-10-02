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

   Options (each also settable via the environment; flags win):

   | Flag | Env | Meaning |
   | --- | --- | --- |
   | `-l`, `--location ID` | `GE_LOCATIONS=5023,7680` | Enrollment center to watch (repeatable) |
   | `--before YYYY-MM-DD` | `GE_BEFORE` | Ignore slots on or after this date |
   | `--interval SEC` | `GE_INTERVAL` | Seconds between polls (default 300) |
   | `--state-file PATH` | `GE_STATE_FILE` | Where already-reported slots are remembered (default `.slots.json`) |
   | `--once` | | Poll once and exit (handy under cron/systemd timers) |
   | `--no-notify` | | Log new slots instead of pushing to ntfy |

Subscribe to the topic in the ntfy app and you're done. Slots are remembered in
the state file so each is reported once; a failed push is retried on the next
poll, and past slots are pruned automatically. Delete the state file to
re-notify about everything.

Enrollment center names and IDs are fetched live from CBP, so new or renamed
centers show up in `locations` without an update. Restart `watch` with new
`-l` flags to add a center.

## Running as a service

`contrib/ge-appointment-finder.service` is a systemd **user** unit. All
configuration comes from `~/.config/ge-appointment-finder/env` (same keys as
`.env.example`), so the unit file itself never needs editing.

```sh
uv tool install git+https://github.com/iQlusi0n/GE-Appointment-Finder
mkdir -p ~/.config/systemd/user ~/.config/ge-appointment-finder
cp contrib/ge-appointment-finder.service ~/.config/systemd/user/
cp .env.example ~/.config/ge-appointment-finder/env
chmod 600 ~/.config/ge-appointment-finder/env
$EDITOR ~/.config/ge-appointment-finder/env     # NTFY_URL, GE_LOCATIONS, GE_BEFORE ...
systemctl --user daemon-reload
systemctl --user enable --now ge-appointment-finder
loginctl enable-linger "$USER"                   # keep it running while logged out
```

```sh
systemctl --user status ge-appointment-finder    # shows "last poll HH:MM:SS, N new slot(s)"
journalctl --user -u ge-appointment-finder -f
```

What the unit gives you:

- `Type=notify`: the service reports `READY=1` once it has resolved your
  locations, and a status line after every poll.
- `WatchdogSec=900`: a hung poll gets the process restarted. Raise it if you
  set `GE_INTERVAL` above ~10 minutes.
- `Restart=on-failure` with `StartLimitIntervalSec=0`: survives network
  outages indefinitely. `SIGTERM` (`systemctl stop`) exits cleanly.
- `StateDirectory=`: the seen-slot file lives in the unit's state directory
  (`~/.config/ge-appointment-finder/slots.json` for user units; newer systemd
  also symlinks it from `~/.local/state/`).
- Log lines carry no timestamps under journald (it adds its own).

After changing the env file: `systemctl --user restart ge-appointment-finder`.

Prefer a timer or cron instead? Run `watch --once` on a schedule; the state
file dedupes across invocations:

```cron
*/5 * * * * GE_LOCATIONS=5023 NTFY_URL=https://ntfy.sh/your-topic ~/.local/bin/ge-appointment-finder watch --once --state-file ~/.slots.json
```

## Development

```sh
uv sync
uv run ruff check . && uv run ruff format --check .
uv run pytest
```

## License

[MIT](LICENSE)
