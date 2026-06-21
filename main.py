# main.py
# -*- coding: utf-8 -*-
import os
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
    # Render provides the port dynamically via the PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    ui.run(title="FocusFlow", host="0.0.0.0", port=port, dark=True, show=False)# main.py
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
    port = int(os.environ.get("PORT", 8080))
    ui.run(title="FocusFlow", host="0.0.0.0", port=port, dark=True, show=False, favicon="🌊​")
