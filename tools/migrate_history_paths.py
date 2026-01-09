from pathlib import Path
import json

APP_ROOT = Path(__file__).resolve().parent.parent

history_path = APP_ROOT / "history.json"
data = json.loads(history_path.read_text(encoding="utf-8"))

changed = 0
for e in data:
    raw = e.get("file", "")
    if not raw:
        continue
    p = Path(raw)
    if not p.is_absolute():
        candidate = (APP_ROOT / p).resolve()
        if candidate.exists():
            e["file"] = str(candidate)
            changed += 1

history_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
print(f"Updated {changed} history entries.")
