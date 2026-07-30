from typing import Dict, Tuple


class ReservationTable:
    """Turn-indexed occupancy for zones and connections, shared across
    drones during route planning so later drones avoid conflicts with
    already-planned ones."""

    def __init__(self) -> None:
        """Initializes empty zone and connection reservation tables."""
        self.zone_res: Dict[Tuple[str, int], int] = {}
        self.conn_res: Dict[Tuple[Tuple[str, str], int], int] = {}

    @staticmethod
    def _conn_key(z1: str, z2: str) -> Tuple[str, str]:
        """Builds a direction-independent key for a connection."""
        a, b = sorted((z1, z2))
        return (a, b)

    def zone_count(self, zone: str, turn: int) -> int:
        """Number of drones already planned to occupy `zone` at `turn`."""
        return self.zone_res.get((zone, turn), 0)

    def conn_count(self, z1: str, z2: str, turn: int) -> int:
        """Number of drones already planned to traverse z1-z2 at `turn`."""
        return self.conn_res.get((self._conn_key(z1, z2), turn), 0)

    def reserve_zone(self, zone: str, turn: int) -> None:
        """Reserves one occupancy slot in `zone` at `turn`."""
        key = (zone, turn)
        self.zone_res[key] = self.zone_res.get(key, 0) + 1

    def reserve_connection(self, z1: str, z2: str, turn: int) -> None:
        """Reserves one occupancy slot on the z1-z2 connection at `turn`."""
        key = (self._conn_key(z1, z2), turn)
        self.conn_res[key] = self.conn_res.get(key, 0) + 1
