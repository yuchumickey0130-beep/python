import streamlit as st
import random
import matplotlib.pyplot as plt
import pandas as pd
import time
import db

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
    TEST_NUM_PERIODS,
    EXPLANATION_MODE,
    PRACTICE_MODE,
    ALLOW_ADMIN_RESET,
)

required_players = (
    TEST_NUM_PLAYERS
    if TEST_MODE
    else NUM_PLAYERS
)

effective_num_periods = TEST_NUM_PERIODS if TEST_MODE else NUM_PERIODS

st.set_page_config(
    page_title="反復投資実験",
    layout="centered"
)

@st.cache_resource
def initialize_experiment_db():
    # Schema initialization must not run on every participant rerun.
    db.init_db()
    return True

initialize_experiment_db()

plt.rcParams["font.family"] = "Yu Gothic"

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
    intervals = list(range(
        MIN_HIGH_INTERVAL,
        MAX_HIGH_INTERVAL + 1
    ))

    random.shuffle(intervals)

    # 1ターン目の終了時に初回公開
    high_periods = [1]
    current_period = 1

    # 2〜6ターンの間隔を各1回使用
    for interval in intervals:
        current_period += interval
        high_periods.append(current_period)

    # 最終通常公開は21ターン目
    assert current_period == NUM_PERIODS - 1

    return high_periods

def plot_wealth_distribution(wealths, my_index):
    import numpy as np

    my_wealth = wealths[my_index]
    values = np.asarray(wealths, dtype=float)

    min_wealth = float(values.min())
    max_wealth = float(values.max())
    bin_width = 5.0

    # 著者提供のHighchartsと同様、全員を匿名で集計
    fig, ax = plt.subplots(figsize=(7, 5), dpi=100)

    if max_wealth > min_wealth:
        # 最小値を起点とする幅5の階級
        # 最大値がちょうど階級境界なら直前の階級に含める
        n_bins = max(
            1,
            int(np.ceil((max_wealth - min_wealth) / bin_width))
        )

        edges = min_wealth + np.arange(n_bins + 1) * bin_width

        counts, _ = np.histogram(values, bins=edges)

        ax.bar(
            edges[:-1],
            counts,
            width=bin_width,
            align="edge",
            color="#058DC7",
            edgecolor="none"
        )

        ax.set_xlim(min_wealth, max_wealth)

    else:
        # 原著では全員同額の場合、棒を表示しない
        ax.set_xlim(min_wealth - 5, max_wealth + 5)

    ax.set_title(
        "現在の総保有資産",
        fontsize=18,
        fontweight="normal"
    )
    ax.set_xlabel("総保有資産", fontsize=14)
    ax.set_ylabel("人数", fontsize=14)

    ax.yaxis.set_major_locator(
        plt.MaxNLocator(integer=True)
    )
    ax.set_ylim(bottom=0)

    if max_wealth > min_wealth:
        from matplotlib.ticker import MultipleLocator
        ax.xaxis.set_major_locator(MultipleLocator(10))

    ax.grid(axis="y", alpha=0.15)
    ax.set_axisbelow(True)

    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

def show_example_decision():
    st.caption("【説明用の画面例】実際の操作はできません")

    with st.container(border=True):
        st.subheader(f"反復投資実験（ターン3/{effective_num_periods}）")
        st.write("あなたは Player 1 です。")

        st.write("現在の総資産：500 ポイント")
        st.write("今回の投資額：50 ポイント")

        st.divider()

        st.write("今回、投資しますか？")

        col1, col2 = st.columns(2)

        with col1:
            st.button(
                "投資する",
                disabled=True,
                use_container_width=True,
                key="example_invest"
            )

        with col2:
            st.button(
                "投資しない",
                disabled=True,
                use_container_width=True,
                key="example_no_invest"
            )

def show_example_wealth_distribution():
    st.caption("【説明用の画面例】架空の資産データです")

    with st.container(border=True):
        st.write("表示中の資産情報：ターン2 終了時")
        st.write("次回の資産情報更新まで：あと2ターン")

        example_wealths = [
            500, 550, 550, 580,
            500, 600, 550, 580
        ]

        plot_wealth_distribution(
            example_wealths,
            my_index=0
        )

        st.info(
            "グラフには、参加者全員の総保有資産の分布が表示されます。"
            "資産情報が更新されない間は、"
            "前回公開された分布が表示されます。"
        )


