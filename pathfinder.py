import heapq
from graph import Graph


class Pathfinder:
    def __init__(self, graph: Graph) -> None:
        self.graph = graph

    def find_path(self, start_name: str, start_turn: int, end_name: str, reservations: dict[tuple[str, int], int]) -> list[str]:
        """Finds the shortest path from start_name
        to end_name using Dijkstra."""
        queue = [(start_turn, start_name)]
        costs = {start_name: start_turn}
        previous: dict[str, str | None] = {start_name: None}

        while queue:
            current_cost, current_zone = heapq.heappop(queue)

            if current_zone == end_name:
                return self._reconstruct_path(previous, end_name)

            if current_cost > costs.get(current_zone, 0):
                continue

            for connection in self.graph.get_neighbors(current_zone):
                neighbor_name = (
                    connection.zone_2
                    if connection.zone_1 == current_zone
                    else connection.zone_1
                )
                neighbor_zone = self.graph.get_zone(neighbor_name)

                if neighbor_zone.zone_type == "blocked":
                    continue

                move_cost = 2 if neighbor_zone.zone_type == "restricted" else 1
                new_cost = current_cost + move_cost

                if new_cost < costs.get(neighbor_name, float('inf')):
                    if reservations.get((neighbor_name, new_cost), 0) >= neighbor_zone.max_drones:
                        continue
                    costs[neighbor_name] = new_cost
                    previous[neighbor_name] = current_zone
                    heapq.heappush(queue, (new_cost, neighbor_name))

        return []

    def _reconstruct_path(
        self, previous: dict[str, str | None], end_name: str
    ) -> list[str]:
        """Backtracks from end_name to start_name to build the path."""
        path = []
        current: str | None = end_name
        while current is not None:
            path.append(current)
            current = previous[current]
        return path[::-1]
