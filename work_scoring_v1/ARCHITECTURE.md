# work_scoring_v1 架构说明

## 职责
当前主流水线：从冻结新闻样本出发，依次进行措施拆分、三路线分类、关系评分、公式合成、日频聚合和质量检查。

## 处理阶段
1. `src/measure_extract.py`：调用措施Prompt，输出 `measure.v1`。
2. `src/routing.py`：调用路由Prompt，输出 `routing.v2`。
3. `src/scoring.py`：按全A、风格、行业调用相应评分Prompt。
4. `src/formulas.py`：用固定公式计算 `state_score`、`a_unit` 等。
5. `src/aggregate.py`：按期限半衰期做日频衰减和面板聚合。
6. `scripts/qa_summary.py`：汇总覆盖、空值、错误和关系分布。

## 关键接口
- 输入：`data/sample_5000.csv`。
- 行业字典：`data/sw2021_l2_industries.csv`。
- 严格数据结构：`src/schemas.py`。
- 模型客户端与配置：`src/llm_client.py`、`src/config.py`。
- 关系级主输出：`output/scores_relations.csv`。

## 特殊约束
- 三条路线可重叠；不得将 `multiple` 当作第四种经济类别。
- 评分模型给维度分，最终综合分由 `src/formulas.py` 计算。
- `policy_delta` 和 `novelty` 当前为空。
- 跑批必须支持断点续跑，错误保留在 `output/errors.jsonl`。
- 修改公式后必须运行 `tests/test_formulas.py` 和聚合测试。
