"""
strategies package

Exposes a registry so the dashboard can look up a strategy by its display
name without an if/elif chain scattered through app.py.
"""

from . import moving_average, momentum, mean_reversion

STRATEGY_REGISTRY = {
    moving_average.STRATEGY_NAME: moving_average,
    momentum.STRATEGY_NAME: momentum,
    mean_reversion.STRATEGY_NAME: mean_reversion,
}

STRATEGY_NAMES = list(STRATEGY_REGISTRY.keys())


def get_strategy_module(name: str):
    """Look up a strategy module by its display name."""
    if name not in STRATEGY_REGISTRY:
        raise ValueError(
            f"Unknown strategy '{name}'. Available: {STRATEGY_NAMES}"
        )
    return STRATEGY_REGISTRY[name]
