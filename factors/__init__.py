"""
__init__.py — 因子注册
"""
from .base_factor import BaseFactor, get_price_col, get_price_at, get_daily_return, compute_drawdown
from .value_factors import PEFactor, PBFactor
from .growth_factors import RevenueGrowthFactor, ProfitGrowthFactor
from .quality_factors import ROEFactor, NetMarginFactor
from .momentum_factors import MomentumFactor
from .volatility_factors import Volatility60DFactor
from .sentiment_factors import TurnoverRateFactor

ALL_FACTORS = [
    PEFactor(),
    PBFactor(),
    RevenueGrowthFactor(),
    ProfitGrowthFactor(),
    ROEFactor(),
    NetMarginFactor(),
    MomentumFactor(21, "momentum_1m"),
    MomentumFactor(63, "momentum_3m"),
    MomentumFactor(126, "momentum_6m"),
    Volatility60DFactor(),
    TurnoverRateFactor(),
]
