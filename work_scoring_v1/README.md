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

## 模型

| 步骤 | 环境变量 | 默认 |
|------|----------|------|
| measure | `SILICONFLOW_MODEL_MEASURE` | Qwen3.5-9B |
| routing | `SILICONFLOW_MODEL_ROUTING` | Qwen3.5-9B |
| scoring | `SILICONFLOW_MODEL_SCORING` | Qwen3.5-35B-A3B |

## 主交付

`output/scores_relations.csv`：关系级长表（含 state_score / a_unit 等；`policy_delta`/`novelty` 固定为空）。

三轨日频因子面板：`output/panels/`（见该目录 `README.md`）。重建：

```bash
python scripts/build_panels.py
```
