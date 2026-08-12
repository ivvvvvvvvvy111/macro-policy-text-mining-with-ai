# Policy Text Router v0.2

当前版本在原有50条新闻实验之上新增：华尔街见闻快讯/长文历史采集、申万2021二级行业路由、PostgreSQL + pgvector 数据结构、新闻版本管理和近重复候选识别。详细说明见 `历史新闻接入说明.md`。

这是一个已经用50条真实政策新闻跑通的原型：读取新闻 CSV，先用 LLM 将政策新闻拆成独立 measure，再把每条 measure 路由到全A、风格和行业研究模块。接口使用硅基流动 OpenAI 兼容 API，JSON输出经过 Pydantic 校验、证据原文校验和限流重试。

## 目录

```text
policy_text_router_v0/
├─ data/news_sample.csv          # 最终50条典型政策新闻
├─ data/human_annotation_template.csv # 105条measure人工标注模板
├─ prompts/                      # 两阶段 prompt
├─ scripts/                      # 更新样例数据的脚本
├─ src/                          # API、schema、拆分与路由模块
├─ output/                       # 运行结果
├─ demo.ipynb                    # 最简运行入口
├─ policy_router_experiment.ipynb # 已执行、带结果的步骤式实验Notebook
├─ 实验报告.md                    # 综合实验报告
├─ run_pipeline.py               # 命令行入口
├─ .env.example                  # API 配置模板
└─ requirements.txt
```

## 最快运行

在本目录打开 PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

打开 `.env`，把 `SILICONFLOW_API_KEY` 改成自己的 Key。默认模型为 `Qwen/Qwen3.5-35B-A3B`。API Key不会写入输出文件。

先做零费用检查：

```powershell
python run_pipeline.py --dry-run
```

首次只跑 3 条：

```powershell
python run_pipeline.py --limit 3 --workers 1 --overwrite
```

确认输出后跑全部 50 条：

```powershell
python run_pipeline.py --workers 2 --overwrite
```

也可以打开 `demo.ipynb` 从上到下运行；若只想查看已完成实验，直接打开 `policy_router_experiment.ipynb`。

## 输入格式

CSV 必须包含：`news_id,title,date,source,url,content`。项目已附 50 条公开快讯样例。快讯不一定都是政策新闻，这正好用于验证第一阶段能否稳定排除行情、公司动态和观点类文本。

## 输出文件

- `output/measures.jsonl`：逐新闻的 measure 拆分原始结构。
- `output/routing_results.jsonl`：逐 measure 的完整 routing 结构。
- `output/routing_results.csv`：方便人工检查和后续统计的扁平表。
- `output/errors.jsonl`：单条失败记录；最终正式运行为空/不存在。
- `output/dry_run_report.json`：本地检查报告，不调用 API。
- `output/qa_summary.json`：样本完整性、证据命中和schema检查。
- `output/results_for_review.csv`：含原文、measure、标签和理由的复核表。
- `output/run_summary.json`：调用次数、token和重试统计。

## Schema v1

`measure.v1` 负责政策识别和原子措施拆分；`routing.v1` 的三个布尔标签可以同时为真，并额外输出风格维度、行业、主路由、置信度和简短依据。

## 费用与数据说明

每条新闻调用一次 measure API；只有提取出 measure 时才继续调用 routing API。新闻样例来自华尔街见闻公开 7x24 接口，仅保存公开快讯文本、时间和原链接，用于研究原型。最终正式运行50条新闻、105条measure，共157次调用。需要重新获取候选时运行：

```powershell
python scripts/build_policy_candidates.py --max-pages 60 --count 150
python scripts/curate_policy_sample.py --count 50 --workers 2
```

运行完成后执行质量检查并刷新Notebook：

```powershell
python scripts/qa_results.py
python scripts/build_notebook.py
```
