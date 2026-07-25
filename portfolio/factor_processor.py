"""
factor_processor.py — 因子处理
===============================
缺失值填充 + 去极值 + 标准化 + 方向调整 + 可选相关性分析
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class FactorProcessor:
    def __init__(self, method="mad", n=3, standardize="zscore", missing="median"):
        self.method = method
        self.n = n
        self.standardize = standardize
        self.missing = missing

    def _fill_missing(self, series):
        if series.dropna().empty:
            return series
        fill = series.median() if self.missing == "median" else series.mean()
        return series.fillna(fill)

    def _winsorize(self, series):
        if len(series.dropna()) < 5:
            return series
        if self.method == "mad":
            med = series.median()
            mad = (series - med).abs().median()
            if mad == 0:
                return series
            return series.clip(med - self.n * mad, med + self.n * mad)
        elif self.method == "percentile":
            return series.clip(series.quantile(0.01), series.quantile(0.99))
        raise ValueError(f"不支持的Winsorize方法: {self.method}")

    def _standardize(self, series):
        if len(series.dropna()) < 2:
            return series
        if self.standardize == "zscore":
            std = series.std()
            return (series - series.mean()) / std if std != 0 else pd.Series(0, index=series.index)
        elif self.standardize == "minmax":
            mn, mx = series.min(), series.max()
            return (series - mn) / (mx - mn) if mx != mn else pd.Series(0.5, index=series.index)
        raise ValueError(f"不支持的标准化方法: {self.standardize}")

    def process(self, factor_df, factor_directions=None):
        result = pd.DataFrame(index=factor_df.index)
        for col in factor_df.columns:
            s = factor_df[col].copy()
            s = self._fill_missing(s)
            s = self._winsorize(s)
            s = self._standardize(s)
            if factor_directions and factor_directions.get(col, 1) == -1:
                s = -s
            result[col] = s
        return result

    def find_high_corr_pairs(self, factor_df, threshold=0.7):
        corr = factor_df.corr()
        pairs = []
        for i in range(len(corr.columns)):
            for j in range(i + 1, len(corr.columns)):
                r = corr.iloc[i, j]
                if abs(r) > threshold:
                    pairs.append((corr.columns[i], corr.columns[j], r))
        if pairs:
            logger.warning(f"高相关因子对 |r|>{threshold}: "
                           + ", ".join(f"{a}↔{b}({r:.2f})" for a, b, r in pairs))
        return pairs
