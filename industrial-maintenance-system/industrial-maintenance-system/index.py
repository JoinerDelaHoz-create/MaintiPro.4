"""
Root Python entry point for Vercel Serverless Functions.
Directly exports CMMSRequestHandler as both 'handler' and 'app'
to satisfy Vercel Python runtime autodetection.
"""

from pathlib import Path
import sys

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.web.server import CMMSRequestHandler

# Vercel entry points
handler = CMMSRequestHandler
app = CMMSRequestHandler
