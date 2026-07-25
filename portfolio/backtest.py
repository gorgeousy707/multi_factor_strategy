"""
backtest.py — 回测引擎
=======================
等权组合 + 月度/季度调仓 + 绩效指标 + 基准对比。
"""

import logging
import pandas as pd
import numpy as np
from factors.base_factor import get_price_col, get_daily_return, compute_drawdown
from config import (
    START_DATE, END_DATE, COMMISSION_RATE, SLIPPAGE_RATE,
    RISK_FREE_RATE, REBALANCE_FREQ,
)

logger = logging.getLogger(__name__)


class BacktestEngine:
    def __init__(self, commission=COMMISSION_RATE, slippage=SLIPPAGE_RATE,
                 risk_free=RISK_FREE_RATE):
        self.commission = commission
        self.slippage = slippage
        self.risk_free = risk_free
        self.nav_series = None
        self.benchmark_nav = None
        self.positions = {}
        self.turnover_records = []
        self._metrics_cache = None

    # ---- 调仓日 ----
    @staticmethod
    def get_rebalance_dates(dates):
        df = pd.DataFrame({"date": sorted(dates)})
        if REBALANCE_FREQ == "M":
            return sorted(df.groupby([df["date"].dt.year, df["date"].dt.month])["date"].max().tolist())
        elif REBALANCE_FREQ == "Q":
            df["q"] = (df["date"].dt.month - 1) // 3 + 1
            return sorted(df.groupby([df["date"].dt.year, "q"])["date"].max().tolist())
        raise ValueError(f"不支持的调仓频率: {REBALANCE_FREQ}")

    # ---- 回测主循环 ----
    def run(self, daily_data, benchmark_data, selection_func):
        logger.info(f"回测: {START_DATE}~{END_DATE}")
        all_dates = sorted({d for df in daily_data.values() for d in df.index
                            if pd.Timestamp(START_DATE) <= d <= pd.Timestamp(END_DATE)})
        if not all_dates:
            raise ValueError("回测区间内无交易日数据！")

        rebalance_dates = self.get_rebalance_dates(all_dates)
        rebalance_set = set(rebalance_dates)
        logger.info(f"交易日: {len(all_dates)}, 调仓: {len(rebalance_dates)}次")

        nav = 1.0
        self.nav_series = pd.Series(index=all_dates, dtype=float)
        holdings = []

        for i, date in enumerate(all_dates):
            if date in rebalance_set:
                selected = selection_func(date, daily_data)
                if selected:
                    if holdings:
                        o, n = set(holdings), set(selected)
                        self.turnover_records.append(
                            {"date": date,
                             "turnover": 1 - len(o & n) / max(len(o | n), 1),
                             "n_holdings": len(selected)})
                    holdings = selected
                self.positions[date] = holdings.copy()

            if holdings and i > 0:
                rets = [get_daily_return(daily_data.get(c, pd.DataFrame()), date) for c in holdings]
                valid = [r for r in rets if not np.isnan(r)]
                if valid:
                    dr = np.mean(valid)
                    if date in rebalance_set:
                        dr -= (self.commission + self.slippage) * 2
                    nav *= (1 + dr)
            self.nav_series.loc[date] = nav

        self.nav_series = self.nav_series.ffill().bfill()
        self._calc_benchmark_nav(benchmark_data, all_dates)
        return self._calc_metrics()

    # ---- 基准 ----
    def _calc_benchmark_nav(self, bm, dates):
        if bm is None or bm.empty or (col := get_price_col(bm)) is None:
            self.benchmark_nav = pd.Series(1.0, index=dates)
            return
        r = bm[col].pct_change().reindex(dates).fillna(0)
        self.benchmark_nav = (1 + r).cumprod().ffill()

    # ---- 绩效指标 ----
    def _calc_metrics(self):
        if self._metrics_cache is not None:
            return self._metrics_cache
        nav = self.nav_series.dropna()
        bm_nav = self.benchmark_nav.dropna()
        if len(nav) < 2:
            return {}

        dr = nav.pct_change().dropna()
        ny = max(len(dr) / 252, 0.01)
        total = nav.iloc[-1] / nav.iloc[0] - 1
        ar = (1 + total) ** (1 / ny) - 1
        vol = dr.std() * np.sqrt(252)
        sharpe = (ar - self.risk_free) / max(vol, 1e-8)
        dd = compute_drawdown(nav)
        mdd = dd.min()
        calmar = ar / max(abs(mdd), 1e-8)
        wr = (dr > 0).mean()

        bt = bm_nav.iloc[-1] / bm_nav.iloc[0] - 1 if len(bm_nav) > 1 else 0
        ba = (1 + bt) ** (1 / ny) - 1
        excess = ar - ba

        sd, bd = nav.pct_change().dropna(), bm_nav.pct_change().dropna()
        ci = sd.index.intersection(bd.index)
        ir = excess / max((sd.loc[ci] - bd.loc[ci]).std() * np.sqrt(252), 1e-8) if len(ci) > 1 else 0.0

        at = np.mean([r["turnover"] for r in self.turnover_records]) if self.turnover_records else 0

        metrics = {
            "累计收益率": f"{total:.2%}", "年化收益率": f"{ar:.2%}",
            "年化波动率": f"{vol:.2%}", "夏普比率": f"{sharpe:.4f}",
            "最大回撤": f"{mdd:.2%}", "Calmar比率": f"{calmar:.4f}",
            "胜率": f"{wr:.2%}", "基准年化收益": f"{ba:.2%}",
            "超额收益": f"{excess:.2%}", "信息比率": f"{ir:.4f}",
            "平均换手率": f"{at:.2%}", "调仓次数": str(len(self.turnover_records)),
        }
        logger.info("\n=== 回测绩效 ===\n" + "\n".join(f"  {k}: {v}" for k, v in metrics.items()))
        self._metrics_cache = metrics
        return metrics

    # ---- 年度统计 ----
    def annual_stats(self):
        if self.nav_series is None or self.nav_series.empty:
            return pd.DataFrame()
        dr = self.nav_series.pct_change().dropna()
        if dr.empty:
            return pd.DataFrame()
        annual = dr.groupby(dr.index.year).apply(lambda x: (1 + x).prod() - 1).rename("策略收益")
        if self.benchmark_nav is not None and not self.benchmark_nav.empty:
            ba = self.benchmark_nav.pct_change().dropna().groupby(
                dr.index.year).apply(lambda x: (1 + x).prod() - 1).rename("基准收益")
            return pd.concat([annual, ba, (annual - ba).rename("超额收益")], axis=1)
        return pd.DataFrame(annual)

    # ---- 月度矩阵 ----
    def monthly_returns_matrix(self):
        if self.nav_series is None or self.nav_series.empty:
            return pd.DataFrame()
        mr = self.nav_series.resample("ME").last().pct_change().dropna()
        return pd.DataFrame({"year": mr.index.year, "month": mr.index.month,
                             "return": mr.values}).pivot(index="year", columns="month", values="return")
