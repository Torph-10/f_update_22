import sys

from graph import Graph
from parser import Parser, ParserError
from reservations import ReservationTable
from simulationengine import SimulationEngine
from simulationstats import Drone, SimulationState
from TimeSpaceRouter import TimeSpaceRouter


def main() -> None:
    """Parses the map, plans every drone's route with the time-space
    router, and runs the turn-by-turn simulation to completion."""
    try:
        parser = Parser("map.txt")
        map_data = parser.parse()
    except ParserError as exc:
        print(f"Error parsing map: {exc}", file=sys.stderr)
        sys.exit(1)

    graph = Graph(map_data)
    state = SimulationState(graph)

    reservations = ReservationTable()
    router = TimeSpaceRouter(graph, reservations)

    start_zone = next(z.name for z in map_data.lis_zones if z.is_start)
    end_zone = next(z.name for z in map_data.lis_zones if z.is_end)

    drones: list[Drone] = []
    for i in range(map_data.nb_drones):
        drone = Drone(f"D{i + 1}", start_zone)

        start_turn = 0
        horizon = start_turn + len(graph.zones) * 2
        path = router.find_path(
            start_zone, end_zone, start_turn, horizon
        )

        if path is None:
            print(
                f"Error: no viable route found for {drone.name} "
                f"within horizon {horizon}",
                file=sys.stderr,
            )
            sys.exit(1)

        router.commit_path(path)
        # Strip the start checkpoint: process_departing_drones treats
        # path[0] as the next zone to move into, not the current one.
        drone.path = [zone for zone, _ in path[1:]]
        drones.append(drone)

    engine = SimulationEngine(state, drones)
    engine.run_engine()


if __name__ == "__main__":
    main()
