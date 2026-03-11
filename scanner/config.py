"""Scanner configuration with JSON file override."""
from __future__ import annotations

import json
from pathlib import Path


_DEFAULTS = {
    "strategy_a": {
        "iv_rv_min": 1.25,
        "iv_rv_near_miss_min": 1.0,
    },
    "strategy_b": {
        "ff_strong_threshold": 0.20,
        "ff_moderate_threshold": 0.10,
        "ff_60_90_preference_min": 0.10,
    },
    "strategy_c": {
        "put_skew_min": 1.3,
        "rv_edge_min": 0.0,
    },
    "hard_filters": {
        "min_price": 10.0,
        "min_open_interest": 2000,
        "min_expected_move_usd": 0.90,
        "max_atm_delta": 0.57,
        "max_ticker_allocation_pct": 0.05,
    },
    "tiering": {
        "volume_pass": 1_500_000,
        "volume_near_miss": 1_000_000,
        "winrate_pass": 50.0,
        "winrate_near_miss": 40.0,
        "iv_rv_pass": 1.25,
        "iv_rv_near_miss": 1.0,
        "term_structure_max": -0.004,
    },
    "general": {
        "signal_threshold_ff": 20.0,
    },
}


def load_config(path: str = "scanner_config.json") -> dict:
    """Load config with JSON overrides merged on top of defaults."""
    config = _deep_copy(_DEFAULTS)
    p = Path(path)
    if p.exists():
        try:
            overrides = json.loads(p.read_text(encoding="utf-8"))
            _deep_merge(config, overrides)
        except Exception:
            pass
    return config


def _deep_copy(d: dict) -> dict:
    return json.loads(json.dumps(d))


def _deep_merge(base: dict, override: dict) -> None:
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
