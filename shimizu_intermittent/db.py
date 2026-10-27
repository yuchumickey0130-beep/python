import sqlite3
import json
import random

from config import (
    INTEREST_RATE,
    NUM_PERIODS,
    NUM_PLAYERS,
    TEST_MODE,
    TEST_NUM_PLAYERS,
    TEST_NUM_PERIODS,
)

EFFECTIVE_NUM_PERIODS = TEST_NUM_PERIODS if TEST_MODE else NUM_PERIODS

DB_NAME = "experiment_room.db"

def connect_db():
    # Separate connection per operation; WAL allows concurrent readers.
    conn = sqlite3.connect(DB_NAME, timeout=15)
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def init_db():
    conn = connect_db()
    conn.execute('PRAGMA journal_mode=WAL')
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
            published_period INTEGER,
            published_wealths TEXT,
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

    c.execute("PRAGMA table_info(room_state)")
    room_columns = [row[1] for row in c.fetchall()]
    if "num_periods" not in room_columns:
        c.execute("ALTER TABLE room_state ADD COLUMN num_periods INTEGER NOT NULL DEFAULT 22")

    # 既存DBにも結果確認用の列を追加
    c.execute("PRAGMA table_info(players)")
    columns = [
        row[1]
        for row in c.fetchall()
    ]

    if "result_confirmed" not in columns:
        c.execute("""
            ALTER TABLE players
            ADD COLUMN result_confirmed INTEGER NOT NULL DEFAULT 0
        """)

    if "game_start_ack" not in columns:
        c.execute("ALTER TABLE players ADD COLUMN game_start_ack INTEGER NOT NULL DEFAULT 0")

    if "game_ready" not in columns:
        c.execute("ALTER TABLE players ADD COLUMN game_ready INTEGER NOT NULL DEFAULT 0")

    if "explanation_confirmed" not in columns:
        c.execute("""
            ALTER TABLE players
            ADD COLUMN explanation_confirmed INTEGER NOT NULL DEFAULT 0
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
            result_review_time REAL,
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
            published_period,
            published_wealths,
            num_invested,
            num_success,
            num_failed,
            num_not_invested
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        None,
        None,
        None
    ))

    # Add result review duration to databases created before this version.
    c.execute("PRAGMA table_info(period_logs)")
    if "result_review_time" not in [row[1] for row in c.fetchall()]:
        c.execute("ALTER TABLE period_logs ADD COLUMN result_review_time REAL")

    conn.commit()
    conn.close()

def register_player(player_id, initial_wealth):
    conn = connect_db()
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

    
    # テストモードに応じて参加人数の上限を切り替える
    max_players = TEST_NUM_PLAYERS if TEST_MODE else NUM_PLAYERS

    if player_count >= max_players:
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
    conn = connect_db()
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
            success,
            result_confirmed,
            explanation_confirmed,
            game_ready,
            game_start_ack
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
        ),
        "result_confirmed": bool(row[7]),
        "explanation_confirmed": bool(row[8]),
        "game_ready": bool(row[9]),
        "game_start_ack": bool(row[10])
    }

def get_all_players():
    conn = connect_db()
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
            result_confirmed,
            explanation_confirmed,
            game_ready,
            game_start_ack
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
            "has_submitted": bool(row[5]),
            "result_confirmed": bool(row[6]),
            "explanation_confirmed": bool(row[7]),
            "game_ready": bool(row[8]),
            "game_start_ack": bool(row[9])
        })

    return players

def get_room_state():
    conn = connect_db()
    c = conn.cursor()

    c.execute("""
        SELECT
            game,
            period,
            phase,
            is_started,
            experiment_over,
            high_periods,
            published_period,
            published_wealths,
            num_invested,
            num_success,
            num_failed,
            num_not_invested,
            num_periods
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
        "published_period": row[6],
        "published_wealths": (
            json.loads(row[7])
            if row[7] is not None
            else None
        ),
        "num_invested": row[8],
        "num_success": row[9],
        "num_failed": row[10],
        "num_not_invested": row[11],
        "num_periods": row[12]
    }


