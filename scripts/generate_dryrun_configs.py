import json
from pathlib import Path
import copy
#Генерация конфигураций для dry-run прарллельно для всех стратегий
# Базовая конфигурация
base_config = {
    "$schema": "https://schema.freqtrade.io/schema.json",
    "max_open_trades": 1000,
    "stake_currency": "USDT",
    "stake_amount": 10,
    "tradable_balance_ratio": 0.99,
    "fiat_display_currency": "USD",
    "timeframe": "5m",
    "dry_run": True,
    "cancel_open_orders_on_exit": False,
    "unfilledtimeout": {
        "entry": 10,
        "exit": 10,
        "exit_timeout_count": 0,
        "unit": "minutes"
    },
    "entry_pricing": {
        "price_side": "same",
        "use_order_book": True,
        "order_book_top": 1,
        "price_last_balance": 0.0,
        "check_depth_of_market": {
            "enabled": False,
            "bids_to_ask_delta": 1
        }
    },
    "exit_pricing": {
        "price_side": "same",
        "use_order_book": True,
        "order_book_top": 1
    },
    "exchange": {
        "name": "bybit",
        "key": "your_exchange_key",
        "secret": "your_exchange_secret",
        "ccxt_config": {
            "defaultType": "spot"
        },
        "ccxt_async_config": {},
        "pair_whitelist": [
            "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT",
            "DOGE/USDT", "ADA/USDT", "AVAX/USDT", "MATIC/USDT",
            "DOT/USDT", "LINK/USDT"
        ],
        "pair_blacklist": []
    },
    "pairlists": [
        {"method": "StaticPairList"}
    ],
    "telegram": {
        "enabled": False,
        "token": "your_telegram_token",
        "chat_id": "your_telegram_chat_id"
    },
    "api_server": {
        "enabled": False,
        "listen_ip_address": "127.0.0.1",
        "listen_port": 8100,
        "verbosity": "error",
        "jwt_secret_key": "somethingrandom",
        "CORS_origins": [],
        "username": "freqtrader",
        "password": "SuperSecurePassword"
    },
    "bot_name": "freqtrade",
    "initial_state": "running",
    "force_entry_enable": False,
    "internals": {
        "process_throttle_secs": 5
    }
}

strategies = [
    "Bandtastic", "RsiStrategy", "ScalpingStrategy",
    "Strategy001", "Strategy002", "Strategy003",
    "Strategy004", "Strategy005"
]

output_dir = Path("user_data/dryrun_configs")
output_dir.mkdir(exist_ok=True)
base_port = 8100

for idx, strat in enumerate(strategies):
    config = copy.deepcopy(base_config)
    # задаём стратегию и пути
    config["strategy"] = strat
    config["logfile"] = f"user_data/dryrun_logs/{strat}.log"
    config["db_url"] = f"sqlite:///user_data/dryrun_db/{strat}.sqlite"
    # рассчитываем порт: 8100, 8101, 8102, ...
    port = base_port + idx
    config["api_server"]["listen_port"] = port
    # включаем API-сервер
    config["api_server"]["enabled"] = True
    # сохраняем файл
    cfg_path = output_dir / f"config_{strat}.json"
    with open(cfg_path, "w") as f:
        json.dump(config, f, indent=4)
    print(f"[✓] Saved config for {strat}: API port {port}")
