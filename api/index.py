import sys
import os

# Add backend directory to Python sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from main import app

class VercelPathFixMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            path = scope.get("path", "")
            if path.startswith("/api/index.py"):
                scope["path"] = path.replace("/api/index.py", "", 1) or "/"
            elif path.startswith("/api/index"):
                scope["path"] = path.replace("/api/index", "", 1) or "/"
        await self.app(scope, receive, send)


app = VercelPathFixMiddleware(_raw_app)
