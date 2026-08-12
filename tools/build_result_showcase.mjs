import fs from "node:fs";
import path from "node:path";

const root = "/Volumes/Elements SE/policy_news_database";
const outDir = path.join(root, "deliverables", "结果展示网页");
fs.mkdirSync(outDir, { recursive: true });

const readJsonl = (file) => fs.readFileSync(file, "utf8").split(/\r?\n/).filter(Boolean).map(JSON.parse);
const csvParse = (text) => {
  const rows = []; let row = [], cell = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (c === '"') quoted = false;
      else cell += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') { row.push(cell); cell = ""; }
    else if (c === '\n') { row.push(cell.replace(/\r$/, "")); rows.push(row); row = []; cell = ""; }
    else cell += c;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  const headers = rows.shift().map((x, i) => i === 0 ? x.replace(/^\uFEFF/, "") : x);
  return rows.filter(r => r.some(Boolean)).map(r => Object.fromEntries(headers.map((h, i) => [h, r[i] ?? ""])));
};

const output = path.join(root, "work_scoring_v1", "output");
const measures = readJsonl(path.join(output, "measures.jsonl"));
const routes = readJsonl(path.join(output, "routing_results.jsonl"));
const relations = csvParse(fs.readFileSync(path.join(output, "scores_relations.csv"), "utf8"));
const errors = readJsonl(path.join(output, "errors.jsonl"));
const qa = JSON.parse(fs.readFileSync(path.join(output, "qa_summary.json"), "utf8"));
const promptDir = path.join(root, "work_scoring_v1", "prompts");
const prompts = [
  ["措施拆分 Prompt", "Qwen3.5-9B", "measure_prompt.txt"],
  ["三路分类 Prompt", "Qwen3.5-9B", "routing_prompt.txt"],
  ["全A评分 Prompt", "Qwen3.5-35B-A3B", "all_a_score_prompt.txt"],
  ["风格评分 Prompt", "Qwen3.5-35B-A3B", "style_score_prompt.txt"],
  ["行业评分 Prompt", "Qwen3.5-35B-A3B", "industry_score_prompt.txt"],
].map(([name, model, file]) => ({ name, model, file, text: fs.readFileSync(path.join(promptDir, file), "utf8") }));

const measureByNews = new Map(measures.map(x => [x.news.news_id, x]));
const routeByKey = new Map(routes.map(x => [`${x.news_id}:${x.measure.measure_id}`, x]));
const relByKey = new Map();
for (const r of relations) {
  const key = `${r.news_id}:${r.measure_id}`;
  if (!relByKey.has(key)) relByKey.set(key, []);
  relByKey.get(key).push(r);
}

const selected = [
  ["全A", "N00009", "M001"],
  ["风格", "N00488", "M001"],
  ["行业", "N00003", "M001"],
  ["三路线同时", "N00611", "M005"],
];

const compactRelation = r => ({
  track: r.track, relation_id: r.relation_id, channel: r.channel, horizon: r.horizon,
  style_axis: r.style_axis, industry: r.industry_l2_name, directness: r.directness,
  direction: r.direction, intensity: r.intensity, relative_strength: r.relative_strength,
  coverage: r.coverage, certainty: r.certainty, persistence: r.persistence,
  info_increment: r.info_increment, confidence: r.confidence,
  state_score: r.state_score, a_unit: r.a_unit, evidence: r.evidence, rationale: r.rationale,
});

const cases = selected.map(([label, nid, mid]) => {
  const key = `${nid}:${mid}`, route = routeByKey.get(key), mrec = measureByNews.get(nid);
  return {
    label, news_id: nid, measure_id: mid, title: route.title,
    date: mrec?.news?.date || "", url: mrec?.news?.url || "",
    source_excerpt: mrec?.news?.content?.slice(0, 440) || "",
    measure: route.measure, routing: route.routing,
    relations: (relByKey.get(key) || []).map(compactRelation),
  };
});

