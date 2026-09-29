"""
Vercel serverless entrypoint.
All routes are rewritten to this handler (see vercel.json).
"""
import sys
import os

# Project root on PYTHONPATH
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import app  # noqa: E402

# Vercel Python runtime looks for `app` or `handler`
# Flask WSGI app is exposed as `app`
