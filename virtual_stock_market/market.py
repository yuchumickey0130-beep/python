# market.py
import pandas as pd
import numpy as np
from config import NUM_STEPS, STOCKS

def generate_and_save_market_data(total_steps=NUM_STEPS, stocks=STOCKS, seed=42, filename="market_data.csv", initial_price=100.0):
    np.random.seed(seed)
    market_list = []
    
    # --- Step 0 (基準状態) ---
    current_prices = {s: float(initial_price) for s in stocks}
    step_0_row = {'Step': 0}
    for s in stocks:
        step_0_row[f'{s}_Return'] = 0.0
        step_0_row[f'{s}_Price'] = current_prices[s]
    market_list.append(step_0_row)
    
    half_steps = total_steps / 2
    
    # ------------------------------------------
    # 外れ値（ショック）が発生するターンを事前に設定 (3〜7ターン間隔)
    # ------------------------------------------
    outlier_steps = set()
    current_step_count = np.random.randint(3, 8)
    while current_step_count <= total_steps:
        outlier_steps.add(current_step_count)
        current_step_count += np.random.randint(3, 8)

    # 銘柄の役割を配列のインデックスで割り当て
    s_w = stocks[0]
    s_x = stocks[1]
    s_y = stocks[2] 
    s_z = stocks[3] 

    # --- Step 1 〜 Step N ---
    for step in range(1, total_steps + 1):
        
        # 1. 0番目の銘柄: 大器晩成・超爆発株
        if step <= half_steps:
            drift_w, vol_w = -0.01, 0.06
        else:
            drift_w, vol_w = 0.03, 0.06
        ret_w = np.random.normal(drift_w, vol_w)
        
        # 2. 1番目の銘柄: ハイボラティリティ・超乱高下株
        ret_x = np.random.normal(0.05, 0.3)
        
        # 3. 2番目の銘柄: 安定成長株
        ret_y = np.random.normal(0.01, 0.01)
        
        # 4. 3番目の銘柄: 山型トレンド株
        if step <= half_steps:
            drift_z, vol_z = 0.03, 0.06
        else:
            drift_z, vol_z = -0.01, 0.06
        ret_z = np.random.normal(drift_z, vol_z)
        
        returns = {
            s_w: ret_w,
            s_x: ret_x,
            s_y: ret_y,
            s_z: ret_z
        }
        
        # ------------------------------------------
        # 外れ値ターン処理（ランダムな銘柄に±25%〜50%のショックを付与）
        # ------------------------------------------
        if step in outlier_steps:
            target_stocks = np.random.choice(stocks, size=np.random.choice([1, 2]), replace=False)
            for target in target_stocks:
                shock_direction = np.random.choice([-1, 1])
                shock_magnitude = np.random.uniform(0.25, 0.50)
                returns[target] += shock_direction * shock_magnitude
        
        row = {'Step': step}
        for s in stocks:
            row[f'{s}_Return'] = returns[s]
            current_prices[s] = current_prices[s] * (1 + returns[s])
            row[f'{s}_Price'] = current_prices[s]
            
        market_list.append(row)
        
    df_market = pd.DataFrame(market_list)
    df_market.to_csv(filename, index=False)
    return df_market

def get_market_info_at_step(df_market, step, stocks=STOCKS):
    curr_row = df_market[df_market['Step'] == step].iloc[0]
    prev_row = df_market[df_market['Step'] == (step - 1)].iloc[0]
    
    curr_prices = {s: curr_row[f'{s}_Price'] for s in stocks}
    prev_prices = {s: prev_row[f'{s}_Price'] for s in stocks}
    returns = {s: curr_row[f'{s}_Return'] for s in stocks}
    
    return curr_prices, prev_prices, returns