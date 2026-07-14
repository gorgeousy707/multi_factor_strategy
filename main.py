"""
main.py — 主入口
=================
多因子选股策略：数据获取 → 因子计算 → 打分选股 → 回测 → 输出结果。

用法：
  python main.py                     # 全流程
  python main.py --step data         # 仅获取数据
  python main.py --step backtest     # 仅回测（需已有数据）
  python main.py --step output       # 仅输出 CSV（需已有回测缓存）
  python main.py --step viz          # 仅画图（需已有回测缓存）
  python main.py --from backtest     # 从回测开始，跑完后续所有步骤
  python main.py --from output       # 从输出开始，跑完后续所有步骤
"""

import os, sys, time, logging, warnings, pickle, argparse
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from config import (
    START_DATE, END_DATE, TOP_N, STOCK_POOL,
    FACTOR_SWITCH, WINSORIZE_METHOD, WINSORIZE_N,
    STANDARDIZE_METHOD, MISSING_FILL, OUTPUT_RESULTS_DIR,
    OUTPUT_FIGURES_DIR, LOG_LEVEL, LOG_FILE,
)
from factors.base_factor import get_price_col, get_price_at

warnings.filterwarnings("ignore")

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"),
              logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("main")

# 中间结果缓存目录
CACHE_DIR = os.path.join(PROJECT_ROOT, "output", "cache")
BACKTEST_CACHE = os.path.join(CACHE_DIR, "backtest_result.pkl")

STEPS = ["data", "factor", "backtest", "output", "viz"]


# ============================================================
#  各步骤实现
# ============================================================

def _load_data(force=False):
    """Step 1: 数据获取 → 返回 (daily, financials, benchmark, spot)"""
    logger.info(">>> Step 1: 数据获取")
    from data.data_fetcher import DataFetcher
    all_data = DataFetcher().fetch_all(force=force)
    daily = all_data["daily"]
    if not daily:
        logger.error("无日线数据"); sys.exit(1)
    logger.info(f"日线:{len(daily)}只  财务:{len(all_data['financials'])}只")
    return daily, all_data["financials"], all_data["benchmark"], all_data.get("spot_data")


def _setup_factors():
    """Step 2-4: 因子 + 打分 → 返回 (enabled_factors, factor_dirs, processor, scorer, selection_func)"""
    logger.info(">>> Step 2-4: 因子 + 打分")
    from factors import ALL_FACTORS
    from portfolio.factor_processor import FactorProcessor
    from portfolio.scorer import Scorer

    enabled = [f for f in ALL_FACTORS if FACTOR_SWITCH.get(f.category, 1)]
    logger.info(f"因子: {len(enabled)} 个")
    factor_dirs = {f.name: f.direction for f in enabled}
    proc = FactorProcessor(WINSORIZE_METHOD, WINSORIZE_N,
                           STANDARDIZE_METHOD, MISSING_FILL)
    scorer = Scorer(TOP_N)

    def selection_func(date, dd):
        fd = {}
        for f in enabled:
            try:
                s = f.get_factor_series(dd, financial_data, date, spot_data)
                if s is not None and not s.empty:
                    fd[f.name] = s
            except Exception:
                pass
        if len(fd) < 2:
            return []
        fdf = pd.DataFrame(fd).dropna(how="all")
        if fdf.empty or fdf.shape[1] < 2:
            return []
        return scorer.select_stocks(proc.process(fdf, factor_dirs))[0]

    return enabled, selection_func


def _run_backtest(daily_data, benchmark_data, selection_func):
    """Step 5: 回测 → 返回 engine"""
    logger.info(">>> Step 5: 回测")
    from portfolio.backtest import BacktestEngine
    engine = BacktestEngine()
    engine.run(daily_data, benchmark_data, selection_func)
    # 缓存回测结果，供后续 output / viz 步骤独立使用
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache = {
        "nav_series": engine.nav_series,
        "benchmark_nav": engine.benchmark_nav,
        "metrics": engine._calc_metrics() if engine.nav_series is not None else {},
        "positions": engine.positions,
        "annual_stats": engine.annual_stats(),
        "monthly_matrix": engine.monthly_returns_matrix(),
    }
    with open(BACKTEST_CACHE, "wb") as f:
        pickle.dump(cache, f)
    logger.info(f"回测结果已缓存至 {BACKTEST_CACHE}")
    return engine


def _load_backtest_cache():
    """从缓存加载回测结果"""
    if not os.path.exists(BACKTEST_CACHE):
        logger.error(f"回测缓存不存在: {BACKTEST_CACHE}，请先运行 --step backtest")
        sys.exit(1)
    with open(BACKTEST_CACHE, "rb") as f:
        return pickle.load(f)


