# database.py
# -*- coding: utf-8 -*-
import sqlite3
import os
import psycopg2
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), 'assets', 'database.sqlite')
POSTGRES_URL = os.environ.get('DATABASE_URL') # Injected by the hosting provider

def load_cloud_backup():
    """Fetches the binary SQLite file from the cloud and restores it locally on boot."""
    if not POSTGRES_URL:
        print("[Backup] DATABASE_URL not found. Running in ephemeral local-only mode.")
        return
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS focusflow_backup (
                id INTEGER PRIMARY KEY,
                file_data BYTEA,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        conn.commit()
        
        cur.execute("SELECT file_data FROM focusflow_backup WHERE id = 1;")
        row = cur.fetchone()
        if row and row[0]:
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            with open(DB_PATH, 'wb') as f:
                f.write(bytes(row[0]))
            print("[Backup] SQLite database successfully restored from the cloud!")
        else:
            print("[Backup] No remote backup found. Initializing a clean database.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[Backup Error] Failed to load backup from cloud: {e}")

def save_cloud_backup():
    """Uploads the consolidated local SQLite file to the cloud."""
    if not POSTGRES_URL:
        return
    try:
        if not os.path.exists(DB_PATH):
            return
        with open(DB_PATH, 'rb') as f:
            binary_data = f.read()
        
        conn = psycopg2.connect(POSTGRES_URL)
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO focusflow_backup (id, file_data, updated_at)
            VALUES (1, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET file_data = EXCLUDED.file_data, updated_at = CURRENT_TIMESTAMP;
        ''', (psycopg2.Binary(binary_data),))
        conn.commit()
        cur.close()
        conn.close()
        print("[Backup] Changes successfully synchronized to the cloud.")
    except Exception as e:
        print(f"[Backup Error] Failed to save backup to cloud: {e}")

@contextmanager
def get_db():
    """Provides a transactional database connection for persistent updates."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        changes = conn.total_changes
        conn.commit()
        conn.close()
        # If any write changes (INSERT, UPDATE, DELETE) occurred, trigger the cloud backup
        if changes > 0:
            save_cloud_backup()

def init_db():
    """Initializes the SQLite tables with schema migrations safely."""
    # First, pull down the current state from the cloud
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
        ''')# database.py
# -*- coding: utf-8 -*-
import sqlite3
import os
import psycopg2
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), 'assets', 'database.sqlite')
POSTGRES_URL = os.environ.get('DATABASE_URL') # Variável injetada pela hospedagem

def load_cloud_backup():
    """Busca o arquivo binário do SQLite na nuvem e restaura localmente no boot."""
    if not POSTGRES_URL:
        print("[Backup] DATABASE_URL não encontrada. Rodando apenas em modo local efêmero.")
        return
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS focusflow_backup (
                id INTEGER PRIMARY KEY,
                file_data BYTEA,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        conn.commit()
        
        cur.execute("SELECT file_data FROM focusflow_backup WHERE id = 1;")
        row = cur.fetchone()
        if row and row[0]:
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            with open(DB_PATH, 'wb') as f:
                f.write(bytes(row[0]))
            print("[Backup] Banco de dados SQLite restaurado com sucesso da nuvem!")
        else:
            print("[Backup] Nenhum backup remoto encontrado. Inicializando banco limpo.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[Backup Erro] Falha ao carregar o backup da nuvem: {e}")

def save_cloud_backup():
    """Envia o arquivo SQLite local consolidado para a nuvem."""
    if not POSTGRES_URL:
        return
    try:
        if not os.path.exists(DB_PATH):
            return
        with open(DB_PATH, 'rb') as f:
            binary_data = f.read()
        
        conn = psycopg2.connect(POSTGRES_URL)
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO focusflow_backup (id, file_data, updated_at)
            VALUES (1, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET file_data = EXCLUDED.file_data, updated_at = CURRENT_TIMESTAMP;
        ''', (psycopg2.Binary(binary_data),))
        conn.commit()
        cur.close()
        conn.close()
        print("[Backup] Alterações sincronizadas com a nuvem com sucesso.")
    except Exception as e:
        print(f"[Backup Erro] Falha ao salvar backup na nuvem: {e}")

@contextmanager
def get_db():
    """Fornece uma conexão transacional para atualizações persistentes."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        changes = conn.total_changes
        conn.commit()
        conn.close()
        # Se houve alguma alteração real de escrita (INSERT, UPDATE, DELETE), faz o backup
        if changes > 0:
            save_cloud_backup()

def init_db():
    """Inicializa as tabelas SQLite aplicando migrations com segurança."""
    # Primeiro baixa o estado atual salvo na nuvem
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