const routeCounts = routes.reduce((a, x) => (a[x.routing.primary_route] = (a[x.routing.primary_route] || 0) + 1, a), {});
const uniqueErrors = new Set(errors.map(x => x.news_id)).size;
const stats = {
  input_news: 5000, measure_news: measures.length, routing_rows: routes.length,
  relation_rows: relations.length, errors: errors.length, unique_errors: uniqueErrors,
  tracks: qa.track_counts, routes: routeCounts,
  completed: 901, non_policy: 404, failed_no_measure: 3691,
};

const data = JSON.stringify({ cases, stats, prompts }).replace(/</g, "\\u003c");
const html = `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>政策新闻提取结果展示</title>
<style>
:root{--ink:#172033;--muted:#667085;--line:#dbe3ef;--blue:#1f5eff;--pale:#f5f8fd;--green:#09815c;--orange:#d97706;--purple:#7c3aed}
*{box-sizing:border-box}body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif;color:var(--ink);background:#fff;line-height:1.58}
header{padding:64px max(24px,calc((100vw - 1180px)/2));background:linear-gradient(135deg,#0f2547,#1f5eff);color:#fff}header h1{font-size:clamp(34px,5vw,62px);margin:0 0 12px;letter-spacing:-.04em}header p{max-width:780px;font-size:18px;opacity:.88;margin:0}.wrap{max-width:1180px;margin:auto;padding:44px 24px 80px}
h2{font-size:30px;margin:48px 0 18px}h3{margin:0 0 8px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.stat{padding:18px;border:1px solid var(--line);border-radius:16px;background:var(--pale)}.stat b{display:block;font-size:27px}.stat span{color:var(--muted);font-size:13px}
.bars{display:grid;grid-template-columns:1fr 1fr;gap:22px}.barbox{border:1px solid var(--line);border-radius:16px;padding:20px}.bar{display:grid;grid-template-columns:110px 1fr 62px;align-items:center;gap:10px;margin:12px 0}.track{height:10px;border-radius:99px;background:#e8edf5;overflow:hidden}.track i{display:block;height:100%;border-radius:99px;background:var(--blue)}
.case{margin:34px 0 54px;border-top:3px solid var(--blue);padding-top:22px}.badge{display:inline-block;background:#eaf0ff;color:#1746ba;border-radius:99px;padding:5px 11px;font-size:13px;font-weight:700}.meta{color:var(--muted);font-size:14px}.flow{display:grid;grid-template-columns:repeat(4,1fr);gap:22px;margin:20px 0}.step{position:relative;padding:17px;border:1px solid var(--line);border-radius:15px;background:#fff;min-height:190px}.step:not(:last-child):after{content:"→";position:absolute;right:-20px;top:46%;color:var(--blue);font-size:25px;font-weight:800}.step small{color:var(--blue);font-weight:800}.step p{font-size:14px;margin:8px 0}.prompt{background:#f7f8fb;border-radius:10px;padding:9px;color:#475467;font-size:12px}.code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;background:#101828;color:#e6edf7;padding:11px;border-radius:10px;font-size:12px;overflow:auto}
.master{display:grid;grid-template-columns:repeat(5,1fr);gap:18px;margin:20px 0}.master .step{min-height:245px}.master .step:nth-child(4){border-color:#c5b5fd}.master .step:nth-child(5){border-color:#a7dfcc}.model{display:inline-block;margin-top:8px;padding:3px 8px;border-radius:6px;background:#edf2ff;color:#1746ba;font-size:11px;font-weight:700}.formula{margin-top:18px;padding:18px;border:1px solid #bbd6c9;background:#f0faf5;border-radius:14px}.formula code{display:block;margin:7px 0;color:#075e45;white-space:normal}.prompt-list{display:grid;grid-template-columns:1fr;gap:10px;margin-top:15px}.prompt-list details{border:1px solid var(--line);border-radius:12px;padding:12px 15px;background:#fff}.prompt-list pre{white-space:pre-wrap;word-break:break-word;background:#101828;color:#e6edf7;padding:15px;border-radius:10px;max-height:430px;overflow:auto;font-size:12px}.legend{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0}.legend span{padding:5px 9px;border-radius:99px;font-size:12px}.ai{background:#eaf0ff;color:#1746ba}.rule{background:#e8f7ef;color:#08704f}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:10px;border-bottom:1px solid var(--line);vertical-align:top}th{background:#f4f7fb;position:sticky;top:0}.score{font-weight:800;color:var(--green)}details{margin-top:12px}summary{cursor:pointer;color:var(--blue);font-weight:700}.note{padding:15px;border-left:4px solid var(--orange);background:#fff8e8;color:#744b00;border-radius:8px}.footer{color:var(--muted);font-size:13px;margin-top:54px}
@media(max-width:850px){.stats{grid-template-columns:repeat(2,1fr)}.bars{grid-template-columns:1fr}.flow,.master{grid-template-columns:1fr}.step:not(:last-child):after{content:"↓";right:50%;top:auto;bottom:-24px}.bar{grid-template-columns:90px 1fr 55px}}
</style></head><body>
<header><h1>政策新闻 → 可解释评分</h1><p>从一篇政策新闻出发，展示它如何被拆成最小措施、路由到全A/风格/行业，并形成可追溯的关系级分数。</p></header>
<main class="wrap"><section><h2>原始新闻如何经过 Prompt 变成分数</h2><p>前四步由大语言模型阅读文本并按 Prompt 输出结构化判断；最后一步由程序执行固定公式。也就是说，模型不直接随意给出最终综合分。</p><div class="legend"><span class="ai">AI + Prompt 判断</span><span class="rule">程序固定公式</span></div><div class="master">
<div class="step"><small>01 原始数据</small><h3>政策新闻全文</h3><p>标题、日期、来源、URL、正文和内容状态。</p><div class="prompt">没有打分；这里只是读取数据库或冻结样本。</div></div>
<div class="step"><small>02 Prompt ①</small><h3>措施拆分</h3><p>判断是否为政策新闻，并拆成最小独立措施。</p><span class="model">Qwen3.5-9B</span><div class="prompt">输出：summary、action、target、mechanism、evidence</div></div>
<div class="step"><small>03 Prompt ②</small><h3>三路分类</h3><p>判断措施进入全A、风格、行业中的哪些模块。</p><span class="model">Qwen3.5-9B</span><div class="prompt">输出：三个布尔标签、行业、风格维度、置信度和理由</div></div>
<div class="step"><small>04 Prompt ③</small><h3>分路线评分</h3><p>按实际路由调用全A、风格和/或行业评分 Prompt。</p><span class="model">Qwen3.5-35B-A3B</span><div class="prompt">模型输出：方向、强度、覆盖、确定性、持续性、置信度等原始维度分</div></div>
<div class="step"><small>05 固定规则</small><h3>计算最终分数</h3><p>Python 公式把维度分组合为 state_score 或 a_unit。</p><span class="model" style="background:#e8f7ef;color:#08704f">不是 Prompt，不是模型再打分</span><div class="prompt">输出关系级长表，并按期限做日频衰减聚合。</div></div></div>
<div class="formula"><b>最终分数如何算</b><code>行业 state_score = direction × intensity/4 × coverage/4 × certainty/4 × (0.5 + 0.5 × persistence/4)</code><code>全A state_score = direction × intensity/4 × coverage/4 × certainty/4 × persistence/4 × confidence</code><code>风格 a_unit = direction × relative_strength/4 × coverage/4 × certainty/4 × confidence</code><p>其中方向、强度等维度由评分 Prompt 约束下的大模型判断；乘法公式由代码固定执行。confidence 是判断把握度，不是政策强度。</p></div>
<h3 style="margin-top:24px">点击查看本项目实际使用的完整 Prompt</h3><div class="prompt-list" id="promptList"></div></section>
<section><h2>当前结果概览</h2><div class="stats" id="stats"></div><div class="bars" id="bars"></div><p class="note">错误日志行数与唯一新闻数不同，是因为同一新闻可能发生多次重试。空值不是 0：policy_delta、novelty 等字段当前缺少历史比较基准。</p></section>
<section><h2>四类真实流程案例</h2><div id="cases"></div></section><p class="footer">数据来源：work_scoring_v1 当前冻结样本与现有模型输出。本页面只展示结果，不重新运行模型。</p></main>
<script>const DATA=${data};
const fmt=n=>Number(n).toLocaleString('zh-CN');
const esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
document.querySelector('#promptList').innerHTML=DATA.prompts.map(p=>\`<details><summary>\${p.name}　<span class="model">\${p.model}</span></summary><p class="meta">文件：\${p.file}</p><pre>\${esc(p.text)}</pre></details>\`).join('');
document.querySelector('#stats').innerHTML=[['输入新闻',DATA.stats.input_news],['已拆分新闻',DATA.stats.measure_news],['措施路由',DATA.stats.routing_rows],['评分关系',DATA.stats.relation_rows],['完成全链路',DATA.stats.completed],['判定非政策',DATA.stats.non_policy],['无拆分结果',DATA.stats.failed_no_measure],['唯一错误新闻',DATA.stats.unique_errors]].map(([k,v])=>\`<div class="stat"><b>\${fmt(v)}</b><span>\${k}</span></div>\`).join('');
const block=(title,obj,max)=>\`<div class="barbox"><h3>\${title}</h3>\${Object.entries(obj).sort((a,b)=>b[1]-a[1]).map(([k,v])=>\`<div class="bar"><span>\${k}</span><div class="track"><i style="width:\${v/max*100}%"></i></div><b>\${fmt(v)}</b></div>\`).join('')}</div>\`;
document.querySelector('#bars').innerHTML=block('评分关系数量',DATA.stats.tracks,Math.max(...Object.values(DATA.stats.tracks)))+block('措施主路由数量',DATA.stats.routes,Math.max(...Object.values(DATA.stats.routes)));
const show=v=>v===''||v==null?'—':v;
document.querySelector('#cases').innerHTML=DATA.cases.map(c=>{const r=c.routing,m=c.measure;return \`<article class="case"><span class="badge">\${c.label}</span><h3>\${c.title}</h3><p class="meta">\${c.news_id} · \${c.date} · 措施 \${c.measure_id} · <a href="\${c.url}" target="_blank">原文</a></p><div class="flow">
<div class="step"><small>01 新闻输入</small><p>\${c.source_excerpt}…</p><div class="prompt">输入：标题、日期、来源、新闻全文</div></div>
<div class="step"><small>02 措施拆分</small><div class="prompt">提示词：按工具、对象、执行期或直接机制拆成最小独立措施；证据必须来自连续原文。</div><p><b>输出：</b>\${m.summary}</p><p>动作：\${m.policy_action}<br>对象：\${m.target}</p></div>
<div class="step"><small>03 三路分类</small><div class="prompt">提示词：all_a、style、industry 可同时为真，但每个标签都要有直接、可解释的传导机制。</div><div class="code">all_a: \${r.all_a}<br>style: \${r.style}<br>industry: \${r.industry}<br>primary: \${r.primary_route}<br>confidence: \${r.confidence}</div></div>
<div class="step"><small>04 关系评分</small><div class="prompt">提示词：按路线展开为“措施 × 渠道 × 期限/行业/风格轴”，分别给方向、强度、覆盖、确定性、持续性与置信度。</div><p><b>输出 \${c.relations.length} 条关系</b></p><p>最终分数见下表。</p></div></div>
<table><thead><tr><th>路线</th><th>渠道 / 对象</th><th>方向</th><th>强度</th><th>覆盖</th><th>确定性</th><th>持续性</th><th>置信度</th><th>最终分数</th></tr></thead><tbody>\${c.relations.map(x=>\`<tr><td>\${x.track}</td><td>\${x.channel}<br>\${x.style_axis||x.industry||''}</td><td>\${show(x.direction)}</td><td>\${show(x.intensity||x.relative_strength)}</td><td>\${show(x.coverage)}</td><td>\${show(x.certainty)}</td><td>\${show(x.persistence)}</td><td>\${show(x.confidence)}</td><td class="score">\${show(x.state_score||x.a_unit)}</td></tr>\`).join('')}</tbody></table><details><summary>查看路由理由和关系评分理由</summary><p><b>路由：</b>\${r.rationale}</p>\${c.relations.map(x=>\`<p><b>\${x.relation_id}：</b>\${x.rationale}</p>\`).join('')}</details></article>\`}).join('');</script></body></html>`;
fs.writeFileSync(path.join(outDir, "index.html"), html);

