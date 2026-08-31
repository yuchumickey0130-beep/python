# app.py
import streamlit as st
import pandas as pd
import time
from config import NUM_STEPS, NUM_PLAYERS, INITIAL_CASH, STOCKS, HUMAN_PLAYER_ID, RANKING_INTERVAL
from market import generate_and_save_market_data, get_market_info_at_step
from ranking import calculate_ranking_info
from player import decide_investment_ai, update_assets
from analysis import create_log_entry, save_logs_to_csv
import db

# データベース初期化
db.init_db()

st.set_page_config(page_title="仮想株式市場投資実験", layout="wide")

def render_brand_badge():
    st.sidebar.markdown(
        """
        <div style="background-color: #f0f2f6; padding: 6px 10px; border-radius: 6px; text-align: center; font-size: 0.85em; font-weight: 600; color: #555; margin-bottom: 12px;">
            🌙 YUTSUKI LAB EXPERIMENT
        </div>
        """, 
        unsafe_allow_html=True
    )

# --- セッション状態の初期化 ---
if 'is_logged_in' not in st.session_state:
    st.session_state.is_logged_in = False
    st.session_state.my_id = ""
    st.session_state.is_host = False
    st.session_state.df_market = generate_and_save_market_data()
    st.session_state.history_logs = []

# ==========================================
# 画面 1: ログイン & ロビー画面
# ==========================================
if not st.session_state.is_logged_in:
    st.caption("🌙 YUTSUKI LAB EXPERIMENT")
    st.header("投資シミュレータ (マルチプレイヤー)")
    st.caption("実験を開始する前に、名前を入力して参加してください。")
    st.divider()

    with st.form(key="login_form"):
        input_name = st.text_input("👤 プレイヤー名（ID）を入力してください", max_chars=20)
        is_host_check = st.checkbox("管理者（ホスト）として参加する")
        submit_login = st.form_submit_button("ロビーに入る ➔")

    if submit_login:
        clean_name = input_name.strip()
        if clean_name == "":
            st.error("⚠️ プレイヤー名を入力してください。")
        else:
            st.session_state.my_id = clean_name
            st.session_state.is_host = is_host_check
            st.session_state.is_logged_in = True
            db.register_player(clean_name, float(INITIAL_CASH), is_ai=False)
            st.rerun()

