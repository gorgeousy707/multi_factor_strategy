"""
data_fetcher.py — 数据获取
==========================
数据源：新浪K线 + 东财datacenter财务 + AKShare成分股
所有数据先写本地CSV，后续直接读取。
"""

import os, time, random, logging
import pandas as pd
import akshare as ak
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import (
    RAW_DATA_DIR, STOCK_POOL, BENCHMARK_INDEX,
    REQUEST_INTERVAL_MIN, REQUEST_INTERVAL_MAX,
    MAX_RETRIES, RETRY_DELAY,
)

logger = logging.getLogger(__name__)

_session = None

def _get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.mount("https://", HTTPAdapter(
            max_retries=Retry(total=3, backoff_factor=2, status_forcelist=[500,502,503,504]),
            pool_connections=10, pool_maxsize=10))
        _session.mount("http://", HTTPAdapter())
        _session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"})
    return _session


class DataFetcher:
    def __init__(self):
        os.makedirs(RAW_DATA_DIR, exist_ok=True)

    def _fp(self, name): return os.path.join(RAW_DATA_DIR, name)

    def _load(self, name):
        fp = self._fp(name)
        if os.path.exists(fp):
            try:    return pd.read_csv(fp, index_col=0, parse_dates=True)
            except: return pd.read_csv(fp, index_col=0)
        return None

    def _save(self, df, name):
        df.to_csv(self._fp(name), encoding="utf-8-sig")

    def _call_ak(self, fn, desc, **kw):
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                time.sleep(random.uniform(REQUEST_INTERVAL_MIN, REQUEST_INTERVAL_MAX)
                           if attempt == 1 else RETRY_DELAY * attempt)
                res = fn(**kw)
                logger.debug(f"[OK] {desc} ({attempt})")
                return res
            except Exception as e:
                logger.warning(f"[RETRY] {desc} ({attempt}): {e}")
        logger.error(f"[FAIL] {desc}")
        return None

    # ---- 批量下载公共方法 ----
    def _batch(self, codes, force, prefix, fetch_one, label):
        result = {}
        to_fetch = []
        for c in codes:
            c = str(c).zfill(6)
            cached = self._load(f"{prefix}_{c}.csv") if not force else None
            if cached is not None:
                result[c] = cached
            else:
                to_fetch.append(c)
        if not to_fetch:
            return result
        logger.info(f"[FETCH] {label} {len(to_fetch)} 只")
        ok = 0
        for i, code in enumerate(to_fetch, 1):
            logger.info(f"  {label} {i}/{len(to_fetch)}: {code}")
            df = fetch_one(code)
            if df is not None:
                self._save(df, f"{prefix}_{code}.csv")
                result[code] = df; ok += 1
        logger.info(f"  {label}: {ok}/{len(to_fetch)}")
        return result

    # ---- 1. 成分股 ----
    def fetch_constituents(self, force=False):
        fn = f"{STOCK_POOL}_constituents.csv"
        if not force and (c := self._load(fn)) is not None:
            return c["stock_code"].tolist()
        idx = {"hs300": "000300", "zz500": "000905"}.get(STOCK_POOL, "000300")
        r = self._call_ak(ak.index_stock_cons, "成分股列表", symbol=idx)
        if r is None and (c := self._load(fn)) is not None:
            return c["stock_code"].tolist()
        if r is None:
            raise RuntimeError("无法获取成分股列表")
        for col in ["品种代码", "code", "成分券代码"]:
            if col in r.columns:
                codes = r[col].astype(str).str.zfill(6).tolist(); break
        else:
            codes = r.iloc[:, 0].astype(str).str.zfill(6).tolist()
        self._save(pd.DataFrame({"stock_code": codes}), fn)
        return codes

    # ---- 2. 日线 (新浪) ----
    def _fetch_one_daily(self, code):
        code = str(code).zfill(6)
        prefix = "sh" if code.startswith(("60", "68", "9")) else "sz"
        r = self._call_ak(ak.stock_zh_a_daily, f"日线-{code}",
                          symbol=f"{prefix}{code}", adjust="hfq")
        if r is not None and len(r) > 0 and "date" in r.columns:
            df = r.copy()
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date"); df.index.name = "date"
            for eng, cn in {"open":"开盘","high":"最高","low":"最低","close":"收盘",
                            "volume":"成交量","amount":"成交额",
                            "outstanding_share":"流通股本","turnover":"换手率"}.items():
                if eng in df.columns and cn not in df.columns:
                    df = df.rename(columns={eng: cn})
            return df
        return None

    def fetch_daily_batch(self, codes, force=False):
        return self._batch(codes, force, "daily", self._fetch_one_daily, "日线")

    # ---- 3. 基准 ----
    def fetch_benchmark(self, force=False):
        fn = f"benchmark_{BENCHMARK_INDEX}.csv"
        if not force and (c := self._load(fn)) is not None:
            return c
        logger.info("[FETCH] 基准行情")
        sym = f"sh{BENCHMARK_INDEX}" if BENCHMARK_INDEX.startswith("000") else f"sz{BENCHMARK_INDEX}"
        r = self._call_ak(ak.stock_zh_index_daily, "基准指数", symbol=sym)
        if r is not None and len(r) > 0:
            df = r.copy()
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"]); df = df.set_index("date")
            df.index.name = "date"; self._save(df, fn)
            return df
        return self._load(fn)

    # ---- 4. 财务数据 ----
    def _fetch_one_financial(self, code):
        code = str(code).zfill(6)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                r = _get_session().get(
                    "https://datacenter-web.eastmoney.com/api/data/v1/get",
                    params={"reportName":"RPT_LICO_FN_CPD",
                            "columns":"SECURITY_CODE,NOTICE_DATE,BASIC_EPS,BPS,WEIGHTAVG_ROE,TOTAL_OPERATE_INCOME,PARENT_NETPROFIT",
                            "filter":f'(SECURITY_TYPE_CODE="058001001")(SECURITY_CODE="{code}")',
                            "pageSize":"50","sortColumns":"NOTICE_DATE","sortTypes":"-1"},
                    timeout=30)
                data = r.json()
                if data.get("success") and data["result"] and data["result"]["data"]:
                    df = pd.DataFrame(data["result"]["data"])
                    df["NOTICE_DATE"] = pd.to_datetime(df["NOTICE_DATE"])
                    return df.rename(columns={
                        "SECURITY_CODE":"stock_code","NOTICE_DATE":"date",
                        "BASIC_EPS":"eps","BPS":"bps","WEIGHTAVG_ROE":"roe",
                        "TOTAL_OPERATE_INCOME":"total_revenue","PARENT_NETPROFIT":"net_profit",
                    }).set_index("date")
                return None
            except Exception as e:
                logger.warning(f"  财务 {code} ({attempt}): {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
        return None

    def fetch_financial_batch(self, codes, force=False):
        return self._batch(codes, force, "financial", self._fetch_one_financial, "财务")

    # ---- 5. 一键获取 ----
    def fetch_all(self, force=False):
        codes = self.fetch_constituents(force)
        daily = self.fetch_daily_batch(codes, force)
        bm = self.fetch_benchmark(force)
        fin = self.fetch_financial_batch(codes, force)
        logger.info(f"数据完成: 日线{len(daily)} 基准{'√' if bm is not None else '×'} 财务{len(fin)}")
        return {"constituents": pd.DataFrame({"stock_code": codes}),
                "spot_data": None, "daily": daily, "financials": fin, "benchmark": bm}
