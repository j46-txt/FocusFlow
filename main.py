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
def main_page(key: str = None):
    """Binds application context channels with a secret key gatekeeper."""
    allowed_key = os.environ.get('ACCESS_KEY', '')
    
    if allowed_key and key != allowed_key:
        with ui.column().classes('w-full h-screen bg-black items-center justify-center'):
            ui.label('404 Not Found').classes('text-neutral-700 text-sm tracking-widest font-mono')
        return

    user_interface.build_ui()

if __name__ in {"__main__", "__mp_main__"}:
    port = int(os.environ.get("PORT", 8080))
    ui.run(title="FocusFlow", host="0.0.0.0", port=port, dark=True, show=False, favicon="🌊")
