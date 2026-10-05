import streamlit as st
import random
import matplotlib.pyplot as plt
import pandas as pd
import time
import db
from collections import Counter
from matplotlib.lines import Line2D

plt.rcParams["font.family"] = "Yu Gothic"

NUM_PERIODS = 3
NUM_PLAYERS = 8
SUCCESS_CAPACITY = 4

INITIAL_WEALTH = 500
INTEREST_RATE = 0.10
RETURN_MULTIPLIER = 1.6

MIN_HIGH_INTERVAL = 3
MAX_HIGH_INTERVAL = 7

db.init_db()

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

    return high_periods

def plot_wealth_distribution(wealths):

    other_wealths = wealths[1:]
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
        wealths[0] + bar_width / 2,
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

if "period" not in st.session_state:
    st.session_state.period = 1
    st.session_state.wealths = [INITIAL_WEALTH] * NUM_PLAYERS
    st.session_state.screen = "decision"
    st.session_state.choice = None
    st.session_state.success = None
    st.session_state.high_periods = generate_high_periods()
    st.session_state.last_published_wealth = None
    st.session_state.last_published_rank = None
    st.session_state.last_published_gap = None
    st.session_state.logs = []

if "decision_start_time" not in st.session_state:
    st.session_state.decision_start_time = None

if "game" not in st.session_state:
    st.session_state.game = 1

if "wait_reason" not in st.session_state:
    st.session_state.wait_reason = None

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

if not room["is_started"]:

    players = db.get_all_players()

    st.subheader("実験開始待機")

    if st.session_state.is_admin:

        st.write("管理者モード")
        st.write(f"現在の参加者：{len(players)} / {NUM_PLAYERS}")

        for player in players:
            st.write(
                f"Player {player['player_number']}："
                f"{player['player_id']}"
            )

        st.divider()

        if len(players) == NUM_PLAYERS:

            if st.button(
                "実験を開始",
                type="primary"
            ):
                high_periods = generate_high_periods()

                db.set_room_started(high_periods)

                st.rerun()

        else:
            st.info(
                f"あと {NUM_PLAYERS - len(players)} 人の参加を待っています。"
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
            f"現在の参加者：{len(players)} / {NUM_PLAYERS}"
        )

    time.sleep(2)
    st.rerun()

