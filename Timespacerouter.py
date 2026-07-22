import heapq
from typing import List, Optional, Tuple

from graph import Graph
from reservations import ReservationTable


class TimeSpaceRouter:
    """Plans a single drone's route as a shortest path over (zone, turn)
    states, respecting zone/connection capacity already reserved by
    previously-planned drones."""

    def __init__(self, graph: Graph, reservations: ReservationTable) -> None:
        self.graph = graph
        self.reservations = reservations

    def _zone_ok(self, zone_name: str, turn: int) -> bool:
        zone = self.graph.get_zone(zone_name)
        if zone.zone_type == "blocked":
            return False
        if zone.is_start or zone.is_end:
            return True
        return self.reservations.zone_count(zone_name, turn) < zone.max_drones

    def _connection_ok(self, z1: str, z2: str, turn: int) -> bool:
        if z1 == z2:
            # Not a real connection; waiting in place is handled by
            # the caller via _zone_ok only.
            return True
        for conn in self.graph.get_neighbors(z1):
            if conn.zone_1 == z2 or conn.zone_2 == z2:
                count = self.reservations.conn_count(z1, z2, turn)
                return count < conn.max_link_capacity
        return False

    def find_path(
        self, start: str, end: str, start_turn: int, horizon: int
    ) -> Optional[List[Tuple[str, int]]]:
        """Time-space Dijkstra. Returns a list of (zone, turn) checkpoints
        the drone occupies, or None if unreachable within `horizon`.

        `horizon` bounds how far into the future waiting is explored —
        without it, the search space is unbounded since waiting is a
        valid move at every turn. A safe default is
        `start_turn + len(self.graph.zones) * 2`.
        """
        counter = 0
        start_state = (start, start_turn)
        best: dict = {start_state: start_turn}
        queue = [
            (start_turn, 0, counter, start, start_turn, [(start, start_turn)])
        ]

        while queue:
            cost, _, _, zone, turn, path = heapq.heappop(queue)
            if cost > best.get((zone, turn), float("inf")):
                continue
            if zone == end:
                return path
            if turn >= horizon:
                continue

            # Option 1: wait one turn in place.
            if self._zone_ok(zone, turn + 1):
                nxt = (zone, turn + 1)
                if turn + 1 < best.get(nxt, float("inf")):
                    best[nxt] = turn + 1
                    counter += 1
                    heapq.heappush(
                        queue,
                        (turn + 1, 0, counter, zone, turn + 1, path + [nxt]),
                    )

            # Option 2: move to a neighbor.
            for conn in self.graph.get_neighbors(zone):
                neighbor = (
                    conn.zone_2 if conn.zone_1 == zone else conn.zone_1
                )
                neighbor_zone = self.graph.get_zone(neighbor)
                if neighbor_zone.zone_type == "blocked":
                    continue

                is_restricted = neighbor_zone.zone_type == "restricted"
                transit_time = 2 if is_restricted else 1
                arrival = turn + transit_time

                # Connection must be free for every turn of the transit.
                if any(
                    not self._connection_ok(zone, neighbor, turn + t)
                    for t in range(transit_time)
                ):
                    continue
                if not self._zone_ok(neighbor, arrival):
                    continue

                nxt = (neighbor, arrival)
                if arrival < best.get(nxt, float("inf")):
                    best[nxt] = arrival
                    is_priority = neighbor_zone.zone_type == "priority"
                    priority_tag = -1 if is_priority else 0
                    counter += 1
                    heapq.heappush(
                        queue,
                        (
                            arrival,
                            priority_tag,
                            counter,
                            neighbor,
                            arrival,
                            path + [nxt],
                        ),
                    )

        return None

    def commit_path(self, path: List[Tuple[str, int]]) -> None:
        """Reserves the exact turn-by-turn occupancy of a finalized path
        into the shared table, so subsequent drones plan around it."""
        for i, (zone, turn) in enumerate(path):
            if i == len(path) - 1:
                self.reservations.reserve_zone(zone, turn)
                continue
            next_zone, next_turn = path[i + 1]
            for t in range(turn, next_turn):
                self.reservations.reserve_connection(zone, next_zone, t)
            self.reservations.reserve_zone(next_zone, next_turn)
