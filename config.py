"""
config.py — 策略配置文件
======================
包含所有策略参数、回测时间范围、股票池、因子配置等。
所有参数集中管理，便于调整和复现。
"""

import os

# ===================== 项目路径配置 =====================
# 项目根目录（当前文件所在目录）
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 数据目录
RAW_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw_data")

# 输出目录
OUTPUT_FIGURES_DIR = os.path.join(PROJECT_ROOT, "output", "figures")
OUTPUT_RESULTS_DIR = os.path.join(PROJECT_ROOT, "output", "results")

# ===================== 回测参数 =====================
# 回测时间范围
START_DATE = "2022-01-01"       # 回测开始日期
END_DATE = "2025-12-31"         # 回测结束日期

# 选股参数
STOCK_POOL = "hs300"            # 股票池: "hs300" 沪深300, "zz500" 中证500
TOP_N = 30                      # 每期持有的股票数量（选取得分最高的N只）

# 调仓频率
REBALANCE_FREQ = "M"            # 调仓频率: "M" 月度, "Q" 季度

# 交易成本
COMMISSION_RATE = 0.0003        # 手续费率（双边万三）
SLIPPAGE_RATE = 0.0002          # 滑点率（万二）

# ===================== 因子配置 =====================
# 因子开关：控制是否启用某类因子（1=启用, 0=停用）
FACTOR_SWITCH = {
    "value": 1,                 # 价值因子（EP、BP）
    "growth": 1,                # 成长因子（营收增长率、净利润增长率）
    "quality": 1,               # 质量因子（ROE、净利润率）
    "momentum": 1,              # 动量因子（1/3/6月收益率）
    "volatility": 1,            # 波动因子（60日波动率）
    "sentiment": 1,             # 情绪因子（20日均换手率）
}

# 具体因子配置（仅记录元数据，实际 direction 由因子类定义）
FACTOR_CONFIG = {
    "pe":             {"category": "value",       "direction": 1,  "name": "EP因子(1/PE)"},
    "pb":             {"category": "value",       "direction": 1,  "name": "BP因子(1/PB)"},
    "revenue_growth": {"category": "growth",      "direction": 1,  "name": "营收同比增长率"},
    "profit_growth":  {"category": "growth",      "direction": 1,  "name": "净利润同比增长率"},
    "roe":            {"category": "quality",     "direction": 1,  "name": "ROE"},
    "net_margin":     {"category": "quality",     "direction": 1,  "name": "净利润率"},
    "momentum_1m":    {"category": "momentum",    "direction": 1,  "name": "1月动量"},
    "momentum_3m":    {"category": "momentum",    "direction": 1,  "name": "3月动量"},
    "momentum_6m":    {"category": "momentum",    "direction": 1,  "name": "6月动量"},
    "volatility_60d": {"category": "volatility",  "direction": -1, "name": "60日波动率"},
    "turnover_rate":  {"category": "sentiment",   "direction": -1, "name": "20日均换手率"},
}

# ===================== 因子处理参数 =====================
# 去极值
WINSORIZE_METHOD = "mad"        # 去极值方法: "mad" 绝对中位差法, "percentile" 百分位法
WINSORIZE_N = 3                 # MAD法的倍数参数（默认3倍MAD）

# 标准化
STANDARDIZE_METHOD = "zscore"   # 标准化方法: "zscore" Z-score标准化, "minmax" 最大最小归一化

# 缺失值处理
MISSING_FILL = "median"         # 缺失值填充: "median" 截面中位数, "mean" 截面均值

# ===================== AKShare 数据获取参数 =====================
# 请求间隔范围（秒），实际间隔在此范围内随机取值，避免被识别为爬虫
REQUEST_INTERVAL_MIN = 2.0         # 最小间隔
REQUEST_INTERVAL_MAX = 4.0         # 最大间隔
# 最大重试次数
MAX_RETRIES = 3
# 重试等待时间（秒）
RETRY_DELAY = 8

# ===================== 日志配置 =====================
LOG_LEVEL = "INFO"              # 日志级别: DEBUG, INFO, WARNING, ERROR
LOG_FILE = os.path.join(PROJECT_ROOT, "output", "strategy.log")

# ===================== 无风险利率（用于计算夏普比率） =====================
RISK_FREE_RATE = 0.03           # 年化无风险利率 3%（十年期国债收益率近似）

# ===================== 基准指数代码 =====================
BENCHMARK_INDEX = "000300"      # 沪深300
