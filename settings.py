# settings.py
# -*- coding: utf-8 -*-
import database
import sqlite3
import threading

# Thread-safe global memory cache to prevent synchronous database read contention on the hot path (ASGI ticker loop)
_SETTINGS_CACHE = {}
_CACHE_LOCK = threading.Lock()
_CACHE_INITIALIZED = False

def _ensure_cache_populated():
    """Guarantees the rapid configuration memory map is hydrated using a double-checked lock pattern."""
    global _CACHE_INITIALIZED
    if _CACHE_INITIALIZED:
        return
    with _CACHE_LOCK:
        if _CACHE_INITIALIZED:
            return
        try:
            with database.get_db() as db:
                rows = db.execute('SELECT key, value FROM settings').fetchall()
                for row in rows:
                    _SETTINGS_CACHE[row['key']] = row['value']
            _CACHE_INITIALIZED = True
        except sqlite3.Error:
            # Safe defensive fallback: if migrations haven't run yet, defer initialization
            pass

def get_setting(key: str, default: str) -> str:
    """Retrieves configuration data strings directly from fast memory, bypassing disk read loops."""
    _ensure_cache_populated()
    with _CACHE_LOCK:
        if key in _SETTINGS_CACHE:
            return _SETTINGS_CACHE[key]
        # Optimization: If the cache has been successfully fully populated from disk, 
        # a missing key means it does not exist in the database. Defer redundant disk IO.
        if _CACHE_INITIALIZED:
            return str(default)
            
    try:
        with database.get_db() as db:
            row = db.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
            if row:
                with _CACHE_LOCK:
                    _SETTINGS_CACHE[key] = row['value']
                return row['value']
            return str(default)
    except sqlite3.Error:
        return str(default)

def set_setting(key: str, value: str) -> None:
    """Saves configuration to disk and instantly propagates changes to the local memory cache."""
    _ensure_cache_populated()
    val_str = str(value)
    with _CACHE_LOCK:
        _SETTINGS_CACHE[key] = val_str
        
    try:
        with database.get_db() as db:
            db.execute('REPLACE INTO settings (key, value) VALUES (?, ?)', (key, val_str))
    except sqlite3.Error:
        # Prevents early initialization write anomalies if state changes occur before table migration hooks
        pass

def get_weekly_goal_hours() -> int:
    """Gets the weekly goal. Defaults strictly to 10 hours."""
    return int(get_setting('weekly_goal_hours', '10'))

def get_pomodoro_minutes() -> int:
    """Gets the length of a single Pomodoro countdown session."""
    return int(get_setting('pomodoro_minutes', '25'))

def get_break_minutes() -> int:
    """Gets the short interval resting state period."""
    return int(get_setting('break_minutes', '5'))

def get_auto_rotate() -> bool:
    """Validates if daily routine rotation rules are active."""
    return get_setting('auto_rotate', '1') == '1'

def set_auto_rotate(enabled: bool) -> None:
    set_setting('auto_rotate', '1' if enabled else '0')

def get_last_rotation_date() -> str:
    """Gets the raw date stamp when the daily selection was updated."""
    return get_setting('last_rotation_date', '')

def set_last_rotation_date(date_str: str) -> None:
    set_setting('last_rotation_date', date_str)
