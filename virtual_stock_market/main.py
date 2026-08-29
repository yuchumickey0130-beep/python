# main.py
from config import NUM_STEPS, NUM_PLAYERS, INITIAL_CASH, HUMAN_PLAYER_ID, HUMAN_INPUT_MAX_STEPS
from market import generate_and_save_market_data, get_market_info_at_step
from ranking import calculate_ranking_info
from player import decide_investment_human, decide_investment_ai, update_assets
from analysis import create_log_entry, save_logs_to_csv, display_formatted_summary

def main():
    print("=== 仮想株式市場シミュレーション（テストプレイモード） ===")
    print(f"操作プレイヤー: {HUMAN_PLAYER_ID}")
    print(f"手動入力ターン数: Step 1 〜 {HUMAN_INPUT_MAX_STEPS} (以降は自動実行)")
    
    # 0ターン目を含む市場データの生成
    df_market = generate_and_save_market_data()
    
    players = [f'Player_{chr(65+i)}' for i in range(NUM_PLAYERS)]
    player_cash = {p: INITIAL_CASH for p in players}
    history_logs = []
    
    for step in range(1, NUM_STEPS + 1):
        print(f"\n==========================================")
        print(f"  --- STEP {step} / {NUM_STEPS} ---")
        print(f"==========================================")
        
        # 現在の株価、前ターンの株価、リターンを取得
        curr_prices, prev_prices, returns = get_market_info_at_step(df_market, step)
        visible_ranks, visible_gaps, is_published = calculate_ranking_info(step, player_cash)
        
        step_investments = {}
        for p in players:
            if p == HUMAN_PLAYER_ID and step <= HUMAN_INPUT_MAX_STEPS:
                # 人間用：株価情報も渡す
                inv = decide_investment_human(p, player_cash[p], visible_ranks[p], curr_prices, prev_prices)
            else:
                inv = decide_investment_ai(p, player_cash[p], visible_ranks[p], NUM_PLAYERS)
            step_investments[p] = inv
            
        for p in players:
            start_cash = player_cash[p]
            inv = step_investments[p]
            new_cash, _ = update_assets(start_cash, inv, returns)
            player_cash[p] = new_cash
            
            log = create_log_entry(step, p, start_cash, inv, returns, new_cash, visible_ranks[p], visible_gaps[p])
            log['Is_Ranking_Published'] = is_published
            history_logs.append(log)

    df_results = save_logs_to_csv(history_logs)
    display_formatted_summary(df_results, HUMAN_PLAYER_ID)

if __name__ == "__main__":
    main()