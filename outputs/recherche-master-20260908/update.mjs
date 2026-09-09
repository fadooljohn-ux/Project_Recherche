// Update the existing master from saved MPTA preparation/terminal records. No science runs.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {Workbook,FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
import {syncCandidateGrades} from './candidate-grades.mjs';
const repo=path.resolve(import.meta.dirname,'../..');
const folder=import.meta.dirname;
const file=path.join(folder,'Project-Recherche-Master.xlsx');
const root=path.resolve(process.argv[2]??'');
const development=process.argv[3]==='--chromatic-development';
const tpa=process.argv[3]==='--tpa-preparation';
const tpaObserved=process.argv[3]==='--tpa-observed';
const ng15=process.argv[3]==='--ng15-preparation';
const ng15Observed=process.argv[3]==='--ng15-observed';
const contextOnly=process.argv[3]==='--candidate-context';
const gradesOnly=process.argv[3]==='--candidate-grades';
const ptaPreparation=process.argv[3]==='--pta-preparation';
const ptaObserved=process.argv[3]==='--pta-observed';
const utmostObserved=process.argv[3]==='--utmost-observed';
const iptaObserved=process.argv[3]==='--ipta-observed';
const pta=ptaPreparation||ptaObserved;
const prepared=tpa||ng15||ptaPreparation;
if(!process.argv[2])throw new Error('Usage: update.mjs BATCH_DATA_ROOT');
const read=async p=>JSON.parse(await fs.readFile(p,'utf8'));
const hash=async p=>crypto.createHash('sha256').update(await fs.readFile(p)).digest('hex');
const exists=async p=>fs.access(p).then(()=>true,()=>false);
const freezePath=path.join(root,'execution-freeze.json');
const selection=gradesOnly?{selected:[]}:await read(path.join(root,'selection.json'));
const source=iptaObserved?'IPTA':utmostObserved?'UTMOST':pta?selection.source:ng15||ng15Observed?'NG15':tpa||tpaObserved?'TPA':'MPTA';
const batchId=pta?path.basename(path.dirname(root))+'-'+path.basename(root):path.basename(root);
const replacementIntake=pta && selection.replacement_of_campaign?await read(path.join(path.dirname(root),'intake.json')):null;
const freeze=gradesOnly?null:await read(prepared?path.join(root,'preparation.json'):development?path.join(root,'diagnosis.json'):freezePath);
if(!gradesOnly && await hash(path.join(root,'selection.json'))!==freeze.selection_sha256)throw new Error('Selection does not match evidence');
if(development && (freeze.status!=='DEVELOPMENT_COMPLETE' || freeze.observed_search_executed!==false))throw new Error('Incomplete chromatic development evidence');
if(prepared && (freeze.status!=='PREPARED' || freeze.observed_search_executed!==false || freeze.results.length!==selection.selected.length))throw new Error('Incomplete TPA preparation');
const lock=file+'.update-lock';
const handle=await fs.open(lock,'wx');
try {
const beforeHash=await hash(file);
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(file));
const targets=wb.worksheets.getItem('Targets'), searches=wb.worksheets.getItem('Searches');
const work=wb.worksheets.getItem('Work log'), overview=wb.worksheets.getItem('Overview');
const originalNames=(await wb.inspect({kind:'sheet',include:'name'})).ndjson;
await fs.writeFile(path.join(folder,'update-before.png'),new Uint8Array(await (await wb.render({sheetName:'Overview',range:'A1:E15',scale:1,format:'png'})).arrayBuffer()));
function rows(sheet){return sheet.getUsedRange().values;}
const beforeSheets=Object.fromEntries([targets,searches,work].map(s=>[s.name,rows(s)]));
const beforeNotes=rows(targets).slice(1).map(r=>[r[0],r[15]]);
let changes=0,completed=0,failed=0;
const contextRows=[];
function set(sheet,address,value){const current=sheet.getRange(address).values[0][0];if(current!==value){sheet.getRange(address).values=[[value]];changes++;}}
function upsert(sheet,row,columns){
  const current=rows(sheet),index=current.findIndex(r=>r[0]===row[0]);
  if(index<0){sheet.tables.items[0].rows.add(null,[row]);const last=rows(sheet).length;sheet.getRange(`A${last}:${columns}${last}`).copyFrom(sheet.getRange(`A${last-1}:${columns}${last-1}`),'all');sheet.getRange(`A${last}:${columns}${last}`).values=[row];sheet.getRange(`A${last}:${columns}${last}`).format.autofitRows();changes++;return;}
  if(JSON.stringify(current[index].slice(0,row.length))!==JSON.stringify(row)){
    if(sheet===searches)throw new Error('Existing scientific record differs: '+row[0]);
    sheet.getRange(`A${index+1}:${columns}${index+1}`).values=[row];changes++;
  }
}
if(gradesOnly){
 // Existing scientific evidence is read by syncCandidateGrades below.
}else if(contextOnly){
 const note=await read(process.argv[4]);
 if(![...selection.selected,...(selection.deferred_targets??[])].includes(note.target))throw new Error('Context target outside selected or explicitly deferred batch targets');
 if(await hash(note.result_path)!==note.result_sha256)throw new Error('Context source result changed');
 const tr=rows(targets).findIndex(r=>r[0]===note.target)+1;
 if(tr<2)throw new Error('Context target absent');
 for(const entry of note.entries){
  const values=[entry.id,new Date(note.created_utc),entry.kind,note.target,entry.status,entry.summary,entry.scope,entry.source,entry.source_sha256??null];
  const existing=rows(work).find(r=>r[0]===entry.id);
  if(existing && JSON.stringify(existing.slice(2,9))!==JSON.stringify(values.slice(2,9)))throw new Error('Context record already differs: '+entry.id);
  if(!existing)upsert(work,values,'I');
  const rowIndex=rows(work).findIndex(r=>r[0]===entry.id)+1;
  contextRows.push(rowIndex);
  work.getRange(`A${rowIndex}:I${rowIndex}`).format.wrapText=true;
  work.getRange(`A${rowIndex}:I${rowIndex}`).format.autofitRows();
 }
 set(targets,`F${tr}`,note.next_step);
 targets.getRange(`F${tr}`).format.wrapText=true;
 targets.getRange(`A${tr}:T${tr}`).format.autofitRows();
}else if(prepared){
 const evidence=path.join(root,'selection.json'), sha=await hash(evidence);
 for(const [column,label] of Object.entries({G:'Timing dataset status',H:'Inventory TOAs',I:'Inventory epochs',J:'Inventory span (days)',K:'Inventory selection',L:'Exclusion reason',S:'PAR SHA',T:'TIM SHA'}))set(targets,column+'1',label);
 const existing=new Set(rows(targets).slice(1).map(r=>r[0]));
 const added=selection.rows.filter(r=>!existing.has(r.target) && (!(ng15||pta) || r.selected)).map(r=>[
  r.target,r.aliases.join(', '),'NOT_SEARCHED',null,'No observed search',
  r.selected?'Calibrated. Next: freeze and launch':r.exclusion_reasons.length?'Retain exclusion for current scope':'Eligible for a later TPA batch',
  r.selected?`${source} PREPARED; NOT SEARCHED`:r.exclusion_reasons.length?'TPA EXCLUDED':'TPA ELIGIBLE',
  r.toas,r.epochs,r.span_days,r.selected?batchId:null,r.exclusion_reasons.join(', ')||null,
  r.prior_search_membership.JBO800==null?'Not checked':r.prior_search_membership.JBO800?'Present':'Absent from named inventory',
  r.prior_search_membership.NANOGrav11==null?'Not checked':r.prior_search_membership.NANOGrav11?'Present':'Absent from named inventory',
  r.prior_search_membership.EPTA_DR2==null?'Not checked':r.prior_search_membership.EPTA_DR2?'Present':'Absent from named inventory',null,evidence,sha,r.par_sha256,r.tim_sha256]);
 const first=rows(targets).length+1;
 if(added.length){targets.tables.items[0].rows.add(null,added);changes+=added.length;
  targets.getRange(`A${first}:T${first+added.length-1}`).format.rowHeight=60;
  targets.getRange(`A${first}:T${first+added.length-1}`).format.wrapText=true;
  targets.getRange(`H${first}:I${first+added.length-1}`).setNumberFormat('#,##0');
  targets.getRange(`J${first}:J${first+added.length-1}`).setNumberFormat('0.0');}
 for(const target of selection.selected){
  const tr=rows(targets).findIndex(r=>r[0]===target)+1;
  if(tr<2 || (!(ng15||pta) && rows(targets)[tr-1][2]!=='NOT_SEARCHED'))throw new Error('Preparation target already searched or missing');
  set(targets,`F${tr}`,'Calibrated. Next: freeze and launch');
  set(targets,`G${tr}`,`${source} PREPARED; DATASET NOT SEARCHED`);
  if(ng15||pta){const r=selection.rows.find(r=>r.target===target), p=await read(path.join(root,target,'prepared/receipt.json'));
   for(const [c,v] of Object.entries({H:p.toas,I:p.epochs,J:p.span_days,S:r.par_sha256,T:r.tim_sha256}))set(targets,`${c}${tr}`,v);}
  set(targets,`K${tr}`,batchId);
  set(targets,`Q${tr}`,evidence);set(targets,`R${tr}`,sha);
  if(pta){targets.getRange(`F${tr}:G${tr}`).format.wrapText=true;targets.getRange(`A${tr}:T${tr}`).format.autofitRows();}
 }
 upsert(work,[`${batchId}-PREPARATION`,new Date(freeze.created_utc),'Inventory and calibration',`${selection.selected.length} ${source} targets`,'PREPARED',`${selection.eligible_targets} eligible; ${selection.selected.length} calibrated; ${selection.remaining_after_selection} remaining. No observed searches.`,pta?'One 18-dataset campaign; previous searches retained by dataset.':ng15?'Six targets new to Recherche; ten have retained searches with other data.':'Prior coverage checked for three named samples. Kerr 151 membership unresolved.',path.join(root,'preparation.json'),await hash(path.join(root,'preparation.json'))],'I');
 upsert(work,['SOURCE-QUEUE-20260908',new Date(freeze.created_utc),'Future sources','Four timing data sources',`${source} ACTIVE`,'Exhaust each eligible source pool in order','Update queue and master after each completed batch',path.join(repo,'docs/FUTURE_DATA_SOURCES.md'),await hash(path.join(repo,'docs/FUTURE_DATA_SOURCES.md'))],'I');
}else if(development){
 for(const r of freeze.results){
  const tr=rows(targets).findIndex(row=>row[0]===r.target)+1;
  if(tr<2 || !selection.selected.includes(r.target))throw new Error('Development target missing from master');
  const evidence=path.join(root,r.target,'diagnosis.json');
  if(JSON.stringify(await read(evidence))!==JSON.stringify(r))throw new Error('Per-target diagnosis differs');
  const trials=r.injections.reduce((n,x)=>n+x.trials,0), recovered=r.injections.reduce((n,x)=>n+x.detections_at_injected_cell,0);
  upsert(work,[`${batchId}-${r.target}`,new Date(freeze.created_utc),'Calibration and injection',r.target,'DEVELOPMENT COMPLETE',`${recovered}/${trials} simulated recoveries. Median amplitude cost +${((r.conditional_sensitivity_cost_ratio_median-1)*100).toFixed(2)}%.`,`Fixed published chromatic shapes/noise. Observed search awaits separate launch.`,evidence,await hash(evidence)],'I');
  set(targets,`F${tr}`,'Chromatic calibration complete. Next: freeze and launch a separately authorized observed search');
  set(targets,`G${tr}`,'CHROMATIC SUPPORT PREPARED; NOT SEARCHED');
 }
}else{
for(const t of selection.selected){
  const tr=rows(targets).findIndex(r=>r[0]===t)+1;
  if(tr<2)throw new Error('Selected target missing from master: '+t);
  const p=path.join(root,t,'run01/result.json'), dir=path.dirname(p);
  if(await exists(p)){
    const r=await read(p), prep=await read(path.join(root,t,'prepared/receipt.json'));
    if(r.execution_freeze_sha256!==await hash(freezePath))throw new Error('Terminal result uses another freeze: '+t);
    const existing=rows(searches).find(row=>row[19]===p);
    if(existing && existing[20]!==await hash(p))throw new Error('Existing scientific result digest changed: '+t);
    const id=existing?.[0]??`${batchId}-${t}-run01`;
    const result=r.candidate?'PERIODIC_SIGNAL_CANDIDATE':r.status;
    const bounds=prep.policy??selection.policy;
    const modelNote=utmostObserved?'Fixed released single-band total timing noise; no epoch DM. ':(ptaObserved||iptaObserved)?prep.noise_model+'. ':ng15Observed?'Fixed released wideband noise; joint TOA and DM likelihood. ':prep.chromatic_support?'Fixed published noise, epoch DM and chromatic support. ':'Fixed published noise and epoch DM. ';
    const noiseNote=(r.noise_adequacy_flag?' Noise adequacy flagged; inspect saved residual diagnostics.':'')+(iptaObserved && prep.checks?.historical_summary_difference_flag?' Historical PAR summary differs; independent fixed-model likelihood verified; historical-model reproduction is not claimed.':'');
    if(!existing)upsert(searches,[id,t,utmostObserved?'UTMOST DR1; original circular search':(ptaObserved||iptaObserved)?selection.dataset+'; circular search':ng15Observed?'NANOGrav15 v2.1.0; wideband circular search':tpaObserved?'TPA DR1; original circular search':'MPTA 4.5 yr; original circular search',result,r.peak_period_days,'Strongest eligible grid peak; candidate status is separate',r.peak_amplitude_us,r.peak_statistic,r.threshold,prep.toas,prep.epochs??prep.observing_days,bounds.minimum_period_days,bounds.maximum_period_days,r.grid_cells,r.grid_cells-r.eligible_cells,r.sensitivity_median_worst_phase_amplitude_us??r.sensitivity_median_worst_phase_us,modelNote+r.threshold_scope+'. '+r.sensitivity_definition+noiseNote,null,'Preserve consumed record; new data/scope requires a new ID',p,await hash(p),`observed=${r.observed_sha256}; calibration=${r.calibration_key}`],'V');
    const sr=rows(searches).findIndex(row=>row[0]===id)+1;
    for(const c of ['E','G','H','I','L','M','P'])searches.getRange(`${c}${sr}`).setNumberFormat(c==='E'?'0.000000':'0.000');
    for(const c of ['J','K','N','O'])searches.getRange(`${c}${sr}`).setNumberFormat('#,##0');
    const replacement=replacementIntake?.datasets.find(item=>item.target===t && item.source===path.basename(root));
    let replacesPriorCandidate=false;
    if(replacement){
      if(await hash(replacement.superseded_result_path)!==replacement.superseded_result_sha256)throw new Error('Superseded result changed');
      const prior=rows(searches).find(row=>row[19]===replacement.superseded_result_path);
      if(!prior)throw new Error('Superseded search absent from workbook');
      replacesPriorCandidate=rows(targets)[tr-1][3]===prior[0];
      upsert(work,[`${batchId}-${t}-IMPORT-CORRECTION`,new Date(replacementIntake.created_utc),'Import correction',t,'SUPERSEDED_INVALID_IMPORT',`${prior[0]} is retained as an invalid import attempt; replaced by ${id}`,replacementIntake.reason,replacement.superseded_result_path,replacement.superseded_result_sha256],'I');
    }
    const priorCandidate=(ptaObserved||iptaObserved) && rows(targets)[tr-1][2]==='PERIODIC_SIGNAL_CANDIDATE' && !r.candidate && !replacesPriorCandidate;
    if(!priorCandidate){set(targets,`C${tr}`,result);set(targets,`D${tr}`,id);
    set(targets,`E${tr}`,r.candidate?'Threshold-crossing periodic candidate; not a confirmed planet':`No qualifying signal in eligible ${bounds.minimum_period_days}–${Math.round(bounds.maximum_period_days)}-day cells`);
    }
    set(targets,`F${tr}`,priorCandidate?'Prior source candidate retained; compare the latest source result before interpretation':r.noise_adequacy_flag?'Review flagged noise adequacy before scientific interpretation':r.candidate?'Review candidate and noise adequacy using saved evidence':'Retain result; consider independent data or a separately defined new scope');
    set(targets,`G${tr}`,utmostObserved?'UTMOST SEARCHED':'SEARCHED');completed++;
  }else if(await exists(dir)){
    const hasGrid=await exists(path.join(dir,'periodogram.npz'));
    upsert(work,[`${batchId}-${t}-incomplete`,new Date(freeze.created_utc),'Observed attempt',t,'INCOMPLETE',hasGrid?'Observed grid saved; terminal result missing':'Run destination consumed; terminal result missing','Diagnose from retained outputs; do not label as NO_TRIGGER',freezePath,await hash(freezePath)],'I');
    set(targets,`F${tr}`,'Incomplete attempt: inspect saved run01 before any continuation');
    set(targets,`G${tr}`,'INCOMPLETE ATTEMPT');failed++;
  }else{
    set(targets,`F${tr}`,`Prepared for ${batchId}; awaiting execution`);
    set(targets,`G${tr}`,'PREPARED; DATASET NOT SEARCHED');
  }
}
const terminal=completed===selection.selected.length;
upsert(work,[`${batchId}-${tpaObserved||ng15Observed||ptaObserved||utmostObserved||iptaObserved?'FREEZE':'PREPARATION'}`,new Date(freeze.created_utc),'Batch preparation',`${selection.selected.length} ${source} original-search targets`,'PREPARED',`${selection.selected.length} profiles and calibrations frozen; no observed scan during preparation`,ng15Observed||ptaObserved?'Preparation and execution authorized together':'Launch is a separate operator instruction',freezePath,await hash(freezePath)],'I');
if(completed||failed)upsert(work,[`${batchId}-CLOSEOUT`,new Date(),'Observed campaign',`${selection.selected.length} ${source} original-search targets`,terminal?'COMPLETE':'PARTIAL',`${completed} terminal results; ${failed} incomplete attempts`,terminal?'All run01 destinations consumed; preserve evidence':'Finish only authorized outstanding work',freezePath,await hash(freezePath)],'I');
if(iptaObserved){
 const campaignState=selection.campaign_manifest?await read(path.join(path.dirname(selection.campaign_manifest),'progress.json')):null;
 const summary=campaignState?`${Object.values(campaignState.targets).filter(r=>r.status==='COMPLETE').length}/${campaignState.selected.length} searched; ${Object.values(campaignState.targets).filter(r=>r.status==='PREPARATION_GAP').length} preparation gaps`:`${completed}/1 selected dataset searched; 13 coverage candidates unprepared`;
 upsert(work,['SOURCE-QUEUE-20260908',new Date(),'Future sources','IPTA DR2 Version B',campaignState?(campaignState.status.startsWith('CLOSED')?(Object.values(campaignState.targets).some(r=>r.status==='PREPARATION_GAP')?'IPTA CAMPAIGN CLOSED WITH GAPS':'IPTA CAMPAIGN COMPLETE'):'IPTA CAMPAIGN ACTIVE'):terminal?'IPTA FIRST SEARCH COMPLETE':'IPTA ACTIVE',summary,'Preserve prior source searches and all exclusions',path.join(repo,'docs/FUTURE_DATA_SOURCES.md'),await hash(path.join(repo,'docs/FUTURE_DATA_SOURCES.md'))],'I');
}
if(ng15Observed)upsert(work,['SOURCE-QUEUE-20260908',new Date(),'Future sources','Four timing data sources',terminal?'NG15 SINGLE POOL COMPLETE':'NG15 ACTIVE',`${completed}/16 additional NG15 searches; B1937 previously completed`,'PPTA DR3 is next in the source queue',path.join(repo,'docs/FUTURE_DATA_SOURCES.md'),await hash(path.join(repo,'docs/FUTURE_DATA_SOURCES.md'))],'I');
if(tpaObserved)upsert(work,['SOURCE-QUEUE-20260908',new Date(),'Future sources','Four timing data sources','TPA ACTIVE',`${completed} TPA searched; ${selection.remaining_after_selection} unselected eligible remain`,'Update queue and master after each completed batch',path.join(repo,'docs/FUTURE_DATA_SOURCES.md'),await hash(path.join(repo,'docs/FUTURE_DATA_SOURCES.md'))],'I');
}
const terminal=!gradesOnly && !contextOnly && !prepared && !development && completed===selection.selected.length;
work.getRange(`B2:B${rows(work).length}`).setNumberFormat('yyyy-mm-dd');
work.getRange(`A1:A${rows(work).length}`).format.columnWidth=46;
searches.getRange(`A1:A${rows(searches).length}`).format.columnWidth=50;
overview.getRange('B4').values=[[new Date()]];
overview.getRange('B4').setNumberFormat('yyyy-mm-dd');
if(!contextOnly && !gradesOnly){
set(overview,'A20',prepared?`Next ${source} batch`:development?'Latest development':terminal?`Latest original ${source} batch`:`Next original ${source} batch`);
set(overview,'B20',prepared?`${selection.selected.length} calibrated; ${selection.remaining_after_selection} eligible remaining; no observed scans`:development?`${selection.selected.length} chromatic profiles calibrated; no observed scans`:terminal?`${selection.selected.length} terminal results recorded`:`${selection.selected.length} prepared; ${completed} searched; ${failed} incomplete`);
}
const campaignCloseout=path.join(path.dirname(root),'closeout.json');
if(ptaObserved && await exists(campaignCloseout)){
 const c=await read(campaignCloseout);
 if(c.status!=='COMPLETE')throw new Error('Campaign closeout is incomplete');
 if(await hash(c.report_path)!==c.report_sha256)throw new Error('Campaign report changed');
 set(overview,'A20','Latest PTA campaign');
 set(overview,'B20',`${c.datasets} datasets; ${c.unique_targets} pulsars; ${c.candidate_datasets} candidate datasets`);
 upsert(work,[`${c.campaign}-COMBINED-REVIEW`,new Date(c.completed_utc),'Combined source review',`${c.datasets} datasets / ${c.unique_targets} pulsars`,'COMPLETE',`${c.no_trigger_datasets} no trigger; ${c.candidate_datasets} candidate datasets; zero confirmed planets`,'Source observations kept separate; fixed-noise thresholds; overlapping pulsars compared',c.report_path,c.report_sha256],'I');
 upsert(work,['SOURCE-QUEUE-20260908',new Date(c.completed_utc),'Future sources','PPTA, EPTA and InPTA','ELIGIBLE POOLS COMPLETE','All 18 compatible source datasets searched','Preserve remaining exclusions and review candidate limitations',c.report_path,c.report_sha256],'I');
 for(const r of c.reviews){
  const tr=rows(targets).findIndex(row=>row[0]===r.target)+1;
  set(targets,`F${tr}`,`${r.disposition}: fixed-period diagnostics and cross-source comparison documented in campaign report`);
  upsert(work,[`${c.campaign}-${r.source}-${r.target}-REVIEW`,new Date(r.created_utc),'Candidate diagnostics',r.target,r.disposition,'Time and radio-frequency splits; one observing-day deletion; saved cross-source grids','Descriptive fixed-frequency checks; original trigger retained',c.report_path,c.report_sha256],'I');
 }
}
overview.getRange('B8').formulas=[['=COUNTIF(Targets!$C$2:$C$1001,"NO_TRIGGER")+COUNTIF(Targets!$C$2:$C$1001,"KNOWN_COMPANION_RECOVERED")+COUNTIF(Targets!$C$2:$C$1001,"PARTIAL_KNOWN_SYSTEM_RECOVERY")+COUNTIF(Targets!$C$2:$C$1001,"PERIODIC_SIGNAL_CANDIDATE")']];
set(overview,'A14','Current candidate targets');
overview.getRange('B14').formulas=[['=COUNTIF(Targets!$C$2:$C$1001,"PERIODIC_SIGNAL_CANDIDATE")']];
const grades=await syncCandidateGrades(wb,repo,gradesOnly?path.join(root,'assessments.json'):null);
changes+=grades.changed;
if(gradesOnly){
 const m=grades.manifest;
 const id=m.assessment_id+'-GRADING';
 const entry=[id,new Date(m.assessed_utc),'Candidate evidence grading',`${m.records.length} candidates`,'COMPLETE',
  'Three separate measures: significance, robustness and independent confirmation. Global FAP remains unestablished.',
  'Saved evidence only; original results and review dispositions retained.',path.join(root,'assessments.json'),grades.manifest_sha256];
 const old=rows(work).find(r=>r[0]===id);
 if(old && JSON.stringify(old.slice(2,9))!==JSON.stringify(entry.slice(2,9)))throw new Error('Existing grading record differs; use a new assessment ID');
 if(!old)upsert(work,entry,'I');
}
if(grades.changed){
 set(overview,'D16','Candidate grades');
 set(overview,'E16','See Candidate grades for significance, robustness and independent confirmation. Blank global FAP/sigma means not established. Conditional review tails are separate.');
 overview.getRange('D16:E16').format.wrapText=true;
 overview.getRange('D16:E16').format.autofitRows();
}
wb.recalculate();
if(JSON.stringify(beforeNotes)!==JSON.stringify(rows(targets).slice(1,1+beforeNotes.length).map(r=>[r[0],r[15]])))throw new Error('Operator notes changed');
for(const row of beforeSheets.Searches.slice(1)){
 const match=rows(searches).find(r=>r[0]===row[0]);
 if(JSON.stringify(match.slice(0,22))!==JSON.stringify(row.slice(0,22)))throw new Error('Historical search changed: '+row[0]);
}
for(const row of rows(targets).slice(1)){
 if(selection.selected.includes(row[0]))continue;
 if(contextOnly && (selection.deferred_targets??[]).includes(row[0]))continue;
 if(ptaObserved && await exists(campaignCloseout) && (await read(campaignCloseout)).reviews.some(r=>r.target===row[0]))continue;
 const old=beforeSheets.Targets.find(r=>r[0]===row[0]);
 if(prepared && !old && selection.rows.some(r=>r.target===row[0]))continue;
 if(JSON.stringify(row)!==JSON.stringify(old))throw new Error('Unselected target changed: '+row[0]);
}
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20}});
console.log(errors.ndjson);
if(contextOnly || gradesOnly){
 if(JSON.stringify(rows(work).slice(0,beforeSheets['Work log'].length))!==JSON.stringify(beforeSheets['Work log']))throw new Error('Historical work log changed');
}
if(contextOnly){
 await fs.writeFile(path.join(folder,'candidate-context.png'),new Uint8Array(await (await wb.render({sheetName:'Work log',range:`C${Math.min(...contextRows)}:G${Math.max(...contextRows)}`,scale:1,format:'png'})).arrayBuffer()));
}
const previews=gradesOnly?[['Overview','D14:E16']]:[['Overview','A1:E29'],['Work log',`A${Math.max(1,rows(work).length-3)}:G${rows(work).length}`],['Searches',`A${Math.max(1,rows(searches).length-4)}:I${rows(searches).length}`]];
if(grades.changed)previews.push(['Candidate grades',`B1:J${wb.worksheets.getItem('Candidate grades').getUsedRange().values.length}`]);
for(const [name,range] of previews){
 await fs.writeFile(path.join(folder,`update-${name.replaceAll(' ','-')}.png`),new Uint8Array(await (await wb.render({sheetName:name,range,scale:1,format:'png'})).arrayBuffer()));
}
if(!gradesOnly){
const selectedRow=rows(targets).findIndex(r=>r[0]===selection.selected[0])+1;
await fs.writeFile(path.join(folder,'update-Targets.png'),new Uint8Array(await (await wb.render({sheetName:'Targets',range:`A${Math.max(1,selectedRow-1)}:G${selectedRow+1}`,scale:1,format:'png'})).arrayBuffer()));
}
const backup=path.join(repo,'../Recherche Recovery/20260907T223404/master-workbook-history',beforeHash+'.xlsx');
await fs.mkdir(path.dirname(backup),{recursive:true});
if(!await exists(backup))await fs.copyFile(file,backup);
const temp=file+'.pending';await (await SpreadsheetFile.exportXlsx(wb)).save(temp);
if(await hash(file)!==beforeHash)throw new Error('Workbook changed during update; pending copy retained');
await fs.rename(temp,file);
const receipt={batch:root,completed,incomplete:failed,selected:selection.selected,previous_sha256:beforeHash,sha256:await hash(file),backup,changes,sheets:originalNames,counts:overview.getRange('B7:B15').values.flat(),updated_utc:new Date().toISOString()};
await fs.writeFile(path.join(root,gradesOnly?'grading-workbook-update.json':contextOnly?'candidate-context-workbook-update.json':'master-workbook-update.json'),JSON.stringify({...receipt,operation:gradesOnly?'candidate_grading':contextOnly?'context_only':'run_bookkeeping',candidate_grades:{records:grades.candidate_records,excluded_invalid_imports:grades.excluded_invalid_imports}},null,2)+'\n');
console.log(JSON.stringify(receipt));
} finally {await handle.close();await fs.unlink(lock);}
