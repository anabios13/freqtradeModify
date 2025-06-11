import pandas as pd
import json
from pathlib import Path
import zipfile
import matplotlib.pyplot as plt
from datetime import datetime

# Путь к папке с результатами
backtest_folder = Path('user_data/backtest_results')
zip_files = list(backtest_folder.glob('backtest-result-*.zip'))

records = []
for zip_file in zip_files:
    # Извлечение даты и времени из имени файла
    ts_str = zip_file.stem.replace('backtest-result-', '')
    test_dt = datetime.strptime(ts_str, '%Y-%m-%d_%H-%M-%S')
    with zipfile.ZipFile(zip_file, 'r') as z:
        json_name = [f for f in z.namelist() if f.endswith('.json') and 'config' not in f][0]
        with z.open(json_name) as jf:
            data = json.load(jf)
    s = data['strategy_comparison'][0]
    trades = s.get('trades', 0)
    # Добавляем только стратегии, где были сделки
    if trades > 0:
        records.append({
            'Дата и время': test_dt,
            'Стратегия': s.get('key', '—'),
            'Прибыль (%)': s.get('profit_total_pct', 0),
            'Фактор прибыли': s.get('profit_factor', 0),
            'Макс. просадка (%)': float(s.get('max_drawdown_account', 0)),
            'Сделок': trades,
            'Коэффициент Шарпа': s.get('sharpe', 0)
        })

# Создание DataFrame и вывод в консоль
if not records:
    print("Нет стратегий с выполненными сделками для отображения.")
    exit()

df = pd.DataFrame(records).sort_values(by='Прибыль (%)', ascending=False)
print("\n=== Сравнение стратегий (с учетом фильтрации по сделкам) ===")
print(df.to_string(index=False))

# Сохранение таблицы в CSV и HTML для удобного просмотра
csv_path = backtest_folder / 'сравнение_стратегий.csv'
html_path = backtest_folder / 'сравнение_стратегий.html'
df.to_csv(csv_path, index=False)
df.to_html(html_path, index=False)
print(f"\nТаблица сохранена в '{csv_path}' и '{html_path}'.")

# Построение всех графиков в одном окне (2x2 подграфика)
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

axes[0, 0].bar(df['Стратегия'], df['Прибыль (%)'])
axes[0, 0].set_title('Прибыльность стратегий (%)')
axes[0, 0].set_xlabel('Стратегия')
axes[0, 0].set_ylabel('Прибыль (%)')

axes[0, 1].bar(df['Стратегия'], df['Фактор прибыли'])
axes[0, 1].set_title('Фактор прибыли (прибыль/убытки)')
axes[0, 1].set_xlabel('Стратегия')
axes[0, 1].set_ylabel('Фактор прибыли')

axes[1, 0].bar(df['Стратегия'], df['Макс. просадка (%)'])
axes[1, 0].set_title('Макс. просадка (%) — ниже лучше')
axes[1, 0].set_xlabel('Стратегия')
axes[1, 0].set_ylabel('Макс. просадка (%)')

axes[1, 1].bar(df['Стратегия'], df['Коэффициент Шарпа'])
axes[1, 1].set_title('Коэффициент Шарпа — выше лучше')
axes[1, 1].set_xlabel('Стратегия')
axes[1, 1].set_ylabel('Коэффициент Шарпа')

for ax in axes.flat:
    ax.tick_params(axis='x', rotation=45)
fig.tight_layout()
plt.show()

# Краткие выводы на основе данных
top_profit = df.iloc[df['Прибыль (%)'].idxmax()]
top_sharpe = df.iloc[df['Коэффициент Шарпа'].idxmax()]
top_factor = df.iloc[df['Фактор прибыли'].idxmax()]
min_drawdown = df.iloc[df['Макс. просадка (%)'].idxmin()]

print("\n=== КРАТКИЕ ВЫВОДЫ ===")
print(f"➤ Лучшая по прибыли: {top_profit['Стратегия']} — {top_profit['Прибыль (%)']:.2f}% (стратегия с наибольшей доходностью).")
print(f"➤ Лучшая по коэффициенту Шарпа: {top_sharpe['Стратегия']} — {top_sharpe['Коэффициент Шарпа']:.2f} (лучший баланс доходности и риска).")
print(f"➤ Лучшая по фактору прибыли: {top_factor['Стратегия']} — {top_factor['Фактор прибыли']:.2f} (наилучшее соотношение прибыли к убыткам).")
print(f"➤ Наименьшая просадка: {min_drawdown['Стратегия']} — {min_drawdown['Макс. просадка (%)']:.2f}% (наименьший риск снижения капитала).")

# Памятка по интерпретации
print("""
📌 КРАТКАЯ ПАМЯТКА ПО ИНТЕРПРЕТАЦИИ:

1. Дата и время — момент тестирования.
2. Прибыль (%) — общая доходность.
3. Фактор прибыли — отношение прибыли к убыткам (>1 хорошо).
4. Макс. просадка (%) — наибольшее падение капитала (ниже — лучше).
5. Коэффициент Шарпа — доходность с учётом риска (выше — лучше).

Стратегии с нулевым количеством сделок автоматически удалены из анализа.
""")
