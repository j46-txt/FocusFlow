# main.py
# -*- coding: utf-8 -*-
from nicegui import app, ui
import database
import subjects
import ui as user_interface

def startup():
    """Initializes basic transaction tables and clears out generic defaults."""
    database.init_db()
    subjects.seed_default_subjects()

app.on_startup(startup)

@ui.page('/')
def main_page():
    """Binds application context channels to the overhauled user interface module."""
    user_interface.build_ui()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="FocusFlow", port=8080, dark=True, show=False)