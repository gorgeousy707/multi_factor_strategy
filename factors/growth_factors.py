"""
growth_factors.py — 成长因子
============================
营收增长率 / 净利润增长率 — 最近两期财务数据同比。
"""

import pandas as pd
import numpy as np
from .base_factor import BaseFactor


class _GrowthFactor(BaseFactor):
    """内部参数化基类"""
    _field = ""          # "total_revenue" or "net_profit"

    def _latest_two(self, fin_df, date):
        if fin_df is None or fin_df.empty:
            return np.nan, np.nan
        mask = fin_df.index <= date
        if mask.sum() < 2:
            return np.nan, np.nan
        recent = fin_df.loc[mask]
        return recent[self._field].iloc[-1], recent[self._field].iloc[-2]

    def calculate(self, daily_data, financial_data, date, spot_data=None):
        growth = {}
        for code, fin_df in financial_data.items():
            try:
                cur, prev = self._latest_two(fin_df, date)
                if pd.notna(cur) and pd.notna(prev) and prev != 0:
                    growth[code] = (cur - prev) / abs(prev)
            except Exception:
                continue
        return pd.Series(growth, name=self.name)


class RevenueGrowthFactor(_GrowthFactor):
    def __init__(self):
        super().__init__()
        self.name = "revenue_growth"
        self.category = "growth"
        self.direction = 1
        self._field = "total_revenue"


class ProfitGrowthFactor(_GrowthFactor):
    def __init__(self):
        super().__init__()
        self.name = "profit_growth"
        self.category = "growth"
        self.direction = 1
        self._field = "net_profit"
