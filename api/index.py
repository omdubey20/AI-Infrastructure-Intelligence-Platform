import sys
import os

# Add backend directory to Python sys.path (check multiple possible serverless paths)
possible_paths = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")),
    os.path.abspath("backend"),
]

for p in possible_paths:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

from main import app
