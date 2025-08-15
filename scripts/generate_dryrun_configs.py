import argparse
import json
from pathlib import Path
import copy

# Parse command-line arguments
parser = argparse.ArgumentParser(
    description='Generate dry-run configuration files for freqtrade strategies'
)
parser.add_argument(
    '-e', '--exclude',
    nargs='*',
    default=[],
    help='List of strategy names to exclude from generation'
)
args = parser.parse_args()
exclude_set = set(args.exclude)

if exclude_set:
    print(f"[i] Excluding strategies: {', '.join(sorted(exclude_set))}")

# Base configuration
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
            "DOGE/USDT", "ADA/USDT", "AVAX/USDT",
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

# Discover available strategies
strategies_dir = Path("user_data/strategies")
strategies = [
    f.stem
    for f in strategies_dir.glob("*.py")
    if f.is_file() and f.name != "__init__.py"
]

# Exclude specified strategies
filtered_strategies = [s for s in strategies if s not in exclude_set]

# Prepare output directory
output_dir = Path("user_data/dryrun_configs")
output_dir.mkdir(parents=True, exist_ok=True)

base_port = 8100

for idx, strat in enumerate(filtered_strategies):
    cfg = copy.deepcopy(base_config)
    cfg["strategy"] = strat
    cfg["logfile"] = f"user_data/dryrun_logs/{strat}.log"
    cfg["db_url"] = f"sqlite:///user_data/dryrun_db/{strat}.sqlite"

    # Assign incremental port per strategy
    port = base_port + idx
    cfg["api_server"]["listen_port"] = port
    cfg["api_server"]["enabled"] = True

    # Special config for AI strategies
    if "AI" in strat:
        cfg["timeframe"] = "3m"
        cfg["freqai"] = {
            "enabled": True,
            "purge_old_models": 2,
            "train_period_days": 15,
            "backtest_period_days": 7,
            "live_retrain_hours": 0,
            "identifier": f"{strat}FreqAIV2",
            "feature_parameters": {
                "include_timeframes": ["3m", "15m", "1h"],
                "include_corr_pairlist": ["BTC/USDT", "ETH/USDT"],
                "label_period_candles": 20,
                "include_shifted_candles": 3,
                "DI_threshold": 0.9,
                "weight_factor": 0.9,
                "principal_component_analysis": False,
                "use_SVM_to_remove_outliers": True,
                "indicator_periods_candles": [10, 20],
                "plot_feature_importances": 1
            },
            "data_split_parameters": {
                "test_size": 0.33,
                "random_state": 1
            },
            "model_training_parameters": {}
        }

    # Save configuration file
    cfg_path = output_dir / f"config_{strat}.json"
    with open(cfg_path, "w") as f:
        json.dump(cfg, f, indent=4)

    print(f"[✓] Saved config for {strat}: API port {port}")
