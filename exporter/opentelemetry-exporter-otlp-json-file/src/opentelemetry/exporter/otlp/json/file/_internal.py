import json


def _format_line(entry: dict) -> str:
    return json.dumps(entry, separators=(",", ".")) + "\n"
