"""
scorer.py — 综合打分与选股
===========================
等权打分 → Top N 选股。
"""

import pandas as pd
import logging
from config import TOP_N

logger = logging.getLogger(__name__)


class Scorer:
    def __init__(self, top_n=TOP_N):
        self.top_n = top_n

    def select_stocks(self, factor_df, method="equal"):
        """
        选出 Top N 只股票。
        factor_df: 已处理且方向调整后的因子矩阵 (stock × factor)。
        """
        valid = factor_df[factor_df.notna().sum(axis=1) >=
                          max(1, len(factor_df.columns) // 2)].copy()
        if valid.empty:
            return [], pd.Series()

        valid = valid.fillna(0)          # 缺失→均值(标准化后0=中性)

        score = valid.sum(axis=1)        # 等权加总
        score = score.sort_values(ascending=False)

        n = min(self.top_n, len(score))
        return list(score.head(n).index), score
