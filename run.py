"""Production entry point for sentinelx.

SEC-01: Binds to 127.0.0.1 only — never 0.0.0.0 or an externally routable address.
SEC-15: debug=False hardcoded — never enabled in this entry point.

Usage:
    source .venv/bin/activate
    python run.py
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    # SEC-01: localhost binding only
    # SEC-15: debug=False hardcoded
    app.run(host="127.0.0.1", port=5000, debug=False)
