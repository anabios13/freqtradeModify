import sqlite3
import json
from pathlib import Path
from datetime import datetime
import pandas as pd

EXPORT_FOLDER = Path("user_data/dryrun_exports")
IDS_FOLDER   = EXPORT_FOLDER / "exported_ids"
EXPORT_FOLDER.mkdir(parents=True, exist_ok=True)
IDS_FOLDER.mkdir(parents=True, exist_ok=True)

def load_exported_ids(strategy: str) -> set:
    """Загрузить множество уже экспортированных trade_id для стратегии."""
    ids_file = IDS_FOLDER / f"{strategy}_ids.json"
    if not ids_file.exists():
        return set()
    with open(ids_file, "r") as f:
        return set(json.load(f))

def save_exported_ids(strategy: str, ids: set):
    """Сохранить обновлённое множество экспортированных trade_id."""
    ids_file = IDS_FOLDER / f"{strategy}_ids.json"
    with open(ids_file, "w") as f:
        json.dump(list(ids), f, indent=2)

def export_trades(strategy: str):
    db_path = Path(f"user_data/dryrun_db/{strategy}.sqlite")
    if not db_path.exists():
        print(f"[!] {strategy}: database not found.")
        return

    # Подключаемся и читаем все трейды
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(
        "SELECT * FROM trades",
        conn,
        parse_dates=["open_date", "close_date"]
    )
    conn.close()

    if df.empty:
        print(f"[!] {strategy}: no trades in DB.")
        return

    # Загружаем уже экспортированные ID и фильтруем новые
    exported_ids = load_exported_ids(strategy)
    df_new = df[~df["id"].isin(exported_ids)]

    if df_new.empty:
        print(f"[→] {strategy}: нет новых сделок для экспорта.")
        return

    # Готовим JSON
    df_new = df_new.where(pd.notnull(df_new), None)
    trades = df_new.to_dict(orient="records")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    json_path = EXPORT_FOLDER / f"{strategy}_{timestamp}.json"

    # Сохраняем
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(trades, f, indent=2, default=str)

    # Обновляем список экспортированных ID
    new_ids = set(df_new["id"].tolist())
    save_exported_ids(strategy, exported_ids | new_ids)

    print(f"[✓] {strategy}: экспортировано {len(new_ids)} новых сделок в {json_path}")

if __name__ == "__main__":
    DB_FOLDER = Path("user_data/dryrun_db")
    for db_file in DB_FOLDER.glob("*.sqlite"):
        export_trades(db_file.stem)
