# app.py
import streamlit as st
import pandas as pd
from config import NUM_STEPS, NUM_PLAYERS, INITIAL_CASH, STOCKS, HUMAN_PLAYER_ID
from market import generate_and_save_market_data, get_market_info_at_step
from ranking import calculate_ranking_info
from player import decide_investment_ai, update_assets
from analysis import create_log_entry, save_logs_to_csv

# --- ページ基本設定 ---
st.set_page_config(page_title="仮想株式市場実験", layout="wide")

# --- セッション状態の初期化 ---
if 'step' not in st.session_state:
    st.session_state.step = 1
    st.session_state.df_market = generate_and_save_market_data()
    st.session_state.players = [f'Player_{chr(65+i)}' for i in range(NUM_PLAYERS)]
    st.session_state.player_cash = {p: float(INITIAL_CASH) for p in st.session_state.players}
    st.session_state.history_logs = []
    st.session_state.game_over = False

st.title("📈 仮想株式市場シミュレーション")

# --- ゲーム終了時の画面表示 ---
if st.session_state.game_over:
    st.success("🎉 シミュレーションが完了しました！")
    
    df_results = pd.DataFrame(st.session_state.history_logs)
    last_step_df = df_results[df_results['Step'] == NUM_STEPS].sort_values(by='End_Cash', ascending=False)
    
    st.subheader("🏆 最終結果ランキング")
    for idx, row in enumerate(last_step_df.itertuples(), start=1):
        mark = " ★ あなた" if row.Player == HUMAN_PLAYER_ID else ""
        st.write(f"**第 {idx} 位**: {row.Player} | 最終資産: **{row.End_Cash:,.1f} 円**{mark}")
        
    st.divider()
    st.subheader("📊 実験データログ")
    st.dataframe(df_results, use_container_width=True)
    
    if st.button("もう一度最初からプレイする"):
        st.session_state.clear()
        st.rerun()

# --- ゲーム実行中の画面表示 ---
else:
    step = st.session_state.step
    curr_prices, prev_prices, returns = get_market_info_at_step(st.session_state.df_market, step)
    visible_ranks, visible_gaps, is_published = calculate_ranking_info(step, st.session_state.player_cash)
    
    # ------------------------------------------
    # サイドバー表示（ステータス ＆ 他プレイヤーの所持金）
    # ------------------------------------------
    st.sidebar.header(f"📌 ステータス (Step {step} / {NUM_STEPS})")
    my_cash = st.session_state.player_cash[HUMAN_PLAYER_ID]
    st.sidebar.metric(label="現在のあなたの現金", value=f"{my_cash:,.1f} 円")
    
    my_rank = visible_ranks[HUMAN_PLAYER_ID]
    rank_disp = f"{my_rank} 位" if my_rank is not None else "[非公開]"
    st.sidebar.metric(label="公開順位", value=rank_disp)

    st.sidebar.divider()
    st.sidebar.subheader("👥 他プレイヤーの所持金（参考）")
    for p in st.session_state.players:
        if p != HUMAN_PLAYER_ID:
            other_cash = st.session_state.player_cash[p]
            st.sidebar.write(f"・**{p}**: {other_cash:,.1f} 円")

    # ------------------------------------------
    # メイン画面：株式市場の情報
    # ------------------------------------------
    st.subheader("💹 株式市場の情報")
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
    st.subheader(f"🎮 あなた（{HUMAN_PLAYER_ID}）の投資入力")
    st.caption("※金額を直接入力してください（キーボード入力）。単位: 円")
    
    with st.form(key=f"invest_form_step_{step}"):
        invest_inputs = {}
        input_cols = st.columns(len(STOCKS))
        
        for idx, s in enumerate(STOCKS):
            # 直接キーボード打ち込みができる数値入力ボックス（st.number_input）
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
                if p == HUMAN_PLAYER_ID:
                    step_investments[p] = invest_inputs
                else:
                    step_investments[p] = decide_investment_ai(p, st.session_state.player_cash[p], visible_ranks[p], NUM_PLAYERS)
            
            for p in st.session_state.players:
                start_cash = st.session_state.player_cash[p]
                inv = step_investments[p]
                new_cash, _ = update_assets(start_cash, inv, returns)
                st.session_state.player_cash[p] = new_cash
                
                log = create_log_entry(step, p, start_cash, inv, returns, new_cash, visible_ranks[p], visible_gaps[p])
                log['Is_Ranking_Published'] = is_published
                st.session_state.history_logs.append(log)
            
            if step >= NUM_STEPS:
                save_logs_to_csv(st.session_state.history_logs)
                st.session_state.game_over = True
            else:
                st.session_state.step += 1
                
            st.rerun()