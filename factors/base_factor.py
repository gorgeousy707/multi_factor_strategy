"""
base_factor.py — 因子基类
=========================
所有因子的抽象基类，定义因子统一接口及公共工具方法。

公共工具（供因子模块 + 回测引擎共用）：
  - get_price_col(df) → 返回价格列名
  - get_price_at(df, date) → 返回指定日期的收盘价
  - get_daily_return(df, date) → 返回指定日期的日收益率
  - compute_drawdown(nav) → 返回回撤序列
"""

from abc import ABC, abstractmethod
import pandas as pd
import numpy as np


# ==================== 公共工具函数（跨模块复用） ====================

def get_price_col(df):
    """返回 DataFrame 中的收盘价列名。优先中文 '收盘'，否则查找 'close'。"""
    if "收盘" in df.columns:
        return "收盘"
    for c in df.columns:
        if c.lower() == "close":
            return c
    return None


def get_price_at(df, date):
    """返回指定日期（含之前）最近一个有效收盘价。"""
    col = get_price_col(df)
    if col is None:
        return np.nan
    mask = df.index <= date
    recent = df.loc[mask, col]
    if recent.empty:
        return np.nan
    recent = pd.to_numeric(recent, errors="coerce").dropna()
    if recent.empty:
        return np.nan
    return recent.iloc[-1]


def get_daily_return(df, date):
    """返回单个股票在指定日期的日收益率。"""
    col = get_price_col(df)
    if col is None or date not in df.index:
        return np.nan
    idx = df.index.get_loc(date)
    if idx == 0:
        return 0.0
    prev, curr = df[col].iloc[idx - 1], df[col].iloc[idx]
    try:
        prev, curr = float(prev), float(curr)
    except (ValueError, TypeError):
        return np.nan
    if prev > 0:
        return (curr - prev) / prev
    return np.nan


def compute_drawdown(nav_series):
    """返回回撤序列（小数），nav_series 为累计净值 Series。"""
    cumulative = nav_series / nav_series.iloc[0]
    rolling_max = cumulative.cummax()
    return cumulative / rolling_max - 1


# ==================== 因子基类 ====================

class BaseFactor(ABC):
    """
    因子基类

    每个具体因子需实现：
      - name / category / direction
      - calculate()
    """

    def __init__(self):
        self.name = ""
        self.category = ""
        self.direction = 1

    @abstractmethod
    def calculate(self, daily_data, financial_data, date, spot_data=None):
        """返回 pd.Series: index=stock_code, value=factor_value"""
        pass

    def get_factor_series(self, daily_data, financial_data, date, spot_data=None):
        result = self.calculate(daily_data, financial_data, date, spot_data=spot_data)
        if isinstance(result, pd.Series):
            return result
        if isinstance(result, pd.DataFrame):
            return result.iloc[:, 0]
        return pd.Series(result)

    def _get_stock_data_before_date(self, daily_data, stock_code, date,
                                    lookback_days):
        df = daily_data.get(stock_code)
        if df is None or df.empty:
            return None
        return df[df.index <= date].tail(lookback_days)

    def _get_price_series(self, daily_data, stock_code, end_date,
                          lookback_days):
        col = get_price_col(daily_data.get(stock_code, pd.DataFrame()))
        if col is None:
            return None
        df = self._get_stock_data_before_date(
            daily_data, stock_code, end_date, lookback_days
        )
        if df is None or df.empty:
            return None
        return df[col]
