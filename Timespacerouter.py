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

    def find_path(self, start, end, start_turn, max_time):
        """Finds the earliest-arrival path from `start` to `end`.

        Works turn-by-turn: `reached` tracks every (zone, turn) state we've
        found a path to. Because we process turns in increasing order and
        every move costs at least 1 turn, the first time we reach `end` is
        guaranteed to be the earliest possible arrival.
        """
        reached = {(start, start_turn): [(start, start_turn)]}
        zones_at_turn = {start_turn: [start]}

        for turn in range(start_turn, max_time + 1):
            for zone in zones_at_turn.get(turn, []):
                path_so_far = reached[(zone, turn)]

                if zone == end:
                    return path_so_far

                # Option 1: wait one turn in place.
                if self._zone_ok(zone, turn + 1):
                    self._add_state(reached, zones_at_turn, zone, turn + 1, path_so_far)

                # Option 2: move to each neighbor.
                for conn in self.graph.get_neighbors(zone):
                    neighbor = conn.zone_2 if conn.zone_1 == zone else conn.zone_1
                    neighbor_zone = self.graph.get_zone(neighbor)
                    if neighbor_zone.zone_type == "blocked":
                        continue

                    transit_time = 2 if neighbor_zone.zone_type == "restricted" else 1
                    arrival = turn + transit_time

                    connection_free = all(
                        self._connection_ok(zone, neighbor, turn + t)
                        for t in range(transit_time)
                    )
                    if not connection_free or not self._zone_ok(neighbor, arrival):
                        continue

                    self._add_state(reached, zones_at_turn, neighbor, arrival, path_so_far)

        return None


    def _add_state(self, reached, zones_at_turn, zone, turn, path_so_far):
        """Records the first path found to (zone, turn), if none exists yet."""
        state = (zone, turn)
        if state not in reached:
            reached[state] = path_so_far + [state]
            zones_at_turn.setdefault(turn, []).append(zone)

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
