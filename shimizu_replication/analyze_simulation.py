import pandas as pd
import matplotlib.pyplot as plt

# =========================
# CSV読み込み
# =========================

df = pd.read_csv("simulation_all_conditions.csv")

# =========================
# Period 11-15 のみ抽出
# =========================

df_late = df[
    (df["Period"] >= 11) &
    (df["Period"] <= 15)
]

# =========================
# Rank別投資率
# =========================

rank_summary = (
    df_late
    .groupby([
        "Endowment_Condition",
        "Visibility_Condition",
        "Rank_Before"
    ])["Choice"]
    .agg(["mean", "std", "count"])
    .reset_index()
)

rank_summary["se"] = (
    rank_summary["std"] /
    rank_summary["count"] ** 0.5
)

# =========================
# Figure 2 Predicted風
# =========================

# conditions = [
#     ("CO", "HIGH"),
#     ("CO", "LOW"),
#     ("FIX", "HIGH"),
#     ("FIX", "LOW")
# ]

# titles = [
#     "CO-High",
#     "CO-Low",
#     "Fix-High",
#     "Fix-Low"
# ]

# fig, axes = plt.subplots(
#     1, 4,
#     figsize=(12, 3.5),
#     sharey=True
# )

# for ax, (endowment, visibility), title in zip(
#     axes,
#     conditions,
#     titles
# ):

#     subset = rank_summary[
#         (rank_summary["Endowment_Condition"] == endowment)
#         &
#         (rank_summary["Visibility_Condition"] == visibility)
#     ]

#     ax.plot(
#         subset["Rank_Before"],
#         subset["mean"],
#         marker="o"
#     )

#     ax.set_title(title)
#     ax.set_xlabel("Rank")
#     ax.set_xticks(range(1, 9))
#     ax.set_ylim(0, 1)

#     ax.grid(True)

# axes[0].set_ylabel("Probability of investment")

# plt.suptitle(
#     "Predicted Investment Probability by Rank (Periods 11–15)"
# )

# plt.tight_layout()

# plt.show()

# ============================================================
# Figure 3: Rank Change
# ============================================================

# rank_df = df[
#     [
#         "Simulation",
#         "Period",
#         "Player",
#         "Rank_After",
#         "Endowment_Condition",
#         "Visibility_Condition"
#     ]
# ].copy()


# # =========================
# # 順位変化を計算する関数
# # =========================

# def calculate_rank_change(data, k):

#     temp = data.copy()

#     # 念のため時系列順に並べる
#     temp = temp.sort_values(
#         [
#             "Endowment_Condition",
#             "Visibility_Condition",
#             "Simulation",
#             "Player",
#             "Period"
#         ]
#     )

#     # 同じPlayerの k 期間後の順位
#     temp["Rank_Future"] = (
#         temp
#         .groupby([
#             "Endowment_Condition",
#             "Visibility_Condition",
#             "Simulation",
#             "Player"
#         ])["Rank_After"]
#         .shift(-k)
#     )

#     # |r_t,i - r_t+k,i|
#     temp["Rank_Difference"] = (
#         temp["Rank_After"] -
#         temp["Rank_Future"]
#     ).abs()

#     # k期間後が存在しない行を除く
#     temp = temp.dropna(
#         subset=["Rank_Future"]
#     )

#     # 8人について平均
#     # d(r_t, r_t+k)
#     group_rank_change = (
#         temp
#         .groupby([
#             "Endowment_Condition",
#             "Visibility_Condition",
#             "Simulation",
#             "Period"
#         ])["Rank_Difference"]
#         .mean()
#         .reset_index()
#     )

#     group_rank_change["k"] = k

#     return group_rank_change


# # =========================
# # k = 1, 10 を計算
# # =========================

# rank_change_k1 = calculate_rank_change(
#     rank_df,
#     k=1
# )

