"""
visualization.py — 结果可视化
==============================
所有图表保存到 output/figures/。
"""

import os, logging
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from config import OUTPUT_FIGURES_DIR
from factors.base_factor import compute_drawdown

# 中文字体 — matplotlib 在 Windows 上需要手动指定已安装的中文字体
import platform
if platform.system() == "Windows":
    import matplotlib.font_manager as fm
    _available = {f.name for f in fm.fontManager.ttflist}
    # 按优先级尝试中文字体，检测到哪个用哪个
    _chosen = None
    for _font in ["Microsoft YaHei", "SimHei", "KaiTi", "FangSong", "SimSun"]:
        if _font in _available:
            _chosen = _font
            break
    if _chosen:
        plt.rcParams["font.sans-serif"] = [_chosen, "DejaVu Sans", "Arial"]
    else:
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
else:
    plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

logger = logging.getLogger(__name__)
os.makedirs(OUTPUT_FIGURES_DIR, exist_ok=True)
plt.style.use("seaborn-v0_8-darkgrid")

# plt.style.use() 会重置部分 rcParams，因此需在之后再次确认中文字体设置
if _chosen:
    plt.rcParams["font.sans-serif"] = [_chosen, "DejaVu Sans", "Arial"]
    plt.rcParams["axes.unicode_minus"] = False

C = {  # 颜色常量
    "st": "#1f77b4", "bm": "#d62728", "dd": "#555555",
    "up": "#2ca02c", "dn": "#d62728",
}

