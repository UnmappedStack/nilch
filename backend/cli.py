from __future__ import annotations

import argparse
import os
import uvicorn

# from backend.main import create_app


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="""
                                Run the FastAPI service. Optional env vars: HOST, NILCH_PORT.
                                """)
    p.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    p.add_argument("--port", type=int, default=int(os.getenv("NILCH_PORT", "5001")))
    p.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug/dev mode (auto-reload, debug logging).",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # In debug/dev, enable reload + more verbose logging.
    # app = create_app(debug=False)
    if args.debug:
        os.environ["NILCH_DEBUG"] = "1"

    uvicorn.run(
        "backend.main:app",
        host=args.host,
        port=args.port,
        reload=args.debug,
        # factory=args.debug,
        log_level="debug" if args.debug else "info",
        # Allow forwarded headers when behind proxies/load balancers
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()
