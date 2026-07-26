from dataclasses import dataclass


@dataclass
class Zone():
    """A single node on the map (a hub, start, or end point).

    Attributes:
        name: Unique identifier for the zone.
        x: X coordinate on the map grid.
        y: Y coordinate on the map grid.
        zone_type: One of "normal", "blocked", "restricted", "priority".
        max_drones: Maximum number of drones allowed in the zone at once.
        is_start: True if this is the unique start_hub.
        is_end: True if this is the unique end_hub.
        color: Optional display color parsed from the map metadata.
    """

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
    """A bidirectional link between two zones.

    Attributes:
        zone_1: Name of one endpoint zone.
        zone_2: Name of the other endpoint zone.
        max_link_capacity: Maximum number of drones allowed to traverse
            this connection at once.
    """

    zone_1: str
    zone_2: str
    max_link_capacity: int = 1


@dataclass
class MapData:
    """The fully parsed map, ready to be turned into a Graph.

    Attributes:
        nb_drones: Number of drones to simulate.
        lis_zones: All zones parsed from the map file.
        lis_connections: All connections parsed from the map file.
    """

    nb_drones: int
    lis_zones: list[Zone]
    lis_connections: list[Connection]
