from enum import Enum
from typing import Optional, Tuple

from graph import Graph


class DroneStatus(Enum):
    """Represents the current state of a drone in the simulation."""

    WAITING = "WAITING"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    ARRIVED = "ARRIVED"


class Drone:
    """Tracks the individual state and planned path of a single drone."""

    def __init__(self, drone_name: str, start_zone: str) -> None:
        self.name: str = drone_name
        self.current_zone: str = start_zone
        self.status: DroneStatus = DroneStatus.WAITING
        self.transit_destination: Optional[str] = None
        self.transit_timer: int = 0
        self.path: list[str] = []


class SimulationState:
    """Tracks the occupancy of all zones and connections turn-by-turn."""

    def __init__(self, graph: Graph) -> None:
        self.graph: Graph = graph
        self.turn_count: int = 0

        self.zone_occupancy: dict[str, int] = {
            zone_name: 0 for zone_name in graph.zones
        }
        self.connection_occupancy: dict[Tuple[str, str], int] = {}

    def get_conn_key(self, z1: str, z2: str) -> Tuple[str, str]:
        """Normalizes connection key to be direction-independent."""
        a, b = sorted((z1, z2))
        return (a, b)

    def has_zone_space(self, zone_name: str) -> bool:
        """Checks if a zone can accept another drone (max_drones)."""
        zone = self.graph.get_zone(zone_name)
        if zone.zone_type == "blocked":
            return False
        if zone.is_start or zone.is_end:
            return True
        return self.zone_occupancy.get(zone_name, 0) < zone.max_drones

    def has_connection_space(self, z1: str, z2: str) -> bool:
        """Checks if a connection can accept another drone."""
        if z1 == z2:
            return True

        conn_key = self.get_conn_key(z1, z2)
        current_count = self.connection_occupancy.get(conn_key, 0)

        for conn in self.graph.get_neighbors(z1):
            if conn.zone_1 == z2 or conn.zone_2 == z2:
                return current_count < conn.max_link_capacity
        return False

    def update_zone(self, zone_name: str, count: int) -> None:
        """Updates the drone count in a zone (count can be +1 or -1)."""
        zone = self.graph.get_zone(zone_name)

        if not zone.is_start and not zone.is_end:
            self.zone_occupancy[zone_name] += count

    def update_connection(self, z1: str, z2: str, count: int) -> None:
        """Updates the drone count on a connection (+1 or -1)."""
        conn_key = self.get_conn_key(z1, z2)
        current_occ = self.connection_occupancy.get(conn_key, 0)
        self.connection_occupancy[conn_key] = current_occ + count

        if self.connection_occupancy[conn_key] <= 0:
            del self.connection_occupancy[conn_key]
