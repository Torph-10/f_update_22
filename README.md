*This project has been created as part of the 42 curriculum by abelgarh.*

# fly-in

## Description

`fly-in` is a multi-drone pathfinding and turn-based simulation engine.

Given a text map describing zones (hubs) and the connections between them —
along with capacity limits, restricted zones that take longer to cross, and
priority zones that are favored when routes tie — the program plans a
conflict-free route for every drone and then simulates the whole fleet
moving turn-by-turn from a shared start hub to a shared end hub, without
ever exceeding a zone's or a connection's capacity at any point in time.

The goal of the project is to explore **time-space routing**: instead of
treating "can I go to zone X?" as a static yes/no question, each drone plans
over `(zone, turn)` states, so a route can be planned around congestion that
will exist *at the time the drone would actually arrive*, not just
congestion that exists right now. Once every drone has a committed route,
the simulation engine replays those routes turn-by-turn and independently
re-checks real-time capacity as a safety net, so the visible output is a
live, second-by-second account of the fleet's movement rather than just a
plan on paper.

## Instructions

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
make install   # uv sync — installs flake8 and mypy as dev dependencies
make run       # uv run python3 main.py map.txt — parses map.txt and runs the simulation
make lint      # flake8 . && mypy . (project's required flag set)
make clean     # removes __pycache__ and .mypy_cache
```

The map is read from `map.txt` in the project root (see the [Example Input
and Output](#example-input-and-output) section below for the exact format).
To run the simulator on a different map, either replace `map.txt` or call
the program directly with a path argument:

```bash
uv run python3 main.py path/to/other_map.txt
```

Zone and connection lines accept optional `[key=value]` metadata:
`zone=<normal|blocked|restricted|priority>`, `color=<name>`,
`max_drones=<n>` (zone lines), and `max_link_capacity=<n>` (connection
lines).

## Algorithm Explanation

Each drone's route is planned independently, in order, by
`TimeSpaceRouter.find_path`:

- A **state** is `(zone, turn)` rather than just `zone` — this is what makes
  it "time-space": the same zone at two different turns is a different
  state, so the router can tell "zone X is full *right now*" apart from
  "zone X will be free by the time I'd actually get there."
- The search processes turns in strictly increasing order via
  `zones_at_turn[turn]`. Because every move costs at least 1 turn, the first
  time the destination is reached is guaranteed to be the earliest
  possible arrival.
- At each state, two kinds of moves are considered: **wait** one turn in
  place, or **travel** to a neighboring zone. Restricted zones take 2 turns
  to enter instead of 1, and the connection is checked as occupied for the
  *entire* transit duration, not just the arrival turn.
- **Priority zones** are preferred on ties: each path tracks a score (+1 per
  priority zone passed through), and when two paths reach the same
  `(zone, turn)` state, the higher-scoring one wins.
- Once a drone's path is finalized, `commit_path` reserves its exact
  turn-by-turn zone and connection occupancy into a shared
  `ReservationTable`, so every subsequent drone plans around it.

Route planning and simulation execution are deliberately separate concerns:
`TimeSpaceRouter`/`ReservationTable` decide *what should happen*, and
`SimulationEngine` actually plays it out turn-by-turn, independently
re-checking real-time capacity via `SimulationState` as a safety net.

### Design decisions

- **Capacity reserved at departure, not arrival.** Early on, zone occupancy
  was only incremented when a drone *arrived*, which let multiple drones
  overshoot a restricted zone's capacity mid-transit. It's now reserved the
  moment a drone commits to entering (`process_departing_drones`), and
  released only when it actually leaves.
- **Sequential planning over joint optimization.** Drones are routed one at
  a time (`main.py`'s loop), each committing its reservations before the
  next plans. This is simpler and fast enough for this project's scale, at
  the cost of not being globally optimal — an earlier-planned drone can
  force a later one into a longer route.
- **Separate `SimulationState` real-time check.** Even though routes are
  pre-planned, the simulation engine still checks live capacity at each turn
  rather than blindly trusting the plan — this keeps the simulation robust
  if routing logic ever has an edge case.

  
## Visual Representation

Every turn, `SimulationEngine.print_turn_summary` prints one line listing
every drone currently in transit, so the whole fleet's movement can be read
as a live feed rather than inferred from a static plan:

- **Per-drone entries.** Each in-transit drone is shown once per turn as
  `<drone_name>-<destination_zone>` (e.g. `D1-junction`), letting a reader
  follow any single drone's progress turn-by-turn just by scanning for its
  name.
- **Restricted-zone visibility.** Zones marked `restricted` take two turns
  to cross, and while a drone is mid-transit into one, the entry is instead
  printed as `<drone_name>-<origin_zone>-<destination_zone>` (e.g.
  `D1-correct_path-intermediate`), making the extra transit turn — and
  which restricted link is causing it — immediately visible instead of
  looking like a stall.
- **Colour-coding by destination.** Each entry is wrapped in an ANSI true-
  colour escape code resolved from the destination zone's `color=`
  metadata (`SimulationEngine._color_code`, backed by `webcolors`). This
  lets a reader visually group drones by which part of the map they're
  heading into (e.g. all drones entering the green end hub stand out from
  those still crossing a blue corridor) without reading any zone names.
  Unrecognised colour names still get a consistent, deterministic colour
  via a CRC32-based fallback rather than being left unstyled, so custom
  colour names in a map file remain visually distinguishable turn after
  turn.
- **Silent turns are skipped.** A turn with no drone currently in transit
  (e.g. everyone waiting for capacity to free up) prints nothing, so the
  output stays readable on congested maps instead of being padded with
  empty lines.

Together, these choices turn the simulation log into something that can be
read almost like a race commentary: who is moving, where they're headed,
which links are the slow (restricted) ones, and which region of the map
each drone is converging on — all from a single line per turn.

## Example Input and Output

Example map (`map.txt`), a "dead end trap" scenario where a naive router
could waste time exploring a dead end before finding the real path to the
goal:

```
# Medium Level 1: Dead end trap - drones might get stuck
nb_drones: 5

