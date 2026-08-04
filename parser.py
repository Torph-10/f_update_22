from models import Zone, Connection, MapData


class ParserError(Exception):
    """Raised when the input map file contains invalid or malformed data."""

    def __init__(self, line_number: int, msg: str) -> None:
        """Initializes the error with the offending line and a message.

        Args:
            line_number: The 1-indexed line number where the error
                occurred, or 0 for file-wide validation errors.
            msg: A human-readable description of what went wrong.
        """
        self.line_number = line_number
        self.msg = msg
        super().__init__(f"Line {line_number}: {msg}")


class Parser:
    """Parses a map file into a MapData object."""

    VALID_TYPES = ("normal", "blocked", "restricted", "priority")

    def __init__(self, file_path: str) -> None:
        """Initializes the parser with the path to the map file.

        Args:
            file_path: Path to the map file to parse.
        """
        self.file_path = file_path

    def parse(self) -> MapData:
        """Read the map file and build a MapData object.

        Returns:
            A MapData object containing the number of drones, zones,
            and connections parsed from the file.

        Raises:
            ParserError: If any line is invalid or required data is missing.
        """
        nb_drones: int = 0
        lis_zones: list[Zone] = []
        lis_connection: list[Connection] = []
        seen_zone_names = set()
        nb_drone_parsed = False

        with open(self.file_path, "r") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if line.startswith("#"):
                    continue
                if line.startswith("nb_drones"):
                    if nb_drone_parsed:
                        raise ParserError(i, "duplicate nb_drones line")
                    nb_drone_parsed = True
                    tokens = line.split(":")
                    if len(tokens) < 2 or not tokens[1].strip():
                        raise ParserError(
                            i, f"invalid nb_drones line '{line}'")
                    try:
                        nb_drones = int(tokens[1].strip())
                    except ValueError:
                        raise ParserError(
                            i, f"number of drones must be integer "
                            f"'{tokens[1].strip()}'"
                        )

                    if nb_drones < 1:
                        raise ParserError(
                            i, f"invalid number of drones '{nb_drones}'"
                        )
                elif line.startswith(("hub", "start_hub", "end_hub")):
                    if not nb_drone_parsed:
                        raise ParserError(
                            i, "nb_drones must be defined before any "
                            "zone line"
                        )
                    zone = self.parse_zone_line(line, i)
                    if zone.name in seen_zone_names:
                        raise ParserError(
                            i, f"duplicate zone name '{zone.name}'"
                        )
                    seen_zone_names.add(zone.name)
                    lis_zones.append(zone)

                elif line.startswith("connection"):
                    if not nb_drone_parsed:
                        raise ParserError(
                            i, "nb_drones must be defined before any "
                            "connection line"
                        )
                    lis_connection.append(self.parse_connection_line(line, i))
                elif line:
                    raise ParserError(i, f"unrecognized line '{line}'")

        self.validate(lis_zones, lis_connection)

        return MapData(nb_drones, lis_zones, lis_connection)

    def parse_zone_line(self, line: str, line_number: int) -> Zone:
        """Parse a single zone definition line into a Zone object.

        Args:
            line: The stripped line of text to parse.
            line_number: The line number, used for error reporting.

        Returns:
            A Zone object built from the line's data.

        Raises:
            ParserError: If the zone type or max_drones value is invalid.
        """
        zone_type = "normal"
        color = None
        max_drones = 1

        is_start = line.startswith("start_hub")
        is_end = line.startswith("end_hub")

        if ("[" in line) != ("]" in line):
            raise ParserError(line_number, "invalid metadata format")
        if line.count("[") > 1 or line.count("]") > 1:
            raise ParserError(
                line_number, "multiple metadata blocks not allowed"
            )

        parts = line.split("[")
        colon_parts = parts[0].split(":")
        if len(colon_parts) < 2:
            raise ParserError(line_number, f"invalid zone line '{line}'")
        main = colon_parts[1].split()

        if len(main) != 3:
            raise ParserError(
                line_number, f"expected '<name> <x> <y>', "
                f"got '{parts[0].strip()}'"
            )

        name = main[0]
        if "-" in name or " " in name:
            raise ParserError(line_number, f"invalid zone name '{name}'")
        try:
            x, y = int(main[1]), int(main[2])
        except ValueError:
            raise ParserError(
                line_number, "invalid data, coordinate must be integer"
            )

        if len(parts) > 1:
            metadata = parts[1].rstrip("]\n").split()
            for item in metadata:
                pieces = item.split("=")
                if len(pieces) != 2 or not pieces[0] or not pieces[1]:
                    raise ParserError(
                        line_number, f"invalid metadata '{item}'"
                    )
                key, value = pieces
                if key == "zone":
                    zone_type = value
                    if zone_type not in self.VALID_TYPES:
                        raise ParserError(
                            line_number, f"invalid zone type '{zone_type}'"
                        )
                elif key == "color":
                    color = value
                elif key == "max_drones":
                    if not (is_start or is_end):
                        try:
                            max_drones = int(value)
                        except ValueError:
                            raise ParserError(
                                line_number,
                                "invalid data, max drones must be integer"
                            )
                        if max_drones < 1:
                            raise ParserError(
                                line_number,
                                f"invalid max drones '{max_drones}'"
                            )
                else:
                    raise ParserError(
                        line_number, f"unknown metadata key '{key}'"
                    )

        return Zone(name, x, y, zone_type, max_drones, is_start, is_end, color)

    def parse_connection_line(self, line: str, line_number: int) -> Connection:
        """Parse a single connection definition line into a Connection object.

        Args:
            line: The stripped line of text to parse.
            line_number: The line number, used for error reporting.

        Returns:
            A Connection object built from the line's data.

        Raises:
            ParserError: If the max_link_capacity value is invalid.
        """
        max_link_capacity = 1

        if ("[" in line) != ("]" in line):
            raise ParserError(line_number, "invalid metadata format")
        if line.count("[") > 1 or line.count("]") > 1:
            raise ParserError(
                line_number, "multiple metadata blocks not allowed"
            )

        parts = line.split("[")
        colon_parts = parts[0].split(":")
        if len(colon_parts) < 2:
            raise ParserError(line_number, f"invalid connection line '{line}'")
        zones_part = colon_parts[1].strip().split("-")

        if (
            len(zones_part) != 2 or
            not zones_part[0].strip() or not
            zones_part[1].strip()
        ):

            raise ParserError(
                line_number, f"invalid connection '{colon_parts[1].strip()}'"
            )

        zone_1, zone_2 = zones_part[0].strip(), zones_part[1].strip()
        if zone_1 == zone_2:
            raise ParserError(
                line_number, f"self-connection not allowed '{zone_1}-{zone_2}'"
            )

        if len(parts) > 1:
            meta = parts[1].rstrip("]\n").strip()
            pieces = meta.split("=")
            if (
                len(pieces) != 2 or
                pieces[0] != "max_link_capacity" or
                not pieces[1]
            ):

                raise ParserError(
                    line_number, f"invalid metadata '{meta}'"
                )
            try:
                max_link_capacity = int(pieces[1])
            except ValueError:
                raise ParserError(
                    line_number, f"max link capacity must be integer "
                    f"'{pieces[1]}'"
                )
            if max_link_capacity < 1:
                raise ParserError(
                    line_number, f"invalid max link capacity "
                    f"'{max_link_capacity}'"
                )

        return Connection(zone_1, zone_2, max_link_capacity)

    def validate(
        self, zones: list[Zone], connections: list[Connection]
    ) -> None:
        """Validate cross-references and counts across the whole parsed map.

        Args:
            zones: All parsed zones.
            connections: All parsed connections.

        Raises:
            ParserError: If start/end zone counts are wrong, or a connection
                references a zone that does not exist.
        """
        seen_connections: set[tuple[str, str]] = set()

        for connection in connections:
            a, b = sorted((connection.zone_1, connection.zone_2))
            pair = (a, b)

            if pair in seen_connections:
                raise ParserError(
                    0, f"duplicate connection "
                    f"'{connection.zone_1}-{connection.zone_2}'"
                )

            seen_connections.add(pair)

        start_count = sum(zone.is_start for zone in zones)
        end_count = sum(zone.is_end for zone in zones)

        if start_count != 1:
            raise ParserError(
                0, f"expected 1 start_hub, found '{start_count}'"
            )
        if end_count != 1:
            raise ParserError(0, f"expected 1 end_hub, found '{end_count}'")

        zone_names = {zone.name for zone in zones}
        for connection in connections:
            if connection.zone_1 not in zone_names:
                raise ParserError(
                    0, f"invalid zone name '{connection.zone_1}'"
                )
            if connection.zone_2 not in zone_names:
                raise ParserError(
                    0, f"invalid zone name '{connection.zone_2}'"
                )
