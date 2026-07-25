"""
momentum_factors.py — 动量因子
===============================
参数化的价格动量因子：过去 N 个交易日的涨跌幅。
"""

import pandas as pd
import numpy as np
from .base_factor import BaseFactor, get_price_col, get_price_at


class MomentumFactor(BaseFactor):
    """N 日动量因子 — 默认提供 1月/3月/6月 三个实例"""

    def __init__(self, lookback, name):
        super().__init__()
        self.name = name
        self.category = "momentum"
        self.direction = 1
        self.lookback = lookback

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
                if len(recent) < self.lookback + 1:
                    continue
                ret = (recent.iloc[-1] - recent.iloc[-self.lookback - 1]) / \
                      recent.iloc[-self.lookback - 1]
                if pd.notna(ret):
                    result[code] = ret
            except Exception:
                continue
        return pd.Series(result, name=self.name)
