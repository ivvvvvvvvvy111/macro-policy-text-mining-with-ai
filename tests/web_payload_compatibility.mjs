import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const html=fs.readFileSync(new URL('../index.html',import.meta.url),'utf8');
const shell=JSON.parse(html.match(/<script[^>]*id="frozenData"[^>]*>(.*?)<\/script>/s)[1]);
const legacyFunctions=html.slice(html.indexOf('function liveDates('),html.indexOf('function showDbLogin('));
const hydrate=html.slice(html.indexOf('const DEFAULT_COMPONENT_KEYS='),html.indexOf('async function loadLiveFrozen('));
const components={
 macro_v5_component_research:{...shell.research,dates:['2021-01-01'],channels:['market_backstop'],signed_intensity:{market_backstop:[2]},intensity:{market_backstop:[2]},relation_count:{market_backstop:[1]},index_returns:{verified:{rows:[{date:'2021-01-01',value:0}]}}},
 macro_v5_component_industry_core:{...shell.industry,industries:['801111'],dates:['2021-01-01']},
 macro_v5_component_style:{...shell.style,axes:['size'],axis_labels:{size:['小','大']}}
};
const ctx=vm.createContext({F:structuredClone(shell),window:{},console:{warn(){}},fetchArtifactPayload:async key=>{if(!(key in components))throw Error('missing optional component');return structuredClone(components[key]);}});
vm.runInContext(legacyFunctions+'\n'+hydrate,ctx);
const rich=await vm.runInContext('hydrateSplitPayload({charts:{}})',ctx);
assert.equal(rich.research.dates[0],'2021-01-01');
assert.equal(rich.industry.industries[0],'801111');
assert.equal(rich.style.axes[0],'size');
assert.deepEqual(Array.from(rich.industry.market_current.dates),[]);
ctx.rich=rich;vm.runInContext('mergeLivePayload(rich)',ctx);
ctx.latest={charts:{all_a_channels:[{date:'2026-10-09',channel:'market_backstop',signed_value:3,intensity:3,relation_count:2},{date:'2026-10-10',channel:'market_backstop',signed_value:null,intensity:null,relation_count:null}]}};
vm.runInContext('mergeLivePayload(latest)',ctx);
assert.deepEqual(Array.from(ctx.F.research.dates),['2021-01-01','2026-10-09','2026-10-10']);
assert.deepEqual(Array.from(ctx.F.research.signed_intensity.market_backstop),[2,3,null]);
assert.ok(ctx.F.research.index_returns.verified.rows.length);
assert.equal(ctx.F.style.axes[0],'size');
assert.equal(ctx.F.industry.industries[0],'801111');
// Optional style failure must retain the other tracks.
delete components.macro_v5_component_style;
const partial=await vm.runInContext('hydrateSplitPayload({charts:{}})',ctx);
assert.equal(partial.industry.industries[0],'801111');
assert.equal(partial.research.dates[0],'2021-01-01');
// Syntax check every inline JavaScript block, including resize and initialization.
for(const match of html.matchAll(/<script([^>]*)>(.*?)<\/script>/gs))if(!/application\/json|src=/.test(match[1]))new vm.Script(match[2]);
assert.equal(fs.readFileSync(new URL('../web/index.html',import.meta.url),'utf8'),html);
console.log('PASS: legacy payload, component fallback, optional failures, historical preservation, null values, script syntax, mirrored entrypoints');
const evidenceLine=html.split('\n').find(line=>line.startsWith('let evidenceChunkCache='));
const evidenceCtx=vm.createContext({F:{},sb:{},fetchArtifactPayload:async()=>{throw {code:'PGRST116'}}});
vm.runInContext(evidenceLine,evidenceCtx);
const unavailable=await vm.runInContext("fetchEvidenceDay('industry','2026-10-09')",evidenceCtx);
assert.equal(unavailable.available,false);
assert.equal(unavailable.news_count,null);
console.log('PASS: unsynced evidence is missing, not zero');
