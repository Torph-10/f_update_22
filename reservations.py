from typing import Dict, Tuple


class ReservationTable:
    """Turn-indexed occupancy for zones and connections, shared across
    drones during route planning so later drones avoid conflicts with
    already-planned ones."""

    def __init__(self) -> None:
        self.zone_res: Dict[Tuple[str, int], int] = {}
        self.conn_res: Dict[Tuple[Tuple[str, str], int], int] = {}

    @staticmethod
    def _conn_key(z1: str, z2: str) -> Tuple[str, str]:
        return tuple(sorted((z1, z2)))

    def zone_count(self, zone: str, turn: int) -> int:
        """Number of drones already planned to occupy `zone` at `turn`."""
        return self.zone_res.get((zone, turn), 0)

    def conn_count(self, z1: str, z2: str, turn: int) -> int:
        """Number of drones already planned to traverse z1-z2 at `turn`."""
        return self.conn_res.get((self._conn_key(z1, z2), turn), 0)

    def reserve_zone(self, zone: str, turn: int) -> None:
        key = (zone, turn)
        self.zone_res[key] = self.zone_res.get(key, 0) + 1

    def reserve_connection(self, z1: str, z2: str, turn: int) -> None:
        key = (self._conn_key(z1, z2), turn)
        self.conn_res[key] = self.conn_res.get(key, 0) + 1

    def prune_before(self, turn: int) -> None:
        """Drops entries whose turn has already elapsed, so the table
        doesn't grow unbounded over a long simulation horizon."""
        self.zone_res = {k: v for k, v in self.zone_res.items() if k[1] >= turn}
        self.conn_res = {k: v for k, v in self.conn_res.items() if k[1] >= turn}