@st.fragment(run_every=4)
def wait_for_phase_change(current_phase, current_game, current_period):

    room_now = db.get_room_state()
    if st.session_state.get("my_id") and not st.session_state.get("is_admin"):
        if db.get_player(st.session_state.my_id) is None:
            st.rerun(scope="app")

    if (
        room_now["phase"] != current_phase
        or room_now["game"] != current_game
        or room_now["period"] != current_period
    ):
        st.rerun(scope="app")


@st.fragment(run_every=4)
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
        confirmed_count_now,
        sum(player["game_ready"] for player in players_now)
    )

    if "admin_state_key" not in st.session_state:
        st.session_state.admin_state_key = current_key

    elif st.session_state.admin_state_key != current_key:
        st.session_state.admin_state_key = current_key
        st.rerun(scope="app")

if "screen" not in st.session_state:
    st.session_state.screen = "decision"

if "decision_start_time" not in st.session_state:
    st.session_state.decision_start_time = None

if "result_review_key" not in st.session_state:
    st.session_state.result_review_key = None
if "result_review_start_time" not in st.session_state:
    st.session_state.result_review_start_time = None
if "result_view_open_key" not in st.session_state:
    st.session_state.result_view_open_key = None

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
                    f"参加人数が上限の{required_players}人に達しています。"
                )

            else:
                st.session_state.my_id = player_id
                st.session_state.player_number = player_number
                st.session_state.is_admin = False
                st.rerun()

    st.stop()

room = db.get_room_state()

# 実験室がリセットされたら参加者をログイン画面へ戻す
if not st.session_state.is_admin:

    registered_player = db.get_player(
        st.session_state.my_id
    )

    if registered_player is None:

        st.session_state.my_id = None
        st.session_state.player_number = None
        st.session_state.screen = "decision"
        st.session_state.decision_start_time = None

        st.rerun()

# DBのフェーズに参加者画面を同期
if not st.session_state.is_admin:

    player = db.get_player(
        st.session_state.my_id
    )

    if room["phase"] == "finished":
        st.session_state.screen = "final_end"

    elif room["phase"] == "game_break":
        st.session_state.screen = "game_break"

    elif room["phase"] == "final_result":
        st.session_state.screen = "final_result"

    elif room["phase"] == "result":
        st.session_state.screen = "result"

    elif room["phase"] == "decision":

        if room["is_started"] and room["period"] == 1 and not player["game_start_ack"]:
            st.session_state.screen = "game_start_gate"
        elif player["has_submitted"]:
            st.session_state.screen = "waiting_submission"
        else:
            st.session_state.screen = "decision"

