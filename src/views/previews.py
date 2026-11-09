"""Canvas-based orthographic and isometric geometry previews."""

from __future__ import annotations

import colorsys

import flet as ft

from flet.controls.core.canvas.canvas import Canvas as FletCanvas
from flet.controls.core.canvas.line import Line as CanvasLine

from dsl import Entity, Layer, Plane, entity_points


def display_color(aci: int):
    """Map an AutoCAD Color Index value to a readable preview color."""
    base = {
        1: "#ff3030",
        2: "#ffd740",
        3: "#00c853",
        4: "#00e5ff",
        5: "#448aff",
        6: "#ff40c4",
        7: ft.Colors.ON_SURFACE,
        8: "#8a8a8a",
        9: "#bdbdbd",
        30: "#ff9100",
    }
    if aci in base:
        return base[aci]
    hue = ((aci - 10) * 137.508) % 360 / 360
    red, green, blue = colorsys.hsv_to_rgb(hue, 0.72, 0.96)
    return "#%02x%02x%02x" % (int(red * 255), int(green * 255), int(blue * 255))


def layer_legend(layers: dict[str, Layer]) -> ft.Row:
    return ft.Row(
        wrap=True,
        spacing=8,
        run_spacing=4,
        controls=[
            ft.Row(
                tight=True,
                spacing=4,
                controls=[
                    ft.Container(width=10, height=10, bgcolor=display_color(layer.color), border_radius=5),
                    ft.Text(layer.name, size=10),
                ],
            )
            for layer in layers.values()
        ],
    )


def _project(point: tuple[float, float, float], view: str) -> tuple[float, float]:
    x, y, z = point
    if view == "FRONT":
        return x, z
    if view == "SIDE":
        return y, z
    if view == "BACK":
        return -x, z
    if view == "ISOMETRIC":
        return (x - y) * 0.8660254, (x + y) * 0.5 - z
    return x, y


def make_preview(
    entities: list[Entity],
    planes: dict[str, Plane],
    layers: dict[str, Layer],
    view: str,
    width: float,
    height: float,
) -> FletCanvas:
    width = max(180, width)
    height = max(150, height)
    projected: list[list[tuple[float, float]]] = [
        [_project(point, view) for point in entity_points(entity, planes[entity.plane])]
        for entity in entities
    ]
    all_points = [point for shape in projected for point in shape]
    if all_points:
        min_x = min(p[0] for p in all_points)
        max_x = max(p[0] for p in all_points)
        min_y = min(p[1] for p in all_points)
        max_y = max(p[1] for p in all_points)
    else:
        min_x, max_x, min_y, max_y = -50, 50, -35, 35
    span_x = max(max_x - min_x, 1)
    span_y = max(max_y - min_y, 1)
    margin = 26
    scale = min((width - margin * 2) / span_x, (height - margin * 2) / span_y)
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2

    def screen(point: tuple[float, float]) -> tuple[float, float]:
        return (
            width / 2 + (point[0] - center_x) * scale,
            height / 2 - (point[1] - center_y) * scale,
        )

    shapes: list = []
    grid_paint = ft.Paint(color=ft.Colors.OUTLINE, stroke_width=0.7)
    for index in range(1, 8):
        x = margin + (width - 2 * margin) * index / 8
        y = margin + (height - 2 * margin) * index / 8
        shapes.append(CanvasLine(x1=x, y1=margin, x2=x, y2=height - margin, paint=grid_paint))
        shapes.append(CanvasLine(x1=margin, y1=y, x2=width - margin, y2=y, paint=grid_paint))

    for entity, points in zip(entities, projected):
        if len(points) < 2:
            continue
        color = display_color(entity.color or layers.get(entity.layer, Layer(entity.layer, 7)).color)
        paint = ft.Paint(color=color, stroke_width=2.2, style=ft.PaintingStyle.STROKE)
        screen_points = [screen(point) for point in points]
        for first, second in zip(screen_points, screen_points[1:]):
            shapes.append(
                CanvasLine(x1=first[0], y1=first[1], x2=second[0], y2=second[1], paint=paint)
            )

    return FletCanvas(width=width, height=height, shapes=shapes)
