import fs from "node:fs/promises";
import path from "node:path";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const root = "/Volumes/Elements SE/policy_news_database";
const deliveryDir = path.join(root, "deliverables");
const payload = JSON.parse(await fs.readFile(path.join(deliveryDir, "policy_pipeline_delivery.json"), "utf8"));
const wb = Workbook.create();

const colors = {
  navy: "#17365D", blue: "#DCE6F1", light: "#F3F6FA", green: "#E2F0D9",
  amber: "#FFF2CC", red: "#FCE4D6", gray: "#E7E6E6", white: "#FFFFFF", text: "#1F2937"
};

function colName(n) {
  let s = "";
  while (n > 0) { n--; s = String.fromCharCode(65 + (n % 26)) + s; n = Math.floor(n / 26); }
  return s;
}

function writeBlock(sheet, headers, rows, tableName, widths = {}) {
  const cols = headers.length;
  const endCol = colName(cols);
  sheet.getRange(`A1:${endCol}1`).values = [headers];
  if (rows.length) sheet.getRange(`A2:${endCol}${rows.length + 1}`).values = rows;
  const used = sheet.getRange(`A1:${endCol}${rows.length + 1}`);
  used.format.font = { name: "Aptos", size: 10, color: colors.text };
  used.format.verticalAlignment = "top";
  sheet.getRange(`A1:${endCol}1`).format = {
    fill: colors.navy, font: { name: "Aptos", size: 10, bold: true, color: colors.white },
    verticalAlignment: "center", wrapText: true,
    borders: { bottom: { style: "medium", color: colors.navy } }
  };
  sheet.getRange(`A1:${endCol}1`).format.rowHeight = 32;
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(Math.min(3, cols));
  sheet.showGridLines = false;
  if (rows.length) {
    const table = sheet.tables.add(`A1:${endCol}${rows.length + 1}`, true, tableName);
    table.style = "TableStyleMedium2";
    table.showFilterButton = true;
  }
  for (const [idx, width] of Object.entries(widths)) sheet.getRange(`${colName(Number(idx))}:${colName(Number(idx))}`).format.columnWidth = width;
  return { endCol, endRow: rows.length + 1 };
}

