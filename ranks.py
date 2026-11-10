"""CPU rank names for CPU Evolution Bot.

The order defines progression: rank N starts at (N - 1) * MESSAGES_PER_RANK
messages. Keep this list in sync with RANK_STYLES in bot.py (same length and
order) — the styles file selects the artwork by rank index.
"""

RANKS = [
    "Intel 286",
    "Intel 386",
    "Intel 486",
    "Pentium",
    "Pentium II",
    "Pentium III",
    "Pentium 4",
    "Core 2 Duo",
    "Core i3",
    "Core i5",
    "Core i7",
    "Core i9",
    "Ryzen 3",
    "Ryzen 5",
    "Ryzen 7",
    "Ryzen 9",
    "Threadripper",
]

# Reached after the last listed rank (>= len(RANKS) * MESSAGES_PER_RANK).
BEYOND_RANK = "Beyond Threadripper"