def set_room_started(high_periods, num_periods):
    conn = connect_db()
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
            high_periods = ?,
            num_periods = ?
        WHERE id = 1
        """,
        (json.dumps(high_periods), num_periods)
    )

    conn.commit()
    conn.close()


def reset_room():
    conn = connect_db()
    c = conn.cursor()

    # 参加者を全員削除
    c.execute("DELETE FROM players")

    # 実験ログを全て削除
    c.execute("DELETE FROM period_logs")

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
            high_periods = '{}',
            num_periods = 22,
            published_period = NULL,
            published_wealths = NULL,
            num_invested = NULL,
            num_success = NULL,
            num_failed = NULL,
            num_not_invested = NULL
        WHERE id = 1
        """
    )

    conn.commit()
    conn.close()

def acknowledge_game_start(player_id):
    conn = connect_db()
    c = conn.cursor()
    c.execute("""
        UPDATE players SET game_start_ack = 1
        WHERE player_id = ? AND game_start_ack = 0
          AND EXISTS (SELECT 1 FROM room_state WHERE id = 1
                      AND phase = 'decision' AND period = 1 AND is_started = 1)
    """, (player_id,))
    conn.commit()
    conn.close()


def submit_choice(player_id, choice, response_time):
    conn = connect_db()
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

def submit_choice_with_log(player_id, game, period, choice, response_time):
    """Commit participant choice and its research log in one transaction."""
    conn = connect_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        room = conn.execute(
            "SELECT game, period, phase FROM room_state WHERE id = 1"
        ).fetchone()
        if (room is None or room[0] != game or room[1] != period
                or room[2] != "decision"):
            raise ValueError("The decision period has already changed.")
        cursor = conn.execute(
            """
            UPDATE players
            SET current_choice = ?, response_time = ?, has_submitted = 1
            WHERE player_id = ? AND has_submitted = 0
            """,
            (choice, response_time, player_id)
        )
        if cursor.rowcount != 1:
            raise ValueError("This player has already submitted or is missing.")
        cursor = conn.execute(
            """
            UPDATE period_logs SET choice = ?, response_time = ?
            WHERE game = ? AND player_id = ? AND period = ?
            """,
            (choice, response_time, game, player_id, period)
        )
        if cursor.rowcount != 1:
            raise ValueError("The period log was not initialized.")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def finalize_period(success_capacity, return_multiplier):
    conn = connect_db()
    c = conn.cursor()

    # Decisionフェーズ以外では結果を確定しない
    c.execute("""
        SELECT game, period, phase, high_periods
        FROM room_state
        WHERE id = 1
    """)

    row = c.fetchone()

    if row is None or row[2] not in ("decision", "practice_decision"):
        conn.close()
        return

    is_practice = row[2] == "practice_decision"

    game = row[0]
    period = row[1]
    high_periods = json.loads(row[3])

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

        investment = wealth * INTEREST_RATE

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

    # 最終ターンのみ、専用の最終結果画面へ移行
    if is_practice:
        next_phase = "practice_result"
    elif period == (TEST_NUM_PERIODS if TEST_MODE else get_num_periods_for_cursor(c)):
        next_phase = "final_result"
    else:
        next_phase = "result"
    

    # HIGHターンなら、このターン終了時の資産情報を公開
    if not is_practice and period != (TEST_NUM_PERIODS if TEST_MODE else get_num_periods_for_cursor(c)):

        c.execute("SELECT published_period, published_wealths FROM room_state WHERE id = 1")
        pub_row = c.fetchone()
        pub_periods = json.loads(pub_row[0]) if pub_row[0] and pub_row[0].startswith("{") else {}
        pub_wealths = json.loads(pub_row[1]) if pub_row[1] and pub_row[1].startswith("{") else {}
        for participant_id, schedule in high_periods.items():
            if period in schedule:
                pub_periods[participant_id] = period
                pub_wealths[participant_id] = group_wealths_after
        c.execute("UPDATE room_state SET published_period = ?, published_wealths = ? WHERE id = 1",
                  (json.dumps(pub_periods), json.dumps(pub_wealths)))

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
    if not is_practice:
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
            phase = ?,
            num_invested = ?,
            num_success = ?,
            num_failed = ?,
            num_not_invested = ?
        WHERE id = 1
        """,
        (
            next_phase,
            num_invested,
            num_success,
            num_failed,
            num_not_invested
        )
    )

    conn.commit()
    conn.close()

def get_num_periods_for_cursor(c):
    c.execute("SELECT num_periods FROM room_state WHERE id = 1")
    return c.fetchone()[0]


def advance_to_next_period():
    conn = connect_db()
    c = conn.cursor()

    # 次のターンへ進める
    c.execute(
        """
        UPDATE room_state
        SET
            period = period + 1,
            phase = 'decision',
            num_invested = NULL,
            num_success = NULL,
            num_failed = NULL,
            num_not_invested = NULL
        WHERE id = 1
        """
    )

    # 各Playerの回答状態をリセット
    c.execute(
        """
        UPDATE players
        SET
            current_choice = NULL,
            response_time = NULL,
            has_submitted = 0,
            success = NULL,
            result_confirmed = 0
        """
    )

    conn.commit()
    conn.close()

def enter_game_break():
    """Show rest/readiness only after every participant confirms final results."""
    conn = connect_db()
    c = conn.cursor()
    c.execute("""
        UPDATE room_state SET phase = 'game_break'
        WHERE id = 1 AND phase = 'final_result'
          AND (SELECT COUNT(*) FROM players WHERE result_confirmed = 1)
              = (SELECT COUNT(*) FROM players)
          AND (SELECT COUNT(*) FROM players) > 0
    """)
    conn.commit()
    conn.close()


def mark_game_ready(player_id):
    conn = connect_db()
    c = conn.cursor()
    c.execute("""
        UPDATE players SET game_ready = 1
        WHERE player_id = ? AND game_ready = 0
          AND EXISTS (SELECT 1 FROM room_state WHERE id = 1 AND phase = 'game_break')
    """, (player_id,))
    conn.commit()
    conn.close()


def start_next_game(initial_wealth, high_periods, num_periods):
    conn = connect_db()
    c = conn.cursor()

    c.execute("""
        SELECT phase,
               (SELECT COUNT(*) FROM players),
               (SELECT COUNT(*) FROM players WHERE game_ready = 1)
        FROM room_state WHERE id = 1
    """)
    state = c.fetchone()
    if state is None or state[0] != "game_break" or state[1] == 0 or state[1] != state[2]:
        conn.close()
        return False

    # 実験全体を次のゲームへ
    c.execute(
        """
        UPDATE room_state
        SET
            game = game + 1,
            period = 1,
            phase = 'decision',
            high_periods = ?,
            num_periods = ?,
            published_period = NULL,
            published_wealths = NULL,
            num_invested = NULL,
            num_success = NULL,
            num_failed = NULL,
            num_not_invested = NULL
        WHERE id = 1
        """,
        (json.dumps(high_periods), num_periods)
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
            success = NULL,
            result_confirmed = 0,
            game_ready = 0,
            game_start_ack = 0
        """,
        (initial_wealth,)
    )

    conn.commit()
    conn.close()

