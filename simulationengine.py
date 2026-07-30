from simulationstats import Drone, DroneStatus, SimulationState


class SimulationEngine:
    """Runs the turn-by-turn drone simulation over a pre-planned set
    of paths, enforcing zone and connection capacity as drones move."""

    def __init__(self, stats: SimulationState, drones: list[Drone]) -> None:
        """Initializes the engine with shared state and the drone fleet."""
        self.stats: SimulationState = stats
        self.drones: list[Drone] = drones

    def is_simulation_complete(self) -> bool:
        """Checks if all drones have reached their final destination."""
        return all(
            drone.status == DroneStatus.DELIVERED for drone in self.drones
        )

    def process_arriving_drones(self) -> None:
        """Handles drones arriving at their destination zone."""
        for drone in self.drones:
            if drone.status == DroneStatus.IN_TRANSIT:
                drone.transit_timer -= 1
                if drone.transit_timer <= 0:
                    if drone.transit_destination is None:
                        continue
                    self.stats.update_connection(
                        drone.current_zone, drone.transit_destination, -1
                    )
                    drone.current_zone = drone.transit_destination
                    drone.status = DroneStatus.ARRIVED

    def process_departing_drones(self) -> None:
        """Handles drones departing from their current zone."""
        for drone in self.drones:
            if drone.status != DroneStatus.WAITING:
                continue

            if not drone.path:
                self.stats.update_zone(drone.current_zone, -1)
                drone.status = DroneStatus.DELIVERED
                continue

            next_zone = drone.path[0]

            if next_zone == drone.current_zone:
                drone.path.pop(0)
                continue

            has_conn_space = self.stats.has_connection_space(
                drone.current_zone, next_zone
            )
            if has_conn_space and self.stats.has_zone_space(next_zone):
                self.stats.update_zone(drone.current_zone, -1)
                self.stats.update_connection(
                    drone.current_zone, next_zone, 1
                )

                drone.transit_destination = next_zone
                self.stats.update_zone(next_zone, 1)
                drone.status = DroneStatus.IN_TRANSIT

                zone_obj = self.stats.graph.get_zone(next_zone)
                is_restricted = zone_obj.zone_type == "restricted"
                drone.transit_timer = 2 if is_restricted else 1
                drone.path.pop(0)

    def finalize_arrivals(self) -> None:
        """Promotes arrived drones to WAITING state for next turn."""
        for drone in self.drones:
            if drone.status == DroneStatus.ARRIVED:
                drone.status = DroneStatus.WAITING

    def print_turn_summary(self) -> None:
        """Prints the simulation state for the current turn."""

        color = {
            "black": "\033[30m",
            "red": "\033[31m",
            "green": "\033[32m",
            "yellow": "\033[33m",
            "blue": "\033[34m",
            "purple": "\033[35m",
            "cyan": "\033[36m",
            "white": "\033[37m",
            "orange": "\033[38;5;208m",
            "brown": "\033[38;5;130m",
            "maroon": "\033[38;5;52m",
            "darkred": "\033[38;5;88m",
            "violet": "\033[38;5;177m",
            "crimson": "\033[38;5;160m",
        }

        sim_output = []
        for drone in self.drones:
            if drone.status == DroneStatus.IN_TRANSIT:
                dest = drone.transit_destination
                if dest is None:
                    continue
                dest_obj = self.stats.graph.get_zone(dest)

                zone_color = getattr(dest_obj, 'color', None)

                color_code = (
                    color.get(zone_color.lower(), "\033[0m")
                    if zone_color else "\033[0m"
                )

                if dest_obj.zone_type == "restricted":
                    output_str = f"{drone.name}-{drone.current_zone}-{dest}"
                else:
                    output_str = f"{drone.name}-{dest}"

                sim_output.append(f"{color_code}{output_str}\033[0m")

        if sim_output:
            print(" ".join(sim_output))

    def run_engine(self) -> None:
        """Main execution loop."""
        while not self.is_simulation_complete():
            self.stats.turn_count += 1
            self.process_arriving_drones()
            self.finalize_arrivals()
            self.process_departing_drones()
            self.print_turn_summary()
