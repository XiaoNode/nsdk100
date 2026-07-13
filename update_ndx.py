#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_ndx.py — 生成 NDX（纳斯达克100指数）查询结果数据文件 ndx_data.js

功能：
  拉取 NDX100（纳斯达克100指数，^NDX）日线历史，计算：
    1) 历史最高收盘记录（all-time high close）及日期
    2) 最新交易日收盘点位及日期
  并写入 ndx_data.js（定义 window.NDX_DATA 全局变量），供 index.html 以 <script> 引入。

数据源（自动回退）：
  1) Stooq 每日 CSV（首选，无需 key）
  2) Yahoo Finance 日线 JSON（Stooq 不可达时回退）

时区：
  以美国纳斯达克交易时区 America/New_York（美东）为准。更新时间戳以 UTC 纪元秒存储，
  由前端用 Intl.DateTimeFormat(timeZone:'America/New_York') 渲染为美东时间。

依赖：仅 Python 3 标准库，无需安装第三方包。

适用场景：
  - 本地手动运行：python update_ndx.py
  - GitHub Actions（见 .github/workflows/update-ndx.yml）每日美东收盘后自动运行并提交，
    从而让 GitHub Pages 展示的最新数据每日刷新。
"""

import csv
import io
import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

STOOQ_URL = "https://stooq.com/q/d/l/?s=ndx.us&i=d"
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENDX?range=max&interval=1d"
OUTPUT_FILE = "ndx_data.js"
UA = "Mozilla/5.0 (compatible; ndx-updater/1.0)"


def _http_get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_stooq():
    """返回 [(date, close), ...]（Stooq CSV）。"""
    raw = _http_get(STOOQ_URL)
    if raw[:3] == b"\xef\xbb\xbf":  # 去 BOM
        raw = raw[3:]
    text = raw.decode("utf-8", errors="replace")
    return parse_stooq(text)


def parse_stooq(text: str):
    reader = csv.DictReader(io.StringIO(text.strip()))
    recs = []
    for row in reader:
        date = (row.get("Date") or row.get("date") or "").strip()
        close_s = (row.get("Close") or row.get("close") or "").strip()
        if not date or not close_s:
            continue
        try:
            close = float(close_s)
        except ValueError:
            continue
        if close <= 0:
            continue
        recs.append((date, close))
    return recs


def fetch_yahoo():
    """返回 [(date, close), ...]（Yahoo chart JSON 回退源）。"""
    raw = _http_get(YAHOO_URL)
    data = json.loads(raw.decode("utf-8", errors="replace"))
    res = (data.get("chart") or {}).get("result")
    if not res:
        raise ValueError("Yahoo 返回为空")
    r0 = res[0]
    timestamps = r0.get("timestamp") or []
    quotes = (r0.get("indicators") or {}).get("quote") or [{}]
    closes = quotes[0].get("close") or []
    recs = []
    for ts, c in zip(timestamps, closes):
        if c is None:
            continue
        try:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            recs.append((dt, float(c)))
        except (ValueError, TypeError, OverflowError):
            continue
    if not recs:
        raise ValueError("Yahoo 未解析到有效数据")
    return recs


def collect_records():
    """依次尝试数据源，返回首个成功的记录列表。"""
    errors = []
    for name, fn in (("Stooq", fetch_stooq), ("Yahoo", fetch_yahoo)):
        try:
            recs = fn()
            if recs:
                # 按日期升序（YYYY-MM-DD 可直接字典序排序）
                recs.sort(key=lambda x: x[0])
                print(f"[update_ndx] 数据源 {name} 成功，共 {len(recs)} 条")
                return recs
        except Exception as e:  # noqa: BLE001 - 任意数据源失败都继续尝试下一个
            errors.append(f"{name}: {e}")
    # 全部失败
    for e in errors:
        sys.stderr.write(f"[update_ndx] 数据源失败 {e}\n")
    sys.exit(1)


def main():
    records = collect_records()

    high_date, high_val = max(records, key=lambda x: x[1])
    latest_date, latest_val = records[-1]

    data = {
        "symbol": "^NDX",
        "name": "纳斯达克100指数 (NDX100)",
        "highValue": round(high_val, 2),
        "highDate": high_date,
        "latestValue": round(latest_val, 2),
        "latestDate": latest_date,
        "updatedAtEpoch": int(time.time()),
        "source": "Stooq / Yahoo Finance · NDX100 (^NDX) 每日收盘",
    }

    js = "window.NDX_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n"
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(js)
    except OSError as e:
        sys.stderr.write(f"[update_ndx] 写入 {OUTPUT_FILE} 失败：{e}\n")
        sys.exit(1)

    print(
        f"[update_ndx] 完成 ▶ 最高记录 {high_val:,.2f}（{high_date}），"
        f"最新收盘 {latest_val:,.2f}（{latest_date}），已写入 {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