# rank_change_k10 = calculate_rank_change(
#     rank_df,
#     k=10
# )

# rank_change = pd.concat(
#     [
#         rank_change_k1,
#         rank_change_k10
#     ],
#     ignore_index=True
# )


# # =========================
# # シミュレーション間で平均
# # =========================

# rank_change_summary = (
#     rank_change
#     .groupby([
#         "Endowment_Condition",
#         "Visibility_Condition",
#         "Period",
#         "k"
#     ])["Rank_Difference"]
#     .mean()
#     .reset_index()
# )


# print("\n=== Rank Change Summary ===")
# print(rank_change_summary.head(20))


# # =========================
# # Figure 3 描画
# # =========================

# fig, axes = plt.subplots(
#     2,
#     2,
#     figsize=(10, 7),
#     sharey="row"
# )

# plot_settings = [
#     ("CO", 1, axes[0, 0], "Carry-Over"),
#     ("FIX", 1, axes[0, 1], "Fix"),
#     ("CO", 10, axes[1, 0], "Carry-Over"),
#     ("FIX", 10, axes[1, 1], "Fix")
# ]


# for (
#     endowment_condition,
#     k,
#     ax,
#     title
# ) in plot_settings:

#     for visibility_condition in [
#         "HIGH",
#         "LOW"
#     ]:

#         subset = rank_change_summary[
#             (
#                 rank_change_summary[
#                     "Endowment_Condition"
#                 ]
#                 == endowment_condition
#             )
#             &
#             (
#                 rank_change_summary[
#                     "Visibility_Condition"
#                 ]
#                 == visibility_condition
#             )
#             &
#             (
#                 rank_change_summary["k"]
#                 == k
#             )
#         ]

#         ax.plot(
#             subset["Period"],
#             subset["Rank_Difference"],
#             label=visibility_condition
#         )

#     ax.set_title(title)

#     ax.set_xlabel("Period")

#     ax.grid(True)

#     ax.legend()


# axes[0, 0].set_ylabel(
#     "Mean Absolute Difference"
# )

# axes[1, 0].set_ylabel(
#     "Mean Absolute Difference"
# )

# axes[0, 0].text(
#     0.02,
#     1.12,
#     "Rank Change: k = 1",
#     transform=axes[0, 0].transAxes,
#     fontsize=12
# )

# axes[1, 0].text(
#     0.02,
#     1.12,
#     "Rank Change: k = 10",
#     transform=axes[1, 0].transAxes,
#     fontsize=12
# )

# plt.tight_layout()

# plt.show()

# # ============================================================
# # HIGH - LOW の差を計算
# # ============================================================

# # HIGHとLOWを横並びにする
# visibility_comparison = (
#     rank_change_summary
#     .pivot(
#         index=[
#             "Endowment_Condition",
#             "Period",
#             "k"
#         ],
#         columns="Visibility_Condition",
#         values="Rank_Difference"
#     )
#     .reset_index()
# )

# # HIGH - LOW を計算
# visibility_comparison["HIGH_minus_LOW"] = (
#     visibility_comparison["HIGH"]
#     - visibility_comparison["LOW"]
# )


# # =========================
# # 条件ごとの平均
# # =========================

# visibility_effect_summary = (
#     visibility_comparison
#     .groupby([
#         "Endowment_Condition",
#         "k"
#     ])["HIGH_minus_LOW"]
#     .mean()
#     .reset_index()
# )


# print(
#     "\n=== Mean Visibility Effect "
#     "(HIGH - LOW) ==="
# )

# print(visibility_effect_summary)

# ============================================================
# Figure 4: 資産の格差指標
# ============================================================

import numpy as np


# =========================
# Gini係数を計算する関数
# =========================

def calculate_gini(values):

    values = np.array(values, dtype=float)

    # 小さい順に並べる
    values = np.sort(values)

    n = len(values)

    # 資産の合計が0の場合への対策
    if values.sum() == 0:
        return 0.0

    gini = (
        2
        * np.sum(
            np.arange(1, n + 1)
            * values
        )
        / (n * values.sum())
        - (n + 1) / n
    )

    return gini


