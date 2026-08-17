#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the enhanced self-contained long-article factor report."""
from __future__ import annotations
import json, math, html
from collections import Counter
from datetime import datetime
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]; WORK=ROOT/'work_scoring_v1'; RUN=WORK/'output/calendar_articles_20240801_20260131'
PAN=RUN/'panels_v1'; MKT=RUN/'market_data'; OUT=ROOT/'deliverables/长文政策因子最终报告'; ANA=RUN/'analysis_v2'; END='2026-01-31'

def rec(df, cols):
    z=[]
    for row in df[cols].to_dict('records'):
        z.append({k:(None if pd.isna(v) else round(float(v),4) if isinstance(v,(float,int)) else str(v)) for k,v in row.items()})
    return z
def future(s,h): return pd.Series([(1+s.iloc[i+1:i+1+h].fillna(0)).prod()-1 if i+h<len(s) else math.nan for i in range(len(s))],index=s.index)
def zscore(s):
    sd=s.std(ddof=0); return (s-s.mean())/sd if sd else s*0
def event_rows(df, series, group=None, n=6):
    x=series.sort_values('date').copy(); x['jump']=x['value'].diff(); chosen=[]
    for _,r in x.reindex(x['jump'].abs().sort_values(ascending=False).index).iterrows():
        d=str(r.date); key=(group,d)
        if any(abs((pd.Timestamp(d)-pd.Timestamp(q['date'])).days)<4 for q in chosen): continue
        q=df[df.date.eq(d)]
        if group is not None:
            if 'style_axis' in q: q=q[q.style_axis.eq(group)]
            elif 'industry_l2_code' in q: q=q[q.industry_l2_code.astype(str).eq(str(group))]
        score='a_unit' if 'a_unit' in df.columns and df['a_unit'].notna().any() else 'state_score'
        q=q.assign(_abs=pd.to_numeric(q[score],errors='coerce').abs()).sort_values('_abs',ascending=False).head(3)
        chosen.append({'date':d,'value':round(float(r.value),3),'jump':round(float(r.jump),3),'news':[{'title':str(a.title),'measure':str(a.measure_summary),'channel':str(a.channel),'score':round(float(a[score]),3)} for _,a in q.iterrows()]})
        if len(chosen)>=n: break
    return chosen

