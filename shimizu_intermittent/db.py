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

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS period_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            game INTEGER NOT NULL,
            player_id TEXT NOT NULL,
            player_number INTEGER NOT NULL,
            period INTEGER NOT NULL,

            visibility_condition TEXT,
            time_since_high INTEGER,
            time_to_high INTEGER,

            wealth_before REAL,
            rank_before INTEGER,
            wealth_gap_before REAL,
            endowment REAL,

            last_published_wealth REAL,
            last_published_rank INTEGER,
            last_published_gap REAL,

            choice TEXT,
            response_time REAL,
            result TEXT,

            wealth_after REAL,
            rank_after INTEGER,
            wealth_gap_after REAL,

            num_invested INTEGER,
            num_success INTEGER,
            num_failed INTEGER,
            num_not_invested INTEGER,

            group_wealths_before TEXT,
            group_wealths_after TEXT,

            UNIQUE(game, player_id, period)
        )
        """
    )

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
        SELECT game, period, phase
        FROM room_state
        WHERE id = 1
    """)

    game = row[0]
    period = row[1]

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

    # 更新後の全Playerを取得
    c.execute(
        """
        SELECT
            player_id,
            player_number,
            wealth,
            current_choice,
            success
        FROM players
        ORDER BY player_number
        """
    )

    updated_players = c.fetchall()

    group_wealths_after = [
        player[2]
        for player in updated_players
    ]

    # 更新後の順位
    ranks_after = [
        1 + sum(
            other_wealth > player_wealth
            for other_wealth in group_wealths_after
        )
        for player_wealth in group_wealths_after
    ]

    # 更新後のトップとの差
    top_wealth_after = max(group_wealths_after)

    wealth_gaps_after = [
        top_wealth_after - player_wealth
        for player_wealth in group_wealths_after
    ]

    # 各Playerのログを完成させる
    for i, player in enumerate(updated_players):

        player_id = player[0]
        wealth_after = player[2]
        choice = player[3]
        success = player[4]

        if choice == "Invest":
            if success:
                result = "Success"
            else:
                result = "Failure"
        else:
            result = "Not Invest"

        c.execute(
            """
            UPDATE period_logs
            SET
                result = ?,
                wealth_after = ?,
                rank_after = ?,
                wealth_gap_after = ?,
                num_invested = ?,
                num_success = ?,
                num_failed = ?,
                num_not_invested = ?,
                group_wealths_after = ?
            WHERE
                game = ?
                AND player_id = ?
                AND period = ?
            """,
            (
                result,
                wealth_after,
                ranks_after[i],
                wealth_gaps_after[i],
                num_invested,
                num_success,
                num_failed,
                num_not_invested,
                json.dumps(group_wealths_after),
                game,
                player_id,
                period
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

def start_next_game(initial_wealth, high_periods):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # 実験全体を次のゲームへ
    c.execute(
        """
        UPDATE room_state
        SET
            game = game + 1,
            period = 1,
            phase = 'decision',
            high_periods = ?,
            num_invested = NULL,
            num_success = NULL,
            num_failed = NULL,
            num_not_invested = NULL
        WHERE id = 1
        """,
        (json.dumps(high_periods),)
    )

    # 全参加者を初期状態へ戻す
    c.execute(
        """
        UPDATE players
        SET
            wealth = ?,
            current_choice = NULL,
            response_time = NULL,
            has_submitted = 0,
            success = NULL
        """,
        (initial_wealth,)
    )

    conn.commit()
    conn.close()

def end_experiment():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute(
        """
        UPDATE room_state
        SET
            experiment_over = 1,
            phase = 'finished'
        WHERE id = 1
        """
    )

    conn.commit()
    conn.close()

def create_period_log(
    game,
    player_id,
    player_number,
    period,
    visibility_condition,
    time_since_high,
    time_to_high,
    wealth_before,
    rank_before,
    wealth_gap_before,
    endowment,
    last_published_wealth,
    last_published_rank,
    last_published_gap,
    group_wealths_before
):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute(
        """
        INSERT OR IGNORE INTO period_logs (
            game,
            player_id,
            player_number,
            period,
            visibility_condition,
            time_since_high,
            time_to_high,
            wealth_before,
            rank_before,
            wealth_gap_before,
            endowment,
            last_published_wealth,
            last_published_rank,
            last_published_gap,
            group_wealths_before
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            game,
            player_id,
            player_number,
            period,
            visibility_condition,
            time_since_high,
            time_to_high,
            wealth_before,
            rank_before,
            wealth_gap_before,
            endowment,
            last_published_wealth,
            last_published_rank,
            last_published_gap,
            json.dumps(group_wealths_before)
        )
    )

    conn.commit()
    conn.close()

def update_period_log_choice(
    game,
    player_id,
    period,
    choice,
    response_time
):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute(
        """
        UPDATE period_logs
        SET
            choice = ?,
            response_time = ?
        WHERE
            game = ?
            AND player_id = ?
            AND period = ?
        """,
        (
            choice,
            response_time,
            game,
            player_id,
            period
        )
    )

    conn.commit()
    conn.close()