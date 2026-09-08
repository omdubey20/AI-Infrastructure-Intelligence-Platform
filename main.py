import sys
import os
import importlib.util

# Add backend directory to Python sys.path so all backend modules can be imported
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Load backend/main.py explicitly to avoid circular import collision with root main.py
backend_main_file = os.path.join(backend_path, "main.py")
spec = importlib.util.spec_from_file_location("backend_main_app", backend_main_file)
mod = importlib.util.module_from_spec(spec)
sys.modules["backend_main_app"] = mod
spec.loader.exec_module(mod)

app = mod.app
