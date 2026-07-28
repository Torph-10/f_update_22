*This project has been created as part of the 42 curriculum by <abelgarh>.*

# fly-in

## Description

`fly-in` is a multi-drone pathfinding and turn-based simulation engine. Given a
map of zones and connections (with capacity limits, restricted zones that take
longer to cross, and priority zones), it plans a conflict-free route for each
drone and then simulates the whole fleet moving turn-by-turn from a shared
start hub to a shared end hub — without ever exceeding a zone's or a
connection's capacity at any point in time.

The core idea is **time-space routing**: instead of treating "can I go to zone
X?" as a static yes/no, each drone plans over `(zone, turn)` states, so it can
route around congestion that will exist *at the time it would arrive*, not
just congestion that exists right now.

## Instructions

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
make lint      # flake8 . && mypy . (project's required flag set)
make clean     # removes __pycache__ and .mypy_cache
make install   # uv sync — installs flake8 and mypy as dev dependencies
make run       # uv run python3 main.py — parses map.txt and runs the simulation
```

The map is read from `map.txt` in the project root. See `map.txt` for the
expected format (`nb_drones`, `start_hub`, `hub`, `end_hub`, `connection`
lines, with optional `[zone=...]`, `[color=...]`, `[max_drones=...]`,
`[max_link_capacity=...]` metadata).

## Algorithm Explanation

Each drone's route is planned independently, in order, by
`TimeSpaceRouter.find_path`:

- A **state** is `(zone, turn)` rather than just `zone` — this is what makes
  it "time-space": the same zone at two different turns is a different state,
  so the router can tell "zone X is full *right now*" apart from "zone X will
  be free by the time I'd actually get there."
- The search processes turns in strictly increasing order via
  `zones_at_turn[turn]`. Because every move costs at least 1 turn, the first
  time the destination is reached is guaranteed to be the *earliest possible*
  arrival — no priority queue needed, a plain turn-ordered sweep suffices.
- At each state, two kinds of moves are considered: **wait** one turn in
  place, or **travel** to a neighboring zone. Restricted zones take 2 turns
  to enter instead of 1, and the connection is checked as occupied for the
  *entire* transit duration, not just the arrival turn.
- **Priority zones** are preferred on ties: each path tracks a score (+1 per
  priority zone passed through), and when two paths reach the same
  `(zone, turn)` state, the higher-scoring one wins.
- Once a drone's path is finalized, `commit_path` reserves its exact
  turn-by-turn zone and connection occupancy into a shared `ReservationTable`,
  so every subsequent drone plans around it.

Route planning and simulation execution are deliberately separate concerns:
`TimeSpaceRouter`/`ReservationTable` decide *what should happen*, and
`SimulationEngine` actually plays it out turn-by-turn, independently
re-checking real-time capacity via `SimulationState` as a safety net.

## Design Decisions

- **Capacity reserved at departure, not arrival.** Early on, zone occupancy
  was only incremented when a drone *arrived*, which let multiple drones
  overshoot a restricted zone's capacity mid-transit. It's now reserved the
  moment a drone commits to entering (`process_departing_drones`), and
  released only when it actually leaves.
- **Sequential planning over joint optimization.** Drones are routed one at a
  time (`main.py`'s loop), each committing its reservations before the next
  plans. This is simpler and fast enough for this project's scale, at the
  cost of not being globally optimal — an earlier-planned drone can force a
  later one into a longer route.
- **Separate `SimulationState` real-time check.** Even though routes are
  pre-planned, the simulation engine still checks live capacity at each turn
  rather than blindly trusting the plan — this keeps the simulation robust if
  routing logic ever has an edge case.

## Performance Analysis

Planning is O(zones × turns) per drone in the worst case, since every
`(zone, turn)` state is visited at most once. `max_time` is scaled with both
map size and drone count (`len(graph.zones) * 2 + nb_drones * 2`) so dense
maps with narrow single-capacity chokepoints (drones forced to queue through
one restricted gate) still have enough horizon to find a valid route instead
of failing early.

## Challenges Faced

- **Chokepoint maps timing out the router.** A map with a single-capacity
  restricted gate as the only path to the exit caused later drones to run out
  of search horizon (`max_time`) before finding a route, since each drone has
  to wait for the ones ahead of it to clear the gate. Fixed by scaling
  `max_time` with `nb_drones`, not just graph size.
- **`mypy --strict` on `Optional[str]` fields.** `Drone.transit_destination`
  is `Optional[str]` since a drone isn't always in transit, but code that
  uses it after checking `status == IN_TRANSIT` still needed explicit
  `is None` narrowing to satisfy mypy, since it can't infer the invariant
  across two different attributes.

## Testing Strategy

- Ran the parser against maps with malformed lines, missing `start_hub`/
  `end_hub`, duplicate zone names, and duplicate connections to confirm
  `ParserError` fires with the right line number.
- Built `map.txt` scenarios that specifically stress capacity handling: a
  circular loop with a single-capacity restricted exit gate, to confirm
  drones queue correctly instead of exceeding `max_drones`/
  `max_link_capacity`.
- Verified `make lint` and `make lint-strict` both pass clean.

## Example Usage

```bash
make install
make run
```

```
Running Simulator
D1-loop_a
D1-loop_b D2-loop_a

## Resources

- [uv documentation](https://docs.astral.sh/uv/) — dependency management
- [mypy documentation](https://mypy.readthedocs.io/) — static type checking
- [PEP 257](https://peps.python.org/pep-0257/) — docstring conventions
- Dijkstra's algorithm / time-expanded graphs — background for the
  time-space routing approach

**AI usage:**
- Fixing `mypy --strict` errors (Optional narrowing, missing type params,
  missing annotations)
- Writing docstrings for existing, already-understood methods
- Generating the initial `pyproject.toml` and this README