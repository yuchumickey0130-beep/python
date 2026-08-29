# player.py
from config import STOCKS, NUM_PLAYERS

def decide_investment_human(player_id, current_cash, visible_rank, curr_prices, prev_prices, stocks=STOCKS):
    print(f"\n==========================================")
    print(f"【あなたのターン: {player_id}】")
    print(f"現在の所持現金: {current_cash:,.1f} 円")
    if visible_rank is not None:
        print(f"現在の公開順位: {visible_rank} 位")
    else:
        print(f"現在の公開順位: [非公開]")
    
    print(f"------------------------------------------")
    print(f"【株式市場の情報】")
    for s in stocks:
        c_p = curr_prices[s]
        p_p = prev_prices[s]
        change_pct = ((c_p - p_p) / p_p) * 100
        sign = "+" if change_pct >= 0 else ""
        print(f" ・{s:7s} | 現在価格: {c_p:6.1f}円 (前ターン: {p_p:6.1f}円 | 前期比: {sign}{change_pct:+.2f}%)")
    print(f"------------------------------------------")
    
    investments = {}
    remaining_cash = current_cash
    
    for s in stocks:
        while True:
            try:
                val = float(input(f"  {s} への投資額 (残金 {remaining_cash:,.1f}円): "))
                if val < 0:
                    print("  0以上の数値を入力してください。")
                elif val > remaining_cash:
                    print("  手持ちの現金を超えています！")
                else:
                    investments[s] = val
                    remaining_cash -= val
                    break
            except ValueError:
                print("  有効な数字を入力してください。")
                
    return investments

def decide_investment_ai(player_id, current_cash, visible_rank, total_players=NUM_PLAYERS, stocks=STOCKS):
    """AI（簡易モデル）の判断ロジック"""
    if visible_rank is None:
        # ランキング非公開：全体に均等分散
        inv = {s: current_cash * 0.2 for s in stocks}
    else:
        if visible_rank == total_players:  # 最下位：一発逆転を狙ってリスク株へ集中
            inv = {
                'Stock_W': current_cash * 0.3,
                'Stock_X': current_cash * 0.4,
                'Stock_Y': 0.0,
                'Stock_Z': current_cash * 0.2
            }
        elif visible_rank == 1:            # 1位：守りの投資（安定株メイン）
            inv = {
                'Stock_W': 0.0,
                'Stock_X': 0.0,
                'Stock_Y': current_cash * 0.4,
                'Stock_Z': current_cash * 0.1
            }
        else:                              # 中間順位
            inv = {
                'Stock_W': current_cash * 0.15,
                'Stock_X': current_cash * 0.2,
                'Stock_Y': current_cash * 0.25,
                'Stock_Z': current_cash * 0.15
            }
            
    return inv

def update_assets(start_cash, investments, returns):
    cash_left = start_cash - sum(investments.values())
    payoffs = {s: investments[s] * (1 + returns[s]) for s in investments}
    new_cash = cash_left + sum(payoffs.values())
    return new_cash, payoffs