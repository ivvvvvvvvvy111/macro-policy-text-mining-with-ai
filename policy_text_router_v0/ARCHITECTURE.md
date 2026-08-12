# policy_text_router_v0 架构说明

## 职责
该模块是早期政策新闻接入、候选样本构建、最小措施拆分和三路线分类实验。它定义了统一 PostgreSQL 模式，并为当前 `work_scoring_v1` 提供了数据和提示词基础。

## 关键文件
- `sql/schema.sql`：来源、新闻版本、事件聚类、行业字典、Prompt版本、模型运行、措施、路由和人工标注表。
- `scripts/load_news_to_postgres.py`：把新闻源数据写入统一数据库。
- `scripts/build_policy_candidates.py`：构建政策候选集。
- `prompts/measure_prompt.txt`：早期措施拆分提示词。
- `prompts/routing_prompt.txt`：早期三路线分类提示词。
- `run_pipeline.py`：早期拆分和路由实验入口。
- `output_baseline_v1/`：历史基线输出，不作为当前主结果。

## 与当前流水线的关系
- 当前评分实现位于 `../work_scoring_v1/`。
- 申万行业字典和拆分/路由结构由此模块演进而来。
- 修改数据库模式时需同步检查 `work_scoring_v1/src/schemas.py` 和交付脚本。

## 特殊约束
- `.env` 只在本地存在，不提交Git。
- `postgres_data/` 是数据库运行数据，不是源代码。
- 数据库初始化和加载属于有状态操作；执行前确认目标连接。
