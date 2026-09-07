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
    
    if len(stocks) != 4:
        raise ValueError("市場は4銘柄（高リスク2・安定2）を前提としています。")

    # 銘柄名による有利不利を作らないため、同じ種類の2銘柄は同一分布から生成する。
    high_risk_stocks = stocks[:2]
    stable_stocks = stocks[2:]

    # --- Step 1 〜 Step N ---
    for step in range(1, total_steps + 1):
        
        # 前半・後半で傾向が反転する予測可能な銘柄は置かず、毎ターン独立に生成する。
        returns = {
            **{s: np.random.normal(0.01, 0.15) for s in high_risk_stocks},
            **{s: np.random.normal(0.005, 0.02) for s in stable_stocks},
        }

        # 価格が負にならないよう、1ターンの損失率を -95% で打ち切る。
        returns = {s: max(ret, -0.95) for s, ret in returns.items()}
        
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