const guide = wb.worksheets.add("导读与质量概览");
guide.showGridLines = false;
guide.getRange("A1:H1").merge();
guide.getRange("A1").values = [["政策新闻信息提取：5,000条样本全链路审阅工作簿"]];
guide.getRange("A1:H1").format = { fill: colors.navy, font: { name: "Aptos Display", size: 18, bold: true, color: colors.white }, verticalAlignment: "center" };
guide.getRange("A1:H1").format.rowHeight = 38;
guide.getRange("A3:B8").values = [
  ["输入新闻", null], ["已产生拆分输出的新闻", null], ["措施路由记录", null],
  ["评分关系", null], ["错误日志行数", null], ["受错误影响的唯一新闻", null]
];
guide.getRange("B3:B8").formulas = [
  ["=COUNTA('新闻总览'!$A$2:$A$5001)"], ["=COUNTIF('新闻总览'!$I$2:$I$5001,\"是\")+COUNTIF('新闻总览'!$I$2:$I$5001,\"否\")"],
  ["=COUNTA('措施与路由'!$A$2:$A$5528)"], ["=COUNTA('评分关系明细'!$A$2:$A$18112)"],
  ["=COUNTA('错误日志'!$A$2:$A$3764)"], [null]
];
guide.getRange("B8").values = [[payload.summary.unique_error_news]];
guide.getRange("A3:B8").format = { fill: colors.light, borders: { preset: "outside", style: "thin", color: "#A6A6A6" } };
guide.getRange("A3:A8").format.font = { bold: true, color: colors.navy };
guide.getRange("B3:B8").format.numberFormat = "#,##0";
guide.getRange("D3:E7").values = [["评分路线", "关系数"], ["行业", null], ["全A", null], ["风格", null], ["合计", null]];
guide.getRange("E4:E6").formulas = [["=COUNTIF('评分关系明细'!$A$2:$A$18112,\"industry\")"], ["=COUNTIF('评分关系明细'!$A$2:$A$18112,\"all_a\")"], ["=COUNTIF('评分关系明细'!$A$2:$A$18112,\"style\")"]];
guide.getRange("E7").formulas = [["=SUM(E4:E6)"]];
guide.getRange("D3:E7").format.borders = { preset: "outside", style: "thin", color: "#A6A6A6" };
guide.getRange("D3:E3").format = { fill: colors.navy, font: { bold: true, color: colors.white } };
guide.getRange("E4:E7").format.numberFormat = "#,##0";
guide.getRange("A10:H10").merge(); guide.getRange("A10").values = [["处理链路"]];
guide.getRange("A10:H10").format = { fill: colors.blue, font: { bold: true, color: colors.navy } };
guide.getRange("A11:H14").values = [
  ["1. 原始新闻", "sample_5000.csv", "→", "2. 措施拆分", "measure.v1", "→", "3. 三路路由", "routing.v2"],
  ["新闻元数据与全文", "5,000条", "", "最小独立政策措施", "工具/对象/时间/机制", "", "全A、风格、行业可重叠", "允许 none"],
  ["4. 路线评分", "关系级输出", "→", "5. 聚合与质检", "状态分/日频面板", "→", "6. 本工作簿", "审阅与追溯"],
  ["全A/风格/行业", "18,111条关系", "", "空值与错误保留", "不臆造比较基准", "", "新闻→措施→分类→评分", "完整可筛选"]
];
guide.getRange("A11:H14").format = { wrapText: true, verticalAlignment: "center", borders: { preset: "inside", style: "thin", color: "#D9E2F3" } };
guide.getRange("A16:H16").merge(); guide.getRange("A16").values = [["如何使用"]];
guide.getRange("A16:H16").format = { fill: colors.blue, font: { bold: true, color: colors.navy } };
guide.getRange("A17:H21").merge(true);
guide.getRange("A17:A21").values = [["新闻总览：查看5,000条输入及每条处理状态。"], ["措施与路由：查看每条最小措施如何分类，以及分类理由。"], ["评分关系明细：查看每条措施在相应路线上的逐维得分。"], ["典型案例：查看全A、风格、行业及多路线代表案例；提示词全文用于复核模型约束。"], ["错误日志：同一新闻可能因重试出现多行；质量判断请同时看日志行数与唯一新闻数。"]];
guide.getRange("A17:H21").format = { wrapText: true, fill: colors.light };
guide.getRange("A23:H25").merge(true);
guide.getRange("A23:A25").values = [["重要限制：现有结果只覆盖当前跑批成功部分。policy_delta、novelty及surprise类字段因缺少历史比较基准而为空，不能解释为0。"], ["质量提示：行业关系占比明显较高、风格样本较少；路由精度和行业标签宽度仍需人工金标准检验。"], ["本工作簿不重新调用模型，忠实呈现现有输出并保留失败与缺失。"]];
guide.getRange("A23:H25").format = { wrapText: true, fill: colors.amber, font: { color: "#7F6000" } };
guide.getRange("A:H").format.columnWidth = 18;
guide.getRange("A:A").format.columnWidth = 24;
guide.getRange("B:B").format.columnWidth = 18;
guide.freezePanes.freezeRows(1);

const overview = wb.worksheets.add("新闻总览");
writeBlock(overview, payload.overview_headers, payload.overview_rows, "NewsOverview", {1:12,2:18,3:12,4:38,5:15,6:35,7:12,8:10,9:12,10:10,11:12,12:12,13:14,14:22,15:12,16:40,17:40,18:70});
overview.getRange(`C2:C${payload.overview_rows.length+1}`).format.numberFormat = "yyyy-mm-dd";
overview.getRange(`D2:D${payload.overview_rows.length+1}`).format.wrapText = true;
overview.getRange(`N2:N${payload.overview_rows.length+1}`).conditionalFormats.add("containsText", {text:"失败", format:{fill:colors.red,font:{color:"#9C0006"}}});
overview.getRange(`N2:N${payload.overview_rows.length+1}`).conditionalFormats.add("containsText", {text:"已完成", format:{fill:colors.green,font:{color:"#006100"}}});

