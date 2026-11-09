# Draftline DSL — Literate Program Guide

Draftline is a small, line-oriented language for drawing 2D primitives on named 3D planes. The same source drives the live orthographic and isometric previews and can be exported as an ASCII DXF R12 file.

This guide describes the commands currently accepted by the parser, their parameters, coordinate semantics, colour rules, and export behavior.

## A first drawing

A program is a sequence of commands. Blank lines and text after `#` are ignored. Commands and parameter names are case-insensitive; plane and layer names are also matched case-insensitively. Each parameter is written as one whitespace-delimited `key=value` token. Vectors are comma-separated numbers without spaces.

```text
UNITS mm
LAYER name=frame color=7
PLANE FRONT origin=0,0,0 u=1,0,0 v=0,0,1
LINE name=bottom-rail from=0,0 to=100,0 plane=FRONT layer=frame
CIRCLE name=badge center=50,40 radius=8 plane=FRONT layer=frame
ARC name=badge-sweep center=50,40 radius=12 start=210 end=330 plane=FRONT layer=frame color=yellow
```

The commands are evaluated in source order. A plane must exist before a drawing command refers to it. A layer may be declared with `LAYER`; if an entity uses an undeclared layer, that layer is created automatically with the default colour.

## Command reference

### `UNITS`

Sets the unit label shown in the editor summary.

```text
UNITS <label>
```

- Exactly one label is required, such as `mm`, `cm`, `in`, or `unitless`.
- This is descriptive only: it does not scale coordinates or add a units field to the DXF R12 export.
- If omitted, the editor reports `unitless`.

### `LAYER`

Declares or updates a drawing layer and its default colour.

```text
LAYER name=<layer-name> [color=<ACI-number-or-name>]
```

Parameters:

