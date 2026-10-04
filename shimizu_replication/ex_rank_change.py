import pandas as pd
import matplotlib.pyplot as plt


# ==============================
# 1. データ読み込み
# ==============================

df = pd.read_csv("simulation_all_conditions.csv")


# ==============================
# 2. 時系列順に並べる
# ==============================

df = df.sort_values([
    "Endowment_Condition",
    "Visibility_Condition",
    "Simulation",
    "Player",
    "Period"
])


# ==============================
# 3. 前期の順位を取得
# ==============================

df["Rank_Previous"] = (
    df
    .groupby([
        "Endowment_Condition",
        "Visibility_Condition",
        "Simulation",
        "Player"
    ])["Rank_After"]
    .shift(1)
)


# ==============================
# 4. 順位変化を計算
# ==============================

df["Rank_Change"] = (
    df["Rank_After"]
    - df["Rank_Previous"]
)


# ==============================
# 5. 次期の投資行動を取得
# ==============================

df["Choice_Next"] = (
    df
    .groupby([
        "Endowment_Condition",
        "Visibility_Condition",
        "Simulation",
        "Player"
    ])["Choice"]
    .shift(-1)
)


# ==============================
# 6. 分析可能な行だけ残す
# ==============================

rank_change_df = df.dropna(
    subset=[
        "Rank_Change",
        "Choice_Next"
    ]
).copy()


# ==============================
# 7. 順位変化ごとの次期投資率
# ==============================

rank_change_summary = (
    rank_change_df
    .groupby([
        "Endowment_Condition",
        "Visibility_Condition",
        "Rank_Change"
    ])["Choice_Next"]
    .agg(["mean", "count"])
    .reset_index()
)

# print("\n=== Investment Rate by Rank Change ===")
# print(rank_change_summary.to_string(index=False))


# ==============================
# 8. グラフ
# ==============================

# fig, axes = plt.subplots(
#     1, 2,
#     figsize=(12, 5),
#     sharey=True
# )

# for ax, endowment_condition in zip(
#     axes,
#     ["CO", "FIX"]
# ):

#     for visibility_condition in ["HIGH", "LOW"]:

#         plot_data = rank_change_summary[
#             (
#                 rank_change_summary["Endowment_Condition"]
#                 == endowment_condition
#             )
#             &
#             (
#                 rank_change_summary["Visibility_Condition"]
#                 == visibility_condition
#             )
#         ]

#         ax.plot(
#             plot_data["Rank_Change"],
#             plot_data["mean"],
#             marker="o",
#             label=visibility_condition
#         )

#     ax.axvline(
#         0,
#         linestyle="--",
#         alpha=0.5
#     )

#     ax.set_title(endowment_condition)
#     ax.set_xlabel("Rank Change")
#     ax.set_ylabel("Next-period Investment Rate")
#     ax.legend()

# plt.tight_layout()
# plt.show()

# ==============================
# 9. 現在順位 × 順位変化
# ==============================

rank_interaction = (
    rank_change_df
    .groupby([
        "Endowment_Condition",
        "Visibility_Condition",
        "Rank_After",
        "Rank_Change"
    ])["Choice_Next"]
    .agg(["mean", "count"])
    .reset_index()
)

# print("\n=== Current Rank × Rank Change ===")
# print(rank_interaction.to_string(index=False))


# ==============================
# 10. 現在順位ごとにグラフ化
# ==============================

# fig, axes = plt.subplots(
#     2, 4,
#     figsize=(16, 8),
#     sharex=True,
#     sharey=True
# )

# for rank in range(1, 9):

#     row = (rank - 1) // 4
#     col = (rank - 1) % 4

#     ax = axes[row, col]

#     for visibility_condition in ["HIGH", "LOW"]:

#         plot_data = rank_interaction[
#             (rank_interaction["Endowment_Condition"] == "CO")
#             &
#             (rank_interaction["Visibility_Condition"] == visibility_condition)
#             &
#             (rank_interaction["Rank_After"] == rank)
#             &
#             (rank_interaction["count"] >= 100)
#         ]

#         ax.plot(
#             plot_data["Rank_Change"],
#             plot_data["mean"],
#             marker="o",
#             label=visibility_condition
#         )

#     ax.axvline(
#         0,
#         linestyle="--",
#         alpha=0.5
#     )

#     ax.set_title(f"Current Rank = {rank}")
#     ax.set_xlabel("Rank Change")
#     ax.set_ylabel("Next-period Investment Rate")

#     ax.legend()

# plt.tight_layout()
# plt.show()

# ==============================
# 11. Result × 順位変化
# ==============================

result_interaction = (
    rank_change_df
    .groupby([
        "Visibility_Condition",
        "Result",
        "Rank_Change"
    ])["Choice_Next"]
    .agg(["mean", "count"])
    .reset_index()
)

