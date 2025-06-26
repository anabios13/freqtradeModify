import json
from pathlib import Path
from datetime import datetime
import pandas as pd

DRYRUN_FOLDER = Path("user_data/dryrun_exports")

records = []
for file in sorted(DRYRUN_FOLDER.glob("*.json")):
    # Из имени: стратегия и время прогона
    strategy, ts_str = file.stem.split("_", 1)
    run_dt = datetime.strptime(ts_str, "%Y-%m-%d_%H-%M-%S")
    # Загружаем trades
    df = pd.read_json(file, orient='records')
    if df.empty:
        continue
    # Добавляем метаданные файла
    df['strategy'] = strategy
    df['file_ts'] = run_dt
    # Предположим, что есть поле 'id' либо формируем свой ключ:
    if 'id' not in df.columns:
        df['id'] = (
            df['open_date'].astype(str) + "|" +
            df.get('pair', pd.Series(''), ).astype(str) + "|" +
            df['close_date'].astype(str)
        )
    records.append(df[['strategy','file_ts','id']])

# Склеиваем в один DataFrame
all_trades = pd.concat(records, ignore_index=True)

# Ищем дубли, т.е. одинаковые 'id', попавшие в более чем один файл
dups = (
    all_trades
      .groupby('id')['file_ts']
      .nunique()
      .reset_index(name='runs')
      .query('runs > 1')
)

print(f"Найдено сделок, попавших более чем в один экспорт: {len(dups)}")
if not dups.empty:
    # Покажем первые 10 дублирующихся id и сколько раз они встретились
    print(dups.head(10))
