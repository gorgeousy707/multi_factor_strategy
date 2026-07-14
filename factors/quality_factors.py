"""
quality_factors.py — 质量因子
==============================
ROE — 从财务数据直接读取
净利润率 — 净利润/营收
"""

import pandas as pd
import numpy as np
from .base_factor import BaseFactor


class ROEFactor(BaseFactor):
    def __init__(self):
        super().__init__()
        self.name = "roe"
        self.category = "quality"
        self.direction = 1

    def calculate(self, daily_data, financial_data, date, spot_data=None):
        roe = {}
        for code, fin_df in financial_data.items():
            try:
                if fin_df is None or fin_df.empty:
                    continue
                mask = fin_df.index <= date
                if not mask.any():
                    continue
                val = fin_df.loc[mask].iloc[-1].get("roe", np.nan)
                if pd.notna(val):
                    roe[code] = float(val)
            except Exception:
                continue
        return pd.Series(roe, name=self.name)


class NetMarginFactor(BaseFactor):
    """净利润率 = 净利润 / 营业总收入"""

    def __init__(self):
        super().__init__()
        self.name = "net_margin"
        self.category = "quality"
        self.direction = 1

    def calculate(self, daily_data, financial_data, date, spot_data=None):
        margin = {}
        for code, fin_df in financial_data.items():
            try:
                if fin_df is None or fin_df.empty:
                    continue
                mask = fin_df.index <= date
                if not mask.any():
                    continue
                row = fin_df.loc[mask].iloc[-1]
                rev = row.get("total_revenue", np.nan)
                pro = row.get("net_profit", np.nan)
                if pd.notna(rev) and pd.notna(pro) and rev > 0:
                    margin[code] = pro / rev
            except Exception:
                continue
        return pd.Series(margin, name=self.name)
