import math
import random

def investment_probability(A_invest, A_not_invest, lambda_):
    numerator = math.exp(lambda_ * A_invest)

    denominator = (
        math.exp(lambda_ * A_invest)
        + math.exp(lambda_ * A_not_invest)
    )

    return numerator / denominator

def choose_action(A_invest, A_not_invest, lambda_):
    p_invest = investment_probability(
        A_invest,
        A_not_invest,
        lambda_
    )

    if random.random() < p_invest:
        choice = 1
    else:
        choice = 0

    return choice, p_invest

def update_experience_weight(N, rho):
    return rho * N + 1

def update_attraction(
    old_attraction,
    old_N,
    new_N,
    payoff,
    chosen,
    phi,
    delta,
    social_term=0.0
):
    if chosen:
        payoff_weight = 1.0
    else:
        payoff_weight = delta

    new_attraction = (
        old_N * phi * old_attraction
        + payoff_weight * payoff
        + social_term
    ) / new_N

    return new_attraction

def calculate_payoffs(
    player_id,
    choices,
    endowment,
    successful_investors,
    return_multiplier,
    success_capacity
):
    # -------------------------
    # 非投資を選んだ場合のpayoff
    # -------------------------
    payoff_not_invest = endowment

    # -------------------------
    # 投資を選んだ場合のpayoff
    # -------------------------

    if choices[player_id] == 1:
        # 実際に投資した場合は、実現した結果を使う

        if player_id in successful_investors:
            payoff_invest = return_multiplier * endowment
        else:
            payoff_invest = 0

    else:
        # 実際には投資しなかった場合
        # 「もし投資していたら」を期待値で計算する

        other_investors = sum(choices)

        hypothetical_total_investors = other_investors + 1

        if hypothetical_total_investors <= success_capacity:
            success_probability = 1.0

        else:
            success_probability = (
                success_capacity
                / hypothetical_total_investors
            )

        payoff_invest = (
            success_probability
            * return_multiplier
            * endowment
        )

    return payoff_invest, payoff_not_invest