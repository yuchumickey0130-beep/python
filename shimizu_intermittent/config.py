# =========================
# Experiment settings
# =========================

NUM_PERIODS = 22
# Pattern 1: 22 turns (intervals 2-6); pattern 2: 16 turns (intervals 2-5).
# This is the default for each newly started game; the admin may select a pattern at game breaks.
GAME_PATTERN = 1
NUM_PLAYERS = 8
SUCCESS_CAPACITY = 4

INITIAL_WEALTH = 500
INTEREST_RATE = 0.10
RETURN_MULTIPLIER = 1.6

MIN_HIGH_INTERVAL = 2
MAX_HIGH_INTERVAL = 6


# =========================
# Development settings
# =========================

TEST_MODE = False
TEST_NUM_PLAYERS = 2
TEST_NUM_PERIODS = 1

EXPLANATION_MODE = True
PRACTICE_MODE = True

ALLOW_ADMIN_RESET = True