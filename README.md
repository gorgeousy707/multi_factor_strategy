# 多因子选股策略

## 一、策略原理

### 1.1 多因子选股概述

多因子选股是一种经典的量化投资策略。其核心思想是：寻找多个与股票未来收益存在显著相关性的因子，通过对每只股票在各因子上的表现进行综合评分，选出得分最高的股票构建投资组合。

### 1.2 因子体系（6大类，共11个因子）

| 因子类别 | 因子名称     | 计算方式                 | 方向                 |
|----------|-------------|-------------------------|---------------------|
| 价值因子 | EP因子       | EPS / 收盘价（1/PE倒数）  | 正向                |
| 价值因子 | BP因子       | BPS / 收盘价（1/PB倒数）  | 正向                |
| 成长因子 | 营收增长率   | 最近两期同比              | 正向                 |
| 成长因子 | 净利润增长率 | 最近两期同比              | 正向                 |
| 质量因子 | ROE         | 加权平均净资产收益率       | 正向                |
| 质量因子 | 净利润率     | 净利润 / 营业总收入       | 正向                 |
| 动量因子 | 1月动量      | 近21日涨跌幅             | 正向                 |
| 动量因子 | 3月动量      | 近63日涨跌幅             | 正向                 |
| 动量因子 | 6月动量      | 近126日涨跌幅            | 正向                 |
| 波动因子 | 60日波动率   | 年化波动率               | 负向（低波优先）      |
| 情绪因子 | 20日均换手率 | 20日均换手率             | 负向（低换手优先）    |

### 1.3 策略流程

数据获取 → 因子计算 → 因子处理（去极值/标准化）→ 综合打分 → 选Top N → 回测 → 绩效评估 → 可视化

### 1.4 因子处理方法

- 缺失值处理：截面中位数填充
- 去极值处理：MAD法（3倍绝对中位差）
- 标准化处理：Z-score标准化
- 方向调整：负向因子取反，使所有因子方向一致

### 1.5 打分选股

所有标准化后的因子等权加总，每月末选取综合得分最高的 Top 30 只股票，等权重建仓。

### 1.6 回测假设

- 回测区间：2022-01-01 ~ 2025-12-31
- 股票池：沪深300成分股
- 调仓频率：月度（每月末）
- 加权方式：等权
- 交易成本：双边手续费万三 + 滑点万二
- 基准指数：沪深300

## 二、代码结构

```
multi_factor_strategy/
├── main.py                    # 主入口，串联整个流程
├── config.py                  # 配置文件（参数、时间范围、股票池等）
├── environment.yml            # Anaconda 环境配置
├── requirements.txt           # pip 依赖包
├── data/
│   ├── data_fetcher.py        # 数据获取模块（AKshare）
│   └── raw_data/              # 离线数据存储目录
├── factors/
│   ├── __init__.py            # 因子模块初始化 + 因子注册
│   ├── base_factor.py         # 因子基类
│   ├── value_factors.py       # 价值因子（EP、BP）
│   ├── growth_factors.py      # 成长因子（营收/利润增长率）
│   ├── quality_factors.py     # 质量因子（ROE、净利润率）
│   ├── momentum_factors.py    # 动量因子（1/3/6月收益率）
│   ├── volatility_factors.py  # 波动因子（60日波动率）
│   └── sentiment_factors.py   # 情绪因子（20日均换手率）
├── portfolio/
│   ├── __init__.py            # 组合模块初始化
│   ├── factor_processor.py    # 因子处理（标准化、去极值、缺失值）
│   ├── scorer.py              # 综合打分与选股
│   └── backtest.py            # 回测引擎
├── utils/
│   ├── __init__.py            # 工具模块初始化
│   └── visualization.py       # 结果可视化
├── output/
│   ├── figures/               # 图表输出
│   └── results/               # 回测结果数据（CSV）
└── README.md                  # 项目文档
```

## 三、主要程序功能

### 3.1 数据获取 (`data/data_fetcher.py`)

- 使用 AKshare 库从网络获取数据，底层对接新浪财经和东方财富API
- 获取沪深300成分股列表（AKshare）、个股日线行情后复权（新浪财经K线）、个股财务指标（东财datacenter API）
- 所有数据先保存为本地 CSV 文件，后续从本地读取
- 内置请求频率控制和重试机制，避免被服务器封禁
- 网络失败时自动降级使用本地缓存数据

### 3.2 因子计算 (`factors/`)

- 基于 `BaseFactor` 抽象基类，统一因子接口
- 每个因子独立实现，便于扩展和测试
- 兼容 AKshare 列名差异

### 3.3 因子处理 (`portfolio/factor_processor.py`)

- 缺失值填充：截面中位数
- 去极值：MAD法（默认3倍）
- 标准化：Z-score
- 方向调整：负向因子取反

