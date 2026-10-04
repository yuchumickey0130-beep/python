# =========================
# Experiment settings
# =========================

NUM_PLAYERS = 8
NUM_PERIODS = 50

INITIAL_WEALTH = 500

SUCCESS_CAPACITY = 4
RETURN_MULTIPLIER = 1.6

INTEREST_RATE = 0.10
FIXED_ENDOWMENT = 50


# =========================
# Simulation settings
# =========================

NUM_SIMULATIONS = 100
VERBOSE = False


# =========================
# EWA parameters
# =========================

LAMBDA = 0.022
PHI = 1.0
DELTA = 0.0
RHO = 1.0
ETA = 0.117


# =========================
# Conditions
# =========================

CONDITIONS = [
    ("FIX", "LOW"),
    ("FIX", "HIGH"),
    ("CO", "LOW"),
    ("CO", "HIGH")
]

# Intermittent HIGH settings
MIN_HIGH_INTERVAL = 3
MAX_HIGH_INTERVAL = 7