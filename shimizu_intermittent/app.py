import streamlit as st
import random
import matplotlib.pyplot as plt
import pandas as pd
import time
import db
from collections import Counter
from matplotlib.lines import Line2D

from config import (
    NUM_PERIODS,
    NUM_PLAYERS,
    SUCCESS_CAPACITY,
    INITIAL_WEALTH,
    INTEREST_RATE,
    RETURN_MULTIPLIER,
    MIN_HIGH_INTERVAL,
    MAX_HIGH_INTERVAL,
    TEST_MODE,
    TEST_NUM_PLAYERS,
)

required_players = (
    TEST_NUM_PLAYERS
    if TEST_MODE
    else NUM_PLAYERS
)

db.init_db()

plt.rcParams["font.family"] = "Yu Gothic"

st.set_page_config(
    page_title="反復投資実験",
    layout="centered"
)

st.markdown(
    """
    <style>
    div.stButton > button[kind="primary"] {
        background-color: #1677FF;
        border-color: #1677FF;
        color: white;
    }

    div.stButton > button[kind="primary"]:hover {
        background-color: #0958D9;
        border-color: #0958D9;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True
)

def render_brand_badge():
    st.markdown(
        """
        <style>
        .brand-badge {
            position: fixed;
            top: 70px;
            right: 25px;
            z-index: 9999;

            font-size: 0.85em;
            font-weight: 600;
            color: #555;
        }
        </style>

        <div class="brand-badge">
            🌙 YUTSUKI LAB EXPERIMENT
        </div>
        """,
        unsafe_allow_html=True
    )

def generate_high_periods():
    high_periods = []

    first_high = random.randint(
        MIN_HIGH_INTERVAL,
        MAX_HIGH_INTERVAL
    )

    high_periods.append(first_high)
    current_period = first_high

    while True:
        interval = random.randint(
            MIN_HIGH_INTERVAL,
            MAX_HIGH_INTERVAL
        )

        next_high = current_period + interval
        high_periods.append(next_high)

        if next_high > NUM_PERIODS:
            break

        current_period = next_high

    return [
        period
        for period in high_periods
        if period != NUM_PERIODS
    ]

def plot_wealth_distribution(wealths, my_index):

    my_wealth = wealths[my_index]

    other_wealths = [
        wealth
        for i, wealth in enumerate(wealths)
        if i != my_index
    ]

    wealth_counts = Counter(other_wealths)

    fig, ax = plt.subplots()

    bar_width = 4

    # 他の参加者
    ax.bar(
        [x - bar_width / 2 for x in wealth_counts.keys()],
        wealth_counts.values(),
        width=bar_width,
        color="tab:blue"
    )

    # あなた
    ax.bar(
        my_wealth + bar_width / 2,
        1,
        width=bar_width,
        color="tab:orange"
    )

    ax.set_xlabel("総資産")
    ax.set_ylabel("人数")
    ax.set_title("現在の総資産分布")

    ax.set_yticks([0, 2, 4, 6, 8])
    ax.set_ylim(0, 8)

    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.grid(
        axis="y",
        alpha=0.2
    )

    ax.set_axisbelow(True)

    ax.tick_params(
        axis="both",
        length=0
    )

    legend_elements = [
        Line2D(
            [0], [0],
            marker="o",
            linestyle="None",
            markersize=5,
            markerfacecolor="tab:blue",
            markeredgecolor="tab:blue",
            label="他の参加者"
        ),
        Line2D(
            [0], [0],
            marker="o",
            linestyle="None",
            markersize=5,
            markerfacecolor="tab:orange",
            markeredgecolor="tab:orange",
            label="あなた"
        )
    ]

    ax.legend(
        handles=legend_elements,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=2,
        frameon=False,
        fontsize=8
    )

    st.pyplot(fig)

@st.fragment(run_every=2)
def wait_for_phase_change(current_phase):

    room_now = db.get_room_state()

    if room_now["phase"] != current_phase:
        st.rerun()

@st.fragment(run_every=2)
def watch_admin_state():

    room_now = db.get_room_state()
    players_now = db.get_all_players()

    submitted_count_now = sum(
        player["has_submitted"]
        for player in players_now
    )

    confirmed_count_now = sum(
        player["result_confirmed"]
        for player in players_now
    )

    current_key = (
        room_now["game"],
        room_now["period"],
        room_now["phase"],
        submitted_count_now,
        confirmed_count_now
    )

    if "admin_state_key" not in st.session_state:
        st.session_state.admin_state_key = current_key

    elif st.session_state.admin_state_key != current_key:
        st.session_state.admin_state_key = current_key
        st.rerun()

if "screen" not in st.session_state:
    st.session_state.screen = "decision"

if "decision_start_time" not in st.session_state:
    st.session_state.decision_start_time = None

render_brand_badge()

if "my_id" not in st.session_state:
    st.session_state.my_id = None

if "player_number" not in st.session_state:
    st.session_state.player_number = None

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

if st.session_state.my_id is None:

    st.subheader("参加者ログイン")

    player_id = st.text_input(
        "参加者IDを入力してください",
        placeholder="例：P01"
    )

    if st.button("ログイン", type="primary"):

        player_id = player_id.strip()

        if player_id == "":
            st.error("参加者IDを入力してください。")

        elif player_id.lower() == "admin":
            st.session_state.my_id = "admin"
            st.session_state.is_admin = True
            st.rerun()

        else:
            player_number = db.register_player(
                player_id,
                INITIAL_WEALTH
            )

            if player_number is None:
                st.error(
                    "参加人数が上限の8人に達しています。"
                )

            else:
                st.session_state.my_id = player_id
                st.session_state.player_number = player_number
                st.session_state.is_admin = False
                st.rerun()

    st.stop()

room = db.get_room_state()

# DBのフェーズに参加者画面を同期
if not st.session_state.is_admin:

    player = db.get_player(
        st.session_state.my_id
    )

    if room["phase"] == "finished":
        st.session_state.screen = "final_end"

    elif room["phase"] == "result":
        st.session_state.screen = "result"

    elif room["phase"] == "decision":

        if player["has_submitted"]:
            st.session_state.screen = "waiting_submission"
        else:
            st.session_state.screen = "decision"

if not room["is_started"]:

    players = db.get_all_players()

    st.subheader("実験開始待機")

    if st.session_state.is_admin:

        st.write("管理者モード")
        st.write(f"現在の参加者：{len(players)} / {required_players}")

        for player in players:
            st.write(
                f"Player {player['player_number']}："
                f"{player['player_id']}"
            )

        st.divider()

        if len(players) == required_players:

            if st.button(
                "実験を開始",
                type="primary"
            ):
                high_periods = generate_high_periods()

                db.set_room_started(high_periods)

                st.rerun()

        else:
            st.info(
                f"あと {required_players - len(players)} 人の参加を待っています。"
            )

        if st.button("実験室をリセット"):
            db.reset_room()

            st.session_state.my_id = None
            st.session_state.player_number = None
            st.session_state.is_admin = False

            st.rerun()

    else:

        st.write(
            f"あなたは Player "
            f"{st.session_state.player_number} です。"
        )

        st.write(
            "他の参加者と実験開始を待っています。"
        )

        st.write(
            f"現在の参加者：{len(players)} / {required_players}"
        )

    time.sleep(2)
    st.rerun()

# 実験開始後の管理者画面
if room["is_started"] and st.session_state.is_admin:

    if room["experiment_over"]:

        st.subheader("実験終了")
        st.success("実験を終了しました。")

        logs = db.get_period_logs()

        if logs:
            log_df = pd.DataFrame(logs)

            csv = log_df.to_csv(
                index=False
            ).encode("utf-8-sig")

            st.download_button(
                label="実験ログCSVをダウンロード",
                data=csv,
                file_name="experiment_logs.csv",
                mime="text/csv"
            )

        if TEST_MODE:
            st.divider()

            if st.button("実験室をリセット"):
                db.reset_room()

                st.session_state.my_id = None
                st.session_state.player_number = None
                st.session_state.is_admin = False
                st.session_state.screen = "decision"
                st.session_state.decision_start_time = None

                st.rerun()

        st.stop()

    players = db.get_all_players()

    st.subheader("管理者画面")

    st.write(f"ゲーム：{room['game']}")
    st.write(f"ターン：{room['period']}")
    st.write(f"フェーズ：{room['phase']}")

    if TEST_MODE:
        if st.button("実験室をリセット"):
            db.reset_room()

            st.session_state.my_id = None
            st.session_state.player_number = None
            st.session_state.is_admin = False
            st.session_state.screen = "decision"
            st.session_state.decision_start_time = None

            st.rerun()

        st.divider()
        st.subheader("実験ログ")

        logs = db.get_period_logs()

        if logs:
            log_df = pd.DataFrame(logs)

            st.dataframe(
                log_df,
                use_container_width=True
            )

            csv = log_df.to_csv(
                index=False
            ).encode("utf-8-sig")

            st.download_button(
                label="CSVをダウンロード",
                data=csv,
                file_name="experiment_logs.csv",
                mime="text/csv"
            )

        else:
            st.write("ログはまだありません。")

    st.divider()

    st.write("提出状況")

    for player in players:

        if player["has_submitted"]:
            status = "提出済み"
        else:
            status = "未提出"

        st.write(
            f"Player {player['player_number']}：{status}"
        )

    submitted_count = sum(
        player["has_submitted"]
        for player in players
    )

    st.write(
        f"合計：{submitted_count}/{required_players}"
    )

    all_submitted = (
        len(players) == required_players
        and submitted_count == required_players
    )

    if room["phase"] == "decision":

        if all_submitted:

            st.success("全員の回答が提出されました。")

            if st.button(
                "結果を確定",
                type="primary"
            ):
                db.finalize_period(
                    SUCCESS_CAPACITY,
                    RETURN_MULTIPLIER
                )
                st.rerun()


    elif room["phase"] == "result":

        confirmed_count = sum(
            player["result_confirmed"]
            for player in players
        )

        st.write(
            f"結果確認済み：{confirmed_count}/{required_players} 人"
        )

        if confirmed_count == required_players:
            st.success("全員が結果を確認しました。")
        else:
            st.info("結果を確認していない参加者がいます。")

        st.success("結果を確定しました。")
        st.write("参加者は結果画面を確認中です。")

        if room["period"] < NUM_PERIODS:

            if st.button(
                "次のターンへ",
                type="primary"
            ):
                db.advance_to_next_period()
                st.rerun()

        else:

            st.success(
                f"ゲーム {room['game']} の全ターンが終了しました。"
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button(
                    "次のゲームを開始",
                    type="primary"
                ):
                    new_high_periods = generate_high_periods()

                    db.start_next_game(
                        INITIAL_WEALTH,
                        new_high_periods
                    )

                    st.rerun()

            with col2:
                if st.button("実験を終了"):

                    db.end_experiment()

                    st.rerun()

# 管理者はここでDBの変化を監視
if st.session_state.is_admin:
    watch_admin_state()
    st.stop()

if st.session_state.screen == "decision":

    period = room["period"]
    wealth = player["wealth"]
    high_periods = room["high_periods"]

    published_period = room["published_period"]
    published_wealths = room["published_wealths"]

    if st.session_state.decision_start_time is None:
        st.session_state.decision_start_time = time.perf_counter()

    room = db.get_room_state()

    player = db.get_player(
        st.session_state.my_id
    )

    players = db.get_all_players()

    period = room["period"]
    wealth = player["wealth"]

    wealths = [
        player_data["wealth"]
        for player_data in players
    ]

    investment = wealth * INTEREST_RATE

    if period in high_periods:
        visibility_condition = "HIGH"
    else:
        visibility_condition = "LOW"

    st.session_state.visibility_condition = visibility_condition

    past_highs = [
        high_period
        for high_period in high_periods
        if high_period <= period
    ]

    future_highs = [
        high_period
        for high_period in high_periods
        if high_period >= period
    ]

    if past_highs:
        last_high = max(past_highs)
        time_since_high = period - last_high
    else:
        last_high = None
        time_since_high = None

    next_high = min(future_highs)

    if next_high <= NUM_PERIODS:
        time_to_high = next_high - period
    else:
        time_to_high = None

    # 判断前の8人の順位
    ranks_before = [
        1 + sum(
            other_wealth > player_wealth
            for other_wealth in wealths
        )
        for player_wealth in wealths
    ]

    # 判断前の8人の資産Gap
    top_wealth_before = max(wealths)

    wealth_gaps_before = [
        top_wealth_before - player_wealth
        for player_wealth in wealths
    ]

    # Player 1自身のGap
    my_index = player["player_number"] - 1

    rank_before = ranks_before[my_index]
    wealth_gap_before = wealth_gaps_before[my_index]

    # 最後に公開された資産情報から、自分の公開情報を計算
    if published_wealths is not None:

        published_ranks = [
            1 + sum(
                other_wealth > player_wealth
                for other_wealth in published_wealths
            )
            for player_wealth in published_wealths
        ]

        published_top_wealth = max(published_wealths)

        published_gaps = [
            published_top_wealth - player_wealth
            for player_wealth in published_wealths
        ]

        last_published_wealth = published_wealths[my_index]
        last_published_rank = published_ranks[my_index]
        last_published_gap = published_gaps[my_index]

    else:

        last_published_wealth = None
        last_published_rank = None
        last_published_gap = None

    db.create_period_log(
        game=room["game"],
        player_id=st.session_state.my_id,
        player_number=player["player_number"],
        period=period,
        visibility_condition=visibility_condition,
        time_since_high=time_since_high,
        time_to_high=time_to_high,
        wealth_before=wealth,
        rank_before=rank_before,
        wealth_gap_before=wealth_gap_before,
        endowment=investment,
        last_published_wealth=last_published_wealth,
        last_published_rank=last_published_rank,
        last_published_gap=last_published_gap,
        group_wealths_before=wealths
    )

    st.subheader(f"反復投資実験 （ターン{period}/{NUM_PERIODS}）")

    st.write(
        f"あなたは Player {st.session_state.player_number} です。"
    )

    st.markdown(
        "<div style='height: 20px;'></div>",
        unsafe_allow_html=True
    )

    decision_info = f"""
    現在の総資産：{wealth:,.0f} ポイント<br>
    今回の投資額：{investment:,.0f} ポイント
    """

    st.markdown(decision_info, unsafe_allow_html=True)

    st.divider()

    turns_to_end = NUM_PERIODS - period

    # 資産情報の公開
    if published_wealths is None:

        st.write("資産情報はまだ公開されていません。")

        if turns_to_end == 0:
            st.write("このターンが最終ターンです.")

        elif time_to_high == 0:
            st.write(
                "このターンの終了後に資産情報が公開されます。"
            )

        elif time_to_high is not None:
            st.write(
                f"資産情報の公開まで：あと {time_to_high} ターン"
            )

        else:
            st.write(
                f"実験終了まで：あと {turns_to_end} ターン"
            )

    else:

        st.write(
            f"表示中の資産情報：ターン {published_period} 終了時"
        )

        if turns_to_end == 0:
            st.write("このターンが最終ターンです。")

        elif time_to_high == 0:
            st.write(
                "このターンの終了後に資産情報が更新されます。"
            )

        elif time_to_high is not None:
            st.write(
                f"次回の資産情報更新まで：あと {time_to_high} ターン"
            )

        else:
            st.write(
                f"実験終了まで：あと {turns_to_end} ターン"
            )

        plot_wealth_distribution(
            published_wealths,
            my_index
        )
    
    st.divider()

    st.write("今回、投資しますか？")

    col1, col2 = st.columns(2)

    with col1:
        invest_button = st.button(
            "投資する",
            use_container_width=True
        )

    with col2:
        no_invest_button = st.button(
            "投資しない",
            use_container_width=True
        )

    if invest_button:
        player_choice = "Invest"

    elif no_invest_button:
        player_choice = "Not Invest"

    else:
        player_choice = None

    if player_choice is not None:

        response_time = (
            time.perf_counter()
            - st.session_state.decision_start_time
        )

        db.submit_choice(
            st.session_state.my_id,
            player_choice,
            response_time
        )

        db.update_period_log_choice(
            game=room["game"],
            player_id=st.session_state.my_id,
            period=period,
            choice=player_choice,
            response_time=response_time
        )

        st.session_state.decision_start_time = None
        st.session_state.screen = "waiting_submission"
        st.rerun()

elif st.session_state.screen == "waiting_submission":

    room = db.get_room_state()

    if room["phase"] == "result":
        st.session_state.screen = "result"
        st.rerun()

    st.subheader(
        f"ターン {room['period']}/{NUM_PERIODS}"
    )

    st.write(
        f"Player {st.session_state.player_number}：提出済み"
    )

    st.write(
        "他の参加者の回答を待っています。"
    )

    wait_for_phase_change("decision")

    st.stop()

elif st.session_state.screen == "result":

    room = db.get_room_state()
    player = db.get_player(st.session_state.my_id)

    period = room["period"]

    high_periods = room["high_periods"]
    published_period = room["published_period"]
    published_wealths = room["published_wealths"]

    is_high = period in high_periods
    my_index = player["player_number"] - 1

    player_number = player["player_number"]
    wealth_after = player["wealth"]
    choice = player["current_choice"]
    success = player["success"]

    period_log = db.get_period_log(
        room["game"],
        st.session_state.my_id,
        period
    )

    wealth_before = period_log["wealth_before"]
    investment = period_log["endowment"]

    acquired_assets = wealth_after - wealth_before

    investment = wealth_before * INTEREST_RATE
    acquired_assets = wealth_after - wealth_before

    st.subheader(
        f"結果 （ターン{period}/{NUM_PERIODS}）"
    )

    st.write(
        f"あなたは Player {player_number} です。"
    )

    st.markdown(
        "<div style='height: 20px;'></div>",
        unsafe_allow_html=True
    )

    if choice == "Invest":

        if success:
            result_text = """
            <b>あなたは投資しました。</b><br>
            <b>あなたの投資は成功しました。</b>
            """

        else:
            result_text = """
            <b>あなたは投資しました。</b><br>
            <b>あなたの投資は失敗しました。</b>
            """

    else:
        result_text = """
        <b>あなたは投資しませんでした。</b>
        """

    st.markdown(
        result_text,
        unsafe_allow_html=True
    )

    details_text = f"""
    あなたの投資額：{investment:,.0f} ポイント<br>
    投資した人数：{room["num_invested"]} 人<br>
    成功した人数：{room["num_success"]} 人<br>
    失敗した人数：{room["num_failed"]} 人<br>
    投資しなかった人数：{room["num_not_invested"]} 人
    """

    st.markdown(
        details_text,
        unsafe_allow_html=True
    )

    st.divider()

    assets_text = f"""
    今期獲得した資産：{acquired_assets:,.0f} ポイント<br>
    <span style="color: red;">
    現在の総資産：{wealth_after:,.0f} ポイント
    </span>
    """

    st.markdown(
        assets_text,
        unsafe_allow_html=True
    )

    # HIGHターンでは、確定した最新の資産情報を公開
    if is_high:

        st.divider()

        if published_period == period and published_wealths is not None:

            past_highs = [
                high_period
                for high_period in high_periods
                if high_period <= period
            ]

            if len(past_highs) == 1:
                st.markdown("**資産情報が公開されました。**")
            else:
                st.markdown("**資産情報が更新されました。**")

            st.write(
                f"表示中の資産情報：ターン {published_period} 終了時"
            )

            plot_wealth_distribution(
                published_wealths,
                my_index
            )

    st.divider()

    if player["result_confirmed"]:

        st.success("結果を確認済みです。")
        st.write("次の案内があるまでお待ちください。")

    else:

        st.write("結果を確認しましたか？")

        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("はい", type="primary"):
                db.confirm_result(st.session_state.my_id)
                st.rerun()

        with col2:
            if st.button("いいえ"):
                st.info("結果を確認してから「はい」を押してください。")

    wait_for_phase_change("result")

    st.stop()


elif st.session_state.screen == "final_result":

    room = db.get_room_state()
    player = db.get_player(st.session_state.my_id)
    players = db.get_all_players()

    # 最終総資産と最終順位を計算
    final_wealth = player["wealth"]

    final_rank = 1 + sum(
        other["wealth"] > final_wealth
        for other in players
    )

    # ゲーム終了画面のヘッダー
    st.caption(
        f"反復投資実験　|　GAME {room['game']}"
    )

    st.markdown(
        "<div style='height: 20px;'></div>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<h1 style='text-align:center;'>"
        "ゲーム終了"
        "</h1>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<p style='text-align:center; color:gray;'>"
        "すべてのターンが終了しました。"
        "</p>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<div style='height: 20px;'></div>",
        unsafe_allow_html=True
    )

    # 最終順位・最終総資産
    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            label="最終順位",
            value=f"{final_rank}位",
            help=f"{len(players)}人中"
        )
        st.caption(f"{len(players)}人中")

    with col2:
        st.metric(
            label="最終総資産",
            value=f"{final_wealth:,.0f}",
        )
        st.caption("ポイント")

    st.divider()

    # 結果確認
    if player["result_confirmed"]:

        st.success("結果を確認済みです。")
        st.write(
            "次の案内があるまでお待ちください。"
        )

    else:

        st.write("結果を確認しましたか？")

        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "はい",
                type="primary",
                use_container_width=True
            ):
                db.confirm_result(
                    st.session_state.my_id
                )
                st.rerun()

        with col2:
            if st.button(
                "いいえ",
                use_container_width=True
            ):
                st.info(
                    "結果を確認してから「はい」を押してください。"
                )

    # 管理者が次のゲームへ進めるまで待機
    wait_for_phase_change("final_result")

    st.stop()


elif st.session_state.screen == "final_end":

    st.subheader("実験終了")

    st.write("これで実験は終了です。")
    st.write("ご参加ありがとうございました。")

    st.stop()