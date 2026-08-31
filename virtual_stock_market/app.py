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
# 画面 1: ログイン画面
# ==========================================
if not st.session_state.is_logged_in:
    st.caption("🌙 YUTSUKI LAB EXPERIMENT")
    st.header("投資シミュレータ (マルチプレイヤー)")
    st.caption("実験を開始する前に、名前を入力して参加してください。")
    st.divider()

    with st.form(key="login_form"):
        input_name = st.text_input("👤 プレイヤー名（ID）を入力してください", value="Admin_Host", max_chars=20)
        is_host_check = st.checkbox("管理者（ホスト）としてログインする（※ゲームには参加しません）")
        submit_login = st.form_submit_button("ロビーに入る ➔")

    if submit_login:
        clean_name = input_name.strip()
        if clean_name == "":
            st.error("⚠️ プレイヤー名を入力してください。")
        else:
            st.session_state.my_id = clean_name
            st.session_state.is_host = is_host_check
            st.session_state.is_logged_in = True
            
            # ホストはプレイヤーリスト（対戦相手）には登録しない
            if not is_host_check:
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
    is_host = st.session_state.is_host

    st.sidebar.caption("📋 メニュー / 実験ステータス")
    st.sidebar.markdown(f"### 📌 Step {room_state['step']} / {NUM_STEPS}")
    st.sidebar.write(f"👤 **ログイン:** {my_id} {'(管理者)' if is_host else ''}")

    # ------------------------------------------
    # 強制終了機能（管理者・一般共通でサイドバーに復元）
    # ------------------------------------------
    st.sidebar.divider()
    with st.sidebar.expander("🛠️ 詳細・管理操作"):
        st.caption("テスト用機能です。途中で切り上げて最終結果画面を表示します。")
        confirm_abort = st.checkbox("強制終了を有効化", key="confirm_abort")
        if st.button("🚨 ここで強制終了する", disabled=not confirm_abort):
            if st.session_state.history_logs:
                save_logs_to_csv(st.session_state.history_logs)
            db.advance_to_next_step(room_state['step'], {p['player_id']: p['cash'] for p in players_data}, game_over=True)
            st.rerun()

    # --- A. 実験開始前の待機ロビー ---
    if not room_state['is_started']:
        st.subheader("⏳ ゲーム開始待機中")
        
        if is_host:
            st.info("参加者が揃ったら「実験を開始する」ボタンを押してください。")
            st.write(f"### 👥 現在参加中のプレイヤー ({len(players_data)} / {NUM_PLAYERS} 人)")
            for p in players_data:
                st.write(f"- **{p['player_id']}** (人間プレイヤー)")
            
            st.divider()
            if st.button("🚀 人数を確定して実験を開始する", type="primary"):
                # 残り枠を AI で自動穴埋めして NUM_PLAYERS 人にする
                current_count = len(players_data)
                for i in range(current_count, NUM_PLAYERS):
                    ai_name = f"Player_{chr(65+i)}"
                    db.register_player(ai_name, float(INITIAL_CASH), is_ai=True)
                
                db.set_room_started(True)
                st.rerun()

            # ホスト画面も定期リロードして新しく入った参加者を更新表示
            time.sleep(2)
            st.rerun()
        else:
            st.info("管理人が実験を開始するまでしばらくお待ちください...")
            st.write("### 👥 現在参加中のプレイヤー")
            for p in players_data:
                st.write(f"- **{p['player_id']}**")
            
            # 参加者画面も2秒ごとに自動更新
            time.sleep(2)
            st.rerun()

    # --- B. ゲーム終了画面 ---
    elif room_state['game_over']:
        st.success("シミュレーションが終了しました")
        df_results = pd.DataFrame(st.session_state.history_logs)
        
        if not df_results.empty:
            last_step = df_results['Step'].max()
            last_step_df = df_results[df_results['Step'] == last_step].sort_values(by='End_Cash', ascending=False)

            st.subheader(f"🏆 最終結果ランキング (Step {last_step} 時点)")
            for idx, row in enumerate(last_step_df.itertuples(), start=1):
                mark = " ★ あなた" if row.Player == my_id else ""
                st.write(f"**第 {idx} 位**: {row.Player} | 最終資産: **{row.End_Cash:,.1f} 円**{mark}")

            st.divider()
            st.subheader("📈 全プレイヤーの総資産推移")
            df_chart = df_results.pivot(index='Step', columns='Player', values='End_Cash')
            st.line_chart(df_chart, width="stretch")

            st.divider()
            st.subheader("📊 実験データログ")
            st.dataframe(df_results, width="stretch")
        else:
            st.info("データが記録される前に終了されました。")

        if is_host and st.button("もう一度最初からプレイする"):
            db.reset_room()
            st.session_state.clear()
            st.rerun()

    # --- C. ゲーム進行中 ---
    else:
        step = room_state['step']
        curr_prices, prev_prices, returns = get_market_info_at_step(st.session_state.df_market, step)
        
        player_cashes = {p['player_id']: p['cash'] for p in players_data}
        visible_ranks, visible_gaps, is_published = calculate_ranking_info(step, player_cashes, True, RANKING_INTERVAL)

        # サイドバーメトリクス表示
        if not is_host:
            my_data = next((p for p in players_data if p['player_id'] == my_id), None)
            my_cash = my_data['cash'] if my_data else 0.0
            st.sidebar.metric(label="現在のあなたの現金", value=f"{my_cash:,.1f} 円")

        # ランキング公開/非公開の表示制御
        if is_published:
            if not is_host:
                my_rank = visible_ranks.get(my_id, None)
                st.sidebar.metric(label="現在のあなたの順位", value=f"{my_rank} 位")
            
            st.sidebar.divider()
            st.sidebar.subheader("👪 プレイヤーの所持金一覧")
            for p in players_data:
                st.sidebar.write(f"・**{p['player_id']}**: {p['cash']:,.1f} 円")
        else:
            # 元のカウントダウン表示
            steps_until_next = RANKING_INTERVAL - (step % RANKING_INTERVAL)
            st.sidebar.info(f"⏳ 次の順位公開まで **あと {steps_until_next} ターン**")

        st.subheader("🏙️ 株式市場")
        cols = st.columns(len(STOCKS))
        for idx, s in enumerate(STOCKS):
            c_p, p_p = curr_prices[s], prev_prices[s]
            diff = c_p - p_p
            pct = (diff / p_p) * 100
            cols[idx].metric(label=s, value=f"{c_p:,.1f} 円", delta=f"{diff:+.1f} 円 ({pct:+.2f}%)")

        st.divider()

        # --- 管理者（ホスト）の画面 ---
        if is_host:
            st.subheader("🎮 管理者コントロール")
            st.write("### 👥 各プレイヤーの入力状況")
            all_submitted = True
            for p in players_data:
                if p['is_ai']:
                    status = "🤖 AI (自動入力)"
                else:
                    status = "✅ 提出済み" if p['has_submitted'] else "⏳ 入力中..."
                    if not p['has_submitted']:
                        all_submitted = False
                st.write(f"- **{p['player_id']}**: {status}")

            st.divider()
            if st.button("➔ 全員の入力結果を反映して次のターンへ進む", disabled=not all_submitted, type="primary"):
                new_cashes = {}
                step_investments = {}

                for p in players_data:
                    p_id = p['player_id']
                    if p['is_ai']:
                        inv = decide_investment_ai(p_id, p['cash'], visible_ranks.get(p_id), NUM_PLAYERS)
                    else:
                        inv = p['current_input']
                    
                    step_investments[p_id] = inv
                    new_cash, _ = update_assets(p['cash'], inv, returns)
                    new_cashes[p_id] = new_cash

                    log = create_log_entry(step, p_id, p['cash'], inv, returns, new_cash, visible_ranks.get(p_id), visible_gaps.get(p_id))
                    log['Is_Ranking_Published'] = is_published
                    st.session_state.history_logs.append(log)

                is_over = step >= NUM_STEPS
                db.advance_to_next_step(step + 1 if not is_over else step, new_cashes, game_over=is_over)
                st.rerun()

            # ホスト画面を2秒ごとにリロードして入力状況を最新化
            time.sleep(2)
            st.rerun()

        # --- プレイヤー（人間）の画面 ---
        else:
            my_data = next((p for p in players_data if p['player_id'] == my_id), None)
            
            # 確定後の待機画面
            if my_data and my_data['has_submitted']:
                st.warning("⏳ ほかのプレイヤーの入力および管理者の進行を待っています...")
                st.write("### 👥 各プレイヤーの入力状況")
                for p in players_data:
                    status = "✅ 提出済み" if p['has_submitted'] or p['is_ai'] else "⏳ 入力中..."
                    st.write(f"- **{p['player_id']}**: {status}")

                # 2秒ごとに自動更新して進行を待つ
                time.sleep(2)
                st.rerun()

            # 入力フォーム
            else:
                st.subheader("🔢 投資内訳")
                st.caption("※金額を直接入力してください。単位: 円")
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