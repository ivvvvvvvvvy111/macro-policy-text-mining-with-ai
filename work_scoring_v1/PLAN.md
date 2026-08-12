# 政策文本关系级打分 + 因子面板 — 进度

## 已确认范围

- 抽样 / 打分：已冻结现有出分样本（不再补跑剩余新闻）
- 面板：三轨日频衰减聚合（全A + 行业 + 风格）
- 不做：IC、行情、仓位映射

## 进度

- [x] 脚手架 / 抽样 / measure+routing+三轨打分
- [x] 关系级分数交付（~1309 新闻 / ~18111 关系）
- [x] 冻结 `data/frozen_scores_relations.csv`
- [x] 半衰期衰减聚合核心
- [x] 生成三轨日频面板 CSV + `panel_manifest.json`
- [x] 聚合单测与 panels README

## 主交付

1. 关系级长表：`output/scores_relations.csv`
2. 因子面板目录：`output/panels/`
   - `industry_channel_daily.csv` / `industry_daily.csv`
   - `all_a_channel_daily.csv` / `all_a_daily.csv`
   - `style_axis_daily.csv`
   - `panel_manifest.json` / `README.md`

## 重建面板

```bash
cd "/Volumes/Elements SE/policy_news_database/work_scoring_v1"
.venv/bin/python scripts/build_panels.py
```
