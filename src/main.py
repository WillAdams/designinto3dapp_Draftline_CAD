import logging

import flet as ft

from views.editor import EditorScreen

LOG_LEVEL = logging.INFO
logging.basicConfig(format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("app").setLevel(LOG_LEVEL)


async def main(page: ft.Page):
    page.title = "Draftline CAD"
    page.padding = 12
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.CYAN)
    page.dark_theme = ft.Theme(color_scheme_seed=ft.Colors.CYAN)

    preferences = ft.SharedPreferences()
    picker = ft.FilePicker()
    saved_mode = await preferences.get("appearance")
    theme_mode = saved_mode if saved_mode in {"system", "light", "dark"} else "system"
    page.theme_mode = {
        "system": ft.ThemeMode.SYSTEM,
        "light": ft.ThemeMode.LIGHT,
        "dark": ft.ThemeMode.DARK,
    }[theme_mode]

    EditorScreen(page, preferences, picker, theme_mode)


ft.run(main)