def end_experiment():
    conn = connect_db()
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
    conn = connect_db()
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
    conn = connect_db()
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

def get_period_log(game, player_id, period):
    conn = connect_db()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute(
        """
        SELECT *
        FROM period_logs
        WHERE
            game = ?
            AND player_id = ?
            AND period = ?
        """,
        (
            game,
            player_id,
            period
        )
    )

    row = c.fetchone()
    conn.close()

    if row is None:
        return None

    return dict(row)

def get_period_logs():
    conn = connect_db()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute(
        """
        SELECT *
        FROM period_logs
        ORDER BY game, period, player_number
        """
    )

    rows = c.fetchall()
    conn.close()

    return [dict(row) for row in rows]

def confirm_result(player_id, result_review_time=None):
    """Confirm the current result, saving its review time only once."""
    conn = connect_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        c = conn.cursor()
        c.execute("""
            SELECT game, period, phase FROM room_state WHERE id = 1
        """)
        room = c.fetchone()
        if room is None or room[2] not in ("result", "final_result", "practice_result"):
            conn.rollback()
            return False

        c.execute("""
            UPDATE players SET result_confirmed = 1
            WHERE player_id = ? AND result_confirmed = 0
        """, (player_id,))
        updated = c.rowcount == 1
        if updated and room[2] in ("result", "final_result") and result_review_time is not None:
            c.execute("""
                UPDATE period_logs SET result_review_time = ?
                WHERE game = ? AND period = ? AND player_id = ?
                  AND result_review_time IS NULL
            """, (max(0.0, float(result_review_time)), room[0], room[1], player_id))
        conn.commit()
        return updated
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def start_explanation():
    conn = connect_db()
    c = conn.cursor()

    c.execute("""
        UPDATE room_state
        SET phase = 'explanation'
        WHERE id = 1
          AND is_started = 0
          AND phase = 'decision'
    """)

    conn.commit()
    conn.close()


