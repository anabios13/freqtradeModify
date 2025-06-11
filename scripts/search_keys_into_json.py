import json
import zipfile

with zipfile.ZipFile('user_data/backtest_results/backtest-result-2025-05-05_12-58-02.zip', 'r') as z:
    result_json_file = [f for f in z.namelist() if f.endswith('.json') and 'config' not in f][0]
    with z.open(result_json_file) as f:
        data = json.load(f)

print(json.dumps(data['strategy_comparison'][0], indent=4))