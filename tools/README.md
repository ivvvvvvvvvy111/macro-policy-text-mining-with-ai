# tools

本目录存放可重复执行的项目维护与交付构建脚本。

- `project_status.py`：汇总冻结样本、拆分、路由、关系和错误数量。
- `repository_check.py`：检查Git发布前的敏感文件忽略规则和大文件风险。
- `prepare_delivery.py`：把分散的JSONL/CSV结果整理成工作簿所需数据。
- `build_delivery_workbook.mjs`：生成并验证Excel审阅工作簿。
- `build_result_showcase.mjs`：生成单文件HTML结果展示和15条案例Notebook。

脚本默认读取现有输出，不应覆盖冻结输入或模型原始结果。