def confirm_explanation(player_id):
    conn = connect_db()
    c = conn.cursor()

    c.execute("""
        UPDATE players
        SET explanation_confirmed = 1
        WHERE player_id = ?
          AND EXISTS (
              SELECT 1 FROM room_state
              WHERE id = 1
                AND phase = 'explanation'
          )
    """, (player_id,))

    conn.commit()
    conn.close()


def get_explanation_confirmed_count():
    conn = connect_db()
    c = conn.cursor()

    c.execute("""
        SELECT COUNT(*)
        FROM players
        WHERE explanation_confirmed = 1
    """)

    count = c.fetchone()[0]
    conn.close()

    return count

def start_practice():
    conn = connect_db()
    c = conn.cursor()

    c.execute("""
        UPDATE room_state
        SET phase = 'practice_decision'
        WHERE id = 1
          AND is_started = 0
          AND (
              phase = 'decision'
              OR (phase = 'explanation' AND (
                  SELECT COUNT(*) FROM players WHERE explanation_confirmed = 1
              ) = (SELECT COUNT(*) FROM players))
          )
    """)

    conn.commit()
    conn.close()

def submit_practice_choice(player_id, choice, response_time):
    if choice not in ("Invest", "Not Invest"):
        return

    conn = connect_db()
    c = conn.cursor()

    c.execute("""
        UPDATE players
        SET
            current_choice = ?,
            response_time = ?,
            has_submitted = 1
        WHERE player_id = ?
          AND has_submitted = 0
          AND EXISTS (
              SELECT 1
              FROM room_state
              WHERE id = 1
                AND phase = 'practice_decision'
                AND is_started = 0
          )
    """, (choice, response_time, player_id))

    conn.commit()
    conn.close()

def finalize_practice(success_capacity, return_multiplier):
    conn = connect_db()
    c = conn.cursor()

    c.execute("""
        SELECT
            (SELECT phase FROM room_state WHERE id = 1),
            (SELECT COUNT(*) FROM players),
            (SELECT COUNT(*) FROM players WHERE has_submitted = 1)
    """)

    phase, player_count, submitted_count = c.fetchone()
    conn.close()

    if (
        phase != "practice_decision"
        or player_count == 0
        or submitted_count != player_count
    ):
        return

    finalize_period(success_capacity, return_multiplier)

def finish_practice():
    conn = connect_db()
    c = conn.cursor()

    c.execute("""
        UPDATE room_state
        SET phase = 'practice_waiting'
        WHERE id = 1
          AND phase = 'practice_result'
          AND is_started = 0
          AND (
              SELECT COUNT(*)
              FROM players
              WHERE result_confirmed = 1
          ) = (
              SELECT COUNT(*)
              FROM players
          )
          AND (SELECT COUNT(*) FROM players) > 0
    """)

    conn.commit()
    conn.close()

def start_main_after_practice(initial_wealth, high_periods, num_periods):
    conn = connect_db()
    c = conn.cursor()

    # 練習終了後の待機状態であることを確認
    c.execute("""
        SELECT phase, is_started
        FROM room_state
        WHERE id = 1
    """)

    room = c.fetchone()

    if room is None or room[0] != "practice_waiting" or room[1]:
        conn.close()
        return

    # 全参加者の状態を初期化
    c.execute("""
        UPDATE players
        SET
            wealth = ?,
            current_choice = NULL,
            response_time = NULL,
            has_submitted = 0,
            success = NULL,
            result_confirmed = 0,
            game_start_ack = 0
    """, (initial_wealth,))

    # 本番用の実験状態を初期化
    c.execute("""
        UPDATE room_state
        SET
            game = 1,
            period = 1,
            phase = 'decision',
            is_started = 1,
            experiment_over = 0,
            high_periods = ?,
            num_periods = ?,
            published_period = NULL,
            published_wealths = NULL,
            num_invested = NULL,
            num_success = NULL,
            num_failed = NULL,
            num_not_invested = NULL
        WHERE id = 1
    """, (json.dumps(high_periods), num_periods))

    conn.commit()
    conn.close()