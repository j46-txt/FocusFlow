# statistics.py
# -*- coding: utf-8 -*-
import datetime
import csv
import io
import database
from typing import Dict, Any

def record_session(subject_id: int, duration_seconds: int, timer_mode: str) -> None:
    """Accurately records the core study session logs in the local database."""
    if duration_seconds <= 0:
        return
    end_dt = datetime.datetime.now(datetime.timezone.utc)
    start_dt = end_dt - datetime.timedelta(seconds=duration_seconds)
    with database.get_db() as db:
        db.execute('''
            INSERT INTO focus_sessions (subject_id, start_date, start_time, end_date, end_time, duration_seconds, timer_mode)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            subject_id,
            start_dt.strftime('%Y-%m-%d'),
            start_dt.strftime('%H:%M:%S'),
            end_dt.strftime('%Y-%m-%d'),
            end_dt.strftime('%H:%M:%S'),
            duration_seconds,
            timer_mode
        ))

def get_stats() -> Dict[str, Any]:
    """Computes total focus time metrics directly from database executions."""
    today_seconds = 0
    week_seconds = 0
    total_seconds = 0
    first_session_date = None
    unique_focus_days = set()

    now = datetime.datetime.now().astimezone()
    today_date = now.date()
    start_of_week = today_date - datetime.timedelta(days=today_date.weekday())

    with database.get_db() as db:
        rows = db.execute('SELECT start_date, end_date, end_time, duration_seconds FROM focus_sessions').fetchall()

    for row in rows:
        duration = row['duration_seconds']
        total_seconds += duration
        
        # Tracks unique calendar days where a session was recorded
        if row['start_date']:
            unique_focus_days.add(row['start_date'])
            
        utc_dt_str = f"{row['end_date']} {row['end_time']}"
        try:
            utc_dt = datetime.datetime.strptime(utc_dt_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc)
            local_date = utc_dt.astimezone().date()
            if local_date == today_date:
                today_seconds += duration
            if start_of_week <= local_date <= today_date:
                week_seconds += duration
            if first_session_date is None or local_date < first_session_date:
                first_session_date = local_date
        except ValueError:
            continue

    avg_week_hours = 0.0
    if first_session_date:
        days_since_first = (today_date - first_session_date).days
        total_weeks = max(1.0, days_since_first / 7.0)
        avg_week_hours = (total_seconds / 3600.0) / total_weeks

    return {
        'today': today_seconds,
        'week': week_seconds,
        'total': total_seconds,
        'avg_week_hours': avg_week_hours,
        'focus_days': len(unique_focus_days)
    }

def format_duration(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours}h {minutes}m"

def export_history_csv() -> bytes:
    with database.get_db() as db:
        rows = db.execute('''
            SELECT fs.start_date, fs.start_time, fs.end_date, fs.end_time, 
                   fs.duration_seconds, fs.timer_mode, s.name as subject_name
            FROM focus_sessions fs
            LEFT JOIN subjects s ON fs.subject_id = s.id
            ORDER BY fs.id DESC
        ''').fetchall()
        
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Subject', 'Start Date', 'Start Time', 'End Date', 'End Time', 'Duration (Seconds)', 'Timer Mode', 'Weekday'])
    
    for row in rows:
        try:
            dt = datetime.datetime.strptime(row['start_date'], '%Y-%m-%d')
            weekday = dt.strftime('%A')
        except ValueError:
            weekday = 'Unknown'
        writer.writerow([row['subject_name'] or "Deleted Subject", row['start_date'], row['start_time'], row['end_date'], row['end_time'], row['duration_seconds'], row['timer_mode'], weekday])
        
    return output.getvalue().encode('utf-8')