# ui.py
# -*- coding: utf-8 -*-
from nicegui import ui
import datetime
from timer import FocusTimer
import subjects
import statistics
import settings
import database

def build_ui():
    """Builds the main user interface layout."""
    
    # Global styles override
    ui.add_head_html('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Courier+Prime:ital,wght=0,400;0,700;1,400;1,700&display=swap');
        
        * {
            font-family: 'Courier Prime', monospace !important;
            font-weight: normal !important;
        }
        
        .q-icon, .material-icons {
            font-family: 'Material Icons' !important;
        }
        
        body {
            background-color: #000000 !important;
            color: #b0b0b0 !important;
            font-size: 15px !important;
        }
        
        .mono-card {
            background-color: #000000 !important;
            border: 1px solid #141414 !important;
        }
        
        .mono-divider {
            border-bottom: 1px solid #141414 !important;
        }
        
        .mono-btn {
            background-color: #000000 !important;
            border: 1px solid #141414 !important;
            color: #d1d1d1 !important;
            text-transform: uppercase !important;
            border-radius: 2px !important;
            box-shadow: none !important;
            font-size: 13px !important;
            padding: 5px 14px !important;
            transition: all 0.1s ease-in-out;
        }
        .mono-btn:hover {
            background-color: #111111 !important;
            color: #ffffff !important;
            border-color: #333333 !important;
        }
        
        .inline-mono-btn {
            background-color: #000000 !important;
            border: 1px solid #38bdf8 !important;
            color: #38bdf8 !important;
            text-transform: uppercase !important;
            border-radius: 2px !important;
            box-shadow: none !important;
            font-size: 11px !important;
            padding: 0px 8px !important;
            height: 22px !important;
            line-height: 22px !important;
            transition: all 0.1s ease-in-out;
        }
        .inline-mono-btn:hover {
            background-color: #111111 !important;
            color: #ffffff !important;
            border-color: #ffffff !important;
        }
        
        .blue-link {
            color: #38bdf8 !important;
            transition: color 0.1s ease-in-out;
        }
        .blue-link:hover {
            color: #7dd3fc !important;
        }
        
        .large-toggle .q-btn {
            font-size: 13px !important;
            padding: 3px 10px !important;
            border-radius: 0px !important;
            border: 1px solid #141414 !important;
            background-color: #000000 !important;
            color: #555555 !important;
        }
        .large-toggle .q-btn--active {
            color: #ffffff !important;
            border-color: #333333 !important;
        }
        
        .q-field__native, .q-field__input {
            color: #b0b0b0 !important;
            font-size: 15px !important;
        }
        .q-field--outlined .q-field__control { border: 1px solid #141414 !important; border-radius: 0px !important; }
        .q-linear-progress { background: #111111 !important; color: #b0b0b0 !important; }
        
        @keyframes gradient-flow-right {
            0% { background-position: 200% 50%; }
            100% { background-position: 0% 50%; }
        }
        .q-linear-progress__model {
            background: linear-gradient(90deg, #111111, #38bdf8, #111111) !important;
            background-size: 200% 200% !important;
            animation: gradient-flow-right 3s linear infinite !important;
        }
    </style>
    ''')

    cached_stats = {'today': 0, 'week': 0, 'total': 0, 'avg_week_hours': 0.0, 'focus_days': 0}
    
    def refresh_cached_stats():
        nonlocal cached_stats
        cached_stats = statistics.get_stats()

    def get_greeting() -> str:
        hour = datetime.datetime.now().hour
        if 5 <= hour < 12:
            return "Good morning!"
        elif 12 <= hour < 18:
            return "Good afternoon!"
        else:
            return "Good evening!"

    # Configuration panel
    def open_settings_panel():
        with ui.dialog() as dialog, ui.card().classes('w-80 rounded-none p-4 mono-card'):
            ui.label('Configuration').classes('text-xs text-white uppercase tracking-wider mb-4 w-full')
            
            pomo_input = ui.number('Focus Period (min)', value=settings.get_pomodoro_minutes(), format='%.0f').classes('w-full mb-2')
            break_input = ui.number('Break Period (min)', value=settings.get_break_minutes(), format='%.0f').classes('w-full mb-2')
            goal_input = ui.number('Weekly Target (hours)', value=settings.get_weekly_goal_hours(), format='%.0f').classes('w-full mb-4')
            auto_rotate = ui.switch('Auto-rotate suggestion daily', value=settings.get_auto_rotate()).classes('w-full mb-4 text-xs')
            
            def confirm_reset():
                with ui.dialog() as confirm_dialog, ui.card().classes('w-72 rounded-none p-4 mono-card'):
                    ui.label('Are you sure?').classes('text-xs text-white uppercase tracking-wider mb-1')
                    ui.label('This will permanently delete all logged focus sessions.').classes('text-xs text-neutral-500 mb-4')
                    with ui.row().classes('w-full justify-end gap-2'):
                        ui.button('Cancel', on_click=confirm_dialog.close).classes('mono-btn text-xs')
                        def perform_reset():
                            with database.get_db() as db:
                                db.execute('DELETE FROM focus_sessions')
                            refresh_cached_stats()
                            update_display()
                            confirm_dialog.close()
                            dialog.close()
                            ui.notify('Statistics wiped out.', type='warning')
                        ui.button('Reset', on_click=perform_reset).classes('mono-btn text-xs border-red-900 text-red-500')
                confirm_dialog.open()
                
            ui.button('Reset statistics', on_click=confirm_reset).props('flat dense').classes('text-red-500/70 hover:text-red-400 text-xs self-start mb-3').style('text-transform: none; padding-left: 0;')

            def save_settings():
                settings.set_setting('pomodoro_minutes', int(pomo_input.value))
                settings.set_setting('break_minutes', int(break_input.value))
                settings.set_setting('weekly_goal_hours', int(goal_input.value))
                settings.set_auto_rotate(auto_rotate.value)
                focus_timer.sync_durations()
                update_display()
                dialog.close()

            ui.button('Save Changes', on_click=save_settings).classes('w-full mono-btn mb-1')
        dialog.open()

    # Suggestions input panel
    def open_suggestions_panel():
        with ui.dialog() as dialog, ui.card().classes('w-[360px] rounded-none p-4 mono-card'):
            ui.label('Edit Suggestions').classes('text-xs text-white uppercase tracking-wider mb-3')
            
            with ui.row().classes('w-full items-center gap-1 mb-3 pb-3 mono-divider'):
                new_name = ui.input(placeholder='Activity name').classes('w-36').props('dense dark')
                new_weight = ui.number(value=1, format='%.0f').classes('w-10').props('dense dark')
                def quick_add():
                    if new_name.value:
                        subjects.add_subject(new_name.value, int(new_weight.value) if new_weight.value else 1)
                        new_name.value = ''
                        rebuild_management_view()
                        reload_subjects()
                        update_display()
                ui.button('Add', on_click=quick_add).classes('mono-btn text-xs py-1')

            subject_list_container = ui.column().classes('w-full gap-1 mb-4 max-h-48 overflow-y-auto')
            
            def trigger_update(s_id, name_val, weight_val):
                subjects.update_subject(s_id, name_val, int(weight_val) if weight_val else 1)
                rebuild_management_view()
                reload_subjects()
                update_display()

            def trigger_delete(s_id):
                subjects.delete_subject(s_id)
                rebuild_management_view()
                reload_subjects()
                update_display()
            
            def rebuild_management_view():
                subject_list_container.clear()
                all_items = subjects.get_all_subjects()
                
                with subject_list_container:
                    if not all_items:
                        ui.label('[No items defined]').classes('text-xs text-neutral-600 italic')
                    
                    for sub in all_items:
                        with ui.row().classes('w-full items-center justify-between gap-1 p-1 bg-neutral-950 mono-divider'):
                            name_edit = ui.input(value=sub.name).classes('w-28').props('dense dark')
                            weight_edit = ui.number(value=sub.weight, format='%.0f').classes('w-10').props('dense dark')
                            
                            with ui.row().classes('gap-1'):
                                ui.button(icon='save', on_click=lambda e, sid=sub.id, n=name_edit, w=weight_edit: trigger_update(sid, n.value, w.value)).props('flat dense size=sm color=grey')
                                ui.button(icon='delete', on_click=lambda e, sid=sub.id: trigger_delete(sid)).props('flat dense size=sm color=grey')

            ui.button('Close Panel', on_click=dialog.close).classes('w-full mono-btn mt-1')
            rebuild_management_view()
        dialog.open()

    # Information panel
    def open_help_panel():
        with ui.dialog() as dialog, ui.card().classes('w-[420px] rounded-none p-4 mono-card'):
            ui.label('Information').classes('text-xs text-white uppercase tracking-wider mb-3 w-full pb-1 mono-divider')
            
            ui.label('• Pomodoro Loop: Runs in a continuous, infinite cycle (Focus → Break → Focus → Break) with fully automated transition states.').classes('text-xs text-neutral-400 mb-2 leading-relaxed')
            ui.label('• Real-Time Logging: Focus metrics are updated automatically and recorded simultaneously in real-time.').classes('text-xs text-neutral-400 mb-2 leading-relaxed')
            ui.label('• Routine Rotation: Task suggestions update only on a clean app launch after a calendar day has concluded. Ongoing sessions active past midnight are never interrupted.').classes('text-xs text-neutral-400 mb-4 leading-relaxed')
            
            with ui.column().classes('w-full pt-2.5 mt-1 gap-1 text-[11px] text-neutral-500').style('border-top: 1px solid #141414;'):
                with ui.row().classes('items-center gap-2 hover:text-white transition-colors cursor-pointer').on('click', lambda: ui.navigate.to('https://github.com/j46-txt/FocusFlow', new_tab=True)):
                    ui.html('''<svg height="14" width="14" viewBox="0 0 16 16" fill="currentColor" style="display:inline-block;vertical-align:middle;"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.85.54 1.71 0 1.24-.01 2.23-.01 2.53 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path></svg>''')
                    ui.label('github.com/j46-txt')
            
            ui.button('Close Info', on_click=dialog.close).classes('w-full mono-btn mt-4 text-xs')
        dialog.open()

    # History logs view modal
    def open_history_panel():
        with ui.dialog() as dialog, ui.card().classes('w-[480px] rounded-none p-4 mono-card'):
            with ui.row().classes('w-full justify-between items-center mb-3 pb-1 mono-divider'):
                ui.label('Focus Sessions Log').classes('text-xs text-white uppercase tracking-wider')
                ui.button('Export CSV', on_click=download_csv_log).classes('mono-btn').style('font-size: 10px !important; padding: 2px 8px !important; height: auto; min-height: 0;')
            
            with database.get_db() as db:
                summary_rows = db.execute('''
                    SELECT start_date, SUM(duration_seconds) as total_sec 
                    FROM focus_sessions 
                    GROUP BY start_date 
                    ORDER BY start_date DESC LIMIT 7
                ''').fetchall()
            
            if summary_rows:
                ui.label('Weekly Activity Blueprint:').classes('text-[11px] text-neutral-500 uppercase mb-1')
                with ui.column().classes('w-full gap-0.5 mb-4 p-2 bg-neutral-950 text-[11px] mono-card'):
                    for s_row in reversed(summary_rows):
                        hours = s_row['total_sec'] / 3600
                        bars = '■' * min(10, max(1, int(hours * 2)))
                        ui.label(f"{s_row['start_date'][-5:]} | {bars:<10} ({hours:.1f}h)").classes('text-neutral-400')

            log_container = ui.column().classes('w-full gap-1 max-h-48 overflow-y-auto mb-4 text-xs text-neutral-400')
            
            with log_container:
                with database.get_db() as db:
                    rows = db.execute('''
                        SELECT fs.start_date, fs.duration_seconds, s.name as subject_name
                        FROM focus_sessions fs
                        LEFT JOIN subjects s ON fs.subject_id = s.id
                        ORDER BY fs.id DESC LIMIT 50
                    ''').fetchall()
                
                if not rows:
                    ui.label('[No sessions recorded yet]').classes('text-xs text-neutral-600 italic')
                else:
                    with ui.row().classes('w-full justify-between mono-divider pb-1 text-neutral-500 text-[11px]'):
                        ui.label('Day (Date | Weekday)').classes('w-36')
                        ui.label('Suggestion Studied').classes('w-24')
                        ui.label('Time').classes('w-16 text-right')
                    
                    for row in rows:
                        duration_str = statistics.format_duration(row['duration_seconds'])
                        sub_name = row['subject_name'] or "Deleted"
                        
                        try:
                            dt_obj = datetime.datetime.strptime(row['start_date'], '%Y-%m-%d')
                            day_name = dt_obj.strftime('%a')
                        except:
                            day_name = '???'
                            
                        with ui.row().classes('w-full justify-between py-1 border-b border-neutral-950 text-[11px]'):
                            ui.label(f"{row['start_date']} ({day_name})").classes('w-36 text-neutral-400')
                            ui.label(sub_name).classes('w-24 truncate text-neutral-300')
                            ui.label(duration_str).classes('w-16 text-right text-white')
                            
            ui.button('Close Log', on_click=dialog.close).classes('w-full mono-btn text-xs')
        dialog.open()

    def toggle_start_pause():
        status = focus_timer.state.status
        if status in ('idle', 'paused'):
            focus_timer.start()
        elif status == 'running':
            focus_timer.pause()

    def download_csv_log():
        csv_data = statistics.export_history_csv()
        ui.download(csv_data, 'focus_history.csv')

    # Display engine update logic handler
    def update_display():
        status = focus_timer.state.status

        if status == 'idle':
            start_pause_btn.props("icon=play_arrow")
        elif status == 'running':
            start_pause_btn.props("icon=pause")
        elif status == 'paused':
            start_pause_btn.props("icon=play_arrow")

        is_pomo_mode = focus_timer.state.mode in ('pomodoro', 'break')
        is_stopwatch = focus_timer.state.mode == 'stopwatch'
        is_break = focus_timer.state.mode == 'break'

        # Proportional padding and symmetric line-height centering fix for Courier Prime
        if focus_timer.state.mode == 'pomodoro':
            timer_status_label.text = 'Focus'
            timer_status_label.style('color: #38bdf8; background-color: rgba(56, 189, 248, 0.06); border: 0.5px solid #38bdf8; padding: 3px 6px 2px 6px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; display: inline-flex; align-items: center; border-radius: 2px; line-height: 1.1 anisotropy;')
            timer_status_label.set_visibility(True)
            mode_label = 'Focus'
        elif focus_timer.state.mode == 'break':
            timer_status_label.text = 'Break'
            timer_status_label.style('color: #4ade80; background-color: rgba(74, 222, 128, 0.06); border: 0.5px solid rgba(74, 222, 128, 0.2); padding: 3px 6px 2px 6px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; display: inline-flex; align-items: center; border-radius: 2px; line-height: 1.1;')
            timer_status_label.set_visibility(True)
            mode_label = 'Break'
        else:
            timer_status_label.set_visibility(False)
            mode_label = 'Stopwatch'

        timer_label.text = focus_timer.display_time

        # --- Minimalist Browser Tab Title Engine ---
        # Natively updates the page title on every tick via WebSocket, enforcing pure formatting like "(25:00) Focus"
        ui.page_title(f"({focus_timer.display_time}) {mode_label}")

        skip_btn.set_visibility(is_break)
        reset_btn.set_visibility(is_pomo_mode and status != 'idle')
        stop_btn.set_visibility(is_stopwatch and status != 'idle')

        if status == 'idle':
            mode_toggle.enable()
        else:
            mode_toggle.disable()

        active_focus_seconds = 0
        if status in ('running', 'paused'):
            if focus_timer.state.mode == 'pomodoro':
                active_focus_seconds = focus_timer.pomodoro_duration - focus_timer.state.seconds_remaining
            elif focus_timer.state.mode == 'stopwatch':
                active_focus_seconds = focus_timer.state.seconds_elapsed

        goal_hours = settings.get_weekly_goal_hours()
        goal_seconds = goal_hours * 3600

        live_today = cached_stats['today'] + active_focus_seconds
        live_week = cached_stats['week'] + active_focus_seconds
        live_total = cached_stats['total'] + active_focus_seconds

        week_label.text = f"{statistics.format_duration(live_week)} / {goal_hours}h"
        total_label.text = statistics.format_duration(live_total)
        
        avg_label.text = f"{cached_stats['avg_week_hours']:.1f} hours/week"
        focus_days_label.text = f"{cached_stats['focus_days']} days"
        
        today_label.text = statistics.format_duration(live_today)
        
        progress_val = min(1.0, live_week / goal_seconds) if goal_seconds > 0 else 0
        week_progress.value = progress_val
        
        active_sub = subjects.get_active_subject()
        if active_sub:
            suggestion_val_label.set_visibility(True)
            edit_suggestion_inline_btn.set_visibility(True)
            add_suggestion_inline_btn.set_visibility(False)
            suggestion_val_label.text = f"{active_sub.name}"
        else:
            suggestion_val_label.set_visibility(False)
            edit_suggestion_inline_btn.set_visibility(False)
            add_suggestion_inline_btn.set_visibility(True)

        timer_label.update()
        week_label.update()
        total_label.update()
        today_label.update()
        focus_days_label.update()
        suggestion_val_label.update()

    def on_session_complete(duration_seconds: int, mode: str):
        active_sub = subjects.get_active_subject()
        if active_sub:
            statistics.record_session(active_sub.id, duration_seconds, mode)
        refresh_cached_stats()
        update_display()
        
    def on_timer_end(mode: str):
        if mode == 'pomodoro':
            ui.run_javascript("const ctx = new (window.AudioContext || window.webkitAudioContext)(); const osc = ctx.createOscillator(); const gain = ctx.createGain(); osc.type = 'sine'; osc.frequency.setValueAtTime(880, ctx.currentTime); gain.gain.setValueAtTime(0.1, ctx.currentTime); gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.5); osc.connect(gain); gain.connect(ctx.destination); osc.start(); osc.stop(ctx.currentTime + 0.5);")
        elif mode == 'break':
            ui.run_javascript("const ctx = new (window.AudioContext || window.webkitAudioContext)(); [0, 0.2].forEach(t => { const osc = ctx.createOscillator(); const gain = ctx.createGain(); osc.type = 'square'; osc.frequency.setValueAtTime(440, ctx.currentTime + t); gain.gain.setValueAtTime(0.05, ctx.currentTime + t); gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + t + 0.15); osc.connect(gain); gain.connect(ctx.destination); osc.start(ctx.currentTime + t); osc.stop(ctx.currentTime + t + 0.15); });")

    subjects.ensure_daily_rotation()
    focus_timer = FocusTimer(on_tick=update_display, on_complete=on_session_complete, on_timer_end=on_timer_end)
    refresh_cached_stats()
    
    def update_clock():
        now = datetime.datetime.now()
        clock_label.text = now.strftime('%d/%m/%Y | %A | %H:%M')
        greeting_label.text = get_greeting()
        update_display()

    ui.timer(1.0, update_clock)
    ui.timer(1.0, focus_timer.tick)

    # --- Main view layout structure ---
    with ui.column().classes('w-full max-w-4xl mx-auto p-4 gap-4').style('background-color: #000000;'):
        
        clock_label = ui.label('').classes('text-neutral-500 tracking-wider text-xs pl-1')
        
        # --- Part 1: Top panel ---
        with ui.column().classes('w-full gap-4 p-4 mono-card'):
            
            with ui.row().classes('w-full justify-between items-start text-sm'):
                with ui.column().classes('gap-1'):
                    greeting_label = ui.label('').classes('text-neutral-300')
                    
                    with ui.row().classes('items-center gap-1.5').style('height: 24px; max-height: 24px; overflow: hidden;'):
                        ui.label("Today's suggestion:").classes('text-neutral-500 text-sm')
                        suggestion_val_label = ui.label('').classes('text-white uppercase text-sm')
                        edit_suggestion_inline_btn = ui.button(icon='edit', on_click=open_suggestions_panel).props('flat dense size=xs color=grey').style('margin-top: -2px; padding: 0; width: 12px; min-width: 12px;')
                        add_suggestion_inline_btn = ui.button('+ Define Suggestions', on_click=open_suggestions_panel).classes('inline-mono-btn')
                
                with ui.row().classes('gap-2 items-center'):
                    ui.button(icon='help', on_click=open_help_panel).props('flat dense size=sm color=grey')
                    ui.button(icon='settings', on_click=open_settings_panel).props('flat dense size=sm color=grey')

            with ui.column().classes('w-full gap-1.5 mt-2'):
                with ui.row().classes('w-full justify-between items-baseline'):
                    ui.label('Weekly Goal').classes('text-xs uppercase tracking-wider text-neutral-500')
                    week_label = ui.label('0h 0m / 10h').classes('text-white text-sm')
                
                week_progress = ui.linear_progress(value=0.0, show_value=False).classes('w-full').style('height: 14px !important; border-radius: 0px;')

        # --- Part 2: Bottom container ---
        with ui.row().classes('w-full gap-6 items-stretch'):
            
            # Statistics card block
            with ui.column().classes('p-4 gap-4 relative mono-card').style('flex: 1 1 0; min-width: 320px; min-height: 250px;'):
                with ui.row().classes('w-full justify-between items-center pb-2 mono-divider'):
                    ui.label('Statistics').classes('text-sm uppercase tracking-wider text-neutral-400')
                
                with ui.column().classes('w-full gap-3 text-sm text-neutral-400'):
                    with ui.column().classes('gap-0'):
                        ui.label('Pace').classes('text-sm uppercase tracking-wider text-neutral-500')
                        avg_label = ui.label('0.0 hours/week').classes('text-white text-base')
                        
                    with ui.column().classes('gap-0'):
                        ui.label('Total Hours').classes('text-sm uppercase tracking-wider text-neutral-500')
                        total_label = ui.label('0h 0m').classes('text-white text-base')

                    with ui.column().classes('gap-0'):
                        ui.label('Total Focus Days').classes('text-sm uppercase tracking-wider text-neutral-500')
                        focus_days_label = ui.label('0 days').classes('text-white text-base')
                
                ui.label('Show More »').on('click', open_history_panel).classes('absolute bottom-4 left-4 cursor-pointer text-xs uppercase tracking-wider transition-colors blue-link')

            # Timer controls card block
            with ui.column().classes('p-4 gap-4 items-center justify-start relative mono-card').style('flex: 1 1 0; min-width: 320px; min-height: 250px;'):
                with ui.row().classes('w-full items-center pb-2 relative').style('height: 32px; min-height: 32px; max-height: 32px; border-bottom: 1px solid #141414;'):
                    ui.label('Timer').classes('text-sm uppercase tracking-wider text-neutral-400')
                    with ui.row().classes('absolute right-0 top-0 bottom-2 items-center'):
                        timer_status_label = ui.label('[Focus]').classes('rounded-none font-mono')
                
                mode_toggle = ui.toggle(
                    ['Pomodoro', 'Stopwatch'],
                    value='Pomodoro',
                    on_change=lambda e: focus_timer.set_mode(e.value)
                ).classes('large-toggle mt-1').props('dense unevaluated flat')
                
                with ui.column().classes('w-full items-center mt-1'):
                    timer_label = ui.label(focus_timer.display_time).classes('text-5xl text-white mb-3 tracking-normal')
                    
                    with ui.row().classes('gap-4 h-10 items-center justify-center w-full'):
                        start_pause_btn = ui.button(on_click=toggle_start_pause).classes('mono-btn').props('flat round size=md')
                        reset_btn = ui.button(on_click=focus_timer.reset).classes('mono-btn').props('flat round icon=refresh size=md')
                        stop_btn = ui.button(on_click=focus_timer.stop).classes('mono-btn').props('flat round icon=stop size=md')

                with ui.row().classes('w-full items-center gap-1.5 mt-auto pt-2').style('border-top: 1px solid #141414;'):
                    ui.label("Today:").classes('text-xs uppercase tracking-wider text-neutral-500')
                    today_label = ui.label('0h 0m').classes('text-xs text-neutral-300')

                skip_btn = ui.label('Skip Break »').on('click', focus_timer.skip).classes('absolute bottom-2 right-4 cursor-pointer text-xs text-neutral-600 hover:text-white uppercase tracking-wider transition-colors')

    update_clock()
    update_display()