start_hub: start 0 0 [color=green]
hub: junction 1 0 [color=yellow max_drones=2]
hub: dead_end 1 1 [color=red]
hub: correct_path 2 0 [color=blue]
hub: intermediate 3 0 [color=blue]
end_hub: goal 4 0 [color=green]

connection: start-junction [max_link_capacity=2]
connection: junction-dead_end
connection: junction-correct_path
connection: correct_path-intermediate
connection: intermediate-goal
```

Running it:

```bash
make run
```

produces (colours omitted here; in a real terminal each entry is tinted by
its destination zone's `color=`):

```
Running Simulator
D1-junction
D1-correct_path D2-junction
D1-intermediate D2-correct_path D3-junction
D1-goal D2-intermediate D3-correct_path D4-junction
D2-goal D3-intermediate D4-correct_path D5-junction
D3-goal D4-intermediate D5-correct_path
D4-goal D5-intermediate
D5-goal
```

Reading it turn by turn: `junction` only has room for `max_drones=2`, and
`start-junction` allows two drones abreast (`max_link_capacity=2`), so the
5 drones filter through the bottleneck two at a time, correctly ignore the
`dead_end` branch entirely, and funnel down the single-file
`correct_path → intermediate → goal` chain until all five have arrived.


## Resources

- https://www.youtube.com/watch?v=pcKY4hjDrxk&t=703s
- https://www.geeksforgeeks.org/dsa/breadth-first-search-or-bfs-for-a-graph/

**AI usage:**
- Fixing `mypy` errors.
- Writing docstrings for existing method and classes.
- Generating the initial `pyproject.toml` and drafting/structuring this
  `README.md`.
