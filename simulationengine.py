from simulationstats import Drone, DroneStatus, SimulationState
import zlib

import webcolors


def _color_code(name: str | None) -> str:
    """Resolves a color name to an ANSI escape code.

    Recognized CSS3 web color names (the standard set — 'gray', 'teal',
    'tomato', 'cornflowerblue', etc.) render as exact 24-bit true color.
    Any other single-word string still gets a deterministic, distinct
    color via a hash into the 256-color palette, so no valid color
    value is ever silently dropped.
    """
    if not name:
        return "\033[0m"
    key = name.lower()
    try:
        r, g, b = webcolors.name_to_rgb(key)
        return f"\033[38;2;{r};{g};{b}m"
    except ValueError:
        code_256 = 16 + (zlib.crc32(key.encode()) % 216)
        return f"\033[38;5;{code_256}m"


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
                    drone.status = DroneStatus.WAITING

    def process_departing_drones(self) -> None:
        """Handles drones departing from their current zone
        using a two-phase approach."""
        moving_drones = []

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

            self.stats.update_zone(drone.current_zone, -1)
            moving_drones.append(drone)

        for drone in moving_drones:
            next_zone = drone.path[0]
            has_conn_space = self.stats.has_connection_space(
                drone.current_zone, next_zone
            )

            if has_conn_space and self.stats.has_zone_space(next_zone):
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
            else:
                self.stats.update_zone(drone.current_zone, 1)

    def print_turn_summary(self) -> None:
        """Prints the simulation state for the current turn."""
        sim_output = []
        for drone in self.drones:
            if drone.status == DroneStatus.IN_TRANSIT:
                dest = drone.transit_destination
                if dest is None:
                    continue
                dest_obj = self.stats.graph.get_zone(dest)
                code = _color_code(getattr(dest_obj, "color", None))
                if dest_obj.zone_type == "restricted":
                    output_str = f"{drone.name}-{drone.current_zone}-{dest}"
                else:
                    output_str = f"{drone.name}-{dest}"

                sim_output.append(f"{code}{output_str}\033[0m")

        if sim_output:
            print(" ".join(sim_output))

    def run_engine(self) -> None:
        """Main execution loop."""
        while not self.is_simulation_complete():
            self.stats.turn_count += 1
            self.process_arriving_drones()
            self.process_departing_drones()
            self.print_turn_summary()
