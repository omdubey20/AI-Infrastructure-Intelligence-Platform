web: sh -c "cd backend 2>/dev/null || true; uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"