const measures = wb.worksheets.add("措施与路由");
writeBlock(measures, payload.measure_headers, payload.measure_rows, "MeasureRouting", {1:12,2:12,3:38,4:10,5:48,6:16,7:25,8:42,9:48,10:9,11:9,12:9,13:12,14:20,15:48,16:12,17:50,18:12,19:14});
measures.getRange(`E2:S${payload.measure_rows.length+1}`).format.wrapText = true;
measures.getRange(`P2:P${payload.measure_rows.length+1}`).format.numberFormat = "0.00";

const scores = wb.worksheets.add("评分关系明细");
writeBlock(scores, payload.relation_headers, payload.relation_rows, "ScoreRelations", {1:11,2:12,3:12,4:38,5:15,6:32,7:10,8:46,9:10,10:22,11:15,12:16,13:14,14:18,15:16,16:10,17:9,18:9,19:11,20:9,21:9,22:9,23:10,24:11,25:10,26:10,27:11,28:10,29:10,30:10,31:18,32:46,33:55,34:13,35:12});
scores.getRange(`Q2:AI${payload.relation_rows.length+1}`).format.numberFormat = "0.000";
scores.getRange(`H2:H${payload.relation_rows.length+1}`).format.wrapText = true;

const examples = wb.worksheets.add("典型案例");
writeBlock(examples, payload.example_headers, payload.example_rows, "TypicalCases", {1:14,2:12,3:12,4:40,5:10,6:50,7:18,8:12,9:12,10:60,11:10,12:65,13:35});
examples.getRange(`D2:M${payload.example_rows.length+1}`).format.wrapText = true;
examples.getRange(`I2:I${payload.example_rows.length+1}`).format.numberFormat = "0.00";

const prompts = wb.worksheets.add("提示词全文");
writeBlock(prompts, payload.prompt_headers, payload.prompt_rows, "PromptTexts", {1:15,2:28,3:120});
prompts.getRange(`C2:C${payload.prompt_rows.length+1}`).format.wrapText = true;
prompts.getRange(`A2:C${payload.prompt_rows.length+1}`).format.rowHeight = 180;

const errs = wb.worksheets.add("错误日志");
writeBlock(errs, payload.error_headers, payload.error_rows, "ErrorLog", {1:10,2:12,3:12,4:42,5:100});
errs.getRange(`D2:E${payload.error_rows.length+1}`).format.wrapText = true;
errs.getRange(`E2:E${payload.error_rows.length+1}`).conditionalFormats.add("containsText", {text:"RuntimeError", format:{fill:colors.red}});

await fs.mkdir(deliveryDir, {recursive:true});
const checks = [];
checks.push((await wb.inspect({kind:"table", range:"导读与质量概览!A1:H25", include:"values,formulas", tableMaxRows:25, tableMaxCols:8, maxChars:8000})).ndjson);
checks.push((await wb.inspect({kind:"match", searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options:{useRegex:true,maxResults:300}, summary:"final formula error scan"})).ndjson);
await fs.writeFile(path.join(deliveryDir,"workbook_checks.ndjson"), checks.join("\n"));
for (const [name, range] of [["导读与质量概览","A1:H25"],["新闻总览","A1:R18"],["措施与路由","A1:S16"],["评分关系明细","A1:AI14"],["典型案例","A1:M14"],["提示词全文","A1:C6"],["错误日志","A1:E16"]]) {
  const img = await wb.render({sheetName:name, range, scale:1.2, format:"png"});
  await fs.writeFile(path.join(deliveryDir, `preview_${name}.png`), new Uint8Array(await img.arrayBuffer()));
}
const output = await SpreadsheetFile.exportXlsx(wb);
await output.save(path.join(deliveryDir, "政策新闻全链路审阅表.xlsx"));
console.log(JSON.stringify({sheets:7, output:path.join(deliveryDir,"政策新闻全链路审阅表.xlsx")}, null, 2));
