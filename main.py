import sys
from typing import Optional
from graph import Graph
from parser import Parser, ParserError
from reservations import ReservationTable
from simulationengine import SimulationEngine
from simulationstats import Drone, SimulationState
from Timespacerouter import TimeSpaceRouter
from models import MapData


class DroneSimulationApp:
    """Main application controller for setting up
    and running the simulation."""

    def __init__(self, map_file: str) -> None:
        """Initializes the application with the target map file."""
        self.map_file: str = map_file
        self.graph: Optional[Graph] = None
        self.map_data: Optional[MapData] = None
        self.drones: list[Drone] = []

    def load_map(self) -> None:
        """Parses the map file and builds the graph."""
        try:
            parser = Parser(self.map_file)
            self.map_data = parser.parse()
            self.graph = Graph(self.map_data)
        except (ParserError, FileNotFoundError) as exc:
            print(f"Error parsing map: {exc}", file=sys.stderr)
            sys.exit(1)

    def plan_routes(self) -> None:
        """Plans collision-free routes for all drones using TimeSpaceRouter."""
        if self.graph is None or self.map_data is None:
            return

        reservations = ReservationTable()
        router = TimeSpaceRouter(self.graph, reservations)

        start_zone = next(
            z.name for z in self.map_data.lis_zones if z.is_start
        )
        end_zone = next(z.name for z in self.map_data.lis_zones if z.is_end)

        for i in range(self.map_data.nb_drones):
            drone = Drone(f"D{i + 1}", start_zone)

            start_turn = 0
            max_time = len(self.graph.zones) * 2 + self.map_data.nb_drones * 2
            path = router.find_path(start_zone, end_zone, start_turn, max_time)

            if path is None:
                print(
                    f"Error: no viable route found for {drone.name} "
                    f"within horizon {max_time}",
                    file=sys.stderr,
                )
                sys.exit(1)

            router.commit_path(path)
            drone.path = [zone for zone, _ in path[1:]]
            self.drones.append(drone)

    @staticmethod
    def main() -> None:
        """Executes the complete simulation workflow."""
        if len(sys.argv) != 2:
            print("Usage: python fly-in.py <map_file>")
            sys.exit(1)

        app = DroneSimulationApp(sys.argv[1])
        app.load_map()
        app.plan_routes()

        if app.graph is None:
            return

        state = SimulationState(app.graph)
        engine = SimulationEngine(state, app.drones)

        try:
            print("Running Simulator")
            engine.run_engine()
        except KeyboardInterrupt:
            print("\nSimulation interrupted by user.")


if __name__ == "__main__":
    DroneSimulationApp.main()
