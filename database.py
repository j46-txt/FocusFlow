# database.py
# -*- coding: utf-8 -*-
import sqlite3
import os
import psycopg2
import threading
import queue
import tempfile
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), 'assets', 'database.sqlite')
POSTGRES_URL = os.environ.get('DATABASE_URL')

# Thread-safe queue to sequentialize cloud backup tasks and avoid thread explosions or out-of-order writes
BACKUP_QUEUE = queue.Queue(maxsize=1)

def load_cloud_backup():
    """Fetches the binary SQLite file from the cloud and restores it locally on boot."""
    if not POSTGRES_URL:
        print("[Backup] DATABASE_URL not found. Running in ephemeral local-only mode.")
        return
    conn = None
    try:
        # Prevent infinite connection hangs during remote network dropouts or database cold starts
        conn = psycopg2.connect(POSTGRES_URL, connect_timeout=5)
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS cafe_backup (
                    id INTEGER PRIMARY KEY,
                    file_data BYTEA,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            conn.commit()
            
            cur.execute("SELECT file_data FROM cafe_backup WHERE id = 1;")
            row = cur.fetchone()
            if row and row[0]:
                os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
                
                # Remove any stale WAL/SHM log files to avoid structural mismatch with the incoming backup
                for suffix in ['-wal', '-shm']:
                    stale_file = DB_PATH + suffix
                    if os.path.exists(stale_file):
                        try:
                            os.remove(stale_file)
                        except Exception:
                            pass
                            
                with open(DB_PATH, 'wb') as f:
                    f.write(bytes(row[0]))
                print("[Backup] SQLite database successfully restored from the cloud!")
            else:
                print("[Backup] No remote backup found. Initializing a clean database.")
    except Exception as e:
        print(f"[Backup Error] Failed to load backup from cloud: {e}")
    finally:
        if conn:
            conn.close()

def save_cloud_backup(binary_data: bytes):
    """Uploads the consolidated local SQLite data to the cloud via a clean connection."""
    if not POSTGRES_URL:
        return
    conn = None
    try:
        conn = psycopg2.connect(POSTGRES_URL, connect_timeout=5)
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO cafe_backup (id, file_data, updated_at)
                VALUES (1, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO UPDATE SET file_data = EXCLUDED.file_data, updated_at = CURRENT_TIMESTAMP;
            ''', (psycopg2.Binary(binary_data),))
            conn.commit()
        print("[Backup] Changes successfully synchronized to the cloud.")
    except Exception as e:
        print(f"[Backup Error] Failed to save backup to cloud: {e}")
    finally:
        if conn:
            conn.close()

def _backup_worker():
    """Dedicated background thread worker that sequentially uploads database snapshots using SQLite's online backup API."""
    while True:
        try:
            # Block until a synchronization signal is queued
            BACKUP_QUEUE.get()
            if os.path.exists(DB_PATH):
                tmp_path = None
                src_conn = None
                dst_conn = None
                try:
                    # Use SQLite native backup API to create a consistent point-in-time file snapshot.
                    # This eliminates torn reads from concurrent writes and removes hot-path checkpoint overhead.
                    with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
                        tmp_path = tmp.name
                    
                    src_conn = sqlite3.connect(DB_PATH, timeout=30.0)
                    dst_conn = sqlite3.connect(tmp_path)
                    src_conn.backup(dst_conn)
                    dst_conn.close()
                    dst_conn = None
                    src_conn.close()
                    src_conn = None
                    
                    with open(tmp_path, 'rb') as f:
                        binary_data = f.read()
                        
                    save_cloud_backup(binary_data)
                except Exception as e:
                    print(f"[Backup Error] Failed to generate consistent database snapshot inside worker: {e}")
                finally:
                    if dst_conn:
                        try:
                            dst_conn.close()
                        except Exception:
                            pass
                    if src_conn:
                        try:
                            src_conn.close()
                        except Exception:
                            pass
                    if tmp_path and os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass
        except Exception as e:
            print(f"[Backup Worker Error] Critical failure in background backup loop: {e}")
        finally:
            BACKUP_QUEUE.task_done()

# Start the persistent background synchronization thread immediately upon module import
threading.Thread(target=_backup_worker, daemon=True, name="CaFE-BackupWorker").start()

def save_cloud_backup_background():
    """Triggers cloud backup network upload by notifying the serialized background queue worker."""
    try:
        # Coalesce concurrent requests: if an upload is pending, drop this request 
        # since the worker will inherently capture the latest disk state on its next pass.
        BACKUP_QUEUE.put_nowait(True)
    except queue.Full:
        pass

@contextmanager
def get_db():
    """Provides a transactional database connection for persistent updates with automatic rollback safety."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = None
    tx_committed = False
    try:
        # Set a prolonged timeout threshold to survive transient write-locks across multiple threads
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        
        # Enforcing WAL mode here guarantees concurrent read-write capabilities on every active session thread.
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA synchronous=NORMAL;')
        
        yield conn
        conn.commit()
        tx_committed = True
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            try:
                changes = conn.total_changes
                # Downgraded from TRUNCATE to PASSIVE. The background worker now uses the online backup 
                # API, so forcing an expensive, blocking journal truncation on the request thread is obsolete.
                if tx_committed and changes > 0:
                    conn.execute('PRAGMA wal_checkpoint(PASSIVE);')
                else:
                    changes = 0
            except Exception as e:
                print(f"[Checkpoint Error] Failed to execute passive WAL checkpoint: {e}")
                changes = 0
                
            conn.close()
            
            # Optimization: Only push to the cloud if the local write was successfully committed
            if tx_committed and changes > 0:
                save_cloud_backup_background()

def init_db():
    """Initializes the SQLite tables with schema migrations safely."""
    load_cloud_backup()
    
    with get_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 0,
                list_order INTEGER NOT NULL,
                weight INTEGER NOT NULL DEFAULT 1
            )
        ''')
        
        cursor = db.execute("PRAGMA table_info(subjects)")
        columns = [row['name'] for row in cursor.fetchall()]
        if 'weight' not in columns:
            db.execute("ALTER TABLE subjects ADD COLUMN weight INTEGER NOT NULL DEFAULT 1")
            
        db.execute('''
            CREATE TABLE IF NOT EXISTS focus_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER,
                start_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_date TEXT NOT NULL,
                end_time TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL,
                timer_mode TEXT NOT NULL,
                FOREIGN KEY (subject_id) REFERENCES subjects(id)
            )
        ''')
        
        # PERFORMANCE OPTIMIZATION: Seed necessary indices to prevent future table scans 
        # as focus log dimensions expand under long-term usage.
        db.execute('CREATE INDEX IF NOT EXISTS idx_focus_sessions_start_date ON focus_sessions(start_date);')
        db.execute('CREATE INDEX IF NOT EXISTS idx_focus_sessions_subject_id ON focus_sessions(subject_id);')
