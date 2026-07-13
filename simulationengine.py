from simulationstats import DroneStatus, Drone, SimulationState
from models import Connection

class SimulationEngine:
    def __init__(self, stats: SimulationState, drones: list[Drone]) -> None:
        self.stats: SimulationState = stats
        self.drones: list[Drone] = drones

    def is_simulation_complete(self) -> bool:
        """Checks if all drones have reached their final destination."""
        for drone in self.drones:
            if drone.status != DroneStatus.DELIVERED:
                return False

        return True

    def process_arriving_drones(self) -> None:
        """Handles drones arriving at their destination zone."""
        for drone in self.drones:
            if drone.status == DroneStatus.IN_TRANSIT:
                drone.transit_timer -= 1

                if drone.transit_timer <= 0:
                    drone.current_zone = drone.transit_destination
                    drone.status = DroneStatus.WAITING

                    print(f"Turn {self.stats.turn_count}: {drone.name} "
                          f"arrived at {drone.current_zone}")

    def process_departing_drones(self) -> None:
        """Handles drones departing from their current zone to the next."""

        for drone in self.drones:
            if drone.status == DroneStatus.WAITING:

                if not drone.path:
                    drone.status = DroneStatus.DELIVERED
                    print(f"Turn {self.stats.turn_count}: {drone.name} is DELIVERED!")
                    continue

                next_zone = drone.path[0]
                if (
                    self.stats.has_connection_space(drone.current_zone, next_zone)
                    and self.stats.has_zone_space(next_zone)
                ):
                    self.stats.update_zone(drone.current_zone, -1)
                    self.stats.update_connection(drone.current_zone, next_zone, 1)

                    drone.transit_destination = next_zone
                    drone.status = DroneStatus.IN_TRANSIT

                    for conn in self.stats.graph.get_neighbors(drone.current_zone):
                        if conn.zone_1 == next_zone or conn.zone_2 == next_zone:
                            if 
                            break
                    drone.transit_timer = 1
                    drone.path.pop(0)

                    print(f"Turn {self.stats.turn_count}: {drone.name} "
                          f"departing from {drone.current_zone} to {next_zone}")


    def print_turn_summary(self) -> None:
        pass

    def run_engine(self) -> None:
        while not self.is_simulation_complete():
            self.stats.turn_count += 1

            self.process_arriving_drones()
            self.process_departing_drones()