def main():
    OUT.mkdir(parents=True,exist_ok=True); ANA.mkdir(parents=True,exist_ok=True)
    rel=pd.read_csv(RUN/'scores_relations_final.csv',dtype={'industry_l2_code':str}); rel['date']=rel.date.astype(str)
    market=pd.read_csv(MKT/'market_returns_daily.csv'); aa=pd.read_csv(PAN/'all_a_daily.csv'); aa=aa[aa.date.le(END)]
    fm=market.merge(aa,on='date',how='left'); fm['temperature_per_news']=fm.temperature/fm.attention_news.replace(0,pd.NA); fm['temperature_z']=zscore(fm.temperature); fm['temperature_per_news_z']=zscore(fm.temperature_per_news)
    corr=[]
    for f in ['temperature','temperature_per_news']:
      for m in ['csi_all_share_return','all_a_equal_weight_return']:
       for h in [1,5,20]:
        y=future(fm[m],h); v=pd.concat([fm[f],y],axis=1).dropna(); corr.append({'factor':f,'market':m,'horizon':h,'pearson':round(float(v.iloc[:,0].corr(v.iloc[:,1])),3),'n':len(v)})
    dims={'all_a':['direction','intensity','coverage','certainty','persistence','info_increment','confidence'],'style':['direction','relative_strength','coverage','certainty','persistence','info_increment','confidence'],'industry':['direction','intensity','coverage','certainty','persistence','confidence']}
    dimdata={}
    for track,cols in dims.items():
        q=rel[rel.track.eq(track)].copy(); group=['date']+(['style_axis'] if track=='style' else ['industry_l2_code','industry_l2_name'] if track=='industry' else [])
        g=q.groupby(group,dropna=False)[cols].mean().reset_index(); dimdata[track]=rec(g,group+cols)
    ch=pd.read_csv(PAN/'all_a_channel_daily.csv'); ch=ch[ch.date.le(END)]
    style=pd.read_csv(PAN/'style_axis_daily.csv'); style=style[style.date.le(END)]
    ind=pd.read_csv(PAN/'industry_daily.csv',dtype={'industry_l2_code':str}); ind=ind[ind.date.le(END)]
    tax=pd.read_csv(WORK/'data/sw2021_l2_industries.csv',dtype={'industry_l2_code':str})[['industry_l2_code','industry_l2_name']]
    irank=ind.groupby(['industry_l2_code','industry_l2_name']).net_sum.apply(lambda s:s.abs().mean()).sort_values(ascending=False)
    top=[x[0] for x in irank.head(8).index]
    all_events=event_rows(rel[rel.track.eq('all_a')],fm[['date','temperature_z']].rename(columns={'temperature_z':'value'}))
    style_events={}
    for axis,q in style.groupby('style_axis'): style_events[str(axis)]=event_rows(rel[rel.track.eq('style')],q[['date','net']].rename(columns={'net':'value'}),str(axis),3)
    ind_events={}
    for code,q in ind.groupby('industry_l2_code'): ind_events[str(code)]=event_rows(rel[rel.track.eq('industry')],q[['date','net_sum']].rename(columns={'net_sum':'value'}),str(code),3)
    payload={'market':rec(fm,['date','temperature_z','temperature_per_news_z','attention_news','csi_all_share_cumulative','all_a_equal_weight_cumulative']),
      'corr':corr,'allChannels':rec(ch,['date','channel','net']),'dims':dimdata,'style':rec(style,['date','style_axis','net']),
      'industry':rec(ind,['date','industry_l2_code','industry_l2_name','net_sum','n_news']),'industries':tax.to_dict('records'),'top':top,
      'events':{'allA':all_events,'style':style_events,'industry':ind_events}}
    data=json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    corrhtml=''.join(f"<tr><td>{'原始温度' if x['factor']=='temperature' else '每新闻归一'}</td><td>{'中证全指' if x['market'].startswith('csi') else '全A等权'}</td><td>{x['horizon']}日</td><td>{x['pearson']:+.3f}</td><td>{x['n']}</td></tr>" for x in corr)
    prompts=''.join(f"<details><summary>{t}</summary><pre>{html.escape((WORK/p).read_text())}</pre></details>" for t,p in [('Prompt 1：政策识别与最小措施拆分','prompts/measure_prompt.txt'),('Prompt 2：多标签路由','prompts/routing_prompt.txt'),('Prompt 3A：全A评分','prompts/all_a_score_prompt.txt'),('Prompt 3B：风格评分','prompts/style_score_prompt.txt'),('Prompt 3C：行业评分','prompts/industry_score_prompt.txt')])
    doc=TEMPLATE.replace('__DATA__',data).replace('__CORR__',corrhtml).replace('__PROMPTS__',prompts).replace('__TIME__',datetime.now().strftime('%Y-%m-%d %H:%M'))
    (OUT/'index.html').write_text(doc,encoding='utf-8'); print(OUT/'index.html', (OUT/'index.html').stat().st_size)

