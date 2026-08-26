#!/usr/bin/env python
"""Send a scripted question to the CodeGraph Agent WebSocket and print events."""
import asyncio
import json
import sys

import websockets  # websockets>=12

QUESTION = "What would break if I removed the Depends() helper?"
URI = "ws://localhost:8000/chat"


async def main() -> int:
    async with websockets.connect(URI) as ws:
        await ws.send(json.dumps({"question": QUESTION}))
        got_text = False
        async for raw in ws:
            event = json.loads(raw)
            t = event.get("type")
            if t == "tool_call":
                print(f"[tool_call] {event['name']}({json.dumps(event.get('args', {}), indent=2)})")
                print(f"  touched_nodes: {event.get('touched_nodes', [])}")
            elif t == "tool_result":
                result_preview = str(event.get("result", ""))[:120]
                print(f"[tool_result] {event['name']} → {result_preview}")
            elif t == "text_delta":
                print(event.get("text", ""), end="", flush=True)
                got_text = True
            elif t == "done":
                print("\n[done]")
                break
            elif t == "error":
                print(f"[error] {event.get('message')}", file=sys.stderr)
                return 1
    return 0 if got_text else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
