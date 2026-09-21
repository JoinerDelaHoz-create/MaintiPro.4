"""
Industrial Maintenance Management System (CMMS)
Main Application Bootstrap Entry Point.

This module initializes the application database and launches the interactive
terminal interface.
"""

import sys
from pathlib import Path

# Ensure 'src' is resolvable regardless of where the script is executed
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from src.ui.cli import run_app


def main():
    """Starts the CMMS application."""
    try:
        run_app()
    except KeyboardInterrupt:
        print("\n\nPrograma interrumpido por el usuario. Saliendo de forma segura...")
        sys.exit(0)


if __name__ == "__main__":
    main()