# CO条件だけに限定
result_interaction_co = (
    rank_change_df[
        rank_change_df["Endowment_Condition"] == "CO"
    ]
    .groupby([
        "Visibility_Condition",
        "Result",
        "Rank_Change"
    ])["Choice_Next"]
    .agg(["mean", "count"])
    .reset_index()
)

# print("\n=== Result × Rank Change (CO) ===")
# print(result_interaction_co.to_string(index=False))


# ==============================
# 12. Resultごとにグラフ化 

# fig, axes = plt.subplots(
#     1, 3,
#     figsize=(15, 5),
#     sharey=True
# )

# results = [
#     "Success",
#     "Fail",
#     "Not Invest"
# ]

# for ax, result in zip(axes, results):

#     for visibility_condition in ["HIGH", "LOW"]:

#         plot_data = result_interaction_co[
#             (result_interaction_co["Result"] == result)
#             &
#             (
#                 result_interaction_co["Visibility_Condition"]
#                 == visibility_condition
#             )
#             &
#             (result_interaction_co["count"] >= 100)
#         ]

#         ax.plot(
#             plot_data["Rank_Change"],
#             plot_data["mean"],
#             marker="o",
#             label=visibility_condition
#         )

#     ax.axvline(
#         0,
#         linestyle="--",
#         alpha=0.5
#     )

#     ax.set_title(result)
#     ax.set_xlabel("Rank Change")
#     ax.set_ylabel("Next-period Investment Rate")
#     ax.legend()

# plt.tight_layout()
# plt.show()

# ==============================
# 13. Result × 順位変化 × Wealth
# ==============================

wealth_interaction_co = (
    rank_change_df[
        rank_change_df["Endowment_Condition"] == "CO"
    ]
    .groupby([
        "Visibility_Condition",
        "Result",
        "Rank_Change"
    ])["Wealth_After"]
    .agg(["mean", "median", "count"])
    .reset_index()
)

# print("\n=== Wealth by Result × Rank Change (CO) ===")
# print(wealth_interaction_co.to_string(index=False))


# ==============================
# 14. Resultごとにグラフ化
# ==============================

# fig, axes = plt.subplots(
#     1, 3,
#     figsize=(15, 5),
#     sharey=True
# )

# results = [
#     "Success",
#     "Fail",
#     "Not Invest"
# ]

# for ax, result in zip(axes, results):

#     for visibility_condition in ["HIGH", "LOW"]:

#         plot_data = wealth_interaction_co[
#             (wealth_interaction_co["Result"] == result)
#             &
#             (
#                 wealth_interaction_co["Visibility_Condition"]
#                 == visibility_condition
#             )
#             &
#             (wealth_interaction_co["count"] >= 100)
#         ]

#         ax.plot(
#             plot_data["Rank_Change"],
#             plot_data["median"],
#             marker="o",
#             label=visibility_condition
#         )

#     ax.axvline(
#         0,
#         linestyle="--",
#         alpha=0.5
#     )

#     ax.set_title(result)
#     ax.set_xlabel("Rank Change")
#     ax.set_ylabel("Median Wealth After")
#     ax.legend()

# plt.tight_layout()
# plt.show()

# ==============================
# 15. 現在順位 × 順位変化 × A_Invest
# ==============================

rank_change_df["Attraction_Difference"] = (
    rank_change_df["A_Invest"]
    - rank_change_df["A_Not_Invest"]
)

attraction_interaction = (
    rank_change_df[
        rank_change_df["Endowment_Condition"] == "CO"
    ]
    .groupby([
        "Visibility_Condition",
        "Rank_After",
        "Rank_Change"
    ])["Attraction_Difference"]
    .agg(["mean", "median", "count"])
    .reset_index()
)

print("\n=== Attraction Difference by Current Rank × Rank Change (CO) ===")
print(attraction_interaction.to_string(index=False))


# ==============================
# 16. 現在順位ごとにグラフ化
# ==============================

fig, axes = plt.subplots(
    2, 4,
    figsize=(16, 8),
    sharex=True,
    sharey=True
)

for rank in range(1, 9):

    row = (rank - 1) // 4
    col = (rank - 1) % 4

    ax = axes[row, col]

    for visibility_condition in ["HIGH", "LOW"]:

        plot_data = attraction_interaction[
            (attraction_interaction["Visibility_Condition"]
             == visibility_condition)
            &
            (attraction_interaction["Rank_After"] == rank)
            &
            (attraction_interaction["count"] >= 100)
        ]

        ax.plot(
            plot_data["Rank_Change"],
            plot_data["median"],
            marker="o",
            label=visibility_condition
        )

    ax.axvline(
        0,
        linestyle="--",
        alpha=0.5
    )

    ax.set_title(f"Current Rank = {rank}")
    ax.set_xlabel("Rank Change")
    ax.set_ylabel("Median Attraction Difference")
    ax.legend()

plt.tight_layout()
plt.show()