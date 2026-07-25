"""
sentiment_factors.py — 情绪因子
===============================
20日均换手率 — 负向因子（低换手加分）
"""

import pandas as pd
from .base_factor import BaseFactor


class TurnoverRateFactor(BaseFactor):
    def __init__(self):
        super().__init__()
        self.name = "turnover_rate"
        self.category = "sentiment"
        self.direction = -1
        self.lookback = 20

    def calculate(self, daily_data, financial_data, date, spot_data=None):
        result = {}
        for code, df in daily_data.items():
            try:
                to_col = None
                for c in df.columns:
                    if "换手" in c or "turnover" in c.lower():
                        to_col = c
                        break
                if to_col is None:
                    continue
                mask = df.index <= date
                recent = pd.to_numeric(
                    df.loc[mask, to_col].tail(self.lookback),
                    errors="coerce"
                ).dropna()
                if len(recent) < max(5, self.lookback * 0.3):
                    continue
                result[code] = recent.mean()
            except Exception:
                continue
        return pd.Series(result, name=self.name)