# ---- 工具 ----
def _save(fig, name):
    p = os.path.join(OUTPUT_FIGURES_DIR, name)
    fig.savefig(p, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

# ---- 1. 净值曲线 ----
def plot_nav_curve(nav, bm_nav=None, title="累计净值曲线"):
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(nav.index, nav.values, label="策略组合", color=C["st"], lw=1.5)
    if bm_nav is not None and not bm_nav.empty:
        ax.plot(bm_nav.index, bm_nav / bm_nav.iloc[0],
                label="基准", color=C["bm"], lw=1.2, alpha=0.8)
    ax.axhline(1.0, color="gray", ls="--", lw=0.8)
    ax.set_title(title, fontsize=16, fontweight="bold")
    ax.set_xlabel("日期"); ax.set_ylabel("累计净值")
    ax.legend(); ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.2f"))
    fig.tight_layout(); _save(fig, "nav_curve.png")

# ---- 2. 回撤曲线 ----
def plot_drawdown(nav, title="回撤曲线"):
    fig, ax = plt.subplots(figsize=(14, 5))
    dd = compute_drawdown(nav) * 100   # 百分比
    ax.fill_between(dd.index, dd, 0, color=C["dd"], alpha=0.5)
    ax.plot(dd.index, dd, color=C["dd"], lw=0.8)
    ax.set_title(title, fontsize=16, fontweight="bold")
    ax.set_xlabel("日期"); ax.set_ylabel("回撤 (%)")
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.0f%%"))
    idx = dd.idxmin()
    ax.annotate(f"最大回撤: {dd[idx]:.1f}%\n{idx.strftime('%Y-%m-%d')}",
                xy=(idx, dd[idx]), xytext=(idx, dd[idx] - 5),
                fontsize=10, color="red",
                arrowprops=dict(arrowstyle="->", color="red"), ha="center")
    fig.tight_layout(); _save(fig, "drawdown.png")

# ---- 3. 年度收益 ----
def plot_annual_returns(df, title="年度收益对比"):
    if df.empty:
        return
    # 列名统一
    cols = df.columns.tolist()
    strat_col = next((c for c in cols if "策略" in c or "组合" in c), cols[0])
    bm_col = next((c for c in cols if "基准" in c), None)

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(df)); w = 0.35
    sv = df[strat_col].values * 100
    bars = ax.bar(x - w / 2, sv, w, label="策略组合", color=C["st"], alpha=0.85)
    if bm_col:
        bv = df[bm_col].values * 100
        ax.bar(x + w / 2, bv, w, label="基准", color=C["bm"], alpha=0.85)
    for b in bars:
        h = b.get_height()
        ax.annotate(f"{h:.1f}%", xy=(b.get_x() + b.get_width() / 2, h),
                    xytext=(0, 3 if h >= 0 else -10),
                    textcoords="offset points", ha="center", fontsize=9)
    ax.axhline(0, color="black", lw=0.5)
    ax.set_title(title, fontsize=16, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(df.index.tolist())
    ax.set_ylabel("收益率 (%)"); ax.legend(); ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout(); _save(fig, "annual_returns.png")

# ---- 4. 月度热力图 ----
def plot_monthly_heatmap(mat, title="月度收益率热力图"):
    if mat.empty:
        return
    fig, ax = plt.subplots(figsize=(12, 6))
    d = mat * 100
    im = ax.imshow(d.values, cmap="RdYlGn", aspect="auto", vmin=-8, vmax=8)
    for i in range(d.shape[0]):
        for j in range(d.shape[1]):
            v = d.iloc[i, j]
            if pd.notna(v):
                ax.text(j, i, f"{v:.1f}%", ha="center", va="center",
                        fontsize=9, color="white" if abs(v) > 4 else "black")
    ax.set_xticks(range(12))
    ax.set_xticklabels([f"{m:02d}" for m in range(1, 13)])
    ax.set_yticks(range(d.shape[0])); ax.set_yticklabels(d.index.tolist())
    ax.set_xlabel("月份"); ax.set_ylabel("年份")
    fig.colorbar(im, ax=ax, shrink=0.8).set_label("收益率 (%)")
    ax.set_title(title, fontsize=16, fontweight="bold")
    fig.tight_layout(); _save(fig, "monthly_heatmap.png")

# ---- 5. 因子IC ----
def plot_factor_ic(ic, title="因子IC值"):
    if ic is None or ic.empty:
        return
    fig, ax = plt.subplots(figsize=(12, 6))
    clr = [C["up"] if v > 0 else C["dn"] for v in ic.values]
    bars = ax.bar(range(len(ic)), ic.values, color=clr, alpha=0.8)
    ax.axhline(0, color="black", lw=0.5)
    for b, v in zip(bars, ic.values):
        ax.annotate(f"{v:.4f}", xy=(b.get_x() + b.get_width() / 2, b.get_height()),
                    xytext=(0, 3 if v >= 0 else -10),
                    textcoords="offset points", ha="center", fontsize=9)
    ax.set_xticks(range(len(ic)))
    ax.set_xticklabels(ic.index.tolist(), rotation=45, fontsize=10)
    ax.set_title(title, fontsize=16, fontweight="bold")
    ax.set_ylabel("Rank IC 均值"); ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout(); _save(fig, "factor_ic.png")

# ---- 6. 指标表 ----
def plot_metrics_table(metrics, title="回测绩效指标"):
    if not metrics:
        return
    fig, ax = plt.subplots(figsize=(10, 5)); ax.axis("off")
    rows = list(metrics.items())
    t = ax.table(cellText=rows, colLabels=["指标", "数值"],
                 cellLoc="left", loc="center", colWidths=[0.5, 0.5])
    t.auto_set_font_size(False); t.set_fontsize(11); t.scale(1.2, 1.6)
    for i in range(len(rows) + 1):
        for j in range(2):
            c = t[i, j]; c.set_edgecolor("#ccc")
            if i == 0:
                c.set_facecolor("#4472C4"); c.set_text_props(weight="bold", color="white")
            elif i % 2 == 0:
                c.set_facecolor("#f2f2f2")
    ax.set_title(title, fontsize=16, fontweight="bold", pad=20)
    fig.tight_layout(); _save(fig, "metrics_table.png")

# ---- 7. IC序列 ----
def plot_ic_sequence(ic_df, title="因子IC序列（12期滚动）"):
    if ic_df is None or ic_df.empty:
        return
    fig, ax = plt.subplots(figsize=(14, 7))
    ma = ic_df.rolling(12, min_periods=1).mean()
    for c in ma.columns:
        ax.plot(ma.index, ma[c], label=c, lw=1.0, alpha=0.8)
    ax.axhline(0, color="black", lw=0.5)
    ax.set_title(title, fontsize=16, fontweight="bold")
    ax.set_xlabel("日期"); ax.set_ylabel("Rank IC")
    ax.legend(fontsize=8, ncol=2); ax.grid(True, alpha=0.3)
    fig.tight_layout(); _save(fig, "ic_sequence.png")

# ---- 8. 仪表盘 ----
def plot_dashboard(nav, bm_nav, metrics, annual, monthly,
                   title="多因子选股策略 — 回测概览"):
    fig = plt.figure(figsize=(20, 16))

    # 净值
    ax1 = fig.add_subplot(2, 2, 1)
    ax1.plot(nav.index, nav.values, label="策略组合", color=C["st"], lw=1.5)
    if bm_nav is not None and not bm_nav.empty:
        ax1.plot(bm_nav.index, bm_nav / bm_nav.iloc[0],
                 label="基准", color=C["bm"], lw=1.2, alpha=0.8)
    ax1.axhline(1.0, color="gray", ls="--", lw=0.8)
    ax1.set_title("累计净值曲线", fontsize=14, fontweight="bold")
    ax1.legend(); ax1.grid(True, alpha=0.3)

    # 回撤
    ax2 = fig.add_subplot(2, 2, 2)
    dd = compute_drawdown(nav) * 100
    ax2.fill_between(dd.index, dd, 0, color=C["dd"], alpha=0.5)
    ax2.plot(dd.index, dd, color=C["dd"], lw=0.8)
    ax2.set_title("回撤曲线", fontsize=14, fontweight="bold")
    ax2.set_ylabel("回撤 (%)"); ax2.grid(True, alpha=0.3)

    # 年度
    ax3 = fig.add_subplot(2, 2, 3)
    if not annual.empty:
        for j, cn in enumerate(annual.columns):
            off = (j - len(annual.columns) / 2 + 0.5) * 0.3
            ax3.bar(np.arange(len(annual)) + off, annual[cn].values * 100,
                    0.3, label=cn, alpha=0.85)
        ax3.axhline(0, color="black", lw=0.5)
        ax3.set_xticks(range(len(annual)))
        ax3.set_xticklabels(annual.index.tolist())
        ax3.legend(fontsize=9)
    ax3.set_title("年度收益对比", fontsize=14, fontweight="bold")
    ax3.set_ylabel("收益率 (%)"); ax3.grid(True, alpha=0.3, axis="y")

    # 热力图
    ax4 = fig.add_subplot(2, 2, 4)
    if not monthly.empty:
        d = monthly * 100
        im = ax4.imshow(d.values, cmap="RdYlGn", aspect="auto", vmin=-8, vmax=8)
        ax4.set_xticks(range(12))
        ax4.set_xticklabels([f"{m:02d}" for m in range(1, 13)])
        ax4.set_yticks(range(d.shape[0]))
        ax4.set_yticklabels(d.index.tolist())
        for i in range(d.shape[0]):
            for j in range(d.shape[1]):
                v = d.iloc[i, j]
                if pd.notna(v):
                    ax4.text(j, i, f"{v:.1f}%", ha="center", va="center",
                             fontsize=7, color="white" if abs(v) > 4 else "black")
        fig.colorbar(im, ax=ax4, shrink=0.8).set_label("收益率 (%)")
    ax4.set_title("月度收益率热力图", fontsize=14, fontweight="bold")
    ax4.set_xlabel("月份"); ax4.set_ylabel("年份")

    fig.suptitle(title, fontsize=18, fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    _save(fig, "dashboard.png")

# ---- 一键生成 ----
def generate_all_charts(nav, bm_nav, metrics, annual, monthly,
                        ic_series=None, ic_df=None):
    logger.info("开始生成图表...")
    plot_nav_curve(nav, bm_nav)
    plot_drawdown(nav)
    if not annual.empty:
        plot_annual_returns(annual)
    plot_monthly_heatmap(monthly)
    if ic_series is not None and not ic_series.empty:
        plot_factor_ic(ic_series)
    if ic_df is not None and not ic_df.empty:
        plot_ic_sequence(ic_df)
    plot_metrics_table(metrics)
    plot_dashboard(nav, bm_nav, metrics, annual, monthly)
    logger.info(f"全部图表已保存到: {OUTPUT_FIGURES_DIR}")