if not room["is_started"]:

    players = db.get_all_players()

    if st.session_state.is_admin:

        st.subheader("実験管理")

        st.write("管理者モード")
        st.write(f"現在の参加者：{len(players)} / {required_players}")

        for player in players:
            st.write(
                f"Player {player['player_number']}："
                f"{player['player_id']}"
            )

        st.divider()

        if room["phase"] == "decision":

            if len(players) == required_players:

                if EXPLANATION_MODE:
                    if st.button("説明開始", type="primary"):
                        db.start_explanation()
                        st.rerun()
                elif PRACTICE_MODE:
                    if st.button("練習を開始（説明を省略）", type="primary"):
                        db.start_practice()
                        st.rerun()
                else:
                    if st.button("本番を開始（説明・練習を省略）", type="primary"):
                        db.set_room_started(generate_high_periods())
                        st.rerun()

            else:
                st.info(
                    f"あと {required_players - len(players)} 人の参加を待っています。"
                )

        elif room["phase"] == "explanation":

            confirmed_count = db.get_explanation_confirmed_count()

            st.write(
                f"説明確認済み：{confirmed_count}/{required_players} 人"
            )

            if confirmed_count == required_players:
                st.success("全員が説明を確認しました。")
                st.info("質問タイムを実施してください。")

                if PRACTICE_MODE:
                    if st.button("練習を開始", type="primary"):
                        db.start_practice()
                        st.rerun()

                else:
                    if st.button("本番を開始", type="primary"):
                        high_periods = generate_high_periods()
                        db.set_room_started(high_periods)
                        st.rerun()

            else:
                st.info("参加者が説明を確認しています。")

        elif room["phase"] == "practice_decision":

            st.subheader("練習モード")

            submitted_count = sum(
                player["has_submitted"]
                for player in players
            )

            st.write(
                f"練習回答済み：{submitted_count}/{required_players} 人"
            )

            if submitted_count == required_players:
                st.success("全員の練習回答が揃いました。")

                if st.button("練習結果を確定", type="primary"):
                    db.finalize_practice(
                        SUCCESS_CAPACITY,
                        RETURN_MULTIPLIER
                    )
                    st.rerun()

            else:
                st.info("参加者の回答を待っています。")

        elif room["phase"] == "practice_result":

            practice_key = ("practice", room["game"], room["period"])
            if st.session_state.result_view_open_key != practice_key:
                st.subheader("練習結果が確定しました")
                st.write("準備ができたら「結果を確認する」を押してください。")
                if st.button("結果を確認する", type="primary", key="open_practice_result"):
                    st.session_state.result_view_open_key = practice_key
                    st.rerun()
                st.stop()

            st.subheader("練習結果")

            confirmed_count = sum(
                player["result_confirmed"]
                for player in players
            )

            st.write(
                f"結果確認済み：{confirmed_count}/{required_players} 人"
            )

            if confirmed_count == required_players:

                st.success("全員が練習結果を確認しました。")

                if st.button("練習を終了", type="primary"):
                    db.finish_practice()
                    st.rerun()

            st.write(f"投資した人数：{room['num_invested']} 人")
            st.write(f"成功した人数：{room['num_success']} 人")
            st.write(f"失敗した人数：{room['num_failed']} 人")
            st.write(f"投資しなかった人数：{room['num_not_invested']} 人")

            st.info("参加者が練習結果を確認しています。")

        elif room["phase"] == "practice_waiting":

            st.subheader("本番開始の準備")

            st.success("全員の練習が終了しました。")

            st.write(
                "本番では全参加者の資産を500ポイントに戻し、"
                "ゲーム1・ターン1から開始します。"
            )

            if st.button("本番を開始", type="primary"):

                high_periods = generate_high_periods()

                db.start_main_after_practice(
                    INITIAL_WEALTH,
                    high_periods
                )

                st.rerun()

        if "confirm_reset" not in st.session_state:
            st.session_state.confirm_reset = False

        if not st.session_state.confirm_reset:

            if st.button("実験室をリセット"):
                st.session_state.confirm_reset = True
                st.rerun()

        else:
            st.warning(
                "参加者情報と実験ログがすべて削除されます。"
                "この操作は取り消せません。"
            )

            st.write("本当に実験室をリセットしますか？")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("キャンセル"):
                    st.session_state.confirm_reset = False
                    st.rerun()

            with col2:
                if st.button("リセットを実行", type="primary"):
                    db.reset_room()

                    st.session_state.confirm_reset = False
                    st.session_state.my_id = None
                    st.session_state.player_number = None
                    st.session_state.is_admin = False
                    st.session_state.screen = "decision"
                    st.session_state.decision_start_time = None

                    st.rerun()

    else:

        if room["phase"] == "explanation":

            st.subheader("投資判断実験の説明")

            st.write(
                "この実験では、複数の参加者が繰り返し投資の判断を行います。"
                "以下のルールをよく読み、内容を理解してから実験に参加してください。"
            )

            st.markdown("### 1. 実験の基本ルール")

            st.markdown("""
    - この実験には、あなたを含めて8人が参加します。
    - 全員の初期資産は500ポイントです。
    - 各ターンで「投資する」「投資しない」のどちらかを選択します。
    - 各ターンの終了後に投資結果が確定し、資産が更新されます。
    - 更新された資産をもとに、次のターンの投資判断を行います。
    """)

            st.markdown("### 2. 投資に使うポイント")

            st.write(
                "各ターンでは、現在の資産の10％に相当するポイントを受け取ります。"
                "このポイントを投資するか、そのまま受け取るかを選択します。"
            )

            st.info(
                "例：現在の資産が500ポイントの場合、"
                "投資に使えるポイントは50ポイントです。"
            )

            st.write(
                "投資に使えるポイントは、各ターンの開始時点の資産によって変わります。"
            )

            st.markdown("### 3. 投資結果と資産の変化")

            st.markdown("""
    **投資しない場合**

    投資に使えるポイントが、そのまま資産に加算されます。

    **投資して成功した場合**

    投資したポイントの1.6倍が資産に加算されます。

    **投資して失敗した場合**

    投資したポイントは受け取れません。
    ただし、それまでに保有していた資産が減ることはありません。
    """)

            st.write(
                "例えば、現在の資産が500ポイント、"
                "投資に使えるポイントが50ポイントの場合、"
                "結果は次のようになります。"
            )

            st.table({
                "選択・結果": [
                    "投資しない",
                    "投資して成功",
                    "投資して失敗"
                ],
                "次のターンの資産": [
                    "550ポイント",
                    "580ポイント",
                    "500ポイント"
                ]
            })

            st.markdown("#### 投資判断画面の例")
            show_example_decision()

            st.markdown("### 4. 投資の成功条件")

            st.write(
                "各ターンで、投資に成功できる人数は最大4人です。"
            )

            st.markdown("""
    - 投資する人が4人以下の場合、投資した人は全員成功します。
    - 投資する人が5人以上の場合、投資した人の中からランダムに4人が選ばれ、成功します。
    - 選ばれなかった人は投資失敗となります。
    """)

            st.write(
                "他の参加者がどのような選択をするかによって、"
                "投資の成功・失敗が変わる場合があります。"
            )

            st.markdown("### 5. 資産情報の表示について")

            st.write(
                "実験中は、自分の資産や投資結果を確認できます。"
            )

            st.write(
                "また、特定のターンの終了時には、"
                "他の参加者を含む資産分布の情報が更新されます。"
            )

            st.write(
                "資産情報が更新されないターンでは、"
                "以前に公開された資産分布が引き続き表示されます。"
            )

            st.warning(
                "表示されている他の参加者の資産が、"
                "必ずしも現在の資産とは限りません。"
            )

            st.markdown("#### 資産分布画面の例")
            show_example_wealth_distribution()

            st.markdown("### 6. 実験の進め方")

            st.markdown("""
    1. 説明を読み終えたら「説明を確認しました」を押してください。
    2. 質問がある場合は挙手し、実験担当者に確認してください。
    3. 練習を実施する場合は、全員の確認後に1ターンの練習を行います。
    4. 練習終了後、本番の実験を開始します。
    5. 本番では初期資産500ポイントから開始し、複数ターンの投資判断を繰り返します。
    """)

            st.write(
                "各ターンでは、自分で投資するかどうかを判断してください。"
                "選択後は、管理者の案内に従って次の画面へ進んでください。"
            )

            st.markdown("### 7. 実験中の注意事項")

            st.markdown("""
            - 実験中は、他の参加者との会話や相談をしないでください。
            - 他の参加者の画面を見ないでください。
            - 質問や不具合がある場合は、挙手して実験担当者にお知らせください。
            - 配布された用紙へのメモは、待機時間中のみ可能です。投資判断中はメモを取らないでください。
            """)

            st.divider()

            if player["explanation_confirmed"]:

                st.success("説明を確認済みです。")
                st.write(
                    "練習開始まで、説明を自由に"
                    "読み返してください。"
                )

            else:

                if st.button(
                    "説明を確認しました",
                    type="primary"
                ):
                    db.confirm_explanation(
                        st.session_state.my_id
                    )
                    st.rerun()

        elif room["phase"] == "practice_decision":

            st.subheader("練習モード（1ターン）")

            st.write(
                f"あなたは Player {st.session_state.player_number} です。"
            )

            wealth = player["wealth"]
            investment = wealth * INTEREST_RATE

            st.write(f"現在の総資産：{wealth:,.0f} ポイント")
            st.write(f"今回の投資額：{investment:,.0f} ポイント")

            st.info(
                "本番と同じルールで投資判断を行ってください。"
                "練習の結果は本番の記録には含まれません。"
            )

            if player["has_submitted"]:

                st.success("練習の回答を提出しました。")
                st.write("他の参加者の回答を待っています。")

            else:

                if "practice_start_time" not in st.session_state:
                    st.session_state.practice_start_time = time.time()

                st.write("投資するかどうかを選択してください。")

                col1, col2 = st.columns(2)

                with col1:
                    if st.button(
                        "投資する",
                        key="practice_invest",
                        type="primary"
                    ):
                        response_time = (
                            time.time()
                            - st.session_state.practice_start_time
                        )

                        db.submit_practice_choice(
                            st.session_state.my_id,
                            "Invest",
                            response_time
                        )

                        st.rerun()

                with col2:
                    if st.button(
                        "投資しない",
                        key="practice_not_invest"
                    ):
                        response_time = (
                            time.time()
                            - st.session_state.practice_start_time
                        )

                        db.submit_practice_choice(
                            st.session_state.my_id,
                            "Not Invest",
                            response_time
                        )

                        st.rerun()

        elif room["phase"] == "practice_result":

            st.subheader("練習結果")

            wealth_after = player["wealth"]
            choice = player["current_choice"]
            success = player["success"]

            # 練習開始時の資産は500ポイント
            wealth_before = INITIAL_WEALTH
            investment = wealth_before * INTEREST_RATE
            acquired_assets = wealth_after - wealth_before

            if choice == "Invest":
                if success:
                    st.markdown(
                        "**あなたは投資しました。**\n\n"
                        "**あなたの投資は成功しました。**"
                    )
                else:
                    st.markdown(
                        "**あなたは投資しました。**\n\n"
                        "**あなたの投資は失敗しました。**"
                    )
            else:
                st.markdown("**あなたは投資しませんでした。**")

            st.write(f"あなたの投資額：{investment:,.0f} ポイント")

            st.write(f"投資した人数：{room['num_invested']} 人")
            st.write(f"成功した人数：{room['num_success']} 人")
            st.write(f"失敗した人数：{room['num_failed']} 人")
            st.write(f"投資しなかった人数：{room['num_not_invested']} 人")

            st.divider()

            st.write(f"今期獲得した資産：{acquired_assets:,.0f} ポイント")
            st.markdown(
                f"**現在の総資産：{wealth_after:,.0f} ポイント**"
            )

            st.divider()
            
            # 練習終了時の全参加者の資産分布を表示
            practice_players = db.get_all_players()

            practice_wealths = [
                p["wealth"]
                for p in practice_players
            ]

            my_index = player["player_number"] - 1

            st.subheader("練習終了時の資産分布")

            plot_wealth_distribution(
                practice_wealths,
                my_index
            )

            st.info(
                "グラフには、参加者全員の総保有資産の分布が表示されます。"
                "本番では、この資産分布が特定のターンに更新されます。"
            )

            st.divider()

            if player["result_confirmed"]:
                st.success("練習結果を確認済みです。")
                st.write("管理者からの案内をお待ちください。")

            else:
                if st.button("練習結果を確認しました", type="primary"):
                    db.confirm_result(st.session_state.my_id)
                    st.rerun()

        elif room["phase"] == "practice_waiting":

            st.subheader("練習終了")

            st.success("練習が終了しました。")

            st.write(
                f"あなたは Player {st.session_state.player_number} です。"
            )

            st.write(
                "これから本番の実験を開始します。"
                "管理者からの案内があるまでお待ちください。"
            )

            st.info(
                "本番は初期資産500ポイントから開始します。"
                "練習結果は本番には引き継がれません。"
            )

        else:

            st.subheader("しばらくお待ちください")

            st.write(
                f"あなたは Player "
                f"{st.session_state.player_number} です。"
            )

            st.write(
                "管理者からの案内があるまで、"
                "この画面でお待ちください。"
            )

            st.write(
                f"現在の参加者：{len(players)} / {required_players}"
            )
    
    @st.fragment(run_every=4)
    def watch_prestart_state(
        displayed_phase,
        displayed_started,
        displayed_player_count,
        displayed_submitted,
        displayed_explanation_confirmed,
        displayed_result_confirmed
    ):
        room_now = db.get_room_state()
        players_now = db.get_all_players()
        if st.session_state.get("my_id") and not st.session_state.get("is_admin"):
            if db.get_player(st.session_state.my_id) is None:
                st.rerun(scope="app")

        if (
            room_now["phase"] != displayed_phase
            or room_now["is_started"] != displayed_started
            or len(players_now) != displayed_player_count
            or sum(p["has_submitted"] for p in players_now)
            != displayed_submitted
            or sum(p["explanation_confirmed"] for p in players_now)
            != displayed_explanation_confirmed
            or sum(p["result_confirmed"] for p in players_now)
            != displayed_result_confirmed
        ):
            st.rerun(scope="app")


    watch_prestart_state(
        room["phase"],
        room["is_started"],
        len(players),
        sum(p["has_submitted"] for p in players),
        sum(p["explanation_confirmed"] for p in players),
        sum(p["result_confirmed"] for p in players)
    )

    st.stop()
    
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

        if ALLOW_ADMIN_RESET:
            st.divider()

            if "confirm_reset" not in st.session_state:
                st.session_state.confirm_reset = False

            if not st.session_state.confirm_reset:

                if st.button("実験室をリセット"):
                    st.session_state.confirm_reset = True
                    st.rerun()

            else:
                st.warning(
                    "参加者情報と実験ログがすべて削除されます。"
                    "この操作は取り消せません。"
                )

                st.write("本当に実験室をリセットしますか？")

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("キャンセル"):
                        st.session_state.confirm_reset = False
                        st.rerun()

                with col2:
                    if st.button("リセットを実行", type="primary"):
                        db.reset_room()

                        st.session_state.confirm_reset = False
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

    if ALLOW_ADMIN_RESET:
        if "confirm_reset" not in st.session_state:
            st.session_state.confirm_reset = False

        if not st.session_state.confirm_reset:

            if st.button("実験室をリセット"):
                st.session_state.confirm_reset = True
                st.rerun()

        else:
            st.warning(
                "参加者情報と実験ログがすべて削除されます。"
                "この操作は取り消せません。"
            )

            st.write("本当に実験室をリセットしますか？")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("キャンセル"):
                    st.session_state.confirm_reset = False
                    st.rerun()

            with col2:
                if st.button("リセットを実行", type="primary"):
                    db.reset_room()

                    st.session_state.confirm_reset = False
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


    elif room["phase"] in ("result", "final_result", "game_break"):

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

        if room["phase"] == "game_break":
            ready_count = sum(p["game_ready"] for p in players)
            st.write(f"次のゲームの準備完了：{ready_count}/{required_players} 人")
            if ready_count == required_players and len(players) == required_players:
                st.success("全員の準備ができました。")
                if st.button("次のゲームを開始", type="primary"):
                    db.start_next_game(INITIAL_WEALTH, generate_high_periods())
                    st.rerun()
            else:
                st.info("全員の準備ができるまで開始できません。")
            if st.button("実験を終了"):
                db.end_experiment()
                st.rerun()

        elif room["period"] < effective_num_periods:

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

            if confirmed_count == required_players and len(players) == required_players:
                if st.button("休憩・準備確認へ進む", type="primary"):
                    db.enter_game_break()
                    st.rerun()
            else:
                st.info("全員が結果を確認するまで休憩画面には進めません。")
            if st.button("実験を終了"):
                db.end_experiment()
                st.rerun()

