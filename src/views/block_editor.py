"""Native Flet block editor for the Draftline DSL."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft


BLOCK_FIELDS: dict[str, list[tuple[str, str, str]]] = {
    "UNITS": [("unit", "Unit label", "mm")],
    "LAYER": [("name", "Layer name", "layer-1"), ("color", "ACI color or name", "7")],
    "PLANE": [
        ("name", "Plane name", "XY"),
        ("origin", "Origin x,y,z", "0,0,0"),
        ("u", "U axis x,y,z", "1,0,0"),
        ("v", "V axis x,y,z", "0,1,0"),
    ],
    "LINE": [
        ("name", "Name", "line-1"),
        ("from", "From x,y", "0,0"),
        ("to", "To x,y", "10,0"),
        ("plane", "Plane", "XY"),
        ("rotate", "Rotate degrees", "0"),
        ("offset", "Normal offset", "0"),
        ("layer", "Layer", "0"),
        ("color", "Color / bylayer", "bylayer"),
    ],
    "CIRCLE": [
        ("name", "Name", "circle-1"),
        ("center", "Center x,y", "0,0"),
        ("radius", "Radius", "5"),
        ("plane", "Plane", "XY"),
        ("rotate", "Rotate degrees", "0"),
        ("offset", "Normal offset", "0"),
        ("layer", "Layer", "0"),
        ("color", "Color / bylayer", "bylayer"),
    ],
    "ARC": [
        ("name", "Name", "arc-1"),
        ("center", "Center x,y", "0,0"),
        ("radius", "Radius", "5"),
        ("start", "Start degrees", "0"),
        ("end", "End degrees", "90"),
        ("plane", "Plane", "XY"),
        ("rotate", "Rotate degrees", "0"),
        ("offset", "Normal offset", "0"),
        ("layer", "Layer", "0"),
        ("color", "Color / bylayer", "bylayer"),
    ],
    "NOTE": [("text", "Comment", "Drawing note")],
}


class BlockEditor:
    """Editable, vertically stacked command blocks with DSL round-tripping."""

    def __init__(self, on_change: Callable[[str], None]):
        self.on_change = on_change
        self.blocks: list[dict[str, object]] = []
        self.kind_picker = ft.Dropdown(
            value="LINE",
            label="Block type",
            options=[ft.DropdownOption(key=kind, text=kind.title()) for kind in BLOCK_FIELDS],
            on_select=self._kind_changed,
            expand=True,
        )
        self.block_list = ft.ListView(expand=True, spacing=8)
        self.view = ft.Column(
            expand=True,
            spacing=8,
            controls=[
                ft.Row(
                    spacing=8,
                    controls=[
                        self.kind_picker,
                        ft.Button(content="Add block", icon=ft.Icons.ADD, on_click=self._add_block),
                    ],
                ),
                self.block_list,
            ],
        )
        self._render_blocks()

    def load_source(self, source: str):
        self.blocks = self._decode(source)
        self._render_blocks()

    def _kind_changed(self, event):
        self.kind_picker.value = event.control.value

    def _add_block(self):
        kind = self.kind_picker.value or "LINE"
        self.blocks.append(self._new_block(kind))
        self._render_blocks()
        self._emit_source()

    def _new_block(self, kind: str) -> dict[str, object]:
        return {
            "kind": kind,
            "fields": {key: initial for key, _label, initial in BLOCK_FIELDS[kind]},
        }

    def _remove_block(self, index: int):
        del self.blocks[index]
        self._render_blocks()
        self._emit_source()

    def _move_block(self, index: int, direction: int):
        destination = index + direction
        if not 0 <= destination < len(self.blocks):
            return
        self.blocks[index], self.blocks[destination] = self.blocks[destination], self.blocks[index]
        self._render_blocks()
        self._emit_source()

    def _field_changed(self, event, index: int, key: str):
        fields = self.blocks[index]["fields"]
        fields[key] = event.control.value
        self._emit_source()

    def _render_blocks(self):
        controls: list[ft.Control] = []
        if not self.blocks:
            controls.append(
                ft.Container(
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text("No blocks yet. Choose a command above to start a drawing.", color=ft.Colors.OUTLINE),
                )
            )
        for index, block in enumerate(self.blocks):
            controls.append(self._block_card(index, block))
        self.block_list.controls = controls
        if self.block_list.page is not None:
            self.block_list.update()

    def _block_card(self, index: int, block: dict[str, object]) -> ft.Container:
        kind = str(block["kind"])
        fields = block["fields"]
        header = ft.Row(
            controls=[
                ft.Text(kind, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.Icons.ARROW_UPWARD,
                    tooltip="Move block up",
                    disabled=index == 0,
                    on_click=lambda event, i=index: self._move_block(i, -1),
                ),
                ft.IconButton(
                    icon=ft.Icons.ARROW_DOWNWARD,
                    tooltip="Move block down",
                    disabled=index == len(self.blocks) - 1,
                    on_click=lambda event, i=index: self._move_block(i, 1),
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    tooltip="Delete block",
                    on_click=lambda event, i=index: self._remove_block(i),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        inputs = [
            ft.TextField(
                label=label,
                value=str(fields.get(key, initial)),
                col={"xs": 12, "sm": 6},
                on_change=lambda event, i=index, field_key=key: self._field_changed(event, i, field_key),
            )
            for key, label, initial in BLOCK_FIELDS[kind]
        ]
        return ft.Container(
            padding=10,
            border=ft.Border.all(1, ft.Colors.OUTLINE),
            border_radius=10,
            content=ft.Column(
                spacing=6,
                controls=[header, ft.ResponsiveRow(controls=inputs, spacing=8, run_spacing=4)],
            ),
        )

    def _emit_source(self):
        self.on_change(self.to_source())

    def to_source(self) -> str:
        lines: list[str] = []
        for block in self.blocks:
            kind = str(block["kind"])
            fields = block["fields"]
            value = lambda key: self._token(str(fields.get(key, "")))
            if kind == "NOTE":
                lines.append("# " + str(fields.get("text", "")).strip())
            elif kind == "UNITS":
                lines.append(f"UNITS {value('unit')}")
            elif kind == "LAYER":
                lines.append(f"LAYER name={value('name')} color={value('color')}")
            elif kind == "PLANE":
                lines.append(
                    f"PLANE {value('name')} origin={value('origin')} u={value('u')} v={value('v')}"
                )
            else:
                params = " ".join(f"{key}={value(key)}" for key, _label, _initial in BLOCK_FIELDS[kind])
                lines.append(f"{kind} {params}")
        return "\n".join(lines) + ("\n" if lines else "")

    @staticmethod
    def _token(value: str) -> str:
        value = value.strip()
        if "," in value:
            return "".join(value.split())
        return "_".join(value.split())

    @classmethod
    def _decode(cls, source: str) -> list[dict[str, object]]:
        blocks: list[dict[str, object]] = []
        for raw_line in source.splitlines():
            command_text, marker, comment = raw_line.partition("#")
            command_text = command_text.strip()
            if command_text:
                tokens = command_text.split()
                command = tokens[0].upper()
                if command not in BLOCK_FIELDS or command == "NOTE":
                    raise ValueError(f"Cannot represent DSL command in blocks: {command}")
                block = cls._new_static_block(command)
                fields = block["fields"]
                if command == "UNITS":
                    fields["unit"] = tokens[1] if len(tokens) > 1 else ""
                else:
                    param_tokens = tokens[2:] if command == "PLANE" else tokens[1:]
                    params = {}
                    for token in param_tokens:
                        if "=" in token:
                            key, value = token.split("=", 1)
                            params[key.lower()] = value
                    if command == "PLANE":
                        fields["name"] = tokens[1] if len(tokens) > 1 else ""
                    fields.update({key: value for key, value in params.items() if key in fields})
                blocks.append(block)
            if marker:
                note = cls._new_static_block("NOTE")
                note["fields"]["text"] = comment.strip()
                blocks.append(note)
        return blocks

    @staticmethod
    def _new_static_block(kind: str) -> dict[str, object]:
        return {"kind": kind, "fields": {key: initial for key, _label, initial in BLOCK_FIELDS[kind]}}
