# analysis.py
import pandas as pd

def create_log_entry(step, player_id, start_cash, investments, returns, end_cash, rank, top_asset_gap):
    total_invested = sum(investments.values())
    risk_ratio = total_invested / start_cash if start_cash > 0 else 0.0
    
    log_entry = {
        'Step': step,
        'Player': player_id,
        'Start_Cash': round(start_cash, 1),
        'Risk_Ratio': round(risk_ratio, 2),
        'End_Cash': round(end_cash, 1),
        'Rank': rank if rank is not None else '-',
        'Asset_Gap_From_Top': round(top_asset_gap, 1) if top_asset_gap is not None else '-'
    }
    for s in investments:
        log_entry[f'Inv_{s}'] = round(investments[s], 1)
        log_entry[f'Return_{s}'] = round(returns[s], 3)
        
    return log_entry

def save_logs_to_csv(history_logs, filename="experiment_results.csv"):
    df = pd.DataFrame(history_logs)
    df.to_csv(filename, index=False)
    print(f"\n実験ログを '{filename}' に保存しました。")
    return df

def display_formatted_summary(df, human_player_id):
    """ターミナル上でログを綺麗に整列して表示し、人間プレイヤーの最終成績を出力する関数"""
    
    # ------------------------------------------
    # pandasの表示オプション（整列・文字幅・桁数の見た目を整える）
    # ------------------------------------------
    pd.set_option('display.max_columns', None)        # 全列を表示
    pd.set_option('display.width', 1000)             # 折返し幅を広げる
    pd.set_option('display.unicode.east_asian_width', True) # 日本語の文字幅のズレを補正
    pd.set_option('display.float_format', '{:.1f}'.format)  # 小数点第1位までに揃える
    
    print("\n==========================================")
    print("【実験ログの確認（主要項目）】")
    print("==========================================")
    
    # 分析用に主要な列だけを選んで綺麗に表示
    cols_to_show = ['Step', 'Player', 'Start_Cash', 'End_Cash', 'Rank', 'Risk_Ratio', 'Is_Ranking_Published']
    print(df[cols_to_show].head(15).to_string(index=False)) # インデックス番号を消してスッキリ表示
    
    # ------------------------------------------
    # 選んだプレイヤーの最終結果（最終ターン時点）の計算と表示
    # ------------------------------------------
    last_step = df['Step'].max()
    final_df = df[df['Step'] == last_step]
    
    # 最終ターン時点での実際の資産額で順位を再計算（最終結果確定用）
    sorted_final = final_df.sort_values(by='End_Cash', ascending=False).reset_index(drop=True)
    
    print("\n==========================================")
    print(f"  --- 最終ゲーム結果 (Step {last_step}) ---")
    print("==========================================")
    
    for idx, row in sorted_final.iterrows():
        rank = idx + 1
        p_name = row['Player']
        cash = row['End_Cash']
        
        # あなた（操作プレイヤー）には強調マークを付与
        mark = " ★ あなた" if p_name == human_player_id else ""
        print(f" 第 {rank} 位 : {p_name} | 最終資産: {cash:,.1f} 円{mark}")
        
    print("==========================================\n")