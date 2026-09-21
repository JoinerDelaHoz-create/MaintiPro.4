"""
ANSI Color Palette and Windows VT100 initialization.
"""

import os
import sys

# Enable ANSI escape sequences on Windows if running in CMD or PowerShell
if os.name == "nt":
    os.system("")  # Enables VT100 mode in Windows 10+ consoles

# Palette definition
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Text Colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"
GRAY = "\033[90m"

# Backgrounds
BG_RED = "\033[41m"
BG_YELLOW = "\033[43m"
BG_BLUE = "\033[44m"
BG_DARK = "\033[100m"


def colorize_status(status: str) -> str:
    """Returns color-coded badge for equipment or order status."""
    st = status.upper()
    if st in ("OPERATIONAL", "COMPLETED", "NORMAL"):
        return f"{GREEN}{st}{RESET}"
    elif st in ("MAINTENANCE", "IN_PROGRESS", "PREVENTIVE"):
        return f"{BLUE}{st}{RESET}"
    elif st in ("WARNING", "PENDING", "PREDICTIVE", "MEDIUM"):
        return f"{YELLOW}{st}{RESET}"
    elif st in ("DOWN", "CRITICAL", "CORRECTIVE", "HIGH"):
        return f"{RED}{st}{RESET}"
    else:
        return f"{GRAY}{st}{RESET}"
