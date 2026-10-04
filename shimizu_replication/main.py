from ewa import (
    choose_action,
    update_experience_weight,
    update_attraction,
    calculate_payoffs
)

from config import (
    NUM_PLAYERS,
    NUM_PERIODS,
    INITIAL_WEALTH,
    SUCCESS_CAPACITY,
    RETURN_MULTIPLIER,
    INTEREST_RATE,
    FIXED_ENDOWMENT,
    NUM_SIMULATIONS,
    VERBOSE,
    LAMBDA,
    PHI,
    DELTA,
    RHO,
    ETA,
    MIN_HIGH_INTERVAL,
    MAX_HIGH_INTERVAL,
    CONDITIONS
)

import random
import csv

def get_endowments(wealth, condition):
    if condition == "FIX":
        return [FIXED_ENDOWMENT] * NUM_PLAYERS

    elif condition == "CO":
        return [w * INTEREST_RATE for w in wealth]

    else:
        raise ValueError("condition must be 'FIX' or 'CO'")

def calculate_ranks(wealth):
    ranks = []

    for i in range(NUM_PLAYERS):
        higher_count = 0

        for j in range(NUM_PLAYERS):
            if wealth[j] > wealth[i]:
                higher_count += 1

        ranks.append(higher_count + 1)

    return ranks

def generate_high_periods():
    high_periods = [1]

    current_period = 1

    while True:
        interval = random.randint(
            MIN_HIGH_INTERVAL,
            MAX_HIGH_INTERVAL
        )

        next_high = current_period + interval

        high_periods.append(next_high)

        if next_high > NUM_PERIODS:
            break

        current_period = next_high

    return high_periods


def play_one_period(wealth, choices, condition):
    endowments = get_endowments(wealth, condition)

    investors = []

    for i in range(NUM_PLAYERS):
        if choices[i] == 1:
            investors.append(i)

    if len(investors) <= SUCCESS_CAPACITY:
        successful_investors = investors
    else:
        successful_investors = random.sample(
            investors,
            SUCCESS_CAPACITY
        )

    for i in range(NUM_PLAYERS):

        if choices[i] == 0:
            wealth[i] += endowments[i]

        elif i in successful_investors:
            wealth[i] += RETURN_MULTIPLIER * endowments[i]

        else:
            pass

    return wealth, endowments, successful_investors

# =========================
# シミュレーション実行
# =========================

all_logs = []

