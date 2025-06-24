import sqlite3, json
from pathlib import Path
from datetime import datetime

STRATEGIES = [
    "Bandtastic", "RsiStrategy", "ScalpingStrategy", "Strategy001",
    "Strategy002", "Strategy003", "Strategy004", "Strategy005"
]

EXPORT_FOLDER = Path("user_data/dryrun_exports")
EXPORT_FOLDER.mkdir(exist_ok=True)

def export_trades(strategy):
    db_path = Path(f"user_data/dryrun_db/{strategy}.sqlite")
    if not db_path.exists():
        print(f"[!] {strategy}: database not found.")
        return

    conn = sqlite3.connect(db_path)
    df = conn.execute("SELECT * FROM trades").fetchall()
    columns = [d[0] for d in conn.execute("PRAGMA table_info(trades)")]
    conn.close()

    trades = [dict(zip(columns, row)) for row in df]
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    json_path = EXPORT_FOLDER / f"{strategy}_{timestamp}.json"

    with open(json_path, "w") as f:
        json.dump(trades, f, indent=2)
    print(f"[✓] {strategy} exported to {json_path}")

for strat in STRATEGIES:
    export_trades(strat)
