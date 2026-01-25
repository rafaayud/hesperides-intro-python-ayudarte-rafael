"""
Factory for creating trading strategies.

This factory centralizes strategy creation logic and handles parameter mapping
from API requests to strategy constructors.
"""
from modules.trading.domain.strategies.base import Strategy
from modules.trading.domain.strategies.mean_cross import MeanCross
from modules.trading.domain.strategies.momentum import Momentum
from modules.trading.domain.strategies.candle_pattern import CandlePatternStrategy
from modules.trading.domain.strategies.mock_strategy import MockStrategy
from modules.trading.domain.value_objects import ExecutionMode
from typing import Any, Dict, Callable


class StrategyFactory:
    """Factory for creating strategies with parameter mapping"""

    _strategies = {
        "mock_strategy": MockStrategy,
        "mean_cross": MeanCross,
        "momentum": Momentum,
        "candle_pattern": CandlePatternStrategy
    }

    @classmethod
    def _parse_execution_mode(cls, mode_str: str | None) -> ExecutionMode:
        """Parse execution mode string to ExecutionMode enum"""
        if mode_str is None:
            return ExecutionMode.ON_CLOSE
        
        mode_upper = mode_str.upper()
        if mode_upper == "ON_CLOSE":
            return ExecutionMode.ON_CLOSE
        elif mode_upper == "ON_TICK":
            return ExecutionMode.ON_TICK
        else:
            raise ValueError(f"Invalid execution mode: {mode_str}. Must be 'ON_CLOSE' or 'ON_TICK'")

    @classmethod
    def _build_common_kwargs(cls, strategy_params: Any) -> Dict[str, Any]:
        """Build common kwargs that apply to all strategies"""
        kwargs: Dict[str, Any] = {}
        
        if strategy_params is None:
            kwargs["mode"] = ExecutionMode.ON_CLOSE
            return kwargs
        
        if hasattr(strategy_params, 'min_candles') and strategy_params.min_candles is not None:
            kwargs["min_candles"] = strategy_params.min_candles
        
        if hasattr(strategy_params, 'execution_mode'):
            if strategy_params.execution_mode is not None:
                kwargs["mode"] = cls._parse_execution_mode(strategy_params.execution_mode)
            else:
                kwargs["mode"] = ExecutionMode.ON_CLOSE
        else:
            kwargs["mode"] = ExecutionMode.ON_CLOSE
        
        return kwargs

    @classmethod
    def _build_mock_strategy_kwargs(cls, strategy_params: Any, common_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Build kwargs for MockStrategy"""
        # MockStrategy only needs common kwargs (min_candles and mode)
        return common_kwargs

    @classmethod
    def _build_mean_cross_kwargs(cls, strategy_params: Any, common_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Build kwargs for MeanCross strategy"""
        # MeanCross doesn't accept min_candles (it calculates it automatically)
        kwargs = {}
        # Only include mode from common_kwargs
        if "mode" in common_kwargs:
            kwargs["mode"] = common_kwargs["mode"]
        
        if strategy_params is None:
            return kwargs
        
        if hasattr(strategy_params, 'slow_period') and strategy_params.slow_period is not None:
            kwargs["slow_period"] = strategy_params.slow_period
        if hasattr(strategy_params, 'fast_period') and strategy_params.fast_period is not None:
            kwargs["fast_period"] = strategy_params.fast_period
        
        return kwargs

    @classmethod
    def _build_momentum_kwargs(cls, strategy_params: Any, common_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Build kwargs for Momentum strategy"""
        # Momentum doesn't accept min_candles (it calculates it automatically)
        kwargs = {}
        # Only include mode from common_kwargs
        if "mode" in common_kwargs:
            kwargs["mode"] = common_kwargs["mode"]
        
        if strategy_params is None:
            return kwargs
        
        if hasattr(strategy_params, 'reference_period') and strategy_params.reference_period is not None:
            kwargs["reference_period"] = strategy_params.reference_period
        if hasattr(strategy_params, 'threshold') and strategy_params.threshold is not None:
            kwargs["threshold"] = strategy_params.threshold
        
        return kwargs

    @classmethod
    def _build_candle_pattern_kwargs(cls, strategy_params: Any, common_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Build kwargs for CandlePatternStrategy"""
        # CandlePatternStrategy doesn't accept min_candles or mode (it calculates min_candles automatically)
        kwargs = {}
        
        if strategy_params is None:
            return kwargs
        
        if hasattr(strategy_params, 'patterns') and strategy_params.patterns is not None:
            kwargs["patterns"] = strategy_params.patterns
        
        return kwargs

    # Dictionary mapping strategy names to their kwargs builder method names
    _kwargs_builders: Dict[str, str] = {
        "mock_strategy": "_build_mock_strategy_kwargs",
        "mean_cross": "_build_mean_cross_kwargs",
        "momentum": "_build_momentum_kwargs",
        "candle_pattern": "_build_candle_pattern_kwargs",
    }

    @classmethod
    def _build_strategy_kwargs(
        cls,
        strategy_name: str,
        strategy_params: Any
    ) -> Dict[str, Any]:
        """
        Build kwargs dictionary for strategy creation based on strategy type.
        
        Uses a dictionary of builder functions.
        """        
        # Build common kwargs first
        common_kwargs = cls._build_common_kwargs(strategy_params)
        
        # Get the specific builder method name for this strategy
        builder_method_name = cls._kwargs_builders.get(strategy_name)
        
        if builder_method_name is None:
            # If no specific builder, use common kwargs (for strategies that don't need extra params)
            return common_kwargs
        
        # Get the builder method and call it
        builder = getattr(cls, builder_method_name)
        return builder(strategy_params, common_kwargs)

    @classmethod
    def create_strategy(
        cls, 
        strategy_name: str, 
        strategy_params: Any = None
    ) -> Strategy:
        """
        Create a strategy instance with proper parameter mapping.
        
        Args:
            strategy_name: Name of the strategy (e.g., "mock_strategy", "mean_cross")
            strategy_params: StrategyParams object from API request (optional)
            
        Returns:
            Strategy: Instance of the requested strategy
            
        Raises:
            KeyError: If strategy_name is not found
            ValueError: If execution_mode is invalid
            TypeError: If kwargs are invalid for the strategy
        """
        strategy_name_lower = strategy_name.lower()
        
        if strategy_name_lower not in cls._strategies:
            available = ", ".join(cls._strategies.keys())
            raise KeyError(
                f"Unknown strategy: {strategy_name}. "
                f"Available strategies: {available}"
            )
        
        # Build kwargs from strategy_params
        kwargs = cls._build_strategy_kwargs(strategy_name_lower, strategy_params)
        
        # Create strategy instance
        strategy_class = cls._strategies[strategy_name_lower]
        return strategy_class(**kwargs)

    @classmethod
    def get_all_strategies(cls) -> list[str]:
        """Get all available strategy names"""
        return list(cls._strategies.keys())