### 3.4 综合打分 (`portfolio/scorer.py`)

- 等权打分：各标准化因子直接加总
- 选股：取综合得分 Top N

### 3.5 回测引擎 (`portfolio/backtest.py`)

- 模拟逐日交易，按月调仓
- 等权组合构建
- 计算完整绩效指标：年化收益、夏普比率、最大回撤、Calmar比率、胜率、盈亏比、信息比率等
- 基准对比（沪深300）

### 3.6 可视化 (`utils/visualization.py`)

- 累计净值曲线图（策略 vs 基准）
- 回撤曲线图
- 年度收益对比柱状图
- 月度收益热力图
- 因子IC柱状图 + 序列图
- 绩效指标汇总表
- 综合仪表盘

## 四、执行流程

1. 运行 `main.py` → 自动串联全部模块
2. 数据获取 → 检查本地缓存，若无则从 AKshare 下载
3. 构建选股函数 → 因子计算 + 处理 + 打分
4. 回测执行 → 逐日模拟，月度调仓
5. 结果输出 → CSV 文件保存到 `output/results/`
6. 图表生成 → PNG 图片保存到 `output/figures/`

## 五、各文件描述

| 文件 | 描述 |
|------|------|
| `main.py` | 主入口，串联全部执行流程，驱动数据获取→因子计算→回测→可视化 |
| `config.py` | 全局参数配置：回测区间、选股数量、因子开关、交易费率等 |
| `environment.yml` | Anaconda 环境定义文件：Python 3.10 + 全部依赖 |
| `requirements.txt` | pip 依赖列表（备选） |
| `data/data_fetcher.py` | 数据获取类，负责AKshare与东财REST API请求、本地缓存读写、重试控制 |
| `factors/base_factor.py` | 因子抽象基类，定义因子统一接口 |
| `factors/value_factors.py` | 价值因子：EP因子、BP因子 |
| `factors/growth_factors.py` | 成长因子：营收增长率、净利润增长率 |
| `factors/quality_factors.py` | 质量因子：ROE、净利润率 |
| `factors/momentum_factors.py` | 动量因子：1月动量、3月动量、6月动量 |
| `factors/volatility_factors.py` | 波动因子：60日年化波动率 |
| `factors/sentiment_factors.py` | 情绪因子：20日均换手率 |
| `portfolio/factor_processor.py` | 因子处理器：缺失值填充、去极值、标准化、方向调整 |
| `portfolio/scorer.py` | 打分器：等权评分、Top N选股 |
| `portfolio/backtest.py` | 回测引擎：模拟交易、计算组合收益与绩效指标 |
| `utils/visualization.py` | 可视化：生成全部分析图表 |

## 六、数据来源

数据源分层：
- AKshare — 开源金融数据接口库，用于获取沪深300成分股列表和封装 API 调用
- 新浪财经 — 个股日线行情（后复权 K 线数据），通过 AKshare 的 `stock_zh_a_daily` 接口获取
- 东方财富 datacenter-web — 个股财务指标（EPS、BPS、ROE、营收、净利润），通过直接 HTTP REST API 获取

数据接口详情：成分股（ak.index_stock_cons）、个股日线（ak.stock_zh_a_daily → 新浪财经K线）、财务指标（东财 RPT_LICO_FN_CPD 报告）、基准指数（ak.stock_zh_a_daily → 新浪指数K线）

## 七、环境配置与运行

### 7.1 创建 Anaconda 环境

```bash
# 进入项目根目录
cd multi_factor_strategy

# 从 environment.yml 创建环境
conda env create -f environment.yml

# 激活环境
conda activate multi_factor_strategy
```

### 7.2 运行策略

```bash
# 全流程（已有本地缓存时会自动跳过数据下载）
python main.py

# 只跑某一步
python main.py --step data       # 仅获取数据
python main.py --step backtest   # 仅回测（需已有数据）
python main.py --step output     # 仅输出 CSV（需已有回测缓存）
python main.py --step viz        # 仅画图（需已有回测缓存）

# 从某一步开始，跑完后面所有
python main.py --from backtest   # 从回测开始 → 输出 → 画图
python main.py --from output     # 从输出开始 → 画图
```

### 7.3 输出

- **图表**：`output/figures/` 目录（PNG格式）
- **数据**：`output/results/` 目录（CSV格式）
- **日志**：`output/strategy.log`


## 八、注意事项

1. 首次运行时，数据获取可能需要较长时间（取决于网络速度和成分股数量）
2. 若AKshare请求失败，程序会自动重试3次，并指数递增等待时间
3. 已获取的数据会缓存到 `data/raw_data/`，后续运行将直接从本地读取
4. 所有路径使用相对路径，确保项目可移植
5. 确保 Windows 系统中已安装 Anaconda 并可正常使用 conda 命令
