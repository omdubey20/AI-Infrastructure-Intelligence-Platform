import sys
import os

api_dir = os.path.abspath(os.path.dirname(__file__))
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

from main import app as _raw_app


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
