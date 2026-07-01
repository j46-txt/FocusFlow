# main.py
# -*- coding: utf-8 -*-
import os
import asyncio
from nicegui import app, ui
import database
import subjects
import ui as user_interface

# Monolithic single-entry startup pipeline to orchestrate dependency loading sequentially
@app.on_startup
async def initialize_application_state():
    loop = asyncio.get_running_loop()
    
    print("[Lifecycle] Stage 1: Initializing local/cloud database storage...")
    await loop.run_in_executor(None, database.init_db)
    
    print("[Lifecycle] Stage 2: Seeding relational tables...")
    await loop.run_in_executor(None, subjects.seed_default_subjects)
    
    print("[Lifecycle] Stage 3: Hydrating user interface state caches...")
    await loop.run_in_executor(None, user_interface.load_initial_stats)
    print("[Lifecycle] System startup sequence completed successfully.")

@ui.page('/')
async def main_page(key: str = None):
    """Binds application context channels with a secret key gatekeeper."""
    allowed_key = os.environ.get('ACCESS_KEY', '')
    
    if allowed_key and key != allowed_key:
        with ui.column().classes('w-full h-screen bg-black items-center justify-center'):
            ui.label('404 Not Found').classes('text-neutral-700 text-sm tracking-widest font-mono')
        return

    await user_interface.build_ui()

if __name__ in {"__main__", "__mp_main__"}:
    port = int(os.environ.get("PORT", 8080))
    ui.run(title="CaFE", host="0.0.0.0", port=port, dark=True, show=False, favicon="☕")