for simulation in range(1, NUM_SIMULATIONS + 1):

    if (
        simulation == 1
        or simulation % 10 == 0
        or simulation == NUM_SIMULATIONS
    ):

        print(
            f"Simulation {simulation}/{NUM_SIMULATIONS}"
        )

    for endowment_condition, visibility_condition in CONDITIONS:

        if VERBOSE:
            print(
                f"\n"
                f"============================\n"
                f"Condition: "
                f"{endowment_condition}-{visibility_condition}\n"
                f"============================"
            )

        wealth = [INITIAL_WEALTH] * NUM_PLAYERS

        A_invest = [45.286] * NUM_PLAYERS
        A_not_invest = [0.0] * NUM_PLAYERS
        N = [1.0] * NUM_PLAYERS

        for period in range(1, NUM_PERIODS + 1):

            ranks_before = calculate_ranks(wealth)

            choices = []
            investment_probs = []

            for i in range(NUM_PLAYERS):

                choice, p_invest = choose_action(
                    A_invest[i],
                    A_not_invest[i],
                    LAMBDA
                )

                choices.append(choice)
                investment_probs.append(p_invest)

            wealth_before = wealth.copy()

            wealth, endowments, successful_investors = play_one_period(
                wealth,
                choices,
                endowment_condition
            )

            # =========================
            # Rank計算
            # =========================
    
            ranks_after = calculate_ranks(wealth)

            top_wealth = max(wealth)

            wealth_gaps = []
            social_terms = []

            for i in range(NUM_PLAYERS):
                gap = top_wealth - wealth[i]
                wealth_gaps.append(gap)

                if visibility_condition == "HIGH":
                    social_term = ETA * wealth_gaps[i]
                else:
                    social_term = 0.0

                social_terms.append(social_term)

                payoff_invest, payoff_not_invest = calculate_payoffs(
                    player_id=i,
                    choices=choices,
                    endowment=endowments[i],
                    successful_investors=successful_investors,
                    return_multiplier=RETURN_MULTIPLIER,
                    success_capacity=SUCCESS_CAPACITY
                )

                old_N = N[i]

                new_N = update_experience_weight(
                    old_N,
                    RHO
                )

                new_A_invest = update_attraction(
                    old_attraction=A_invest[i],
                    old_N=old_N,
                    new_N=new_N,
                    payoff=payoff_invest,
                    chosen=(choices[i] == 1),
                    phi=PHI,
                    delta=DELTA,
                    social_term=social_term
                )

                new_A_not_invest = update_attraction(
                    old_attraction=A_not_invest[i],
                    old_N=old_N,
                    new_N=new_N,
                    payoff=payoff_not_invest,
                    chosen=(choices[i] == 0),
                    phi=PHI,
                    delta=DELTA
                )

                A_invest[i] = new_A_invest
                A_not_invest[i] = new_A_not_invest
                N[i] = new_N

            # =========================
            # ログを保存
            # =========================

            for i in range(NUM_PLAYERS):

                if choices[i] == 0:
                    result = "Not Invest"
                elif i in successful_investors:
                    result = "Success"
                else:
                    result = "Fail"

                all_logs.append({
                    "Simulation": simulation,
                    "Period": period,
                    "Player": i + 1,
                    "Rank_Before": ranks_before[i],
                    "Rank_After": ranks_after[i],
                    "Endowment_Condition": endowment_condition,
                    "Visibility_Condition": visibility_condition,
                    "Choice": choices[i],
                    "Wealth_Before": round(wealth_before[i], 2),
                    "Endowment": round(endowments[i], 2),
                    "Result": result,
                    "Wealth_After": round(wealth[i], 2),
                    "Wealth_Gap": round(wealth_gaps[i], 2),
                    "Social_Term": round(social_terms[i], 3),
                    "Investment_Probability": round(investment_probs[i], 3),
                    "A_Invest": round(A_invest[i], 3),
                    "A_Not_Invest": round(A_not_invest[i], 3),
                    "N": round(N[i], 3)
                })

            if VERBOSE:
                print(f"\n===== Period {period} =====")
                
                for i in range(NUM_PLAYERS):
                    result = ""
    
                    if choices[i] == 0:
                        result = "Not Invest"
                    elif i in successful_investors:
                        result = "Invest / Success"
                    else:
                        result = "Invest / Fail"
                    
                    print(
                        f"Player {i + 1:>2} | "
                        f"Rank={ranks_before[i]:>2}->{ranks_after[i]:<2} | "
                        f"Wealth={wealth[i]:>8.2f} | "
                        f"B={endowments[i]:>7.2f} | "
                        f"Gap={wealth_gaps[i]:>8.2f} | "
                        f"Social={social_terms[i]:>8.3f} | "
                        f"P(Invest)={investment_probs[i]:>6.3f} | "
                        f"A_Invest={A_invest[i]:>8.3f} | "
                        f"A_Not={A_not_invest[i]:>8.3f} | "
                        f"N={N[i]:>6.3f} | "
                        f"Result={result:<16}"
                    )

# =========================
# CSVとして保存
# =========================

filename = "simulation_all_conditions.csv"

with open(filename, "w", newline="", encoding="utf-8") as f:

    fieldnames = [
        "Simulation",
        "Period",
        "Player",
        "Rank_Before",
        "Rank_After",
        "Endowment_Condition",
        "Visibility_Condition",
        "Choice",
        "Wealth_Before",
        "Endowment",
        "Result",
        "Wealth_After",
        "Wealth_Gap",
        "Social_Term",
        "Investment_Probability",
        "A_Invest",
        "A_Not_Invest",
        "N"
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(all_logs)

print(f"\nログを {filename} に保存しました。")
print(f"ログ件数: {len(all_logs)}")