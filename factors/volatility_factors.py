"""
volatility_factors.py — 波动因子
=================================
60日年化波动率 — 负向因子（低波动加分）
"""

import pandas as pd
import numpy as np
from .base_factor import BaseFactor, get_price_col


class Volatility60DFactor(BaseFactor):
    def __init__(self):
        super().__init__()
        self.name = "volatility_60d"
        self.category = "volatility"
        self.direction = -1
        self.lookback = 60

    def calculate(self, daily_data, financial_data, date, spot_data=None):
        result = {}
        for code, df in daily_data.items():
            try:
                col = get_price_col(df)
                if col is None:
                    continue
                mask = df.index <= date
                recent = pd.to_numeric(df.loc[mask, col],
                                       errors="coerce").dropna()
                if len(recent) < self.lookback:
                    continue
                rets = recent.pct_change().dropna().tail(self.lookback)
                if len(rets) < self.lookback * 0.5:
                    continue
                vol = rets.std() * np.sqrt(252)
                if pd.notna(vol):
                    result[code] = vol
            except Exception:
                continue
        return pd.Series(result, name=self.name)