def _output_results(engine=None, daily_data=None, financial_data=None,
                    enabled=None, spot_data=None):
    """Step 6: 结果输出 → 写 CSV"""
    logger.info(">>> Step 6: 结果输出")

    if engine is None:
        cache = _load_backtest_cache()
        nav_series = cache["nav_series"]
        benchmark_nav = cache["benchmark_nav"]
        metrics = cache["metrics"]
        annual_stats = cache["annual_stats"]
        monthly_matrix = cache["monthly_matrix"]
        positions = cache["positions"]
        ic_results = pd.DataFrame()  # IC 需要原始数据，独立 output 时跳过
    else:
        nav_series = engine.nav_series
        benchmark_nav = engine.benchmark_nav
        metrics = engine._calc_metrics() if nav_series is not None else {}
        annual_stats = engine.annual_stats()
        monthly_matrix = engine.monthly_returns_matrix()
        positions = engine.positions
        ic_results = _calc_ic(engine, daily_data, financial_data, enabled, spot_data)

    os.makedirs(OUTPUT_RESULTS_DIR, exist_ok=True)

    if nav_series is not None:
        ndf = pd.DataFrame({"date": nav_series.index, "strategy_nav": nav_series.values})
        if benchmark_nav is not None and not benchmark_nav.empty:
            ndf["benchmark_nav"] = benchmark_nav.values[:len(ndf)]
        ndf.to_csv(os.path.join(OUTPUT_RESULTS_DIR, "nav_series.csv"), index=False, encoding="utf-8-sig")
    if metrics:
        pd.DataFrame(metrics.items(), columns=["指标","数值"]).to_csv(
            os.path.join(OUTPUT_RESULTS_DIR, "metrics.csv"), index=False, encoding="utf-8-sig")
    for df, name in [(annual_stats,"annual_stats"), (monthly_matrix,"monthly_returns"),
                     (ic_results,"factor_ic")]:
        if df is not None and not df.empty:
            df.to_csv(os.path.join(OUTPUT_RESULTS_DIR, f"{name}.csv"), encoding="utf-8-sig")
    if positions:
        pd.DataFrame([{"date": d, "stocks": ";".join(s or []), "count": len(s or [])}
                      for d, s in positions.items()]).to_csv(
            os.path.join(OUTPUT_RESULTS_DIR, "positions.csv"), index=False, encoding="utf-8-sig")

    logger.info("CSV 输出完成")


def _visualize():
    """Step 7: 可视化 → 生成图表"""
    logger.info(">>> Step 7: 可视化")
    cache = _load_backtest_cache()
    from utils.visualization import generate_all_charts

    # IC 从缓存文件加载（如果存在）
    ic_path = os.path.join(OUTPUT_RESULTS_DIR, "factor_ic.csv")
    ic_df = None
    if os.path.exists(ic_path):
        ic_df = pd.read_csv(ic_path, index_col=0)
        ic_df.index = pd.to_datetime(ic_df.index)

    generate_all_charts(
        nav=cache["nav_series"],
        bm_nav=cache["benchmark_nav"],
        metrics=cache["metrics"],
        annual=cache["annual_stats"],
        monthly=cache["monthly_matrix"],
        ic_series=ic_df.mean() if ic_df is not None and not ic_df.empty else None,
        ic_df=ic_df,
    )
    logger.info("图表生成完成")


# ---- IC 计算 ----
def _calc_ic(engine, daily_data, financial_data, active_factors, spot_data=None):
    if not engine.positions:
        return pd.DataFrame()
    dates = sorted(engine.positions.keys())
    records = {}
    for i, date in enumerate(dates[:-1]):
        next_date = dates[i + 1]
        next_ret = {}
        for code, df in daily_data.items():
            if df is not None:
                sp = get_price_at(df, date)
                ep = get_price_at(df, next_date)
                if not np.isnan(sp) and not np.isnan(ep) and sp > 0:
                    next_ret[code] = (ep - sp) / sp
        date_ics = {}
        for f in active_factors:
            try:
                fs = f.get_factor_series(daily_data, financial_data, date, spot_data)
                if fs.dropna().empty:
                    continue
                common = set(fs.dropna().index) & set(next_ret)
                if len(common) < 10:
                    continue
                ic = fs[list(common)].corr(pd.Series({c: next_ret[c] for c in common}), method="spearman")
                if pd.notna(ic):
                    date_ics[f.name] = ic
            except Exception:
                pass
        if date_ics:
            records[date] = date_ics
    if not records:
        return pd.DataFrame()
    ic_df = pd.DataFrame(records).T
    ic_df.index.name = "date"
    return ic_df


# ============================================================
#  调度逻辑
# ============================================================

def _parse_args():
    parser = argparse.ArgumentParser(description="多因子选股策略")
    parser.add_argument("--step", choices=STEPS, default=None,
                        help="只运行指定步骤")
    parser.add_argument("--from", dest="from_step", choices=STEPS, default=None,
                        help="从指定步骤开始，运行至结尾")
    parser.add_argument("--force-data", action="store_true",
                        help="强制重新获取数据（忽略缓存）")
    return parser.parse_args()


def main():
    t0 = time.time()
    args = _parse_args()

    # ---- 确定要跑哪些步骤 ----
    if args.step:
        todo = [args.step]
    elif args.from_step:
        idx = STEPS.index(args.from_step)
        todo = STEPS[idx:]
    else:
        todo = STEPS  # 全流程

    logger.info(f"多因子选股策略 | {STOCK_POOL} | {START_DATE}~{END_DATE} | Top{TOP_N}")
    logger.info(f"执行步骤: {' → '.join(todo)}")

    # 全局变量（步骤间共享）
    global financial_data, spot_data
    daily_data = financial_data = benchmark_data = spot_data = None
    enabled = None
    engine = None

    # ---- 按序执行 ----
    if "data" in todo:
        daily_data, financial_data, benchmark_data, spot_data = _load_data(force=args.force_data)

    if "factor" in todo or "backtest" in todo:
        if daily_data is None:
            daily_data, financial_data, benchmark_data, spot_data = _load_data()
        enabled, selection_func = _setup_factors()

    if "backtest" in todo:
        engine = _run_backtest(daily_data, benchmark_data, selection_func)

    if "output" in todo:
        _output_results(engine=engine, daily_data=daily_data,
                        financial_data=financial_data, enabled=enabled,
                        spot_data=spot_data)

    if "viz" in todo:
        _visualize()

    logger.info(f"完成! 耗时 {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
