# work_scoring_v1

政策新闻 → measure 拆分 → 全A/风格/行业路由 → 关系级打分。

## 快速开始

```bash
cd work_scoring_v1
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 填入 SILICONFLOW_API_KEY
```

抽样（Top5000）：

```bash
python scripts/build_sample.py --n 5000
```

跑批（支持断点续跑）：

```bash
python scripts/run_pipeline.py --limit 5 --workers 2 --overwrite   # 冒烟
python scripts/run_pipeline.py --workers 8                         # 全量
python scripts/qa_summary.py
```

查看当前日历长文全量任务进度（在仓库根目录执行）：

```bash
make long-run-status
```

## 模型

| 步骤 | 环境变量 | 默认 |
|------|----------|------|
| measure | `SILICONFLOW_MODEL_MEASURE` | Qwen3.5-9B |
| routing | `SILICONFLOW_MODEL_ROUTING` | Qwen3.5-9B |
| scoring | `SILICONFLOW_MODEL_SCORING` | Qwen3.5-35B-A3B |

也支持DeepSeek官方OpenAI兼容接口。密钥只写入本地受忽略的 `.env`：

```bash
python scripts/configure_deepseek_key.py
python scripts/check_llm_connection.py  # 仅一次最小调用
python scripts/run_pipeline.py --limit 1 --workers 1 --output-dir output/deepseek_smoke
```

默认使用 `deepseek-v4-flash` 做措施拆分与路由、`deepseek-v4-pro` 做关系评分。生产Prompt和评分公式不因提供方切换而改变。

## 主交付

`output/scores_relations.csv`：关系级长表（含 state_score / a_unit 等；`policy_delta`/`novelty` 固定为空）。

构建无Top-N截断的18个月长文日历窗口：

```bash
python scripts/build_calendar_article_sample.py
```

输出保留原生 `source_type=article`、精确发布时间、来源和事件ID；manifest同时报告月份覆盖、每日候选数量和内容缺失。

冻结当前长文终版、构建面板、获取市场收益并生成HTML：

```bash
python scripts/finalize_calendar_results.py
python scripts/build_panels.py \
  --input output/calendar_articles_20240801_20260131/scores_relations_final.csv \
  --frozen data/frozen_calendar_articles_20240801_20260131_scores_relations.csv \
  --output-dir output/calendar_articles_20240801_20260131/panels_v1
python scripts/fetch_market_data.py
cd .. && make calendar-report
```

其中中证全指使用`000985.CSI`；全A等权为逐交易日有效A股`pct_chg`简单平均后的研究构造市场收益序列。两者均为政策因子之外的市场基准；详细定义见`docs/FACTOR_AND_BENCHMARK_DEFINITIONS.md`。

三轨日频因子面板：`output/panels/`（见该目录 `README.md`）。重建：

```bash
python scripts/build_panels.py
```