TEMPLATE=r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>长文政策因子研究报告</title>
<style>:root{--ink:#13213c;--muted:#60708b;--line:#dbe4f0;--blue:#245fe8;--cyan:#04a6a6;--gold:#d79b22;--red:#d95757;--bg:#f5f8fd}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;line-height:1.65}header{padding:50px max(22px,calc((100vw - 1200px)/2));background:linear-gradient(120deg,#112e64,#245fe8);color:#fff}header h1{font-size:clamp(30px,4vw,50px);margin:0 0 10px}nav{position:sticky;top:0;z-index:3;display:flex;gap:18px;overflow:auto;padding:10px max(18px,calc((100vw - 1200px)/2));background:#fffffff2;border-bottom:1px solid var(--line)}nav a{white-space:nowrap;text-decoration:none;color:var(--ink);font-weight:700}main{max-width:1200px;margin:auto;padding:24px 18px 70px}.block{background:#fff;border:1px solid var(--line);border-radius:16px;padding:24px;margin:20px 0}h2{font-size:28px;margin:0 0 14px}h3{margin:24px 0 8px}.note{border-left:4px solid var(--gold);background:#fff8e8;padding:10px 13px}.defs{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.def{border:1px solid var(--line);padding:13px;border-radius:10px}.def b{display:block;color:var(--blue)}details{border:1px solid var(--line);border-radius:9px;margin:7px 0}summary{padding:10px 12px;cursor:pointer;font-weight:700}pre{white-space:pre-wrap;max-height:420px;overflow:auto;padding:0 12px 12px;font-size:12px}.chart{border:1px solid var(--line);border-radius:10px;padding:10px;margin:12px 0;position:relative}canvas{width:100%;height:340px;display:block}.controls{display:flex;gap:12px;flex-wrap:wrap;align-items:center}.controls label{font-weight:650}select,input{padding:7px;border:1px solid var(--line);border-radius:7px;background:#fff}.legend{display:flex;flex-wrap:wrap;gap:12px;font-size:12px}.legend i{display:inline-block;width:12px;height:3px;margin-right:5px;background:var(--c)}.checks{display:flex;flex-wrap:wrap;gap:7px 14px;padding:10px 12px;border:1px solid var(--line);border-radius:9px;background:#f9fbff;max-height:210px;overflow:auto}.checks label{font-size:13px;white-space:nowrap}.checks input{padding:0;vertical-align:middle;margin-right:5px}.help{max-width:720px;color:var(--muted);font-size:13px}.tip{display:none;position:absolute;pointer-events:none;background:#13213cec;color:#fff;padding:7px;border-radius:6px;font-size:12px;white-space:pre-line}.events{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.event{border:1px solid var(--line);border-radius:9px;padding:11px}.event b{color:var(--blue)}table{border-collapse:collapse;width:100%;font-size:13px}td,th{padding:7px;border-bottom:1px solid var(--line);text-align:left}.scroll{overflow:auto}.axis-list{columns:2}.muted{color:var(--muted)}@media(max-width:760px){.defs,.events{grid-template-columns:1fr}.axis-list{columns:1}.block{padding:16px}canvas{height:300px}}</style></head><body>
<header><h1>长文政策新闻因子研究报告</h1><p>市场基准与政策因子分开呈现；每个最终值都能下钻到渠道、评分维度和异常日期新闻。</p></header><nav><a href="#definition">口径</a><a href="#all-a">全A</a><a href="#style">风格</a><a href="#industry">行业</a><a href="#prompts">Prompt</a></nav><main>
<section class="block" id="definition"><h2>1. 三条线分别是什么</h2><div class="defs"><div class="def"><b>中证全指（外部市场基准）</b>官方宽基指数000985.CSI。日收益=当日收盘/前收盘−1；累计收益=∏(1+日收益)−1。</div><div class="def"><b>全A等权（外部市场基准）</b>每天对全部有效A股个股涨跌幅做简单平均，再逐日复利。它是本项目构造的市场收益序列，不是官方指数，也不是政策因子。</div><div class="def"><b>全A政策因子（本项目因子）</b>模型关系分经期限衰减后，在8个全A渠道内先聚合，再按1/8等权合成政策温度；画图用样本内Z值。</div></div>
<p class="note"><b>“因子口径不同”</b>指同一批关系分的聚合分母不同：原始温度保留政策密集度，政策多的日期绝对值可能更大；“每关注新闻归一”再除以当日活跃新闻数，更接近单篇平均影响。前者是当前基线，后者只做敏感性对照。</p><p><b>时间范围：</b>当前长文日历样本确实只覆盖 <b>2024-08-01—2026-01-31</b>。此前不是0，而是没有纳入本轮样本，因此图中不向前补值。</p></section>
<section class="block" id="all-a"><h2>2. 全A政策因子与市场收益</h2><div class="controls"><label>因子口径 <select id="factor"><option value="temperature_z">原始政策温度Z值</option><option value="temperature_per_news_z">每关注新闻归一Z值</option></select></label><span class="help" id="factorHelp"></span></div><p class="note"><b>为什么政策因子不从0开始？</b>蓝线是政策温度的Z值，不是收益率或净值。Z=0表示“处于样本平均水平”，样本第一天可以高于或低于平均，因此不需要从0起步。两条市场累计收益会以图中首个交易日重新归零，表示从该日起累计涨跌。</p><div class="chart"><div class="legend"><span><i style="--c:#245fe8"></i>政策因子Z值（左轴）</span><span><i style="--c:#04a6a6"></i>中证全指累计收益（右轴，首日=0）</span><span><i style="--c:#d79b22"></i>全A等权累计收益（右轴，首日=0）</span></div><canvas id="market"></canvas><div class="tip"></div></div>
<h3>8个渠道中间变量</h3><p class="muted">勾选任意渠道进行组合比较。每条线是该渠道衰减后净信号；最终政策温度是8条渠道线的等权平均。</p><div class="checks" id="acChecks"></div><div class="chart"><canvas id="ac"></canvas><div class="tip"></div></div>
<h3>绝对跳变最大的日期与新闻</h3><div class="events" id="aae"></div><h3>领先未来收益的探索性Pearson相关</h3><p>Pearson相关系数衡量两个变量的线性同向程度，范围−1到+1：正值表示因子高时未来收益倾向更高，负值相反，越接近0表示线性关系越弱。这里比较的是日期t的政策因子与t之后1/5/20个交易日的复合收益，只是探索，不代表因果。</p><div class="scroll"><table><thead><tr><th>因子</th><th>市场收益</th><th>未来窗口</th><th>相关</th><th>样本</th></tr></thead><tbody>__CORR__</tbody></table></div></section>
<section class="block" id="style"><h2>3. 风格因子</h2><div class="axis-list"><p><b>size：</b>正=小盘，负=大盘</p><p><b>growth_value：</b>正=成长，负=价值</p><p><b>quality：</b>正=高质量，负=低质量/困境</p><p><b>risk：</b>正=高弹性/高Beta，负=低波/防御</p><p><b>dividend：</b>正=高股息，负=低股息</p><p><b>liquidity：</b>正=高流动性，负=低流动性</p></div><p class="note">风格轴净值来自关系分按期限衰减后的加总。样本起点不强制设为0：当天有有效政策就有信号；无有效关系时才可能为0。</p><p class="muted">勾选任意风格轴进行组合比较。</p><div class="checks" id="styleChecks"></div><div class="chart"><canvas id="styleChart"></canvas><div class="tip"></div></div><h3>所选风格轴的大跳变新闻</h3><div class="events" id="se"></div></section>
<section class="block" id="industry"><h2>4. 行业因子：多行业对比</h2><p>下面列出项目字典中的全部131个申万2021二级行业，可任意勾选多条行业政策因子。默认勾选样本期平均绝对政策信号最大的3个行业。</p><div class="checks" id="indChecks"></div><div class="controls"><label>市场基准 <select id="bench"><option value="csi_all_share_cumulative">中证全指</option><option value="all_a_equal_weight_cumulative">全A等权</option><option disabled>申万行业指数（待接入）</option><option disabled>沪深300（待接入）</option></select></label><label>起点 <input type="range" id="from" min="0" value="0"></label><label>终点 <input type="range" id="to" min="1" value="1"></label><span id="rangeLabel"></span></div><div class="chart"><canvas id="indChart"></canvas><div class="tip"></div></div><h3>所选行业的大跳变新闻</h3><div class="events" id="ie"></div><p class="note">市场基准和行业政策因子使用双轴。申万行业指数不等于行业成分股简单等权；若后续构造行业等权收益，必须使用历史时点成分股，避免前视偏差。</p></section>
<section class="block" id="prompts"><h2>5. 实际生产Prompt</h2><p>新闻识别、拆分、路由和维度评分由Qwen模型在以下Prompt约束下判断；最终关系分、衰减和日频聚合由Python固定公式完成。</p>__PROMPTS__</section><p class="muted">生成：__TIME__ · 单文件HTML可直接发送，不依赖本机数据库。</p></main>
<script id="data" type="application/json">__DATA__</script><script>
const D=JSON.parse(document.getElementById('data').textContent),COL=['#245fe8','#04a6a6','#d79b22','#d95757','#7658bd','#31915b','#c76d22','#536780'];
function prep(id){let c=document.getElementById(id),d=devicePixelRatio||1,w=c.clientWidth,h=c.clientHeight;c.width=w*d;c.height=h*d;let x=c.getContext('2d');x.scale(d,d);return{c,x,w,h,tip:c.parentElement.querySelector('.tip')}}function ext(a){a=a.filter(Number.isFinite);if(!a.length)return[-1,1];let l=Math.min(...a),u=Math.max(...a);if(l==u){l-=1;u+=1}let p=(u-l)*.08;return[l-p,u+p]}
function chart(id,rows,ss,dual=false){let q=prep(id),{x,w,h}=q,m={l:58,r:dual?58:18,t:14,b:35},pw=w-m.l-m.r,ph=h-m.t-m.b,val=(d,k)=>d[k]===null||d[k]===undefined?NaN:+d[k],L=ext(ss.filter(s=>!s.r).flatMap(s=>rows.map(d=>val(d,s.k)))),R=dual?ext(ss.filter(s=>s.r).flatMap(s=>rows.map(d=>val(d,s.k)))):L;x.clearRect(0,0,w,h);x.font='11px sans-serif';for(let i=0;i<5;i++){let y=m.t+ph*i/4;x.strokeStyle='#e1e7f0';x.beginPath();x.moveTo(m.l,y);x.lineTo(w-m.r,y);x.stroke();x.fillStyle='#60708b';x.fillText((L[1]-(L[1]-L[0])*i/4).toFixed(2),4,y+4);if(dual)x.fillText((R[1]-(R[1]-R[0])*i/4).toFixed(2),w-48,y+4)}ss.forEach((s,j)=>{let E=s.r?R:L;x.strokeStyle=s.c||COL[j%COL.length];x.lineWidth=1.6;x.beginPath();let on=false;rows.forEach((d,i)=>{let v=val(d,s.k);if(!Number.isFinite(v)){on=false;return}let xx=m.l+pw*i/Math.max(1,rows.length-1),yy=m.t+ph*(E[1]-v)/(E[1]-E[0]);on?x.lineTo(xx,yy):x.moveTo(xx,yy);on=true});x.stroke()});for(let i=0;i<5;i++){let j=Math.round((rows.length-1)*i/4);x.fillStyle='#60708b';x.fillText((rows[j]?.date||'').slice(0,7),m.l+pw*i/4-20,h-9)}q.c.onmousemove=e=>{let b=q.c.getBoundingClientRect(),i=Math.max(0,Math.min(rows.length-1,Math.round((e.clientX-b.left-m.l)/pw*(rows.length-1)))),d=rows[i];q.tip.style.display='block';q.tip.style.left=Math.min(w-220,e.clientX-b.left+10)+'px';q.tip.style.top=Math.max(5,e.clientY-b.top-55)+'px';q.tip.textContent=(d?.date||'')+'\n'+ss.map(s=>{let v=val(d,s.k);return s.n+': '+(Number.isFinite(v)?v.toFixed(3):'—')}).join('\n')};q.c.onmouseleave=()=>q.tip.style.display='none'}
function wide(rows,g,v){let dates=[...new Set(rows.map(x=>x.date))].sort(),gs=[...new Set(rows.map(x=>x[g]))],mp=gs.map(a=>new Map(rows.filter(x=>x[g]==a).map(x=>[x.date,x[v]])));return{rows:dates.map(date=>{let o={date};gs.forEach((a,i)=>o['s'+i]=mp[i].get(date));return o}),ss:gs.map((a,i)=>({k:'s'+i,n:a,c:COL[i%COL.length]}))}}
function legend(id,ss){document.getElementById(id).innerHTML=ss.map(s=>`<span><i style="--c:${s.c}"></i>${s.n}</span>`).join('')}
function events(id,a){document.getElementById(id).innerHTML=(a||[]).map(e=>`<div class="event"><b>${e.date} · Z/信号 ${e.value>=0?'+':''}${e.value} · 日变动 ${e.jump>=0?'+':''}${e.jump}</b>${e.news.length?e.news.map(n=>`<p>${n.title}<br><span class="muted">${n.measure}；${n.channel}；关系分 ${n.score}</span></p>`).join(''):'<p class="muted">当天没有新增对应关系；跳变主要来自既有信号衰减或到期。</p>'}</div>`).join('')}
let dims={direction:'方向',intensity:'强度',relative_strength:'相对强度',coverage:'覆盖',certainty:'确定性',persistence:'持续性',info_increment:'信息增量',confidence:'把握度'};
function dim(id,lid,rows){let keys=Object.keys(dims).filter(k=>rows.some(r=>r[k]!==null&&r[k]!==undefined&&Number.isFinite(+r[k]))),ss=keys.map((k,i)=>({k,n:dims[k],c:COL[i%COL.length]}));legend(lid,ss);chart(id,rows,ss)}
function checks(id,items,defaults,draw){let box=document.getElementById(id);box.innerHTML=items.map((x,i)=>`<label><input type="checkbox" value="${x.value}" ${defaults.includes(x.value)?'checked':''}><i style="display:inline-block;width:11px;height:3px;background:${COL[i%COL.length]};margin-right:4px"></i>${x.label}</label>`).join('');box.querySelectorAll('input').forEach(x=>x.onchange=draw)}
function picked(id){return[...document.querySelectorAll(`#${id} input:checked`)].map(x=>x.value)}
function rebase(rows,key,out){let first=rows.find(x=>x[key]!==null&&x[key]!==undefined)?.[key];rows.forEach(x=>x[out]=first===null||first===undefined||x[key]===null?null:(1+x[key])/(1+first)-1)}
let fw=wide(D.allChannels,'channel','net');
function drawAll(){factorHelp.textContent=factor.value==='temperature_z'?'保留政策总量效应：政策越密集，绝对温度通常越大。适合观察政策总压力/支持度，是当前基线。':'先除以当日活跃新闻数：更接近“平均每篇新闻”的影响。适合检查结果是否只是被新闻数量推动。';let rows=D.market.map(x=>({...x}));rebase(rows,'csi_all_share_cumulative','csi0');rebase(rows,'all_a_equal_weight_cumulative','ewa0');chart('market',rows,[{k:factor.value,n:'政策因子Z',c:COL[0]},{k:'csi0',n:'中证全指',c:COL[1],r:1},{k:'ewa0',n:'全A等权',c:COL[2],r:1}],true)}
function drawChannels(){let sel=new Set(picked('acChecks')),ss=fw.ss.filter(x=>sel.has(x.n));chart('ac',fw.rows,ss)}
checks('acChecks',fw.ss.map(x=>({value:x.n,label:x.n})),fw.ss.map(x=>x.n),drawChannels);factor.onchange=drawAll;drawAll();drawChannels();events('aae',D.events.allA);
let axes=[...new Set(D.style.map(x=>x.style_axis))],sw=wide(D.style,'style_axis','net');
function drawStyle(){let sel=new Set(picked('styleChecks')),ss=sw.ss.filter(x=>sel.has(x.n));chart('styleChart',sw.rows,ss);events('se',[...sel].flatMap(a=>(D.events.style[a]||[]).map(e=>({...e,axis:a}))).slice(0,12))}
checks('styleChecks',axes.map(x=>({value:x,label:x})),axes,drawStyle);drawStyle();
from.max=to.max=D.market.length-1;to.value=D.market.length-1;
function drawInd(){let codes=picked('indChecks'),a=+from.value,b=+to.value;if(a>=b){b=Math.min(D.market.length-1,a+1);to.value=b}let dates=D.market.slice(a,b+1).map(x=>({...x})),set=new Set(dates.map(x=>x.date));rebase(dates,bench.value,'benchmark0');let ss=[],maps=codes.map(code=>new Map(D.industry.filter(x=>x.industry_l2_code==code&&set.has(x.date)).map(x=>[x.date,x.net_sum])));codes.forEach((code,j)=>{let key='i'+j;dates.forEach(x=>x[key]=maps[j].get(x.date));let meta=D.industries.find(x=>x.industry_l2_code==code);ss.push({k:key,n:meta?.industry_l2_name||code,c:COL[j%COL.length]})});ss.push({k:'benchmark0',n:bench.options[bench.selectedIndex].text+'累计收益',c:'#111827',r:1});rangeLabel.textContent=(dates[0]?.date||'')+' — '+(dates.at(-1)?.date||'');chart('indChart',dates,ss,true);events('ie',codes.flatMap(code=>(D.events.industry[code]||[])).slice(0,12))}
checks('indChecks',D.industries.map(x=>({value:x.industry_l2_code,label:`${x.industry_l2_name} (${x.industry_l2_code})`})),D.top.slice(0,3),drawInd);[bench,from,to].forEach(x=>x.oninput=drawInd);drawInd();
new ResizeObserver(()=>{drawAll();drawChannels();drawStyle();drawInd()}).observe(document.querySelector('main'));
</script></body></html>'''
if __name__=='__main__': main()
