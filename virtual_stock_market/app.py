# app.py
import streamlit as st
import pandas as pd
from config import NUM_STEPS, NUM_PLAYERS, INITIAL_CASH, STOCKS, HUMAN_PLAYER_ID, RANKING_INTERVAL
from market import generate_and_save_market_data, get_market_info_at_step
from ranking import calculate_ranking_info
from player import decide_investment_ai, update_assets
from analysis import create_log_entry, save_logs_to_csv

# --- ページ基本設定 ---
st.set_page_config(page_title="仮想株式市場投資実験", layout="wide")

# --- セッション状態の初期化 ---
if 'step' not in st.session_state:
    st.session_state.step = 1
    st.session_state.df_market = generate_and_save_market_data()
    st.session_state.players = [f'Player_{chr(65+i)}' for i in range(NUM_PLAYERS)]
    st.session_state.player_cash = {p: float(INITIAL_CASH) for p in st.session_state.players}
    st.session_state.history_logs = []
    st.session_state.game_over = False
    st.session_state.human_id = HUMAN_PLAYER_ID
    st.session_state.is_logged_in = False  # ログイン状態フラグ

# ==========================================
# 画面 1: ユーザー名入力（ログイン画面）
# ==========================================
if not st.session_state.is_logged_in:
    st.header("投資シミュレーター")
    st.caption("実験を開始する前に、プレイヤー名を入力してください。")
    st.divider()

    with st.form(key="login_form"):
        input_name = st.text_input(
            "👤 プレイヤー名（ID）を入力してください", 
            value=st.session_state.human_id,
            max_chars=20
        )
        submit_login = st.form_submit_button("シミュレーションを開始する ➔")

    if submit_login:
        clean_name = input_name.strip()
        if clean_name == "":
            st.error("⚠️ プレイヤー名を入力してください。")
        else:
            old_name = st.session_state.human_id
            st.session_state.human_id = clean_name
            st.session_state.players[0] = clean_name
            
            # Cash辞書のキーを更新
            cash_val = st.session_state.player_cash.pop(old_name, float(INITIAL_CASH))
            st.session_state.player_cash[clean_name] = cash_val
            
            st.session_state.is_logged_in = True
            st.rerun()

