from __future__ import annotations

import csv
import html
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def e(value: object) -> str:
    return html.escape(str(value or ""))


def yes(value: str) -> bool:
    return value.lower() == "true"


def route_tags(row: dict[str, str]) -> str:
    tags = []
    if yes(row["all_a"]):
        tags.append('<span class="route-tag all-a">全A</span>')
    if yes(row["style"]):
        tags.append('<span class="route-tag style">风格</span>')
    if yes(row["industry"]):
        tags.append('<span class="route-tag industry">行业</span>')
    if not tags:
        tags.append('<span class="route-tag none">不路由</span>')
    return "".join(tags)


def markdown_table_rows(rows: list[dict[str, str]]) -> str:
    output = []
    for row in rows:
        routes = []
        if yes(row["all_a"]): routes.append("全A")
        if yes(row["style"]): routes.append("风格")
        if yes(row["industry"]): routes.append("行业")
        if not routes: routes.append("不路由")
        cells = [
            row["sample_order"], row["date"][:10], row["theme"], row["title"], row["measure_id"],
            row["measure_summary"], row["evidence"], " / ".join(routes), row["style_dimensions"],
            row["industries"], row["confidence"], row["rationale"], row["url"],
        ]
        output.append("<tr>" + "".join(f"<td>{e(v)}</td>" for v in cells) + "</tr>")
    return "\n".join(output)


def main() -> None:
    review = read_csv(ROOT / "output" / "results_for_review.csv")
    news = read_csv(ROOT / "data" / "news_sample.csv")
    qa = read_json(ROOT / "output" / "qa_summary.json")
    run = read_json(ROOT / "output" / "run_summary.json")
    curation = read_json(ROOT / "work" / "curation" / "summary.json")

    example = [row for row in review if row["news_id"] == "3142203"]
    assert len(example) == 2
    theme_counts = Counter(row["candidate_theme"] for row in news)
    final_cost = (
        run["llm"]["prompt_tokens"] * 0.4 / 1_000_000
        + run["llm"]["completion_tokens"] * 3.2 / 1_000_000
    )
    curation_cost = (
        curation["llm"]["prompt_tokens"] * 0.4 / 1_000_000
        + curation["llm"]["completion_tokens"] * 3.2 / 1_000_000
    )
    total_cost = final_cost + curation_cost

    html_rows = []
    for row in review:
        html_rows.append(f"""
        <tr>
          <td class="num">{e(row['sample_order'])}</td>
          <td class="nowrap">{e(row['date'][:10])}</td>
          <td class="nowrap">{e(row['theme'])}</td>
          <td class="title-cell"><a href="{e(row['url'])}">{e(row['title'])}</a></td>
          <td class="nowrap">{e(row['measure_id'])}</td>
          <td>{e(row['measure_summary'])}</td>
          <td>{e(row['evidence'])}</td>
          <td class="nowrap">{route_tags(row)}</td>
          <td>{e(row['style_dimensions']) or '—'}</td>
          <td>{e(row['industries']) or '—'}</td>
          <td class="num">{e(row['confidence'])}</td>
          <td>{e(row['rationale'])}</td>
        </tr>""")

    html_doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>政策文本路由初步实验报告</title>
