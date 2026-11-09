"""Responsive IDE surface and editor actions for Draftline CAD."""

from __future__ import annotations

import logging

import flet as ft

from data import SAMPLE_PROGRAM
from dsl import dxf_r12, parse_program
from views.previews import layer_legend, make_preview

log = logging.getLogger(f"app.{__name__}")


class EditorScreen:
    def __init__(self, page: ft.Page, preferences: ft.SharedPreferences, picker: ft.FilePicker, theme_mode: str):
        self.page = page
        self.preferences = preferences
        self.picker = picker
        self.theme_mode = theme_mode
        self.mobile_panel = "code"
        self.orthographic_view = "XY"
        self.collapsed = {"iso": False, "2d": False}
        self.entities, self.planes, self.units, self.layers, self.errors = parse_program(SAMPLE_PROGRAM)
        self.editor = ft.TextField(
            value=SAMPLE_PROGRAM,
            multiline=True,
            expand=True,
            text_style=ft.TextStyle(font_family="monospace", size=13),
            content_padding=12,
            on_change=self._code_changed,
            autofocus=False,
        )
        self.status = ft.Text(size=12)
        self.summary = ft.Text(size=12, color=ft.Colors.OUTLINE)
        self.iso_canvas = make_preview(self.entities, self.planes, self.layers, "ISOMETRIC", 360, 390)
        self.two_canvas = make_preview(self.entities, self.planes, self.layers, self.orthographic_view, 360, 390)
        self.body_slot = ft.Container(expand=True)
        self.mobile_mode = self._is_mobile()
        self.page.on_resize = self._on_resize
        self.page.add(self._build_root())
        self._set_body()
        self.page.update()
        self._update_status()

    def _build_root(self) -> ft.Control:
        title_row = ft.Row(
            controls=[
                ft.Icon(ft.Icons.VIEW_IN_AR, color=ft.Colors.PRIMARY, size=24),
                ft.Column(
                    tight=True,
                    spacing=0,
                    controls=[
                        ft.Text("Draftline CAD", size=20, weight=ft.FontWeight.BOLD),
                        ft.Text("R12 VECTOR WORKSPACE", size=10, color=ft.Colors.OUTLINE),
                    ],
                ),
                ft.Container(expand=True),
                ft.IconButton(ft.Icons.TUNE, tooltip="Preferences", on_click=self._show_preferences),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        actions = ft.Row(
            wrap=True,
            spacing=8,
            controls=[
                ft.Button(content="Save code", icon=ft.Icons.SAVE, on_click=self.save_code),
                ft.OutlinedButton(content="Load code", icon=ft.Icons.FOLDER_OPEN, on_click=self.load_code),
                ft.OutlinedButton(content="Write DXF", icon=ft.Icons.FILE_DOWNLOAD, on_click=self.export_dxf),
                self.status,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        return ft.Column(
            expand=True,
            spacing=10,
            controls=[title_row, actions, self.body_slot],
        )

    def _is_mobile(self) -> bool:
        return (self.page.width or 900) < 820

    def _on_resize(self, _event):
        mobile_mode = self._is_mobile()
        if mobile_mode != self.mobile_mode:
            self.mobile_mode = mobile_mode
            self._set_body()
        self._refresh_previews()
        self.page.update()

    def _set_body(self):
        if self._is_mobile():
            tabs = ft.Row(
                spacing=6,
                controls=[
                    ft.Button(content="Code", icon=ft.Icons.CODE, on_click=lambda: self._select_mobile("code")),
                    ft.OutlinedButton(content="3D", icon=ft.Icons.VIEW_IN_AR, on_click=lambda: self._select_mobile("iso")),
                    ft.OutlinedButton(content="2D", icon=ft.Icons.WYSIWYG, on_click=lambda: self._select_mobile("2d")),
                ],
            )
            content = {
                "code": self._code_panel(),
                "iso": self._preview_panel("iso", mobile=True),
                "2d": self._preview_panel("2d", mobile=True),
            }[self.mobile_panel]
            self.body_slot.content = ft.Column(expand=True, spacing=8, controls=[tabs, content])
        else:
            panels = [self._code_panel()]
            for key in ("iso", "2d"):
                panels.append(self._collapsed_strip(key) if self.collapsed[key] else self._preview_panel(key))
            row_controls = []
            for panel, key in zip(panels, ("code", "iso", "2d")):
                if key == "code":
                    panel.expand = 2
                elif self.collapsed[key]:
                    panel.width = 42
                else:
                    panel.expand = 3
                row_controls.append(panel)
            self.body_slot.content = ft.Row(
                expand=True,
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=row_controls,
            )

    def _select_mobile(self, panel: str):
        self.mobile_panel = panel
        self._set_body()
        self.page.update()

    def _code_panel(self) -> ft.Container:
        header = ft.Row(
            controls=[
                ft.Icon(ft.Icons.CODE, color=ft.Colors.PRIMARY, size=18),
                ft.Text("SOURCE", weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.Text(".dline", size=12, color=ft.Colors.OUTLINE),
            ]
        )
        return ft.Container(
            expand=True,
            padding=10,
            border=ft.Border.all(1, ft.Colors.OUTLINE),
            border_radius=10,
            content=ft.Column(expand=True, spacing=8, controls=[header, self.editor, self.summary]),
        )

    def _preview_panel(self, key: str, mobile: bool = False) -> ft.Container:
        is_iso = key == "iso"
        title = "ISOMETRIC" if is_iso else "ORTHOGRAPHIC"
        canvas = self.iso_canvas if is_iso else self.two_canvas
        if mobile:
            header = ft.Row(
                controls=[
                    ft.Text(title, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    self._orthographic_picker() if not is_iso else ft.Text("X · Y · Z", size=11, color=ft.Colors.OUTLINE),
                ],
            )
        else:
            header = ft.Row(
                controls=[
                    ft.TextButton(content=title, on_click=lambda: self._toggle_collapse(key)),
                    ft.Container(expand=True),
                    self._orthographic_picker() if not is_iso else ft.Text("X · Y · Z", size=11, color=ft.Colors.OUTLINE),
                ],
            )
        return ft.Container(
            expand=True,
            padding=10,
            border=ft.Border.all(1, ft.Colors.OUTLINE),
            border_radius=10,
            content=ft.Column(
                expand=True,
                spacing=8,
                controls=[
                    header,
                    ft.Container(expand=True, alignment=ft.Alignment.CENTER, content=canvas),
                    layer_legend(self.layers),
                ],
            ),
        )

    def _orthographic_picker(self) -> ft.Dropdown:
        return ft.Dropdown(
            value=self.orthographic_view,
            options=[
                ft.DropdownOption(key="XY", text="Top · XY"),
                ft.DropdownOption(key="FRONT", text="Front · XZ"),
                ft.DropdownOption(key="SIDE", text="Side · YZ"),
                ft.DropdownOption(key="BACK", text="Back · XZ"),
            ],
            on_select=self._orthographic_changed,
            dense=True,
            width=148,
        )

    def _collapsed_strip(self, key: str) -> ft.Container:
        label = "I\nS\nO" if key == "iso" else "2\nD"
        return ft.Container(
            width=42,
            alignment=ft.Alignment.CENTER,
            border=ft.Border.all(1, ft.Colors.OUTLINE),
            border_radius=10,
            ink=True,
            tooltip=f"Restore {'isometric' if key == 'iso' else '2D'} preview",
            on_click=lambda: self._toggle_collapse(key),
            content=ft.Text(label, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD),
        )

    def _toggle_collapse(self, key: str):
        self.collapsed[key] = not self.collapsed[key]
        self._set_body()
        self._refresh_previews()
        self.page.update()

    def _orthographic_changed(self, event):
        self.orthographic_view = event.control.value
        self._refresh_previews()
        self.page.update()

    def _code_changed(self, _event):
        self.entities, self.planes, self.units, self.layers, self.errors = parse_program(self.editor.value or "")
        self._update_status()
        self._refresh_previews()

    def _update_status(self):
        if self.errors:
            self.status.value = f"{len(self.errors)} issue{'s' if len(self.errors) != 1 else ''}"
            self.status.color = ft.Colors.ERROR
        else:
            self.status.value = "Ready"
            self.status.color = ft.Colors.PRIMARY
        self.summary.value = f"{len(self.entities)} entities  ·  {len(self.planes)} planes  ·  {len(self.layers)} layers  ·  {self.units}"
        if self.status.page is not None:
            self.status.update()
            self.summary.update()

    def _refresh_previews(self):
        width = max(220, int((self.page.width or 900) / (1 if self._is_mobile() else 3) - 44))
        height = max(180, int((self.page.height or 760) - (245 if self._is_mobile() else 205)))
        if not self._is_mobile():
            height = max(220, height)
        iso = make_preview(self.entities, self.planes, self.layers, "ISOMETRIC", width, height)
        two = make_preview(self.entities, self.planes, self.layers, self.orthographic_view, width, height)
        self.iso_canvas.width, self.iso_canvas.height, self.iso_canvas.shapes = iso.width, iso.height, iso.shapes
        self.two_canvas.width, self.two_canvas.height, self.two_canvas.shapes = two.width, two.height, two.shapes
        if self.iso_canvas.page is not None:
            self.iso_canvas.update()
        if self.two_canvas.page is not None:
            self.two_canvas.update()

    async def save_code(self):
        content = (self.editor.value or "").encode("utf-8")
        path = await self.picker.save_file(
            dialog_title="Save Draftline source",
            file_name="draftline-project.dline",
            src_bytes=content,
        )
        if path:
            self.status.value = "Source saved"
            self.status.color = ft.Colors.PRIMARY
            self.status.update()

    async def load_code(self):
        files = await self.picker.pick_files(
            dialog_title="Open Draftline source",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["dline", "txt"],
            allow_multiple=False,
            with_data=True,
        )
        if files:
            try:
                self.editor.value = (files[0].bytes or b"").decode("utf-8")
                self.entities, self.planes, self.units, self.layers, self.errors = parse_program(self.editor.value)
                self._update_status()
                self._refresh_previews()
                self.editor.update()
            except UnicodeDecodeError:
                self.status.value = "Could not read that file as UTF-8"
                self.status.color = ft.Colors.ERROR
                self.status.update()

    async def export_dxf(self):
        output, errors = dxf_r12(self.editor.value or "")
        if errors or output is None:
            self.status.value = errors[0] if errors else "DXF export failed"
            self.status.color = ft.Colors.ERROR
            self.status.update()
            return
        path = await self.picker.save_file(
            dialog_title="Export DXF R12",
            file_name="draftline-project.dxf",
            src_bytes=output.encode("ascii", errors="replace"),
        )
        if path:
            self.status.value = "DXF R12 exported"
            self.status.color = ft.Colors.PRIMARY
            self.status.update()

    def _show_preferences(self):
        selector = ft.Dropdown(
            value=self.theme_mode,
            label="Appearance",
            options=[
                ft.DropdownOption(key="system", text="Use device setting"),
                ft.DropdownOption(key="light", text="Light"),
                ft.DropdownOption(key="dark", text="Dark"),
            ],
            on_select=self._theme_changed,
        )
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Preferences"),
            content=ft.Column(
                tight=True,
                spacing=10,
                controls=[ft.Text("Choose a theme or follow your device appearance."), selector],
            ),
            actions=[ft.TextButton(content="Done", on_click=self.page.pop_dialog)],
        )
        self.page.show_dialog(dialog)

    async def _theme_changed(self, event):
        self.theme_mode = event.control.value
        modes = {
            "system": ft.ThemeMode.SYSTEM,
            "light": ft.ThemeMode.LIGHT,
            "dark": ft.ThemeMode.DARK,
        }
        self.page.theme_mode = modes[self.theme_mode]
        await self.preferences.set("appearance", self.theme_mode)
        self.page.update()
        log.info("appearance preference set to %s", self.theme_mode)