# ==========================================
# 画面 2: シミュレーション本編（ログイン後）
# ==========================================
else:
    # 共通ヘッダー
    st.header("投資シミュレーター")

    # ------------------------------------------
    # サイドバー表示
    # ------------------------------------------
    st.sidebar.caption("📋 メニュー / 実験ステータス")
    st.sidebar.markdown(f"### 📌 Step {st.session_state.step} / {NUM_STEPS}")

    human_id = st.session_state.human_id
    st.sidebar.write(f"👤 **ログイン:** {human_id}")

    # --- ゲーム終了時の画面表示 ---
    if st.session_state.game_over:
        st.success("シミュレーションが終了しました")

        df_results = pd.DataFrame(st.session_state.history_logs)
        
        if not df_results.empty:
            last_step = df_results['Step'].max()
            last_step_df = df_results[df_results['Step'] == last_step].sort_values(by='End_Cash', ascending=False)

            st.subheader(f"🏆 最終結果ランキング (Step {last_step} 時点)")
            for idx, row in enumerate(last_step_df.itertuples(), start=1):
                mark = " ★ あなた" if row.Player == human_id else ""
                st.write(f"**第 {idx} 位**: {row.Player} | 最終資産: **{row.End_Cash:,.1f} 円**{mark}")

            st.divider()

            st.subheader("📈 全プレイヤーの総資産推移")
            df_chart = df_results.pivot(index='Step', columns='Player', values='End_Cash')
            st.line_chart(df_chart, use_container_width=True)

            st.divider()

            st.subheader("📊 実験データログ")
            st.dataframe(df_results, use_container_width=True)
        else:
            st.info("データが記録される前に終了されました。")

        if st.button("もう一度最初からプレイする"):
            st.session_state.clear()
            st.rerun()

    # --- ゲーム実行中の画面表示 ---
    else:
        step = st.session_state.step
        curr_prices, prev_prices, returns = get_market_info_at_step(st.session_state.df_market, step)
        visible_ranks, visible_gaps, is_published = calculate_ranking_info(step, st.session_state.player_cash)

        # サイドバーへのメトリクス出力
        my_cash = st.session_state.player_cash[human_id]
        st.sidebar.metric(label="現在のあなたの現金", value=f"{my_cash:,.1f} 円")

        # ------------------------------------------
        # 順位および他プレイヤー情報の表示制御
        # ------------------------------------------
        if is_published:
            # 【公開ターン】順位と他プレイヤー所持金を表示
            my_rank = visible_ranks.get(human_id, None)
            st.sidebar.metric(label="現在のあなたの順位", value=f"{my_rank} 位")

            st.sidebar.divider()
            st.sidebar.subheader("👪 他プレイヤーの所持金")
            for p in st.session_state.players:
                if p != human_id:
                    other_cash = st.session_state.player_cash[p]
                    st.sidebar.write(f"・**{p}**: {other_cash:,.1f} 円")
        else:
            # 【非公開ターン】順位・他者金額を伏せ、次回公開までのカウントダウンを表示
            steps_until_next = RANKING_INTERVAL - ((step - 1) % RANKING_INTERVAL)
            st.sidebar.info(f"⏳ 次の順位公開まで **あと {steps_until_next} ターン**")

        st.sidebar.divider()

        with st.sidebar.expander("🛠️ 詳細・管理操作"):
            st.caption("テスト用機能です。途中で切り上げて最終結果画面を表示します。")
            confirm_abort = st.checkbox("強制終了を有効化", key="confirm_abort")
            if st.button("🚨 ここで強制終了する", disabled=not confirm_abort):
                if st.session_state.history_logs:
                    save_logs_to_csv(st.session_state.history_logs)
                st.session_state.game_over = True
                st.rerun()

        # ------------------------------------------
        # メイン画面：株式市場の情報
        # ------------------------------------------
        st.subheader("🏙️ 株式市場")
        cols = st.columns(len(STOCKS))
        for idx, s in enumerate(STOCKS):
            c_p = curr_prices[s]
            p_p = prev_prices[s]
            diff = c_p - p_p
            pct = (diff / p_p) * 100
            cols[idx].metric(
                label=s,
                value=f"{c_p:,.1f} 円",
                delta=f"{diff:+.1f} 円 ({pct:+.2f}%)"
            )

        st.divider()

        # ------------------------------------------
        # メイン画面：キーボード入力式の投資フォーム
        # ------------------------------------------
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

            submit_button = st.form_submit_button(label="投資を確定して次のターンへ ➔")

        # ------------------------------------------
        # 確定時の計算処理
        # ------------------------------------------
        if submit_button:
            total_invested = sum(invest_inputs.values())

            if total_invested > my_cash:
                st.warning("⚠️ 投資額の合計が所持現金を超えています！再入力してください。")
            else:
                step_investments = {}
                for p in st.session_state.players:
                    if p == human_id:
                        step_investments[p] = invest_inputs
                    else:
                        step_investments[p] = decide_investment_ai(p, st.session_state.player_cash[p], visible_ranks.get(p), NUM_PLAYERS)

                for p in st.session_state.players:
                    start_cash = st.session_state.player_cash[p]
                    inv = step_investments[p]
                    new_cash, _ = update_assets(start_cash, inv, returns)
                    st.session_state.player_cash[p] = new_cash

                    log = create_log_entry(step, p, start_cash, inv, returns, new_cash, visible_ranks.get(p), visible_gaps.get(p))
                    log['Is_Ranking_Published'] = is_published
                    st.session_state.history_logs.append(log)

                if step >= NUM_STEPS:
                    save_logs_to_csv(st.session_state.history_logs)
                    st.session_state.game_over = True
                else:
                    st.session_state.step += 1

                st.rerun()