# 管理者はここでDBの変化を監視
if st.session_state.is_admin:
    watch_admin_state()
    st.stop()

if st.session_state.screen == "game_start_gate":
    st.subheader(f"ゲーム {room['game']} を開始します")
    st.write("準備ができたら「OK」を押して投資判断を始めてください。")
    if st.button("OK・投資判断を開始", type="primary"):
        db.acknowledge_game_start(st.session_state.my_id)
        st.session_state.decision_start_time = time.perf_counter()
        st.rerun()
    wait_for_phase_change("decision", room["game"], room["period"])
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

    
    # 判断時点ですでに公開済みの情報
    past_highs = [
        high_period
        for high_period in high_periods
        if high_period < period
    ]

    # 判断後に行われる次の公開
    future_highs = [
        high_period
        for high_period in high_periods
        if high_period >= period
    ]

    if past_highs:
        last_high = max(past_highs)
        time_since_high = period - last_high
    else:
        time_since_high = None

    if future_highs:
        next_high = min(future_highs)
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

    st.subheader(f"反復投資実験 （ターン{period}/{effective_num_periods}）")

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

    turns_to_end = effective_num_periods - period

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

        try:
            db.submit_choice_with_log(
                player_id=st.session_state.my_id,
                game=room["game"],
                period=period,
                choice=player_choice,
                response_time=response_time
            )
        except ValueError:
            st.warning("ターンの状態が変わりました。画面を更新して確認してください。")
            st.stop()

        st.session_state.decision_start_time = None
        st.session_state.screen = "waiting_submission"
        st.rerun()

