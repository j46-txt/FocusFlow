# settings.py
# -*- coding: utf-8 -*-
import database

def get_setting(key: str, default: str) -> str:
    """Retrieves configuration data strings from the database table."""
    with database.get_db() as db:
        row = db.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
        return row['value'] if row else str(default)

def set_setting(key: str, value: str) -> None:
    """Saves or replaces a distinct configuration key state."""
    with database.get_db() as db:
        db.execute('REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))

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