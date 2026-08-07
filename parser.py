from models import Zone, Connection, MapData


class ParserError(Exception):
    """Raised when the input map file contains invalid or malformed data."""

    def __init__(self, line_number: int, msg: str) -> None:
        """Initializes the error with the offending line and a message."""
        self.line_number = line_number
        self.msg = msg
        super().__init__(f"Line {line_number}: {msg}")


class Parser:
    """Parses a map file into a MapData object."""

    VALID_TYPES = ("normal", "blocked", "restricted", "priority")

    def __init__(self, file_path: str) -> None:
        """Initializes the parser with the path to the map file."""
        self.file_path = file_path

    @staticmethod
    def _split_metadata(line: str) -> tuple[str, str | None]:
        """Splits off a trailing [key=value ...] metadata block, if present."""
        if not line.endswith("]"):
            return line, None

        open_bracket = line.rfind("[")
        if open_bracket == -1:
            return line, None

        content = line[:open_bracket].rstrip()
        metadata = line[open_bracket + 1:-1]
        return content, metadata

    def parse(self) -> MapData:
        """Reads the map file line by line
        and builds a validated MapData object."""
        nb_drones: int = 0
        lis_zones: list[Zone] = []
        lis_connection: list[Connection] = []
        zone_lines: list[int] = []
        connection_lines: list[int] = []
        seen_zone_names = set()
        nb_drone_parsed: bool = False
        last_line: int = 0

        with open(self.file_path, "r") as f:
            for i, line in enumerate(f, 1):
                last_line = i
                line = line.strip()
                if line.startswith("#"):
                    continue
                keyword = line.split(":", 1)[0].strip()
                if keyword == "nb_drones":
                    if nb_drone_parsed:
                        raise ParserError(i, "duplicate nb_drones line")
                    nb_drone_parsed = True
                    tokens = line.split(":")
                    if len(tokens) != 2 or not tokens[1].strip():
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
                elif keyword in ("hub", "start_hub", "end_hub"):
                    if not nb_drone_parsed:
                        raise ParserError(
                            i, "nb_drones must be defined before any "
                            "zone line"
                        )
                    zone = self.parse_zone_line(line, keyword, i)
                    if zone.name in seen_zone_names:
                        raise ParserError(
                            i, f"duplicate zone name '{zone.name}'"
                        )
                    seen_zone_names.add(zone.name)
                    lis_zones.append(zone)
                    zone_lines.append(i)

                elif keyword == "connection":
                    if not nb_drone_parsed:
                        raise ParserError(
                            i, "nb_drones must be defined before any "
                            "connection line"
                        )
                    lis_connection.append(self.parse_connection_line(line, i))
                    connection_lines.append(i)
                elif line:
                    raise ParserError(i, f"unrecognized line '{line}'")

        self.validate(
            lis_zones, lis_connection, zone_lines, connection_lines, last_line
        )

        return MapData(nb_drones, lis_zones, lis_connection)

    def parse_zone_line(
        self, line: str, keyword: str, line_number: int
    ) -> Zone:
        """Parses a single zone definition line
        and its metadata into a Zone object."""
        zone_type: str = "normal"
        color: str | None = None
        max_drones: int = 1

        is_start: bool = keyword == "start_hub"
        is_end: bool = keyword == "end_hub"

        content, metadata_str = self._split_metadata(line)

        colon_parts = content.split(":", 1)
        if len(colon_parts) < 2:
            raise ParserError(line_number, f"invalid zone line '{line}'")
        main = colon_parts[1].split()

        if len(main) != 3:
            raise ParserError(
                line_number, f"expected '<name> <x> <y>', "
                f"got '{colon_parts[1].strip()}'"
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

        if metadata_str:
            for item in metadata_str.split():
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
        """Parses a single connection definition line
        and its metadata into a Connection object."""
        max_link_capacity = 1

        content, metadata_str = self._split_metadata(line)

        colon_parts = content.split(":", 1)
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

        if metadata_str:
            meta = metadata_str.strip()
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
        self,
        zones: list[Zone],
        connections: list[Connection],
        zone_lines: list[int],
        connection_lines: list[int],
        last_line: int,
    ) -> None:
        """Validates cross-references, ensures unique
        connections, and verifies start/end hub counts.
        `zone_lines`/`connection_lines` give the source line number for
        each entry in `zones`/`connections` (same order, same index), so
        every error raised here can point at a real line."""
        seen_connections: dict[tuple[str, str], int] = {}

        zone_names = {zone.name for zone in zones}

        for connection, line_number in zip(connections, connection_lines):
            if connection.zone_1 not in zone_names:
                raise ParserError(
                    line_number, f"invalid zone name '{connection.zone_1}'"
                )
            if connection.zone_2 not in zone_names:
                raise ParserError(
                    line_number, f"invalid zone name '{connection.zone_2}'"
                )

            a, b = sorted((connection.zone_1, connection.zone_2))
            pair = (a, b)

            if pair in seen_connections:
                raise ParserError(
                    line_number, f"duplicate connection "
                    f"'{connection.zone_1}-{connection.zone_2}'"
                )

            seen_connections[pair] = line_number

        start_lines = [
            line for zone, line in zip(zones, zone_lines) if zone.is_start
        ]
        end_lines = [
            line for zone, line in zip(zones, zone_lines) if zone.is_end
        ]

        if len(start_lines) == 0:
            raise ParserError(
                last_line, "expected 1 start_hub, found '0'"
            )
        if len(start_lines) > 1:
            raise ParserError(
                start_lines[1],
                f"expected 1 start_hub, found '{len(start_lines)}'"
            )
        if len(end_lines) == 0:
            raise ParserError(
                last_line, "expected 1 end_hub, found '0'"
            )
        if len(end_lines) > 1:
            raise ParserError(
                end_lines[1],
                f"expected 1 end_hub, found '{len(end_lines)}'"
            )
