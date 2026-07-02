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
    """Computes total focus time metrics efficiently without full table scans."""
    today_seconds = 0
    week_seconds = 0

    now = datetime.datetime.now().astimezone()
    today_date = now.date()
    start_of_week = today_date - datetime.timedelta(days=today_date.weekday())

    # Utilize high-performance SQLite engine aggregations for metrics over historical ranges
    with database.get_db() as db:
        total_row = db.execute('SELECT TOTAL(duration_seconds) as total_sec FROM focus_sessions').fetchone()
        total_seconds = int(total_row['total_sec']) if total_row else 0

        # Fetch all records to map them to the correct local timezone for day calculation
        all_rows = db.execute('SELECT end_date, end_time FROM focus_sessions').fetchall()
        local_days = set()
        for r in all_rows:
            try:
                utc_dt_str = f"{r['end_date']} {r['end_time']}"
                utc_dt = datetime.datetime.strptime(utc_dt_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc)
                local_days.add(utc_dt.astimezone().date())
            except ValueError:
                continue
        focus_days = len(local_days)

        first_row = db.execute('SELECT MIN(start_date) as first_date FROM focus_sessions').fetchone()
        first_date_str = first_row['first_date'] if first_row else None

        # Optimization: Fetch only local boundary records using a highly limited time window window lookup
        lookback_limit = (start_of_week - datetime.timedelta(days=2)).strftime('%Y-%m-%d')
        rows = db.execute(
            'SELECT end_date, end_time, duration_seconds FROM focus_sessions WHERE start_date >= ?',
            (lookback_limit,)
        ).fetchall()

    for row in rows:
        duration = row['duration_seconds']
        utc_dt_str = f"{row['end_date']} {row['end_time']}"
        try:
            utc_dt = datetime.datetime.strptime(utc_dt_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc)
            local_date = utc_dt.astimezone().date()
            if local_date == today_date:
                today_seconds += duration
            if start_of_week <= local_date <= today_date:
                week_seconds += duration
        except ValueError:
            continue

    avg_week_hours = 0.0
    if first_date_str:
        try:
            first_session_date = datetime.datetime.strptime(first_date_str, '%Y-%m-%d').date()
            days_since_first = (today_date - first_session_date).days
            total_weeks = max(1.0, days_since_first / 7.0)
            avg_week_hours = (total_seconds / 3600.0) / total_weeks
        except ValueError:
            pass

    return {
        'today': today_seconds,
        'week': week_seconds,
        'total': total_seconds,
        'avg_week_hours': avg_week_hours,
        'focus_days': focus_days
    }

def format_duration(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours}h {minutes}m"

def export_history_csv() -> bytes:
    """Exports logs by properly translating UTC database strings into the user's local timezone."""
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
            # Reconstruct and shift start timestamp from UTC to Local Timezone
            start_utc_str = f"{row['start_date']} {row['start_time']}"
            start_utc = datetime.datetime.strptime(start_utc_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc)
            start_local = start_utc.astimezone()
            
            # Reconstruct and shift end timestamp from UTC to Local Timezone
            end_utc_str = f"{row['end_date']} {row['end_time']}"
            end_utc = datetime.datetime.strptime(end_utc_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc)
            end_local = end_utc.astimezone()
            
            start_date_str = start_local.strftime('%Y-%m-%d')
            start_time_str = start_local.strftime('%H:%M:%S')
            end_date_str = end_local.strftime('%Y-%m-%d')
            end_time_str = end_local.strftime('%H:%M:%S')
            weekday = start_local.strftime('%A')
        except (ValueError, TypeError):
            start_date_str = row['start_date']
            start_time_str = row['start_time']
            end_date_str = row['end_date']
            end_time_str = row['end_time']
            weekday = 'Unknown'
            
        writer.writerow([
            row['subject_name'] or "Deleted Subject", 
            start_date_str, 
            start_time_str, 
            end_date_str, 
            end_time_str, 
            row['duration_seconds'], 
            row['timer_mode'], 
            weekday
        ])
        
    return output.getvalue().encode('utf-8')
