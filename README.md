**复利计算与定投可视化 小玩具**

- 功能：模拟每月定投并按年化利率按月复利，展示总金额与本金的时间序列
- 技术：纯前端，使用 `ECharts` 绘制折线图
- 运行：直接用浏览器打开 `index.html`
- 可调参数（在 `index.html` 中修改）：
  - `monthlyDeposit`：每月存入金额，默认 `2000`
  - `annualInterestRate`：年利率，默认 `0.1`（10%）
  - `totalMonths`：总月数，默认 `30 * 12`
- 图表：绿色为总金额，橙色为本金；悬浮提示显示时间、总金额、本金与利息

---

## NDX 查询结果面板（新增）

图表下方新增一块「NDX 查询结果」面板，展示纳斯达克 100 指数（NDX）相对历史最高记录的对比，例如：

> NDX 最高记录是 30,762.20 点（2026年6月3日），今天是 2026年7月10日（美东时间）NDX 为 29,825.11 点，距离最高点下降了 937.09 点，下降了 3.05%。

- **时区**：以美国纳斯达克交易时区（America/New_York，美东）为准；面板里的「今天」指最新交易日。
- **配色**：涨用红色、跌用绿色（A 股习惯）。
- **数据来源**：Stooq 的 NDX 每日收盘（`Close`）。

### 数据如何更新（每个交易日后）

面板数据由 `ndx_data.js` 提供（定义 `window.NDX_DATA` 全局变量，用 `<script>` 标签引入，因此直接用 `file://` 打开也不会有 CORS 问题）。

每个交易日后，运行一次更新脚本即可刷新数据：

```bash
python update_ndx.py
```

脚本会从 Stooq 拉取 NDX 日线，计算历史最高收盘与最新交易日收盘，并覆盖写入 `ndx_data.js`。重新打开 `index.html` 即显示最新结果。

### 在 GitHub Pages 上每日自动更新（关键）

**GitHub Pages 是纯静态托管：它只伺服你提交的文件，不会运行 Python，也不会定时执行任何脚本。** 因此把当前文件 push 上去，数据只会在那一刻定格，**不会每天自动更新**。

要实现「每个交易日后 GitHub Pages 展示最新数据」，正确做法是把刷新任务交给 **GitHub Actions 定时工作流**：

- 已提供 `.github/workflows/update-ndx.yml`，按 **UTC 21:00（美东收盘后，仅工作日）** 触发；
- 工作流在 GitHub runner 上运行 `update_ndx.py` → 拉取最新 NDX 数据 → 把新的 `ndx_data.js` 提交回仓库；
- 该提交会自动触发 GitHub Pages 重建，站点即显示当日最新结果。

> 使用前确认：仓库 **Settings → Actions → General** 中工作流权限为「Read and write」（工作流里已声明 `permissions: contents: write`）；并且仓库近期有提交活动（GitHub 对超过 60 天无活动的仓库会暂停定时工作流）。

### 本地 / 自有服务器定时（备选）

若不在 GitHub Pages 托管，也可在本机或服务器用系统计划任务定时运行（原理同上，只是不依赖 Actions）：

**Windows 任务计划**（示例操作）：
```
python.exe "D:\fuli\update_ndx.py"
```
触发时间建议设为美东 16:30 之后（对应北京次日 04:30 之后），触发器选「每个工作日」。

**macOS / Linux（crontab）**，美东收盘后（UTC 20:30，仅工作日）：
```
30 20 * * 1-5 /usr/bin/python3 /path/to/fuli/update_ndx.py
```

> 注：美股节假日无交易，当日脚本取到的「最新交易日」仍为前一交易日，属正常现象。

### 文件结构

- `index.html`：页面与逻辑（原有 ECharts 图表 + 新增 NDX 查询面板）
- `echarts.js`：本地引入的 ECharts 库
- `ndx_data.js`：**由 `update_ndx.py` 生成**，NDX 展示数据（不要手动修改，由脚本维护）
- `update_ndx.py`：NDX 数据更新脚本（仅依赖 Python 标准库，无需安装第三方包）
