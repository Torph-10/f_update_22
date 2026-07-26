from typing import List, Optional, Tuple

from graph import Graph
from reservations import ReservationTable


class TimeSpaceRouter:
    """Plans a single drone's route as a shortest path over (zone, turn)
    states, respecting zone/connection capacity already reserved by
    previously-planned drones."""

    def __init__(self, graph: Graph, reservations: ReservationTable) -> None:
        """Initializes the router with the map and the shared reservation
        table used to avoid conflicts with already-planned drones."""
        self.graph = graph
        self.reservations = reservations

    def _zone_ok(self, zone_name: str, turn: int) -> bool:
        """Checks if a zone has a free slot at a given turn."""
        zone = self.graph.get_zone(zone_name)
        if zone.zone_type == "blocked":
            return False
        if zone.is_start or zone.is_end:
            return True
        return self.reservations.zone_count(zone_name, turn) < zone.max_drones

    def _connection_ok(self, z1: str, z2: str, turn: int) -> bool:
        """Checks if the connection between two zones has a free slot
        at a given turn."""
        if z1 == z2:
            return True
        for conn in self.graph.get_neighbors(z1):
            if conn.zone_1 == z2 or conn.zone_2 == z2:
                count = self.reservations.conn_count(z1, z2, turn)
                return count < conn.max_link_capacity
        return False

    def find_path(
        self, start: str, end: str, start_turn: int, max_time: int
    ) -> Optional[List[Tuple[str, int]]]:
        """Finds the earliest-arrival path from `start` to `end`.

        Works turn-by-turn: `reached` tracks every (zone, turn) state
        found so far, along with a priority score (higher when the
        path passes through more "priority" zones). Because turns are
        processed in increasing order and every move costs at least
        1 turn, the first time `end` is reached is guaranteed to be
        the earliest possible arrival; among equal-turn ties at the
        same state, the higher-priority-score path wins."""
        start_score = (
            1 if self.graph.get_zone(start).zone_type == "priority" else 0
        )
        reached = {(start, start_turn): (start_score, [(start, start_turn)])}
        zones_at_turn = {start_turn: [start]}

        for turn in range(start_turn, max_time + 1):

            for zone in zones_at_turn.get(turn, []):
                score_so_far, path_so_far = reached[(zone, turn)]

                if zone == end:
                    return path_so_far

                if self._zone_ok(zone, turn + 1):
                    self._add_state(
                        reached, zones_at_turn, zone, turn + 1,
                        path_so_far, score_so_far
                    )

                for conn in self.graph.get_neighbors(zone):
                    neighbor = (
                        conn.zone_2 if conn.zone_1 == zone else conn.zone_1
                    )
                    neighbor_zone = self.graph.get_zone(neighbor)
                    if neighbor_zone.zone_type == "blocked":
                        continue

                    transit_time = (
                        2 if neighbor_zone.zone_type == "restricted" else 1)
                    arrival = turn + transit_time

                    connection_free = all(
                        self._connection_ok(zone, neighbor, turn + t)
                        for t in range(transit_time)
                    )
                    if (
                        not connection_free or not
                        self._zone_ok(neighbor, arrival)
                    ):
                        continue

                    new_score = score_so_far + (
                        1 if neighbor_zone.zone_type == "priority" else 0
                    )
                    self._add_state(
                        reached, zones_at_turn, neighbor, arrival,
                        path_so_far, new_score
                    )

        return None

    def _add_state(
        self,
        reached: dict,
        zones_at_turn: dict,
        zone: str,
        turn: int,
        path_so_far: list,
        score: int,
    ) -> None:
        """Records the path to (zone, turn), preferring higher-priority-zone
        paths when a state is reached again at the same turn."""
        state = (zone, turn)
        new_path = path_so_far + [state]
        existing = reached.get(state)
        if existing is None:
            reached[state] = (score, new_path)
            zones_at_turn.setdefault(turn, []).append(zone)
        elif score > existing[0]:
            reached[state] = (score, new_path)

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
