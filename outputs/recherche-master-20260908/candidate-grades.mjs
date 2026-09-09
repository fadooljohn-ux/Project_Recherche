// Evidence grading only. Never launches searches or changes their results.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';

const headers=['Search record ID','Pulsar','Statistical significance','Signal robustness',
 'Independent confirmation','Global FAP','Global sigma','Conditional review tail',
 'Noise exceedances','Noise simulations','Significance scope','Robustness evidence',
 'Confirmation evidence','Review disposition','Assessment ID','Evidence manifest'];
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');

export async function syncCandidateGrades(wb,repo,manifestPath=null){
 const searches=wb.worksheets.getItem('Searches').getUsedRange().values.slice(1);
 const log=wb.worksheets.getItem('Work log').getUsedRange().values.slice(1);
 // Invalid import attempts remain historical rows, but are not scientific candidates.
 const invalid=new Set(log.filter(r=>r[4]==='SUPERSEDED_INVALID_IMPORT').map(r=>r[8]));
 const candidates=searches.filter(r=>r[3]==='PERIODIC_SIGNAL_CANDIDATE'&&!invalid.has(r[20]));
 let sheet;
 for(let i=0;i<wb.worksheets.items.length;i++){
  const s=wb.worksheets.getItemAt(i);if(s.name==='Candidate grades')sheet=s;
 }
 if(!sheet){
  sheet=wb.worksheets.add('Candidate grades');sheet.showGridLines=false;
  sheet.getRange('A1:P1').values=[headers];
  sheet.getRange('A1:P1').format={fill:'#29465B',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,horizontalAlignment:'center'};
  sheet.getRange('A1:P1').format.rowHeight=42;
  sheet.tables.add('A1:P1',true,'CandidateGrades');
  sheet.freezePanes.freezeRows(1);sheet.freezePanes.freezeColumns(2);
 }
 const rows=()=>sheet.getUsedRange().values;
 if(JSON.stringify(rows()[0])!==JSON.stringify(headers))throw new Error('Candidate grade columns differ');
 let changed=0;
 for(const r of candidates){
  if(rows().some(x=>x[0]===r[0]))continue;
  sheet.tables.items[0].rows.add(null,[[r[0],r[1],'REVIEW_PENDING','NOT_ASSESSED','NOT_ASSESSED',null,null,null,null,null,
   'Global FAP not established. Complete the bounded review and record its scope.',null,null,'REVIEW_PENDING',null,null]]);changed++;
 }
 let manifest=null;
 if(manifestPath){
  const bytes=await fs.readFile(manifestPath);manifest=JSON.parse(bytes);
  if(manifest.schema_version!==1||!manifest.assessment_id||!Array.isArray(manifest.records))throw new Error('Invalid assessment manifest');
  if(new Set(manifest.records.map(r=>r.record_id)).size!==manifest.records.length)throw new Error('Duplicate assessment record');
  for(const a of manifest.records){
   const source=candidates.find(r=>r[0]===a.record_id);
   if(!source||source[1]!==a.target||source[20]!==a.result_sha256)throw new Error('Assessment does not match a valid candidate: '+a.record_id);
   if(sha(await fs.readFile(source[19]))!==a.result_sha256)throw new Error('Original candidate evidence changed');
   for(const evidence of a.sources){
    if(sha(await fs.readFile(path.resolve(repo,evidence.path)))!==evidence.sha256)throw new Error('Review evidence changed: '+evidence.path);
   }
   if(!a.sources.some(s=>s.path===a.diagnostic_source))throw new Error('Diagnostic source not bound');
   const diagnostic=JSON.parse(await fs.readFile(path.resolve(repo,a.diagnostic_source),'utf8'));
   if(!Number.isInteger(a.null_count)||a.null_count<1||!Number.isInteger(a.null_exceedances)||a.null_exceedances<0||a.null_exceedances>a.null_count)throw new Error('Invalid simulation counts');
   const p=(a.null_exceedances+1)/(a.null_count+1);
   if(!Number.isFinite(a.diagnostic_p_plus_one)||!Number.isFinite(diagnostic.diagnostic_p_plus_one)||diagnostic.null_count!==a.null_count||diagnostic[a.exceedance_field]!==a.null_exceedances||Math.abs(p-a.diagnostic_p_plus_one)>1e-12||Math.abs(p-diagnostic.diagnostic_p_plus_one)>1e-12)throw new Error('Diagnostic tail differs from saved evidence');
   // v1 reports conditional diagnostics. It cannot manufacture a global significance.
   if(a.statistical_grade!=='NOT_ESTABLISHED'||a.global_fap!==null||a.global_sigma!==null)throw new Error('Global significance requires a separately supported calibration');
   if(!['NOISE_SENSITIVE','MIXED','ROBUST_WITHIN_REVIEW','NOT_ASSESSED'].includes(a.robustness_grade))throw new Error('Unknown robustness grade');
   if(!['UNAVAILABLE','UNDERPOWERED','NOT_CORROBORATED','CORROBORATED','NOT_ASSESSED'].includes(a.confirmation_grade))throw new Error('Unknown confirmation grade');
   if(!a.robustness_evidence||!a.confirmation_evidence||!a.diagnostic_scope||!a.global_scope||!a.disposition)throw new Error('Missing grade explanation');
   const index=rows().findIndex(r=>r[0]===a.record_id)+1;
   const values=[a.record_id,a.target,a.statistical_grade,a.robustness_grade,a.confirmation_grade,null,null,p,a.null_exceedances,a.null_count,
    a.global_scope+' '+a.diagnostic_scope,a.robustness_evidence,a.confirmation_evidence,a.disposition,manifest.assessment_id,path.relative(repo,manifestPath)];
   if(JSON.stringify(rows()[index-1])!==JSON.stringify(values)){
    sheet.getRange(`A${index}:P${index}`).values=[values];changed++;
   }
   sheet.getRange(`H${index}`).formulas=[[`=(I${index}+1)/(J${index}+1)`]];
  }
 }
 const last=rows().length;
 if(changed){
  sheet.getRange(`A2:P${last}`).format.font={name:'Arial',size:10};
  sheet.getRange(`A2:P${last}`).format.wrapText=true;
  sheet.getRange(`A2:P${last}`).format.verticalAlignment='top';
  for(const [c,width] of Object.entries({A:49,B:18,C:24,D:23,E:24,F:15,G:15,H:18,I:15,J:15,K:65,L:65,M:65,N:35,O:35,P:65}))sheet.getRange(`${c}1:${c}${last}`).format.columnWidth=width;
  sheet.getRange(`F2:F${last}`).setNumberFormat('0.00E+00');
  sheet.getRange(`G2:G${last}`).setNumberFormat('0.00');
  sheet.getRange(`H2:H${last}`).setNumberFormat('0.0%');
  sheet.getRange(`I2:J${last}`).setNumberFormat('#,##0');
  sheet.getRange(`A2:P${last}`).format.autofitRows();
 }
 return {changed,candidate_records:candidates.length,excluded_invalid_imports:searches.filter(r=>r[3]==='PERIODIC_SIGNAL_CANDIDATE'&&invalid.has(r[20])).length,
  manifest,manifest_sha256:manifestPath?sha(await fs.readFile(manifestPath)):null};
}
