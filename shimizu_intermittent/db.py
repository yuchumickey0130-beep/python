import sqlite3
import json
import random

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
            high_periods TEXT,
            num_invested INTEGER,
            num_success INTEGER,
            num_failed INTEGER,
            num_not_invested INTEGER
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
            has_submitted INTEGER,
            success INTEGER
        )
    """)

    # room_state は1行だけ使用
    c.execute("""
        INSERT OR IGNORE INTO room_state (
            id,
            game,
            period,
            phase,
            is_started,
            experiment_over,
            high_periods,
            num_invested,
            num_success,
            num_failed,
            num_not_invested
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        1,
        1,
        1,
        "decision",
        0,
        0,
        "[]",
        None,
        None,
        None,
        None
    ))

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
            has_submitted,
            success
        )
        VALUES (?, ?, ?, '', NULL, 0, NULL)
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

def get_player(player_id):
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
            has_submitted,
            success
        FROM players
        WHERE player_id = ?
        """,
        (player_id,)
    )

    row = c.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "player_id": row[0],
        "player_number": row[1],
        "wealth": row[2],
        "current_choice": row[3],
        "response_time": row[4],
        "has_submitted": bool(row[5]),
        "success": (
            bool(row[6])
            if row[6] is not None
            else None
        )
    }

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
            high_periods,
            num_invested,
            num_success,
            num_failed,
            num_not_invested
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
        "high_periods": json.loads(row[5]),
        "num_invested": row[6],
        "num_success": row[7],
        "num_failed": row[8],
        "num_not_invested": row[9]
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
            high_periods = '[]',
            num_invested = NULL,
            num_success = NULL,
            num_failed = NULL,
            num_not_invested = NULL
        WHERE id = 1
        """
    )

    conn.commit()
    conn.close()

def submit_choice(player_id, choice, response_time):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute(
        """
        UPDATE players
        SET
            current_choice = ?,
            response_time = ?,
            has_submitted = 1
        WHERE player_id = ?
        """,
        (
            choice,
            response_time,
            player_id
        )
    )

    conn.commit()
    conn.close()

def finalize_period(success_capacity, return_multiplier):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Decisionフェーズ以外では結果を確定しない
    c.execute("""
        SELECT phase
        FROM room_state
        WHERE id = 1
    """)

    row = c.fetchone()

    if row is None or row[0] != "decision":
        conn.close()
        return

    # Player番号順に、現在の状態と選択を取得
    c.execute("""
        SELECT
            player_id,
            player_number,
            wealth,
            current_choice
        FROM players
        WHERE has_submitted = 1
        ORDER BY player_number
    """)

    rows = c.fetchall()

    # 投資したPlayerを取得
    investors = [
        row[1]
        for row in rows
        if row[3] == "Invest"
    ]

    # 成功者を決定
    if len(investors) <= success_capacity:
        successful_players = investors
    else:
        successful_players = random.sample(
            investors,
            success_capacity
        )

    num_invested = len(investors)
    num_success = len(successful_players)
    num_failed = num_invested - num_success
    num_not_invested = len(rows) - num_invested

    # 各Playerの結果を計算してDBへ保存
    for row in rows:

        player_id = row[0]
        player_number = row[1]
        wealth = row[2]
        choice = row[3]

        investment = wealth * 0.10

        if choice == "Not Invest":
            new_wealth = wealth + investment
            success = None

        elif player_number in successful_players:
            new_wealth = (
                wealth
                + investment * return_multiplier
            )
            success = 1

        else:
            new_wealth = wealth
            success = 0

        c.execute(
            """
            UPDATE players
            SET
                wealth = ?,
                success = ?
            WHERE player_id = ?
            """,
            (
                new_wealth,
                success,
                player_id
            )
        )

    # ターン全体の結果を保存し、Resultフェーズへ
    c.execute(
        """
        UPDATE room_state
        SET
            phase = 'result',
            num_invested = ?,
            num_success = ?,
            num_failed = ?,
            num_not_invested = ?
        WHERE id = 1
        """,
        (
            num_invested,
            num_success,
            num_failed,
            num_not_invested
        )
    )

    conn.commit()
    conn.close()

def advance_to_next_period():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # 共有ターンを1つ進め、Decisionフェーズへ戻す
    c.execute("""
        UPDATE room_state
        SET period = period + 1,
            phase = 'decision',
            num_invested = NULL,
            num_success = NULL,
            num_failed = NULL,
            num_not_invested = NULL
        WHERE id = 1
    """)

    # 全参加者を「次ターン未回答」の状態へ戻す
    c.execute("""
        UPDATE players
        SET current_choice = '',
            response_time = NULL,
            has_submitted = 0,
            success = NULL
    """)

    conn.commit()
    conn.close()