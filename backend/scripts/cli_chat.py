#!/usr/bin/env python3
"""Interactive CLI for testing multi-turn chat against the backend."""

import argparse
import uuid

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="HomeGuide AI CLI chat client")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="FastAPI base URL")
    parser.add_argument("--session-id", default=None, help="Reuse an existing session ID")
    args = parser.parse_args()

    session_id = args.session_id or f"cli-{uuid.uuid4().hex[:8]}"
    print(f"HomeGuide AI CLI (session: {session_id})")
    print("Type 'exit' or 'quit' to stop.\n")

    with httpx.Client(base_url=args.base_url, timeout=120.0) as client:
        while True:
            user_message = input("You: ").strip()
            if not user_message:
                continue
            if user_message.lower() in {"exit", "quit"}:
                print("Goodbye.")
                break

            response = client.post(
                "/chat",
                json={"session_id": session_id, "message": user_message},
            )

            if response.status_code != 200:
                print(f"\nError {response.status_code}: {response.text}\n")
                continue

            payload = response.json()
            print(f"\nAgent: {payload['message']}\n")

            if payload.get("properties"):
                print("Properties returned:")
                for item in payload["properties"]:
                    print(
                        f"  - {item['id']} | {item['address']}, {item['city']} | "
                        f"${item['price']:,} | {item['beds']}bd/{item['baths']}ba"
                    )
                print()

            if payload.get("preferences"):
                prefs = {k: v for k, v in payload["preferences"].items() if v is not None}
                if prefs:
                    print(f"Saved preferences: {prefs}\n")


if __name__ == "__main__":
    main()
