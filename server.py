"""Run the Python Election Process Assistant."""

from __future__ import annotations

import argparse
import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # Optional helper for local .env files.
    def load_dotenv() -> bool:
        return False

from election_assistant.web import run_server


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run the Python Election Process Assistant")
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    parser.add_argument("--port", default=int(os.getenv("PORT", "4173")), type=int)
    args = parser.parse_args()
    run_server(args.host, args.port)


if __name__ == "__main__":
    main()
