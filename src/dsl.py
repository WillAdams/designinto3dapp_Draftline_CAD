"""Parser, world-coordinate geometry, and ASCII DXF R12 writer for Draftline."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import math

log = logging.getLogger(f"app.{__name__}")

Vec3 = tuple[float, float, float]
Vec2 = tuple[float, float]


@dataclass
class Plane:
    name: str
    origin: Vec3
    u: Vec3
    v: Vec3
    normal: Vec3 = field(init=False)

    def __post_init__(self):
        self.u = normalize(self.u)
        self.v = normalize(self.v)
        self.normal = normalize(cross(self.u, self.v))


@dataclass
class Entity:
    kind: str
    name: str
    layer: str
    plane: str
    rotate: float
    offset: float
    values: dict[str, object]
    line_no: int
    color: int | None = None


@dataclass
class Layer:
    name: str
    color: int = 7


COLOR_NAMES = {
    "red": 1,
    "yellow": 2,
    "green": 3,
    "cyan": 4,
    "blue": 5,
    "magenta": 6,
    "white": 7,
    "black": 7,
    "gray": 8,
    "grey": 8,
    "lightgray": 9,
    "orange": 30,
}


def parse_color(raw: str, allow_bylayer: bool = False) -> int | None:
    value = raw.strip().lower()
    if allow_bylayer and value == "bylayer":
        return None
    if value in COLOR_NAMES:
        return COLOR_NAMES[value]
    try:
        index = int(value)
    except ValueError as exc:
        raise ValueError(f"unknown color '{raw}'; use an ACI number or color name") from exc
    if not 1 <= index <= 255:
        raise ValueError("color index must be between 1 and 255")
    return index


def add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def scale(a: Vec3, amount: float) -> Vec3:
    return (a[0] * amount, a[1] * amount, a[2] * amount)


def dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def normalize(a: Vec3) -> Vec3:
    length = math.sqrt(dot(a, a))
    if length < 1e-9:
        raise ValueError("plane axes must not be parallel or zero length")
    return scale(a, 1.0 / length)


DEFAULT_PLANES = {
    "XY": Plane("XY", (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
}


def parse_vector(raw: str, count: int, label: str) -> tuple[float, ...]:
    parts = raw.split(",")
    if len(parts) != count:
        raise ValueError(f"{label} expects {count} comma-separated numbers")
    return tuple(float(part) for part in parts)


def parse_program(source: str) -> tuple[list[Entity], dict[str, Plane], str, dict[str, Layer], list[str]]:
    planes = dict(DEFAULT_PLANES)
    entities: list[Entity] = []
    layers = {"0": Layer("0", 7)}
    errors: list[str] = []
    units = "unitless"

    for line_no, raw_line in enumerate(source.splitlines(), start=1):
        command_line = raw_line.split("#", 1)[0].strip()
        if not command_line:
            continue
        tokens = command_line.split()
        command = tokens[0].upper()
        try:
            if command == "UNITS":
                if len(tokens) != 2:
                    raise ValueError("syntax: UNITS <name>")
                units = tokens[1]
                continue

            if command == "LAYER":
                params = _parameters(tokens[1:])
                _check_keys(params, {"name", "color"})
                if "name" not in params:
                    raise ValueError("syntax: LAYER name=<name> color=<ACI number or name>")
                name = params["name"].upper()
                layers[name] = Layer(name, parse_color(params.get("color", "7")))
                continue

            if command == "PLANE":
                if len(tokens) < 2:
                    raise ValueError("syntax: PLANE <name> origin=x,y,z u=x,y,z v=x,y,z")
                name = tokens[1].upper()
                params = _parameters(tokens[2:])
                _check_keys(params, {"origin", "u", "v"})
                origin = parse_vector(params.get("origin", "0,0,0"), 3, "origin")
                u = parse_vector(params.get("u", "1,0,0"), 3, "u")
                v = parse_vector(params.get("v", "0,1,0"), 3, "v")
                planes[name] = Plane(name, origin, u, v)  # type: ignore[arg-type]
                continue

            if command not in {"LINE", "CIRCLE", "ARC"}:
                raise ValueError(f"unknown command '{tokens[0]}'")
            params = _parameters(tokens[1:])
            allowed = {"name", "plane", "rotate", "offset", "layer", "color"}
            required: set[str]
            if command == "LINE":
                allowed |= {"from", "to"}
                required = {"from", "to"}
                values = {
                    "from": parse_vector(params.get("from", ""), 2, "from"),
                    "to": parse_vector(params.get("to", ""), 2, "to"),
                }
            elif command == "CIRCLE":
                allowed |= {"center", "radius"}
                required = {"center", "radius"}
                values = {
                    "center": parse_vector(params.get("center", ""), 2, "center"),
                    "radius": float(params.get("radius", "")),
                }
            else:
                allowed |= {"center", "radius", "start", "end"}
                required = {"center", "radius", "start", "end"}
                values = {
                    "center": parse_vector(params.get("center", ""), 2, "center"),
                    "radius": float(params.get("radius", "")),
                    "start": float(params.get("start", "")),
                    "end": float(params.get("end", "")),
                }
            _check_keys(params, allowed)
            missing = required - params.keys()
            if missing:
                raise ValueError(f"missing parameter(s): {', '.join(sorted(missing))}")
            plane = params.get("plane", "XY").upper()
            if plane not in planes:
                raise ValueError(f"undefined plane '{plane}'")
            if float(values.get("radius", 1)) <= 0:
                raise ValueError("radius must be greater than zero")
            layer_name = params.get("layer", "0").upper()
            layers.setdefault(layer_name, Layer(layer_name, 7))
            entity_color = parse_color(params["color"], allow_bylayer=True) if "color" in params else None
            entity = Entity(
                kind=command,
                name=params.get("name", f"{command.lower()}-{len(entities) + 1}"),
                layer=layer_name,
                plane=plane,
                rotate=float(params.get("rotate", "0")),
                offset=float(params.get("offset", "0")),
                values=values,
                line_no=line_no,
                color=entity_color,
            )
            entities.append(entity)
        except (ValueError, KeyError) as exc:
            errors.append(f"Line {line_no}: {exc}")

    log.debug("parsed %d entities, %d planes, %d layers with %d issues", len(entities), len(planes), len(layers), len(errors))
    return entities, planes, units, layers, errors


def _parameters(tokens: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for token in tokens:
        if "=" not in token:
            raise ValueError(f"expected key=value, got '{token}'")
        key, value = token.split("=", 1)
        key = key.lower()
        if key in result:
            raise ValueError(f"parameter '{key}' is repeated")
        result[key] = value
    return result


def _check_keys(params: dict[str, str], allowed: set[str]) -> None:
    unknown = set(params) - allowed
    if unknown:
        raise ValueError(f"unknown parameter(s): {', '.join(sorted(unknown))}")


def world_point(plane: Plane, local: Vec2, rotate: float = 0, offset: float = 0) -> Vec3:
    angle = math.radians(rotate)
    x, y = local
    rx = x * math.cos(angle) - y * math.sin(angle)
    ry = x * math.sin(angle) + y * math.cos(angle)
    return add(add(add(plane.origin, scale(plane.u, rx)), scale(plane.v, ry)), scale(plane.normal, offset))


def entity_points(entity: Entity, plane: Plane, segments: int = 64) -> list[Vec3]:
    values = entity.values
    if entity.kind == "LINE":
        return [
            world_point(plane, values["from"], entity.rotate, entity.offset),  # type: ignore[arg-type]
            world_point(plane, values["to"], entity.rotate, entity.offset),  # type: ignore[arg-type]
        ]
    cx, cy = values["center"]  # type: ignore[misc]
    radius = float(values["radius"])
    if entity.kind == "CIRCLE":
        start, end = 0.0, 360.0
    else:
        start, end = float(values["start"]), float(values["end"])
        while end < start:
            end += 360.0
    count = max(2, int(segments * (end - start) / 360.0))
    return [
        world_point(
            plane,
            (cx + radius * math.cos(math.radians(start + (end - start) * i / count)),
             cy + radius * math.sin(math.radians(start + (end - start) * i / count))),
            entity.rotate,
            entity.offset,
        )
        for i in range(count + 1)
    ]


def _ocs_axes(normal: Vec3) -> tuple[Vec3, Vec3]:
    # DXF's arbitrary-axis algorithm for a stable OCS basis.
    if abs(normal[0]) < 1 / 64 and abs(normal[1]) < 1 / 64:
        x_axis = normalize(cross((0.0, 1.0, 0.0), normal))
    else:
        x_axis = normalize(cross((0.0, 0.0, 1.0), normal))
    y_axis = cross(normal, x_axis)
    return x_axis, y_axis


def dxf_r12(source: str) -> tuple[str | None, list[str]]:
    entities, planes, _units, layers, errors = parse_program(source)
    if errors:
        return None, errors
    layer_names = sorted({_dxf_layer(layer.name) for layer in layers.values()})
    rows = [
        "0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1009", "0", "ENDSEC",
        "0", "SECTION", "2", "TABLES", "0", "TABLE", "2", "LAYER", "70", str(len(layer_names)),
    ]
    layer_colors = {_dxf_layer(layer.name): layer.color for layer in layers.values()}
    for layer in layer_names:
        rows.extend(["0", "LAYER", "2", layer, "70", "0", "62", str(layer_colors[layer]), "6", "CONTINUOUS"])
    rows.extend(["0", "ENDTAB", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"])
    for entity in entities:
        plane = planes[entity.plane]
        rows.extend(["0", entity.kind, "8", _dxf_layer(entity.layer)])
        if entity.color is not None:
            rows.extend(["62", str(entity.color)])
        if entity.kind == "LINE":
            first, second = entity_points(entity, plane)
            rows.extend(_dxf_point(10, first) + _dxf_point(11, second))
        else:
            center_local = entity.values["center"]  # type: ignore[assignment]
            center = world_point(plane, center_local, entity.rotate, entity.offset)  # type: ignore[arg-type]
            x_axis, y_axis = _ocs_axes(plane.normal)
            center_ocs = (dot(center, x_axis), dot(center, y_axis), dot(center, plane.normal))
            rows.extend(_dxf_point(10, center_ocs))
            rows.extend(["40", _num(float(entity.values["radius"]))])
            if entity.kind == "ARC":
                start = math.radians(float(entity.values["start"]) + entity.rotate)
                end = math.radians(float(entity.values["end"]) + entity.rotate)
                su = add(scale(plane.u, math.cos(start)), scale(plane.v, math.sin(start)))
                eu = add(scale(plane.u, math.cos(end)), scale(plane.v, math.sin(end)))
                a0 = math.degrees(math.atan2(dot(su, y_axis), dot(su, x_axis))) % 360
                a1 = math.degrees(math.atan2(dot(eu, y_axis), dot(eu, x_axis))) % 360
                rows.extend(["50", _num(a0), "51", _num(a1)])
            rows.extend(["210", _num(plane.normal[0]), "220", _num(plane.normal[1]), "230", _num(plane.normal[2])])
    rows.extend(["0", "ENDSEC", "0", "EOF"])
    return "\n".join(rows) + "\n", []


def _dxf_point(code: int, point: Vec3) -> list[str]:
    return [str(code), _num(point[0]), str(code + 10), _num(point[1]), str(code + 20), _num(point[2])]


def _num(value: float) -> str:
    if abs(value) < 1e-10:
        value = 0.0
    return f"{value:.6f}".rstrip("0").rstrip(".") or "0"


def _dxf_layer(layer: str) -> str:
    return layer[:31].replace(" ", "_") or "0"
