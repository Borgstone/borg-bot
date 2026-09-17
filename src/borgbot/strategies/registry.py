from typing import Callable, Dict

from borgbot.strategies.sma import SMAStrategy
from borgbot.strategies.rsi import RSIStrategy
from borgbot.strategies.rsi_trend_v2 import RSITrendV2Strategy
from borgbot.strategies.stack import StrategyStack


def build_sma(config):
    return SMAStrategy(
        {
            "fast": config["fast"],
            "slow": config["slow"],
        }
    )


def build_rsi(config):
    return RSIStrategy(
        {
            "period": config["period"],
            "overbought": config.get("overbought", 70),
            "oversold": config.get("oversold", 30),
        }
    )


def build_sma_rsi(config):
    return StrategyStack(
        [
            (
                SMAStrategy(
                    {
                        "fast": config["fast"],
                        "slow": config["slow"],
                    }
                ),
                0.5,
            ),
            (
                RSIStrategy(
                    {
                        "period": config["period"],
                        "overbought": config.get("overbought", 70),
                        "oversold": config.get("oversold", 30),
                    }
                ),
                0.5,
            ),
        ]
    )


def build_rsi_trend_v2(config):
    return RSITrendV2Strategy(
        {
            "period": config["period"],
            "pullback_low": config["pullback_low"],
            "pullback_high": config["pullback_high"],
            "trend_period": config["trend_period"],
        }
    )


STRATEGY_REGISTRY: Dict[str, Callable] = {
    "sma": build_sma,
    "rsi": build_rsi,
    "sma_rsi": build_sma_rsi,
    "rsi_trend_v2": build_rsi_trend_v2,
}


def build_strategy(config):
    strategy_type = config.get("type")

    if strategy_type not in STRATEGY_REGISTRY:
        available = ", ".join(sorted(STRATEGY_REGISTRY))
        raise ValueError(
            f"Unknown strategy type: {strategy_type}. "
            f"Available strategies: {available}"
        )

    return STRATEGY_REGISTRY[strategy_type](config)


def available_strategies():
    return tuple(sorted(STRATEGY_REGISTRY))