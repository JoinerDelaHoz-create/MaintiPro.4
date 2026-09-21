"""
Vercel Serverless Function entry point for CMMS Industrial Web Application.
Exports handler inheriting from BaseHTTPRequestHandler for @vercel/python runtime.
"""

from pathlib import Path
import sys

# Add project root to sys.path so modules in src/ resolve properly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.web.server import CMMSRequestHandler

# Vercel looks for 'handler' in Serverless Python functions
handler = CMMSRequestHandler
