from dataclasses import dataclass


@dataclass
class Zone():
    """A single node on the map (a hub, start, or end point)."""

    name: str
    x: int
    y: int
    zone_type: str
    max_drones: int = 1
    is_start: bool = False
    is_end: bool = False
    color: str | None = None


@dataclass
class Connection:
    """A bidirectional link between two zones."""

    zone_1: str
    zone_2: str
    max_link_capacity: int = 1


@dataclass
class MapData:
    """The fully parsed map, ready to be turned into a Graph."""

    nb_drones: int
    lis_zones: list[Zone]
    lis_connections: list[Connection]
