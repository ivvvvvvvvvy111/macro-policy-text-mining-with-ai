# Macro Policy Text Mining with AI

使用大语言模型把政策新闻拆成最小政策措施，并提取其对A股全市场、风格和申万行业的结构化影响。

## 当前流程
```text
政策新闻 → 最小措施拆分 → 全A/风格/行业多标签路由
        → 路线级维度评分 → 固定公式合成 → 日频因子面板
```

## 从哪里开始
- AI或新开发者：先读 [`AGENTS.md`](AGENTS.md)、[`PROGRESS.md`](PROGRESS.md) 和 [`DECISIONS.md`](DECISIONS.md)。
- 当前评分流水线：[`work_scoring_v1/README.md`](work_scoring_v1/README.md)。
- 早期数据和路由实验：[`policy_text_router_v0/README.md`](policy_text_router_v0/README.md)。
- 结果展示：[`deliverables/结果展示网页/index.html`](deliverables/结果展示网页/index.html)。
- 在线研究台前端 / Vercel 部署：[`web/README.md`](web/README.md)。

## 在线网页部署

前端源码在 [`web/`](web/)，可用 Vercel 直接部署：

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fivvvvvvvvvy111%2Fmacro-policy-text-mining-with-ai&project-name=macro-policy-research-hub&repository-name=macro-policy-text-mining-with-ai&root-directory=web)

导入时确认 `Root Directory = web`。

## 快速检查
```bash
make status
make test
make check
```

## 当前状态
- 冻结样本：5,000条新闻。
- 已有拆分输出：1,309条新闻。
- 措施路由：5,527条。
- 评分关系：18,111条。
- 当前主要任务：人工金标准、失败重跑、评分锚点和样本外有效性检验。

## 数据说明
本仓库不发布密钥、本地数据库运行目录、日志和大体积原始/派生数据。复现时需在本地配置数据源与模型API；结构说明和小型展示保留在仓库内。
