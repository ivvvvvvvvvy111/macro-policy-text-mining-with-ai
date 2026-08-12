from __future__ import annotations

from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "policy_router_experiment.ipynb"


def md(text: str):
    return nbf.v4.new_markdown_cell(text)


def code(text: str):
    return nbf.v4.new_code_cell(text)


def main() -> None:
    nb = nbf.v4.new_notebook()
    nb["metadata"]["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nb["metadata"]["language_info"] = {"name": "python", "version": "3.11"}
    nb["cells"] = [
        md("""# Policy Text Router v0.1：50条政策新闻实验

这个 Notebook 按“数据 → measure 拆分 → routing → 质量检查 → 典型案例 → 人工标注入口”的顺序展示已经跑完的结果。所有结果都已预先执行；只看输出也能理解实验过程。API Key 不在 Notebook 中。"""),
        md("""## 步骤1：读取实验文件

先载入50条最终样本、105条 measure 路由结果、运行统计和质量检查结果。"""),
        code("""from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display

ROOT = Path.cwd()
if not (ROOT / 'data' / 'news_sample.csv').exists():
    raise RuntimeError('请把Notebook工作目录设为 policy_text_router_v0 项目根目录')

news = pd.read_csv(ROOT / 'data' / 'news_sample.csv')
routes = pd.read_csv(ROOT / 'output' / 'routing_results.csv')
review = pd.read_csv(ROOT / 'output' / 'results_for_review.csv')
qa = json.loads((ROOT / 'output' / 'qa_summary.json').read_text(encoding='utf-8'))
run = json.loads((ROOT / 'output' / 'run_summary.json').read_text(encoding='utf-8'))

print(f"新闻数：{len(news)}；measure数：{len(routes)}；运行错误：{qa['api_or_pipeline_errors']}")"""),
        md("""## 步骤2：看样本覆盖

样本全部来自华尔街见闻公开7×24快讯。不是直接取最新50条，而是从历史快讯池中先做政策主体与政策动作筛选，再经过模型有效性筛选、主题均衡、标题去重和人工规则精修。"""),
        code("""summary = pd.DataFrame({
    '项目': ['时间起点', '时间终点', '来源', '正文平均长度', '主题数'],
    '结果': [news['date'].min(), news['date'].max(), ', '.join(news['source'].unique()),
           round(news['content'].str.len().mean(), 1), news['candidate_theme'].nunique()]
})
display(summary)
display(news['candidate_theme'].value_counts().rename_axis('主题').to_frame('新闻数'))
display(news[['news_id','date','candidate_theme','title','url']].head(10))"""),
        md("""## 步骤3：measure 拆分结果

measure 是最小政策动作单元。同一政策工具、对象和执行期下的多个数字目标合并，不再逐项拆成大量相似 measure；每条 evidence 必须逐字命中标题或正文。"""),
        code("""measure_dist = routes.groupby('news_id').size().value_counts().sort_index().rename_axis('每条新闻的measure数').to_frame('新闻数')
display(measure_dist)
print('evidence逐字命中率：', f"{qa['evidence_exact_match_rate']:.0%}")
display(review[['sample_order','title','measure_id','measure_summary','evidence']].head(12))"""),
        md("""## 步骤4：routing 分类结果

三个标签可同时为真：`all_a` 表示全市场共同环境，`style` 表示股票特征组合间的系统性差异，`industry` 表示具体行业供需、成本、产能、融资或监管约束。"""),
        code("""label_counts = pd.Series(qa['label_positive_counts']).rename({'all_a':'全A','style':'风格','industry':'行业'})
combo_counts = pd.Series(qa['route_combinations']).sort_values(ascending=False)
display(label_counts.to_frame('正标签measure数'))
display(combo_counts.to_frame('measure数'))

ax = label_counts.plot(kind='bar', color=['#4C78A8','#F58518','#54A24B'], figsize=(7,3.5), rot=0)
ax.set_title('Routing标签分布（标签可重叠）')
ax.set_ylabel('measure数')
for p in ax.patches:
    ax.annotate(str(int(p.get_height())), (p.get_x()+p.get_width()/2, p.get_height()), ha='center', va='bottom')
plt.tight_layout(); plt.show()"""),
        md("""## 步骤5：自动质量检查

这些检查不判断“经济含义是否一定正确”，但能保证数据与程序没有静默损坏：50条是否全部返回、schema逻辑是否一致、行业标签是否越界、evidence是否来自原文、是否仍存在高度重复的measure。"""),
        code("""checks = pd.DataFrame([
    ['输入新闻=输出新闻', qa['news_input'], qa['news_output'], qa['news_input']==qa['news_output']==50],
    ['API/流程错误', 0, qa['api_or_pipeline_errors'], qa['api_or_pipeline_errors']==0],
    ['Evidence逐字命中', qa['measure_count'], qa['evidence_exact_match'], qa['evidence_exact_match']==qa['measure_count']],
    ['Schema不变量错误', 0, qa['schema_invariant_errors'], qa['schema_invariant_errors']==0],
    ['非法行业标签', 0, len(qa['invalid_industry_labels']), len(qa['invalid_industry_labels'])==0],
    ['高度相似measure对', 0, qa['near_duplicate_measure_pairs'], qa['near_duplicate_measure_pairs']==0],
], columns=['检查项','目标','实际','通过'])
display(checks)
assert checks['通过'].all()
print('全部自动检查通过。')"""),
        md("""## 步骤6：查看典型分类

下面每种主路由各取若干案例。`none` 不是失败，而是政策真实存在、但不应进入当前三个A股研究模块。"""),
        code("""examples = (review.sort_values(['primary_route','confidence'], ascending=[True,False])
            .groupby('primary_route', group_keys=False).head(3))
display(examples[['primary_route','title','measure_summary','style_dimensions','industries','confidence','rationale']])"""),
        md("""## 步骤7：首轮与最终版对比

这个对比用于说明工程迭代，不是严格控制变量实验：期间既修改了prompt，也替换了10条不够典型或重复的样本。"""),
        code("""def load_jsonl(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]

base_m = load_jsonl(ROOT / 'output_baseline_v1' / 'measures.jsonl')
base_r = load_jsonl(ROOT / 'output_baseline_v1' / 'routing_results.jsonl')
base_measure_count = len(base_r)
base_exact = sum(m['evidence'] in x['news']['content'] for x in base_m for m in x['result']['measures'])
comparison = pd.DataFrame([
    ['measure数', base_measure_count, qa['measure_count']],
    ['Evidence逐字命中率', f"{base_exact/base_measure_count:.1%}", f"{qa['evidence_exact_match_rate']:.1%}"],
    ['风格正标签', sum(x['routing']['style'] for x in base_r), qa['label_positive_counts']['style']],
    ['高度相似measure对', 12, qa['near_duplicate_measure_pairs']],
    ['流程错误', 0, qa['api_or_pipeline_errors']],
], columns=['指标','首轮','最终版'])
display(comparison)"""),
        md("""## 步骤8：人工标注入口

人工标注暂不代填。模板已经按一行一条 measure 展开，保留原文、模型标签和空白人工字段；下一步可以直接在 CSV 中逐条核对。"""),
        code("""annotation = pd.read_csv(ROOT / 'data' / 'human_annotation_template.csv')
human_cols = [c for c in annotation.columns if c.startswith('human_')]
print('待人工标注行数：', len(annotation))
print('人工字段：', human_cols)
display(annotation[['sample_order','title','measure_summary','all_a','style','industry'] + human_cols].head())"""),
        md("""## 步骤9：当前结论

- 50条新闻全部被识别为政策新闻，共拆出105条独立 measure。
- 最终输出包含9条全A、5条风格、82条行业正标签；其中有2条多标签 measure，12条为 `none`。
- 自动工程检查全部通过：零错误、evidence 100%逐字命中、行业词表无越界、schema逻辑无冲突、无高度重复 measure。
- 当前结果可以作为人工标注前的 baseline，但不能直接当作“模型准确率”。最需要人工核对的是跨境政策是否真的传导到A股、风格标签是否过度解释、以及行业标签是否过宽。"""),
    ]
    nbf.write(nb, NOTEBOOK)
    client = NotebookClient(nb, timeout=180, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}})
    client.execute()
    nbf.write(nb, NOTEBOOK)
    print(f"written and executed: {NOTEBOOK}")


if __name__ == "__main__":
    main()
