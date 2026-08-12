import sys
import os

# Add api directory to sys.path for standalone Vercel Serverless Function execution
api_dir = os.path.abspath(os.path.dirname(__file__))
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

from main import app
