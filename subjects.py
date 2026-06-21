# subjects.py
# -*- coding: utf-8 -*-
import datetime
import random
from dataclasses import dataclass
from typing import Optional, List
import database
import settings

@dataclass
class Subject:
    id: int
    name: str
    is_active: bool
    list_order: int
    weight: int = 1

def seed_default_subjects() -> None:
    """Explicitly empty to prevent any deletion queries from wiping user data during runtime restarts."""
    pass

def get_all_subjects() -> List[Subject]:
    with database.get_db() as db:
        rows = db.execute('SELECT * FROM subjects ORDER BY list_order ASC').fetchall()
        return [Subject(**dict(row)) for row in rows]

def add_subject(name: str, weight: int = 1) -> None:
    if not name.strip():
        return
    with database.get_db() as db:
        max_order = db.execute('SELECT MAX(list_order) as max_ord FROM subjects').fetchone()['max_ord']
        new_order = 0 if max_order is None else max_order + 1
        db.execute(
            'INSERT INTO subjects (name, is_active, list_order, weight) VALUES (?, ?, ?, ?)',
            (name.strip(), 0, new_order, max(1, weight))
        )
        count = db.execute('SELECT COUNT(*) as count FROM subjects').fetchone()['count']
        if count == 1:
            db.execute('UPDATE subjects SET is_active = 1 WHERE name = ?', (name.strip(),))

def update_subject(subject_id: int, name: str, weight: int) -> None:
    if not name.strip():
        return
    with database.get_db() as db:
        db.execute('UPDATE subjects SET name = ?, weight = ? WHERE id = ?', (name.strip(), max(1, weight), subject_id))

def delete_subject(subject_id: int) -> None:
    with database.get_db() as db:
        current = db.execute('SELECT is_active FROM subjects WHERE id = ?', (subject_id,)).fetchone()
        db.execute('DELETE FROM subjects WHERE id = ?', (subject_id,))
        if current and current['is_active']:
            fallback = db.execute('SELECT id FROM subjects ORDER BY list_order ASC LIMIT 1').fetchone()
            if fallback:
                db.execute('UPDATE subjects SET is_active = 1 WHERE id = ?', (fallback['id'],))

def set_active_subject(subject_id: int) -> None:
    with database.get_db() as db:
        db.execute('UPDATE subjects SET is_active = 0')
        db.execute('UPDATE subjects SET is_active = 1 WHERE id = ?', (subject_id,))

def get_active_subject() -> Optional[Subject]:
    with database.get_db() as db:
        row = db.execute('SELECT * FROM subjects WHERE is_active = 1 LIMIT 1').fetchone()
        if row:
            return Subject(**dict(row))
        row = db.execute('SELECT * FROM subjects ORDER BY list_order ASC LIMIT 1').fetchone()
        if row:
            db.execute('UPDATE subjects SET is_active = 1 WHERE id = ?', (row['id'],))
            return Subject(**dict(row))
    return None

def rotate_subject() -> None:
    """Performs a non-repeating weighted random shuffle selection."""
    with database.get_db() as db:
        all_subs = db.execute('SELECT * FROM subjects').fetchall()
        if not all_subs:
            return
        if len(all_subs) == 1:
            db.execute('UPDATE subjects SET is_active = 1 WHERE id = ?', (all_subs[0]['id'],))
            return
        current = db.execute('SELECT * FROM subjects WHERE is_active = 1 LIMIT 1').fetchone()
        candidates = [s for s in all_subs if not current or s['id'] != current['id']]
        weights = [s['weight'] for s in candidates]
        chosen = random.choices(candidates, weights=weights, k=1)[0]
        db.execute('UPDATE subjects SET is_active = 0')
        db.execute('UPDATE subjects SET is_active = 1 WHERE id = ?', (chosen['id'],))

def ensure_daily_rotation() -> None:
    """Rotates suggestion only when a new day arrives and the user opens the application."""
    if not settings.get_auto_rotate():
        return
    today_str = datetime.datetime.now().strftime('%Y-%m-%d')
    last_date = settings.get_last_rotation_date()
    if not last_date:
        settings.set_last_rotation_date(today_str)
        return
    if last_date < today_str:
        rotate_subject()
        settings.set_last_rotation_date(today_str)