# =========================
# 各グループ・各Periodの格差指標を計算
# =========================

inequality_logs = []

grouped = df.groupby([
    "Endowment_Condition",
    "Visibility_Condition",
    "Simulation",
    "Period"
])


for (
    endowment_condition,
    visibility_condition,
    simulation,
    period
), group in grouped:

    wealth = (
        group["Wealth_After"]
        .to_numpy()
    )

    # -------------------------
    # Gini係数
    # -------------------------

    gini = calculate_gini(wealth)

    # -------------------------
    # Standard Deviation
    # -------------------------

    sd = np.std(
        wealth,
        ddof=1
    )

    # -------------------------
    # 資産を大きい順に並べる
    # -------------------------

    sorted_wealth = np.sort(wealth)[::-1]

    # -------------------------
    # Top 50%
    # 上位4人 / 下位4人
    # -------------------------

    top_50_ratio = (
        sorted_wealth[:4].sum()
        / sorted_wealth[4:].sum()
    )

    # -------------------------
    # Top 25%
    # 上位2人 / 残り6人
    # -------------------------

    top_25_ratio = (
        sorted_wealth[:2].sum()
        / sorted_wealth[2:].sum()
    )

    inequality_logs.append({
        "Endowment_Condition":
            endowment_condition,

        "Visibility_Condition":
            visibility_condition,

        "Simulation":
            simulation,

        "Period":
            period,

        "Gini":
            gini,

        "SD":
            sd,

        "Top_50_Ratio":
            top_50_ratio,

        "Top_25_Ratio":
            top_25_ratio
    })


# =========================
# DataFrameに変換
# =========================

inequality_df = pd.DataFrame(
    inequality_logs
)


# =========================
# 1000 simulations の平均
# =========================

inequality_summary = (
    inequality_df
    .groupby([
        "Endowment_Condition",
        "Visibility_Condition",
        "Period"
    ])[
        [
            "Gini",
            "SD",
            "Top_50_Ratio",
            "Top_25_Ratio"
        ]
    ]
    .mean()
    .reset_index()
)


print(
    "\n=== Inequality Summary ==="
)

print(
    inequality_summary.head(20)
)


# ============================================================
# Figure 4 描画
# ============================================================

fig, axes = plt.subplots(
    2,
    2,
    figsize=(10, 7)
)


# =========================
# 描画設定
# =========================

plot_settings = [
    (
        "Gini",
        axes[0, 0],
        "Gini coefficient"
    ),
    (
        "SD",
        axes[0, 1],
        "Standard deviation"
    ),
    (
        "Top_50_Ratio",
        axes[1, 0],
        "Disparity ratio (Top 50%)"
    ),
    (
        "Top_25_Ratio",
        axes[1, 1],
        "Disparity ratio (Top 25%)"
    )
]


# =========================
# 4つの指標を描画
# =========================

for metric, ax, title in plot_settings:

    for (
        endowment_condition,
        visibility_condition
    ) in [
        ("CO", "HIGH"),
        ("CO", "LOW"),
        ("FIX", "HIGH"),
        ("FIX", "LOW")
    ]:

        subset = inequality_summary[
            (
                inequality_summary[
                    "Endowment_Condition"
                ]
                == endowment_condition
            )
            &
            (
                inequality_summary[
                    "Visibility_Condition"
                ]
                == visibility_condition
            )
        ]

        label = (
            f"{endowment_condition}-"
            f"{visibility_condition}"
        )

        ax.plot(
            subset["Period"],
            subset[metric],
            label=label
        )

    ax.set_title(title)
    ax.set_xlabel("Period")
    ax.grid(True)
    ax.legend()


plt.tight_layout()

plt.show()