<style>
:root {{ --ink:#152a38; --muted:#667884; --line:#dbe5ea; --paper:#ffffff; --soft:#f4f8fa;
  --navy:#174866; --teal:#0f7c78; --amber:#d98720; --green:#297a52; --purple:#7657a6; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:#eef3f6; color:var(--ink); font-family:"Microsoft YaHei","PingFang SC",Arial,sans-serif; }}
.report {{ max-width:1420px; margin:28px auto; background:var(--paper); padding:46px 56px 64px; box-shadow:0 10px 34px rgba(25,54,70,.08); }}
h1 {{ margin:0; font-size:34px; font-weight:600; letter-spacing:.02em; }}
.subtitle {{ margin-top:9px; color:var(--muted); font-size:16px; }}
.lead {{ margin:28px 0 0; padding:18px 22px; border-left:5px solid var(--teal); background:var(--soft); font-size:17px; line-height:1.8; }}
h2 {{ margin:46px 0 18px; padding-bottom:10px; border-bottom:2px solid var(--ink); font-size:24px; }}
h3 {{ margin:28px 0 12px; font-size:18px; }}
p, li {{ line-height:1.75; }}
.metrics {{ display:grid; grid-template-columns:repeat(5,1fr); gap:12px; margin-top:22px; }}
.metric {{ border-top:3px solid var(--navy); background:var(--soft); padding:15px 16px; }}
.metric b {{ display:block; font-size:25px; margin-bottom:4px; }}
.metric span {{ color:var(--muted); font-size:13px; }}
.flow-wrap {{ overflow-x:auto; padding:4px 0 12px; }}
.flow {{ min-width:1220px; display:grid; grid-template-columns:260px 48px 320px 48px 320px 48px 165px; align-items:center; }}
.flow-card {{ min-height:310px; border:1px solid var(--line); padding:18px; background:#fff; }}
.flow-card .step {{ color:var(--teal); font-weight:600; font-size:13px; letter-spacing:.08em; }}
.flow-card h3 {{ margin:8px 0 12px; font-size:18px; }}
.flow-card p {{ font-size:13px; line-height:1.65; margin:7px 0; }}
.news-card {{ border-top:5px solid var(--navy); }}
.measure-card {{ border-top:5px solid var(--amber); }}
.route-card {{ border-top:5px solid var(--green); }}
.output-card {{ border-top:5px solid var(--purple); }}
.arrow {{ text-align:center; font-size:30px; color:#8ba0ac; }}
.mini {{ border:1px solid var(--line); background:var(--soft); padding:10px; margin:9px 0; }}
.mini b {{ display:block; margin-bottom:4px; font-size:13px; }}
.evidence {{ color:var(--muted); font-size:12px !important; }}
.route-tag {{ display:inline-block; margin:2px 4px 2px 0; padding:3px 8px; border-radius:11px; font-size:12px; font-weight:600; }}
.all-a {{ color:#174866; background:#dcecf4; }} .style {{ color:#70451a; background:#f8e8c9; }}
.industry {{ color:#1d6745; background:#dcefe5; }} .none {{ color:#68737a; background:#e9eef1; }}
.route-legend {{ display:flex; gap:16px; flex-wrap:wrap; margin:10px 0 2px; }}
.simple-table {{ width:100%; border-collapse:collapse; }}
.simple-table th,.simple-table td {{ border-bottom:1px solid var(--line); padding:10px 12px; text-align:left; vertical-align:top; }}
.simple-table th {{ background:var(--soft); font-weight:600; }}
.result-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:28px; }}
.bar-row {{ display:grid; grid-template-columns:80px 1fr 44px; gap:10px; align-items:center; margin:10px 0; }}
.bar {{ height:14px; background:#e8eef1; }} .bar i {{ display:block; height:100%; background:var(--teal); }}
.checks {{ display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }}
.check {{ padding:12px 14px; background:var(--soft); border-left:3px solid var(--green); font-size:14px; }}
.table-note {{ color:var(--muted); font-size:13px; margin:0 0 10px; }}
.policy-table-wrap {{ overflow-x:auto; border:1px solid var(--line); max-height:720px; overflow-y:auto; }}
.policy-table {{ border-collapse:separate; border-spacing:0; min-width:2550px; width:100%; font-size:13px; }}
.policy-table th,.policy-table td {{ padding:10px 11px; border-right:1px solid #edf1f3; border-bottom:1px solid var(--line); vertical-align:top; line-height:1.55; background:#fff; }}
.policy-table th {{ position:sticky; top:0; z-index:3; background:var(--navy); color:#fff; text-align:left; white-space:nowrap; }}
.policy-table td:nth-child(1),.policy-table th:nth-child(1) {{ position:sticky; left:0; z-index:2; width:52px; min-width:52px; background:#f7fafb; }}
.policy-table th:nth-child(1) {{ z-index:4; background:var(--navy); }}
.policy-table td:nth-child(4),.policy-table th:nth-child(4) {{ min-width:310px; }}
.policy-table td:nth-child(6) {{ min-width:300px; }} .policy-table td:nth-child(7) {{ min-width:280px; }}
.policy-table td:nth-child(12) {{ min-width:440px; }}
.policy-table a {{ color:var(--navy); text-decoration:none; }}
.nowrap {{ white-space:nowrap; }} .num {{ text-align:right; font-variant-numeric:tabular-nums; }}
.judgement {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }}
.judgement article {{ padding:16px; background:var(--soft); }}
.judgement h3 {{ margin-top:0; }}
.foot {{ color:var(--muted); font-size:13px; margin-top:38px; padding-top:16px; border-top:1px solid var(--line); }}
@media (max-width:900px) {{ .report{{margin:0;padding:28px 20px}} .metrics{{grid-template-columns:repeat(2,1fr)}} .result-grid,.judgement{{grid-template-columns:1fr}} }}
</style>
</head>
<body>
<main class="report">
  <h1>政策文本路由初步实验报告</h1>
  <div class="subtitle">50条真实政策新闻 · measure拆分 · 全A / 风格 / 行业路由</div>
  <div class="lead"><b>结论先行：</b>原型已经完整跑通，可以进入人工标注。50条新闻拆成105条独立政策措施，全部保留可回查原文证据；自动检查无缺失、无结构冲突。当前结果是人工标注前的 baseline，不是模型准确率。</div>
  <section class="metrics">
    <div class="metric"><b>50</b><span>政策新闻</span></div>
    <div class="metric"><b>105</b><span>独立 measure</span></div>
    <div class="metric"><b>9 / 5 / 82</b><span>全A / 风格 / 行业正标签</span></div>
    <div class="metric"><b>100%</b><span>evidence 原文命中</span></div>
    <div class="metric"><b>¥{total_cost:.2f}</b><span>筛选 + 正式运行估算成本</span></div>
  </section>

  <h2>一、一张图看清整个实验</h2>
  <div id="flowchart" class="flow-wrap">
    <div class="flow" role="img" aria-label="从新闻到measure拆分，再到全A风格行业路由和结构化结果的流程图">
      <article class="flow-card news-card">
        <div class="step">INPUT</div><h3>一条政策新闻</h3>
        <p><b>中共中央政治局会议：</b>深化资本市场投融资综合改革，提升资本市场韧性和信心</p>
        <p class="evidence">原文同时包含：一揽子化债、地方中小金融机构改革化险、资本市场投融资改革。</p>
      </article>
      <div class="arrow">→</div>
      <article class="flow-card measure-card">
        <div class="step">STEP 1</div><h3>拆成独立 measure</h3>
        <div class="mini"><b>M001 · 化债与金融风险处置</b><p>对象：房地产、地方中小金融机构</p><p class="evidence">证据：“实施好一揽子化债方案……”</p></div>
        <div class="mini"><b>M002 · 资本市场投融资改革</b><p>对象：资本市场</p><p class="evidence">证据：“深化资本市场投融资综合改革……”</p></div>
      </article>
      <div class="arrow">→</div>
      <article class="flow-card route-card">
        <div class="step">STEP 2</div><h3>每条 measure 单独路由</h3>
        <div class="mini"><b>M001</b><span class="route-tag all-a">全A</span><span class="route-tag style">风格</span><span class="route-tag industry">行业</span><p>风格：质量、流动性、波动率<br>行业：房地产、银行</p></div>
        <div class="mini"><b>M002</b><span class="route-tag all-a">全A</span><p>影响市场投融资制度与共同定价环境</p></div>
      </article>
      <div class="arrow">→</div>
      <article class="flow-card output-card">
        <div class="step">OUTPUT</div><h3>结构化结果</h3>
        <p>JSONL：保留完整层级</p><p>CSV：人工复核与统计</p><p>标注模板：下一步形成真值</p>
      </article>
    </div>
  </div>

  <h2>二、实验设置</h2>
  <table class="simple-table">
    <tr><th>项目</th><th>本次设置</th></tr>
    <tr><td>新闻来源</td><td>华尔街见闻公开7×24快讯；2026-07-22 至 2026-08-06</td></tr>
    <tr><td>样本形成</td><td>约6000条历史快讯 → 332条规则候选 → 150条主题均衡候选 → 81条有效政策候选 → 最终50条</td></tr>
    <tr><td>模型</td><td>硅基流动 · Qwen/Qwen3.5-35B-A3B · 关闭思考模式 · JSON Mode</td></tr>
    <tr><td>任务</td><td>第一阶段拆 measure；第二阶段判断全A、风格、行业，三个标签允许重叠</td></tr>
    <tr><td>正式调用</td><td>{run['llm']['calls']}次；输入 {run['llm']['prompt_tokens']:,} tokens，输出 {run['llm']['completion_tokens']:,} tokens</td></tr>
    <tr><td>成本</td><td>候选筛选约 ¥{curation_cost:.2f}，最终正式运行约 ¥{final_cost:.2f}，合计约 ¥{total_cost:.2f}（不含调试重跑）</td></tr>
  </table>

  <h2>三、拆分与分类结果</h2>
  <div class="result-grid">
    <section>
      <h3>Routing标签</h3>
      <div class="bar-row"><span>行业</span><div class="bar"><i style="width:78.1%"></i></div><b>82</b></div>
      <div class="bar-row"><span>全A</span><div class="bar"><i style="width:8.6%"></i></div><b>9</b></div>
      <div class="bar-row"><span>风格</span><div class="bar"><i style="width:4.8%"></i></div><b>5</b></div>
      <div class="bar-row"><span>不路由</span><div class="bar"><i style="width:11.4%"></i></div><b>12</b></div>
      <p class="table-note">标签允许重叠，因此合计会超过105。行业占比较高与本轮能源、制造、产业标准样本较多有关。</p>
    </section>
    <section>
      <h3>自动质量检查</h3>
      <div class="checks">
        <div class="check">50条输入<br><b>50条输出</b></div>
        <div class="check">流程错误<br><b>0</b></div>
        <div class="check">证据命中<br><b>105 / 105</b></div>
        <div class="check">Schema冲突<br><b>0</b></div>
        <div class="check">非法行业标签<br><b>0</b></div>
        <div class="check">高度重复measure<br><b>0对</b></div>
      </div>
    </section>
  </div>

  <h2>四、105条政策measure与分类结果</h2>
  <p class="table-note">下表可横向滚动，左侧序号固定；标题可打开原新闻。每一行是一条measure，而不是一整篇新闻。</p>
  <div class="policy-table-wrap" aria-label="政策measure完整分类表">
    <table class="policy-table">
      <thead><tr><th>序号</th><th>日期</th><th>主题</th><th>政策新闻</th><th>Measure</th><th>措施概括</th><th>原文证据</th><th>路由</th><th>风格维度</th><th>行业</th><th>置信度</th><th>分类理由</th></tr></thead>
      <tbody>{''.join(html_rows)}</tbody>
    </table>
  </div>

  <h2>五、当前判断</h2>
  <div class="judgement">
    <article><h3>已经解决</h3><p>流程完整、输出稳定；measure可回查原文；行业标签口径统一；可直接进入人工标注。</p></article>
    <article><h3>仍需人工确认</h3><p>跨境政策是否真的传导到A股、风格标签是否存在后验解释、复杂会议是否仍有漏拆或合并过度。</p></article>
    <article><h3>下一步</h3><p>对105条measure填写人工真值，分别计算全A、风格、行业的precision、recall和F1，再决定下一版prompt。</p></article>
  </div>
  <div class="foot">说明：模型置信度集中在0.85—0.95，尚未校准，不能解释为真实正确概率；本次结果是初步实验 baseline，不直接形成投资结论。</div>
</main>
</body></html>"""
    (ROOT / "实验报告.html").write_text(html_doc, encoding="utf-8")

    theme_md = "\n".join(f"| {e(k)} | {v} |" for k, v in theme_counts.most_common())
    md_rows = markdown_table_rows(review)
    md_doc = f"""# 政策文本路由初步实验报告

50条真实政策新闻 · measure拆分 · 全A / 风格 / 行业路由

> **结论：** 原型已经完整跑通，可以进入人工标注。50条新闻拆成105条独立政策措施，全部保留可回查原文证据；自动检查无缺失、无结构冲突。当前结果是人工标注前的 baseline，不是模型准确率。

| 新闻 | Measure | 全A | 风格 | 行业 | Evidence命中 | 估算成本 |
|---:|---:|---:|---:|---:|---:|---:|
| 50 | 105 | 9 | 5 | 82 | 100% | ¥{total_cost:.2f} |

## 一、一张图看清整个实验

![从政策新闻到measure拆分和研究路由的流程图](assets/policy-router-flow.png)

图中使用一条真实样本说明完整数据结构：同一篇政治局会议新闻先拆成“化债与金融风险处置”和“资本市场投融资改革”两条measure，再分别判断全A、风格与行业路由。完整可缩放版本见 [实验报告.html](实验报告.html)。

## 二、实验设置

| 项目 | 本次设置 |
|---|---|
| 新闻来源 | 华尔街见闻公开7×24快讯；2026-07-22至2026-08-06 |
| 样本形成 | 约6000条快讯 → 332条规则候选 → 150条均衡候选 → 81条有效政策候选 → 最终50条 |
| 模型 | 硅基流动 `Qwen/Qwen3.5-35B-A3B`；关闭思考模式；JSON Mode |
| 正式调用 | {run['llm']['calls']}次；输入{run['llm']['prompt_tokens']:,} tokens，输出{run['llm']['completion_tokens']:,} tokens |
| 成本 | 候选筛选约¥{curation_cost:.2f}，正式运行约¥{final_cost:.2f}，合计约¥{total_cost:.2f}，不含调试重跑 |
| 拆分判断 | 不同工具、对象、执行期或传导机制拆开；同一工具下的多个数字目标合并 |
| 路由判断 | 全A、风格、行业允许重叠；找不到直接传导时保留“不路由” |

主题分布：

| 主题 | 新闻数 |
|---|---:|
{theme_md}

## 三、结果与质量检查

| 检查项 | 结果 |
|---|---:|
| 输入新闻 / 输出新闻 | 50 / 50 |
| 独立measure | 105 |
| 全A / 风格 / 行业正标签 | 9 / 5 / 82 |
| 不路由measure | 12 |
| API或流程错误 | 0 |
| Evidence逐字命中 | 105 / 105 |
| Schema逻辑冲突 | 0 |
| 非法行业标签 | 0 |
| 高度重复measure | 0对 |

## 四、105条政策measure与分类结果

下表使用HTML容器承载，可以横向滚动查看全部字段。若当前Markdown阅读器禁用了HTML样式，请直接打开 [实验报告.html](实验报告.html) 或 [results_for_review.csv](output/results_for_review.csv)。

<div style="overflow-x:auto; width:100%; border:1px solid #dbe5ea;">
<table style="border-collapse:collapse; min-width:2500px; width:100%; font-size:13px;">
<thead><tr><th>序号</th><th>日期</th><th>主题</th><th>政策新闻</th><th>Measure</th><th>措施概括</th><th>原文证据</th><th>路由</th><th>风格维度</th><th>行业</th><th>置信度</th><th>分类理由</th><th>原文链接</th></tr></thead>
<tbody>
{md_rows}
</tbody></table></div>

## 五、当前判断

1. **可以进入人工标注：** 数据链、模型调用、结构校验和复核表已经完整。
2. **仍需重点核对：** 跨境政策是否真的传导到A股；风格标签是否存在后验解释；复杂会议是否仍有漏拆或合并过度。
3. **不能把confidence当准确率：** 模型置信度集中在0.85—0.95，尚未校准。
4. **下一步不是继续盲改prompt：** 先对105条measure填人工真值，再分别计算全A、风格和行业的precision、recall、F1。
"""
    (ROOT / "实验报告.md").write_text(md_doc, encoding="utf-8")
    print(json.dumps({"html": str(ROOT / '实验报告.html'), "md": str(ROOT / '实验报告.md'), "rows": len(review)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