if st.session_state.screen == "decision":

    if st.session_state.decision_start_time is None:
        st.session_state.decision_start_time = time.perf_counter()

    period = st.session_state.period
    wealth = st.session_state.wealths[0]
    investment = wealth * INTEREST_RATE

    if period in st.session_state.high_periods:
        visibility_condition = "HIGH"
    else:
        visibility_condition = "LOW"

    st.session_state.visibility_condition = visibility_condition

    past_highs = [
        high_period
        for high_period in st.session_state.high_periods
        if high_period <= period
    ]

    future_highs = [
        high_period
        for high_period in st.session_state.high_periods
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
            for other_wealth in st.session_state.wealths
        )
        for player_wealth in st.session_state.wealths
    ]

    # 判断前の8人の資産Gap
    top_wealth_before = max(st.session_state.wealths)

    wealth_gaps_before = [
        top_wealth_before - player_wealth
        for player_wealth in st.session_state.wealths
    ]

    # Player 1自身のGap
    wealth_gap_before = wealth_gaps_before[0]

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
    if st.session_state.last_published_wealth is None:

        st.write("資産情報はまだ公開されていません。")

        if turns_to_end == 0:
            st.write("このターンが最終ターンです。")
    
        elif time_to_high == 0:
            st.write("このターンの終了後に資産情報が公開されます。")

        elif time_to_high is not None:
            st.write(
                f"資産情報の公開まで：あと {time_to_high} ターン"
            )

        else:
            st.write(
                f"実験終了まで：あと {turns_to_end} ターン"
            )

    else:
        if visibility_condition == "HIGH":
            if len(past_highs) == 1:
                st.markdown("**資産情報が公開されました。**")
            else:
                st.markdown("**資産情報が更新されました。**")

        else:
            st.write(
                f"表示中の資産情報：ターン {last_high}終了時"
            )
        
        if turns_to_end == 0:
            st.write("このターンが最終ターンです。")

        elif time_to_high == 0:
            st.write("このターンの終了後に資産情報が更新されます。")

        elif time_to_high is not None:
            st.write(
                f"次回の資産情報更新まで：あと {time_to_high} ターン"
            )

        else:
            st.write(
                f"実験終了まで：あと {turns_to_end} ターン"
            )
    
        if st.session_state.last_published_wealth is not None:
            plot_wealth_distribution(
                st.session_state.last_published_wealth
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

        st.session_state.response_time = response_time

        # Player 1（人間）の選択
        choices = [player_choice]

        # Player 2～8の仮の選択
        for i in range(1, NUM_PLAYERS):
            ai_choice = random.choice(["Invest", "Not Invest"])
            choices.append(ai_choice)

        # 投資したPlayerの番号を取得
        investors = [
            i for i, choice in enumerate(choices)
            if choice == "Invest"
        ]

        # 成功者を決定
        if len(investors) <= SUCCESS_CAPACITY:
            successful_investors = investors
        else:
            successful_investors = random.sample(
                investors,
                SUCCESS_CAPACITY
            )

        new_wealths = []

        for i in range(NUM_PLAYERS):

            player_wealth = st.session_state.wealths[i]
            player_investment = player_wealth * INTEREST_RATE
            player_choice_i = choices[i]

            if player_choice_i == "Not Invest":
                player_wealth_after = player_wealth + player_investment

            elif i in successful_investors:
                player_wealth_after = (
                    player_wealth
                    + player_investment * RETURN_MULTIPLIER
                )

            else:
                player_wealth_after = player_wealth

            new_wealths.append(player_wealth_after)

        ranks_after = [
            1 + sum(
                other_wealth > player_wealth
                for other_wealth in new_wealths
            )
            for player_wealth in new_wealths
        ]

        top_wealth_after = max(new_wealths)

        wealth_gaps_after = [
            top_wealth_after - player_wealth
            for player_wealth in new_wealths
        ]

        wealth_gap_after = wealth_gaps_after[0]

        num_invested = choices.count("Invest")
        num_success = len(successful_investors)
        num_failed = num_invested - num_success
        num_not_invested = choices.count("Not Invest")

        # 後の結果画面で使えるように保存
        st.session_state.choices = choices
        st.session_state.successful_investors = successful_investors
        st.session_state.new_wealths = new_wealths

        st.session_state.choice = player_choice

        player_success = (
            0 in successful_investors
            if player_choice == "Invest"
            else None
        )

        st.session_state.success = player_success

        log = {
            "Game": st.session_state.game,
            "Session": 1,
            "Player": 1,
            "Period": period,

            "Visibility_Condition": visibility_condition,
            "Time_Since_High": time_since_high,
            "Time_To_High": time_to_high,

            "Wealth_Before": wealth,
            "Rank_Before": ranks_before[0],
            "Wealth_Gap_Before": wealth_gap_before,
            "Endowment": investment,

            "Last_Published_Wealth": (
                st.session_state.last_published_wealth[0]
                if st.session_state.last_published_wealth is not None
                else None
            ),

            "Last_Published_Rank": (
                st.session_state.last_published_rank[0]
                if st.session_state.last_published_rank is not None
                else None
            ),

            "Last_Published_Gap": (
                st.session_state.last_published_gap[0]
                if st.session_state.last_published_gap is not None
                else None
            ),

            "Choice": player_choice,
            "Response_Time": response_time,

            "Result": player_success,

            "Wealth_After": new_wealths[0],
            "Rank_After": ranks_after[0],
            "Wealth_Gap_After": wealth_gap_after,

            "Num_Invested": num_invested,
            "Num_Success": num_success,
            "Num_Failed": num_failed,
            "Num_Not_Invested": num_not_invested,

            "Group_Wealths_Before": st.session_state.wealths.copy(),
            "Group_Wealths_After": new_wealths.copy()
        }

        st.session_state.logs.append(log)

        # HIGHのとき、今回の結果を公開情報として保存
        if visibility_condition == "HIGH":

            st.session_state.last_published_wealth = (
                new_wealths.copy()
            )

            st.session_state.last_published_rank = (
                ranks_after.copy()
            )

            st.session_state.last_published_gap = (
                wealth_gaps_after.copy()
            )
    

        st.session_state.screen = "result"
        st.rerun()

elif st.session_state.screen == "result":

    period = st.session_state.period
    wealth = st.session_state.wealths[0]
    investment = wealth * INTEREST_RATE

    wealth_after = st.session_state.new_wealths[0]
    acquired_assets = wealth_after - wealth

    choices = st.session_state.choices
    successful_investors = st.session_state.successful_investors

    num_invested = choices.count("Invest")
    num_success = len(successful_investors)
    num_failed = num_invested - num_success
    num_not_invested = choices.count("Not Invest")

    st.subheader(f"結果 （ターン{period}/{NUM_PERIODS}）")

    st.write(
        f"あなたは Player {st.session_state.player_number} です。"
    )

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    if st.session_state.choice == "Invest":

        if st.session_state.success:
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

    st.markdown(result_text, unsafe_allow_html=True)

    details_text = f"""
    あなたの投資額：{investment:,.0f} ポイント<br>
    投資した人数：{num_invested} 人<br>
    成功した人数：{num_success} 人<br>
    失敗した人数：{num_failed} 人<br>
    投資しなかった人数：{num_not_invested} 人
    """

    st.markdown(details_text, unsafe_allow_html=True)

    st.divider()

    assets_text = f"""
    今期獲得した資産：{acquired_assets:,.0f} ポイント<br>
    <span style="color: red;">現在の総資産：{wealth_after:,.0f} ポイント</span>
    """

    st.markdown(assets_text, unsafe_allow_html=True)

    if st.session_state.visibility_condition == "HIGH":
        plot_wealth_distribution(
            st.session_state.new_wealths
        )
            
    if st.button("次へ", type="primary"):

        st.session_state.wealths = st.session_state.new_wealths

        if period == NUM_PERIODS:
            st.session_state.screen = "wait"
            st.session_state.wait_reason = "game_end"

        else:
            st.session_state.period += 1
            st.session_state.screen = "decision"

        st.session_state.choice = None
        st.session_state.success = None
        st.session_state.decision_start_time = None

        st.rerun()

elif st.session_state.screen == "wait":

    if st.session_state.wait_reason == "game_end":

        st.subheader(
            f"ゲーム {st.session_state.game} 終了"
        )

        st.write(
            "次の案内があるまで、そのままお待ちください。"
        )

        st.divider()

        st.write("管理者操作")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("次のゲームを開始"):

                st.session_state.game += 1
                st.session_state.period = 1

                st.session_state.wealths = (
                    [INITIAL_WEALTH] * NUM_PLAYERS
                )

                st.session_state.high_periods = (
                    generate_high_periods()
                )

                st.session_state.last_published_wealth = None
                st.session_state.last_published_rank = None
                st.session_state.last_published_gap = None

                st.session_state.choice = None
                st.session_state.success = None
                st.session_state.decision_start_time = None

                st.session_state.wait_reason = None
                st.session_state.screen = "decision"

                st.rerun()

        with col2:
            if st.button("実験を終了"):

                st.session_state.wait_reason = None
                st.session_state.screen = "final_end"

                st.rerun()

elif st.session_state.screen == "final_end":

    st.subheader("実験終了")

    st.write("これで実験は終了です。")
    st.write("ご参加ありがとうございました。")

    log_df = pd.DataFrame(
        st.session_state.logs
    )

    csv = log_df.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        label="CSVをダウンロード",
        data=csv,
        file_name="experiment_log.csv",
        mime="text/csv"
    )