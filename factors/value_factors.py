"""
value_factors.py — 价值因子
============================
EP因子 = EPS / 收盘价 (1/PE倒数)
BP因子 = BPS / 收盘价 (1/PB倒数)
"""

import pandas as pd
import numpy as np
from .base_factor import BaseFactor, get_price_col, get_price_at


class _EPBPFactor(BaseFactor):
    """内部参数化基类：EP / BP"""
    _field = ""          # "eps" or "bps"

    def calculate(self, daily_data, financial_data, date, spot_data=None):
        values = {}
        for code, fin_df in financial_data.items():
            try:
                if fin_df is None or fin_df.empty:
                    continue
                mask = fin_df.index <= date
                if not mask.any():
                    continue
                fin_val = fin_df.loc[mask].iloc[-1].get(self._field, np.nan)
                if pd.isna(fin_val) or fin_val <= 0:
                    continue
                df = daily_data.get(code)
                if df is None or df.empty:
                    continue
                price = get_price_at(df, date)
                if pd.notna(price) and price > 0:
                    values[code] = fin_val / price
            except Exception:
                continue
        return pd.Series(values, name=self.name)


class PEFactor(_EPBPFactor):
    """EP = EPS / Price"""

    def __init__(self):
        super().__init__()
        self.name = "pe"
        self.category = "value"
        self.direction = 1
        self._field = "eps"


class PBFactor(_EPBPFactor):
    """BP = BPS / Price"""

    def __init__(self):
        super().__init__()
        self.name = "pb"
        self.category = "value"
        self.direction = 1
        self._field = "bps"
