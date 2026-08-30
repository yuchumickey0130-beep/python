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
    
    # stocks の要素数に応じて動的に比率を割り当てる（ハードコーディングの不一致を防止）
    n_stocks = len(stocks)
    inv = {s: 0.0 for s in stocks}

    if visible_rank is None:
        # ランキング非公開：全銘柄に均等分散（現金全体の20%ずつを各銘柄へ）
        ratio = 0.8 / n_stocks if n_stocks > 0 else 0
        inv = {s: current_cash * ratio for s in stocks}
    else:
        if visible_rank == total_players:  # 最下位：ハイリスク傾向（前半の銘柄に集中投資）
            if n_stocks >= 2:
                inv[stocks[0]] = current_cash * 0.4
                inv[stocks[1]] = current_cash * 0.4
            elif n_stocks == 1:
                inv[stocks[0]] = current_cash * 0.8
        elif visible_rank == 1:            # 1位：守りの投資（後半の銘柄に控えめ投資）
            if n_stocks >= 2:
                inv[stocks[-1]] = current_cash * 0.2
                inv[stocks[-2]] = current_cash * 0.2
            elif n_stocks == 1:
                inv[stocks[0]] = current_cash * 0.3
        else:                              # 中間順位：バランス投資
            ratio = 0.6 / n_stocks if n_stocks > 0 else 0
            inv = {s: current_cash * ratio for s in stocks}
            
    return inv

def update_assets(start_cash, investments, returns):
    """資産の更新計算（キー参照の型エラーを防止する安全設計）"""
    cash_left = start_cash - sum(investments.values())
    
    # returns[s] ではなく returns.get(s, 0.0) を使用することで KeyError / TypeError を回避
    payoffs = {s: investments[s] * (1 + returns.get(s, 0.0)) for s in investments}
    
    new_cash = cash_left + sum(payoffs.values())
    return new_cash, payoffs