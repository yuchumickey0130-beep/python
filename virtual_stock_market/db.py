# db.py
import sqlite3
import json

DB_NAME = "game_room.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # 部屋の状態管理
    c.execute('''
        CREATE TABLE IF NOT EXISTS room_state (
            id INTEGER PRIMARY KEY,
            step INTEGER,
            is_started INTEGER,
            game_over INTEGER
        )
    ''')
    # プレイヤー管理
    c.execute('''
        CREATE TABLE IF NOT EXISTS players (
            player_id TEXT PRIMARY KEY,
            is_ai INTEGER,
            cash REAL,
            current_input TEXT,
            has_submitted INTEGER
        )
    ''')
    # 初期データセット
    c.execute("INSERT OR IGNORE INTO room_state (id, step, is_started, game_over) VALUES (1, 1, 0, 0)")
    conn.commit()
    conn.close()

def reset_room():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM room_state")
    c.execute("DELETE FROM players")
    c.execute("INSERT INTO room_state (id, step, is_started, game_over) VALUES (1, 1, 0, 0)")
    conn.commit()
    conn.close()

def get_room_state():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT step, is_started, game_over FROM room_state WHERE id=1")
    row = c.fetchone()
    conn.close()
    return {"step": row[0], "is_started": bool(row[1]), "game_over": bool(row[2])}

def set_room_started(started=True):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE room_state SET is_started=? WHERE id=1", (1 if started else 0,))
    conn.commit()
    conn.close()

def register_player(player_id, initial_cash, is_ai=False):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT OR IGNORE INTO players (player_id, is_ai, cash, current_input, has_submitted)
        VALUES (?, ?, ?, '', 0)
    ''', (player_id, 1 if is_ai else 0, initial_cash))
    conn.commit()
    conn.close()

def get_all_players():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT player_id, is_ai, cash, has_submitted, current_input FROM players")
    rows = c.fetchall()
    conn.close()
    players = []
    for r in rows:
        players.append({
            "player_id": r[0],
            "is_ai": bool(r[1]),
            "cash": r[2],
            "has_submitted": bool(r[3]),
            "current_input": json.loads(r[4]) if r[4] else {}
        })
    return players

def submit_player_input(player_id, invest_dict):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        UPDATE players 
        SET current_input=?, has_submitted=1 
        WHERE player_id=?
    ''', (json.dumps(invest_dict), player_id))
    conn.commit()
    conn.close()

def advance_to_next_step(new_step, new_cashes, game_over=False):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE room_state SET step=?, game_over=? WHERE id=1", (new_step, 1 if game_over else 0))
    for p_id, cash in new_cashes.items():
        c.execute("UPDATE players SET cash=?, has_submitted=0, current_input='' WHERE player_id=?", (cash, p_id))
    conn.commit()
    conn.close()