# ranking.py
import importlib
import config

importlib.reload(config)  # config モジュールを強制再読み込み

def calculate_ranking_info(step, player_cash, is_ranking_visible, ranking_interval):
    sorted_players = sorted(player_cash.items(), key=lambda x: x[1], reverse=True)
    actual_ranks = {p: i + 1 for i, (p, a) in enumerate(sorted_players)}
    top_asset = sorted_players[0][1]
    actual_gaps = {p: top_asset - player_cash[p] for p in player_cash}
    
    is_published = is_ranking_visible and (step % ranking_interval == 0)
    
    if is_published:
        return actual_ranks, actual_gaps, True
    else:
        none_ranks = {p: None for p in player_cash}
        none_gaps = {p: None for p in player_cash}
        return none_ranks, none_gaps, False