elif st.session_state.screen == "waiting_submission":

    room = db.get_room_state()

    if room["phase"] == "result":
        st.session_state.screen = "result"
        st.rerun()

    st.subheader(
        f"ターン {room['period']}/{effective_num_periods}"
    )

    st.write(
        f"Player {st.session_state.player_number}：提出済み"
    )

    st.write(
        "他の参加者の回答を待っています。"
    )
    
    wait_for_phase_change(
        "decision",
        room["game"],
        room["period"]
    )

    st.stop()

elif st.session_state.screen == "result":

    room = db.get_room_state()
    review_key = (room["game"], room["period"])
    if st.session_state.result_view_open_key != ("result", *review_key):
        st.subheader(f"ターン {room['period']} の結果が確定しました")
        st.write("準備ができたら「結果を確認する」を押してください。")
        if st.button("結果を確認する", type="primary", key="open_result"):
            st.session_state.result_view_open_key = ("result", *review_key)
            st.session_state.result_review_key = review_key
            st.session_state.result_review_start_time = time.perf_counter()
            st.rerun()
        wait_for_phase_change("result", room["game"], room["period"])
        st.stop()
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

    if period_log is None:
        st.error("結果ログが見つかりません。管理者に連絡してください。")
        st.stop()

    wealth_before = period_log["wealth_before"]
    investment = period_log["endowment"]

    acquired_assets = wealth_after - wealth_before

    investment = wealth_before * INTEREST_RATE
    acquired_assets = wealth_after - wealth_before

    st.subheader(
        f"結果 （ターン{period}/{effective_num_periods}）"
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
                elapsed = time.perf_counter() - st.session_state.result_review_start_time
                db.confirm_result(st.session_state.my_id, elapsed)
                st.rerun()

        with col2:
            if st.button("いいえ"):
                st.info("結果を確認してから「はい」を押してください。")
    
    wait_for_phase_change(
        "result",
        room["game"],
        room["period"]
    )

    st.stop()


elif st.session_state.screen == "final_result":

    room = db.get_room_state()
    review_key = (room["game"], room["period"])
    if st.session_state.result_view_open_key != ("final_result", *review_key):
        st.subheader("ゲームの結果が確定しました")
        st.write("準備ができたら「結果を確認する」を押してください。")
        if st.button("結果を確認する", type="primary", key="open_final_result"):
            st.session_state.result_view_open_key = ("final_result", *review_key)
            st.session_state.result_review_key = review_key
            st.session_state.result_review_start_time = time.perf_counter()
            st.rerun()
        wait_for_phase_change("final_result", room["game"], room["period"])
        st.stop()
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
                elapsed = time.perf_counter() - st.session_state.result_review_start_time
                db.confirm_result(st.session_state.my_id, elapsed)
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
    wait_for_phase_change(
        "final_result",
        room["game"],
        room["period"]
    )

    st.stop()

elif st.session_state.screen == "game_break":
    room = db.get_room_state()
    player = db.get_player(st.session_state.my_id)
    st.subheader(f"ゲーム {room['game']} が終了しました")
    st.write("休憩が必要な方は、ここで休憩してください。")
    st.write("次のゲームの準備ができたら「準備できました」を押してください。")
    if player["game_ready"]:
        st.success("準備完了を受け付けました。")
        st.write("全員の準備ができた後、実験者が次のゲームを開始します。")
    elif st.button("準備できました", type="primary"):
        db.mark_game_ready(st.session_state.my_id)
        st.rerun()
    wait_for_phase_change("game_break", room["game"], room["period"])
    st.stop()

elif st.session_state.screen == "final_end":

    st.subheader("実験終了")

    st.write("これで実験は終了です。")
    st.write("ご参加ありがとうございました。")

    wait_for_phase_change("finished", room["game"], room["period"])
    st.stop()