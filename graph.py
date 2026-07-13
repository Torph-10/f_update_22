from models import Zone, Connection, MapData


class Graph:
    """Represents the map as a
    graph with zones and bidirectional connections."""

    def __init__(self, map_data: MapData):
        """Initializes the graph from MapData.

        Args:
            map_data: The parsed MapData object
            containing zones and connections.
        """
        self.zones: dict[str, Zone] = {
            zone.name: zone for zone in map_data.lis_zones
            }

        self.adjacency: dict[str, list[Connection]] = {
            zone.name: [] for zone in map_data.lis_zones
            }

        for conn in map_data.lis_connections:
            self.adjacency[conn.zone_1].append(conn)
            self.adjacency[conn.zone_2].append(conn)

    def get_zone(self, name: str) -> Zone:
        """Returns the zone object associated with the given name."""
        return self.zones[name]

    def get_neighbors(self, name: str) -> list[Connection]:
        """Returns a list of all connections
        connected to the given zone name."""
        return self.adjacency.get(name, [])
