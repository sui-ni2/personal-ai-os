from __future__ import annotations

import json
import sys
from typing import Any


TOOL = {
    "name": "external.echo",
    "description": "Echo a message from the stdio test connector.",
    "inputSchema": {
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
        "additionalProperties": False,
    },
}


def respond(request: dict[str, Any]) -> dict[str, Any]:
    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params") or {}
    if method == "tools/list":
        result: dict[str, Any] = {"tools": [TOOL]}
    elif method == "tools/call" and params.get("name") == TOOL["name"]:
        message = str((params.get("arguments") or {}).get("message") or "")
        result = {"content": [{"type": "text", "text": f"stdio:{message}"}]}
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": "Method or tool not found"},
        }
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


for line in sys.stdin:
    try:
        request = json.loads(line)
        response = respond(request)
    except (TypeError, ValueError, json.JSONDecodeError):
        response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32700, "message": "Parse error"},
        }
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()