- `name` — required. A single token; spaces are not supported. Names are matched case-insensitively and exported in uppercase.
- `color` — optional; defaults to ACI `7` (the conventional background-adaptive black/white). Accepts an AutoCAD Color Index number from `1` to `255` or one of the names listed under [Colours](#colours).

Declaring the same layer again replaces its colour. Layer `0` exists by default. Entities without a `layer` parameter use layer `0`.

### `PLANE`

Defines the local drawing coordinate system used by subsequent entities. `XY` is predefined as the world XY plane, so an explicit `PLANE XY ...` command may replace its definition.

```text
PLANE <plane-name> [origin=x,y,z] [u=x,y,z] [v=x,y,z]
```

Parameters:

- `<plane-name>` — required positional name, for example `TOP`, `FRONT`, or `RIGHT`.
- `origin` — optional world-space XYZ origin; defaults to `0,0,0`.
- `u` — optional world-space direction for local X; defaults to `1,0,0`.
- `v` — optional world-space direction for local Y; defaults to `0,1,0`.

The parser normalizes `u` and `v`; their magnitudes therefore do not scale the drawing. Their cross product defines the plane normal used by `offset`. Use non-zero, non-parallel, perpendicular axes for predictable circles, arcs, and DXF export. The parser rejects zero or parallel axes but does not orthogonalize skew axes.

For an entity point `(x, y)` with in-plane rotation `rotate` and normal displacement `offset`, Draftline first rotates the local coordinates around the plane origin, then maps them through `u` and `v`, and finally moves along the plane normal:

```text
x' = x*cos(rotate) - y*sin(rotate)
y' = x*sin(rotate) + y*cos(rotate)
point = origin + u*x' + v*y' + normal*offset
normal = normalize(u × v)
```

Angles for `rotate` are in degrees. Positive angles follow the local plane's `u`-to-`v` orientation. A plane whose origin has a non-zero world Z places its drawing at that elevation. `offset` is along the plane normal—not always world Z. For an XY plane, normal offset is a Z displacement; for a front plane it is typically depth.

### Shared entity parameters

`LINE`, `CIRCLE`, and `ARC` accept these common optional parameters:

- `name=<token>` — source-side entity label. Defaults to a generated name. It is not written into DXF R12, which has no standard per-entity name field used by this exporter.
- `plane=<plane-name>` — plane on which local coordinates are interpreted; defaults to `XY`. The plane must already be defined.
- `rotate=<degrees>` — rotates local coordinates about the plane origin; defaults to `0`.
- `offset=<number>` — displaces the entity along the plane normal; defaults to `0`.
- `layer=<layer-name>` — drawing layer; defaults to `0`. An undeclared layer is created with ACI `7`.
- `color=<ACI-number-or-name>` — optional per-entity colour override. If omitted, the entity inherits its layer colour. `color=BYLAYER` explicitly requests inheritance.

Unknown parameters and repeated keys are reported as line-specific parser errors. Numeric values must be valid numbers; coordinates and radii use the program's chosen unit label.

### `LINE`

Draws one straight segment between two local 2D points.

```text
LINE from=x1,y1 to=x2,y2 [name=...] [plane=...] [rotate=...] [offset=...] [layer=...] [color=...]
```

Required parameters:

- `from=x1,y1` — local start point.
- `to=x2,y2` — local end point.

The resulting world-space points may differ in X, Y, and Z depending on the plane and its offset. DXF output uses a native `LINE` entity.

### `CIRCLE`

Draws a circle in the selected plane.

```text
CIRCLE center=x,y radius=r [name=...] [plane=...] [rotate=...] [offset=...] [layer=...] [color=...]
```

Required parameters:

- `center=x,y` — local center point.
- `radius=r` — positive radius; zero and negative radii are rejected.

The preview tessellates the circle for display, while DXF output writes a native `CIRCLE` entity with its plane normal.

### `ARC`

Draws a circular arc in the selected plane.

```text
ARC center=x,y radius=r start=degrees end=degrees [name=...] [plane=...] [rotate=...] [offset=...] [layer=...] [color=...]
```

Required parameters:

- `center=x,y` — local center point.
- `radius=r` — positive radius.
- `start=degrees` — local start angle, measured counter-clockwise from local +X.
- `end=degrees` — local end angle. If it is less than `start`, Draftline advances it by full turns until it is not less than `start`.

For interoperable DXF R12 arcs, keep the intended sweep at or below 360 degrees. Equal start and end angles do not mean a full circle; use `CIRCLE` for that. DXF output writes a native `ARC` with its plane normal.

## Colours

Layer and entity colours use AutoCAD Color Index (ACI), which is supported by DXF R12. Valid numeric indexes are `1` through `255`. The parser also accepts these case-insensitive names:

| Name | ACI | Name | ACI |
|---|---:|---|---:|
| `red` | 1 | `yellow` | 2 |
| `green` | 3 | `cyan` | 4 |
| `blue` | 5 | `magenta` | 6 |
| `white` | 7 | `black` | 7 |
| `gray`, `grey` | 8 | `lightgray` | 9 |
| `orange` | 30 | | |

ACI `7` is conventionally rendered black on a light background and white on a dark background. Other ACI indexes are preserved in DXF; preview swatches for less-common indexes are approximations. A per-entity `color` overrides its layer's colour in both preview and DXF export.

## Orthographic and isometric views

The 2D preview can show:

- **Top · XY** — world X and Y; default.
- **Front · XZ** — world X and elevation Z.
- **Side · YZ** — world Y and elevation Z.
- **Back · XZ** — world X reversed and elevation Z.

The isometric preview projects world X, Y, and Z together. Plane origins and offsets therefore appear at their corresponding 3D positions; for example, an XY entity with `offset=20` appears 20 units higher in the isometric view and in the front/back elevations.

## DXF R12 export notes

The exporter writes an ASCII DXF R12 (`AC1009`) with a layer table, layer ACI colours, and native `LINE`, `CIRCLE`, and `ARC` entities. Entity colours are written as ACI overrides when explicitly set; otherwise they inherit from the layer. Lines are written as world-space endpoints. Circles and arcs include DXF extrusion directions for their planes. The `UNITS` label and entity `name` are not embedded in the R12 file.

## Complete sample program

This is the sample preloaded in the editor. It demonstrates every command and every supported parameter, including layer colours, an entity colour override, distinct drawing planes, rotation, and normal displacement.

```text
# Dimensions are in millimetres
UNITS mm

LAYER name=frame color=7
LAYER name=divider color=cyan
LAYER name=detail color=green
LAYER name=accent color=magenta

PLANE XY origin=0,0,0 u=1,0,0 v=0,1,0
PLANE TOP origin=0,0,70 u=1,0,0 v=0,-1,0
PLANE FRONT origin=0,0,0 u=1,0,0 v=0,0,1
PLANE RIGHT origin=100,0,0 u=0,1,0 v=0,0,1
PLANE BACK origin=100,60,0 u=-1,0,0 v=0,0,1

LINE name=top-edge-a from=0,0 to=100,0 plane=TOP rotate=0 offset=0 layer=frame
LINE name=top-edge-b from=100,0 to=100,60 plane=TOP rotate=0 offset=0 layer=frame
LINE name=front-rail from=0,0 to=100,0 plane=FRONT rotate=0 offset=0 layer=frame
LINE name=front-upright from=0,0 to=0,70 plane=FRONT rotate=0 offset=0 layer=frame
LINE name=front-right-upright from=100,0 to=100,70 plane=FRONT rotate=0 offset=0 layer=frame
LINE name=right-rail from=0,0 to=60,0 plane=RIGHT rotate=0 offset=0 layer=frame
LINE name=top-mark from=38,30 to=62,30 plane=TOP rotate=10 offset=1 layer=detail
LINE name=offset-divider from=20,22 to=80,22 plane=FRONT rotate=0 offset=3 layer=divider

CIRCLE name=badge center=50,44 radius=9 plane=FRONT rotate=0 offset=1 layer=detail
CIRCLE name=raised-fastener center=18,18 radius=3 plane=XY rotate=0 offset=74 layer=detail

ARC name=badge-sweep center=50,44 radius=13 start=205 end=335 plane=FRONT rotate=8 offset=1 layer=accent color=yellow
ARC name=top-corner center=88,48 radius=8 start=0 end=90 plane=TOP rotate=0 offset=0 layer=detail
```
