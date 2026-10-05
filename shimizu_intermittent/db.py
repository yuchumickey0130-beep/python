import sqlite3
import json

DB_NAME = "experiment_room.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # 実験全体の進行状態
    c.execute("""
        CREATE TABLE IF NOT EXISTS room_state (
            id INTEGER PRIMARY KEY,
            game INTEGER,
            period INTEGER,
            phase TEXT,
            is_started INTEGER,
            experiment_over INTEGER,
            high_periods TEXT
        )
    """)

    # 各参加者の状態
    c.execute("""
        CREATE TABLE IF NOT EXISTS players (
            player_id TEXT PRIMARY KEY,
            player_number INTEGER UNIQUE,
            wealth REAL,
            current_choice TEXT,
            response_time REAL,
            has_submitted INTEGER
        )
    """)

    # room_state は常に id=1 の1行だけ使う
    c.execute("""
        INSERT OR IGNORE INTO room_state (
            id,
            game,
            period,
            phase,
            is_started,
            experiment_over,
            high_periods
        )
        VALUES (1, 1, 1, 'decision', 0, 0, '[]')
    """)

    conn.commit()
    conn.close()

def register_player(player_id, initial_wealth):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # すでに登録済みなら、そのPlayer番号を返す
    c.execute(
        """
        SELECT player_number
        FROM players
        WHERE player_id = ?
        """,
        (player_id,)
    )

    row = c.fetchone()

    if row is not None:
        conn.close()
        return row[0]

    # 現在の参加人数を調べる
    c.execute("SELECT COUNT(*) FROM players")
    player_count = c.fetchone()[0]

    # 8人埋まっていたら登録しない
    if player_count >= 8:
        conn.close()
        return None

    # 登録順に Player 1, 2, ... と割り振る
    player_number = player_count + 1

    c.execute(
        """
        INSERT INTO players (
            player_id,
            player_number,
            wealth,
            current_choice,
            response_time,
            has_submitted
        )
        VALUES (?, ?, ?, '', NULL, 0)
        """,
        (
            player_id,
            player_number,
            initial_wealth
        )
    )

    conn.commit()
    conn.close()

    return player_number


def get_all_players():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute(
        """
        SELECT
            player_id,
            player_number,
            wealth,
            current_choice,
            response_time,
            has_submitted
        FROM players
        ORDER BY player_number
        """
    )

    rows = c.fetchall()
    conn.close()

    players = []

    for row in rows:
        players.append({
            "player_id": row[0],
            "player_number": row[1],
            "wealth": row[2],
            "current_choice": row[3],
            "response_time": row[4],
            "has_submitted": bool(row[5])
        })

    return players

def get_room_state():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT
            game,
            period,
            phase,
            is_started,
            experiment_over,
            high_periods
        FROM room_state
        WHERE id = 1
    """)

    row = c.fetchone()
    conn.close()

    return {
        "game": row[0],
        "period": row[1],
        "phase": row[2],
        "is_started": bool(row[3]),
        "experiment_over": bool(row[4]),
        "high_periods": json.loads(row[5])
    }


def set_room_started(high_periods):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute(
        """
        UPDATE room_state
        SET
            is_started = 1,
            game = 1,
            period = 1,
            phase = 'decision',
            experiment_over = 0,
            high_periods = ?
        WHERE id = 1
        """,
        (json.dumps(high_periods),)
    )

    conn.commit()
    conn.close()


def reset_room():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # 参加者を全員削除
    c.execute("DELETE FROM players")

    # 実験全体を初期状態へ戻す
    c.execute(
        """
        UPDATE room_state
        SET
            game = 1,
            period = 1,
            phase = 'decision',
            is_started = 0,
            experiment_over = 0,
            high_periods = '[]'
        WHERE id = 1
        """
    )

    conn.commit()
    conn.close()