const notebookKeys = [
  ["N00009","M001"],["N00052","M001"],["N00135","M010"],
  ["N00467","M002"],["N00488","M001"],["N00488","M003"],
  ["N00001","M001"],["N00003","M001"],["N00037","M002"],
  ["N00056","M007"],["N00611","M003"],["N00611","M005"],
  ["N00611","M006"],["N00995","M002"],["N00368","M001"],
];
const md = ["# 政策新闻到评分：15条案例 Notebook", "", "> 目的：像 Notebook 一样逐步查看真实输入、中间结果和最终分数。本文件不重新调用模型。", "",
"## 统一处理步骤", "", "1. 输入新闻标题、日期、来源与全文。", "2. 用措施提示词拆出最小政策措施。", "3. 用路由提示词判断全A、风格和行业，可多选。", "4. 对进入的路线分别展开关系并评分。", "5. 保留证据、理由及空值，确保可追溯。", ""];
for (let i=0;i<notebookKeys.length;i++) {
  const [nid,mid]=notebookKeys[i], key=`${nid}:${mid}`, route=routeByKey.get(key), mrec=measureByNews.get(nid), rs=relByKey.get(key)||[];
  if(!route) continue;
  md.push(`## 案例 ${i+1}｜${route.title}`, "", `**标识：** ${nid} / ${mid}　　**日期：** ${mrec?.news?.date||""}`, "",
  "### Step 1：输入", "", `- 新闻标题：${route.title}`, `- 原文链接：${mrec?.news?.url||""}`, `- 正文节选：${(mrec?.news?.content||"").slice(0,300)}……`, "",
  "### Step 2：措施拆分结果", "", `- 摘要：${route.measure.summary}`, `- 政策动作：${route.measure.policy_action}`, `- 作用对象：${route.measure.target}`, `- 直接机制：${route.measure.mechanism}`, `- 原文证据：${route.measure.evidence}`, "",
  "### Step 3：路由结果", "", "```yaml", `all_a: ${route.routing.all_a}`, `style: ${route.routing.style}`, `industry: ${route.routing.industry}`, `primary_route: ${route.routing.primary_route}`, `confidence: ${route.routing.confidence}`, "```", "", `路由理由：${route.routing.rationale}`, "",
  "### Step 4：最终评分", "", "| 路线 | 关系ID | 渠道 | 行业/风格轴 | 方向 | 强度/相对强度 | 覆盖 | 确定性 | 持续性 | 置信度 | 最终分数 |", "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|");
  for(const r of rs) md.push(`| ${r.track} | ${r.relation_id} | ${r.channel} | ${r.style_axis||r.industry_l2_name||"—"} | ${r.direction||"—"} | ${r.intensity||r.relative_strength||"—"} | ${r.coverage||"—"} | ${r.certainty||"—"} | ${r.persistence||"—"} | ${r.confidence||"—"} | ${r.state_score||r.a_unit||"—"} |`);
  md.push("", "<details><summary>查看各关系评分理由</summary>", "", ...rs.map(r=>`- **${r.relation_id}**：${r.rationale}`), "", "</details>", "");
}
md.push("## 阅读结果时的三个注意事项", "", "1. `confidence` 是模型判断把握度，不是政策影响强度。", "2. 风格方向表示风格轴的相对端点；行业方向范围为 -2..+2，全A和风格为 -1/0/+1。", "3. 空值表示缺少信息或比较基准，不应替换成 0。", "");
fs.writeFileSync(path.join(root,"deliverables","政策新闻到评分_15条案例Notebook.md"), md.join("\n"));
console.log(JSON.stringify({html:path.join(outDir,"index.html"),markdown:path.join(root,"deliverables","政策新闻到评分_15条案例Notebook.md"),cases:cases.length,notebookCases:notebookKeys.length},null,2));