# ==========================================
# 画面 2: シミュレーション本編（ログイン後）
# ==========================================
else:
    st.caption("🌙 YUTSUKI LAB EXPERIMENT")
    st.header("投資シミュレータ")

    render_brand_badge()
    room_state = db.get_room_state()
    players_data = db.get_all_players()
    my_id = st.session_state.my_id

    st.sidebar.caption("📋 メニュー / 実験ステータス")
    st.sidebar.markdown(f"### 📌 Step {room_state['step']} / {NUM_STEPS}")
    st.sidebar.write(f"👤 **プレイヤー:** {my_id} {'(ホスト)' if st.session_state.is_host else ''}")

    # --- A. 実験開始前の待機ロビー ---
    if not room_state['is_started']:
        st.subheader("⏳ ゲーム開始待機中")
        st.info("管理人が実験を開始するまでしばらくお待ちください。")

        st.write("### 👥 現在参加中のプレイヤー")
        for p in players_data:
            st.write(f"- **{p['player_id']}** ({'ホスト' if p['player_id'] == my_id and st.session_state.is_host else '参加者'})")

        # ホスト専用の開始ボタン
        if st.session_state.is_host:
            st.divider()
            if st.button("🚀 人数を確定して実験を開始する", type="primary"):
                # 残り枠を AI で自動埋め
                current_count = len(players_data)
                for i in range(current_count, NUM_PLAYERS):
                    ai_name = f"AI_Player_{chr(65+i)}"
                    db.register_player(ai_name, float(INITIAL_CASH), is_ai=True)
                
                db.set_room_started(True)
                st.rerun()
        else:
            # 自動更新（他ユーザーの参加を反映）
            time.sleep(2)
            st.rerun()

    # --- B. ゲーム終了画面 ---
    elif room_state['game_over']:
        st.success("シミュレーションが終了しました")
        df_results = pd.DataFrame(st.session_state.history_logs)
        if not df_results.empty:
            st.dataframe(df_results, width="stretch")
        
        if st.session_state.is_host:
            if st.button("リセットしてもう一度最初から"):
                db.reset_room()
                st.session_state.clear()
                st.rerun()

    # --- C. ゲーム進行中 ---
    else:
        step = room_state['step']
        curr_prices, prev_prices, returns = get_market_info_at_step(st.session_state.df_market, step)
        
        # 現在の所持金辞書・AI判定用の情報を作成
        player_cashes = {p['player_id']: p['cash'] for p in players_data}
        visible_ranks, visible_gaps, is_published = calculate_ranking_info(step, player_cashes, True, RANKING_INTERVAL)

        my_data = next((p for p in players_data if p['player_id'] == my_id), None)
        my_cash = my_data['cash'] if my_data else 0.0

        st.sidebar.metric(label="現在のあなたの現金", value=f"{my_cash:,.1f} 円")

        # ランキング公開/非公開の表示制御
        if is_published:
            my_rank = visible_ranks.get(my_id, None)
            st.sidebar.metric(label="現在のあなたの順位", value=f"{my_rank} 位")
            st.sidebar.divider()
            st.sidebar.subheader("👪 他プレイヤーの所持金")
            for p in players_data:
                if p['player_id'] != my_id:
                    st.sidebar.write(f"・**{p['player_id']}**: {p['cash']:,.1f} 円")
        else:
            # 【非公開ターン】順位・他者金額を伏せ、次回公開までのカウントダウンを表示

            steps_until_next = RANKING_INTERVAL - (step % RANKING_INTERVAL)

            st.sidebar.info(f"⏳ 次の順位公開まで **あと {steps_until_next} ターン**")

        st.sidebar.divider()

        st.subheader("🏙️ 株式市場")
        cols = st.columns(len(STOCKS))
        for idx, s in enumerate(STOCKS):
            c_p, p_p = curr_prices[s], prev_prices[s]
            diff = c_p - p_p
            pct = (diff / p_p) * 100
            cols[idx].metric(label=s, value=f"{c_p:,.1f} 円", delta=f"{diff:+.1f} 円 ({pct:+.2f}%)")

        st.divider()

        # --- 確定後の待機判定 ---
        if my_data and my_data['has_submitted']:
            st.warning("⏳ ほかのプレイヤーの入力および進行を待っています...")
            
            # 入力状況の可視化
            st.write("### 👥 各プレイヤーの入力状況")
            for p in players_data:
                status = "✅ 提出済み" if p['has_submitted'] else "⏳ 入力中..."
                st.write(f"- **{p['player_id']}**: {status}")

            # ホストの場合: 全員揃ったら次のターンに進行するボタン
            all_submitted = all(p['has_submitted'] or p['is_ai'] for p in players_data)
            if st.session_state.is_host:
                st.divider()
                if st.button("➔ 全員の入力結果を反映して次のターンへ進む", disabled=not all_submitted, type="primary"):
                    new_cashes = {}
                    step_investments = {}

                    # AIの意志決定と人間の入力を統合
                    for p in players_data:
                        p_id = p['player_id']
                        if p['is_ai']:
                            inv = decide_investment_ai(p_id, p['cash'], visible_ranks.get(p_id), len(players_data))
                        else:
                            inv = p['current_input']
                        
                        step_investments[p_id] = inv
                        new_cash, _ = update_assets(p['cash'], inv, returns)
                        new_cashes[p_id] = new_cash

                        # ログ作成
                        log = create_log_entry(step, p_id, p['cash'], inv, returns, new_cash, visible_ranks.get(p_id), visible_gaps.get(p_id))
                        log['Is_Ranking_Published'] = is_published
                        st.session_state.history_logs.append(log)

                    is_over = step >= NUM_STEPS
                    db.advance_to_next_step(step + 1 if not is_over else step, new_cashes, game_over=is_over)
                    st.rerun()

            # 他プレイヤーは画面を定期リロードして待機
            time.sleep(2)
            st.rerun()

        # --- 投資フォーム ---
        else:
            st.subheader("🔢 投資内訳")
            with st.form(key=f"invest_form_step_{step}"):
                invest_inputs = {}
                input_cols = st.columns(len(STOCKS))
                for idx, s in enumerate(STOCKS):
                    invest_inputs[s] = input_cols[idx].number_input(
                        label=f"{s} への投資額",
                        min_value=0.0,
                        max_value=float(my_cash),
                        value=0.0,
                        step=100.0,
                        format="%.0f",
                        key=f"input_{s}_{step}"
                    )
                submit_button = st.form_submit_button(label="投資を確定する ➔")

            if submit_button:
                if sum(invest_inputs.values()) > my_cash:
                    st.warning("⚠️ 投資額の合計が所持現金を超えています！")
                else:
                    db.submit_player_input(my_id, invest_inputs)
                    st.rerun()