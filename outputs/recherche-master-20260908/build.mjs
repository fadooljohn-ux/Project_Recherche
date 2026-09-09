import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const repo = process.cwd();
const out = path.join(repo, 'outputs/recherche-master-20260908');
const data = path.resolve(repo, '../Project Recherche Data');
const read = async p => JSON.parse(await fs.readFile(p, 'utf8'));
const hash = async p => crypto.createHash('sha256').update(await fs.readFile(p)).digest('hex');
const evidence = [];
async function source(p) { const abs=path.resolve(p); const sha=await hash(abs); evidence.push({path:abs,sha256:sha}); return [abs,sha]; }
const selectionPath=path.join(data,'mpta-batch01-20260908/selection.json');
const selection=await read(selectionPath);
const batch=await read(path.join(repo,'results/observed/mpta-batch01-20260908-closeout.json'));
const comp=await read(path.join(repo,'results/observed/five-companion-20260908-closeout.json'));
const b1257=await read(path.join(repo,'results/observed/b1257-20260908-closeout.json'));
const selSource=await source(selectionPath);
const aliases={'J1300+1240':'B1257+12','J1623-2631':'B1620-26','J1701-3006H':'M62H; NGC6266H','J1939+2134':'B1937+21','J1857+0943':'B1855+09','J1955+2908':'B1953+29'};
const observed=new Map();
const runs=[];
const runHeaders=['Record ID','Target ID','Data / method','Result','Period (days)','Period meaning','Amplitude (µs)','Peak statistic','Threshold','TOAs used','Epochs','Search min (days)','Search max (days)','Grid cells','Masked cells','Median 95% amplitude (µs)','Disposition detail','Previous record','Repeat rule','Evidence file','Evidence SHA-256','Input / calibration binding'];
async function addRun(x) {
  const src=await source(x.file);
  if(x.expected && src[1]!==x.expected) throw new Error('Result digest mismatch: '+x.id);
  runs.push([x.id,x.target,x.method,x.status,x.period??null,x.periodMeaning??null,x.amplitude??null,x.stat??null,x.threshold??null,x.toas??null,x.epochs??null,x.min??null,x.max??null,x.grid??null,x.masked??null,x.sensitivity??null,x.note??null,x.previous??null,'Preserve consumed record; new data/scope requires a new ID',...src,x.binding??null]);
}
for(const r of batch.results) {
  const id=`MPTA01-${r.target}-run01`;
  await addRun({id,target:r.target,method:'MPTA 4.5 yr; original circular search',status:r.status,period:r.peak_period_days,periodMeaning:'Strongest eligible grid peak; not a detected orbit',amplitude:r.peak_amplitude_us,stat:r.peak_statistic,threshold:r.threshold,toas:r.toas,epochs:r.epochs,min:30,max:400,grid:r.grid_cells,masked:r.grid_cells-r.eligible_cells,sensitivity:r.sensitivity_median_worst_phase_us,note:'Fixed published noise + epoch DM. 1% batch allowance for 10 fixed grids. Sensitivity: circular on-grid, worst phase, 95% detection probability; not an upper limit.',file:path.join(data,`mpta-batch01-20260908/${r.target}/run01/result.json`),expected:r.result_sha256,binding:`observed=${r.observed_sha256}; calibration=${r.calibration_key}`});
  observed.set(r.target,{status:'NO_TRIGGER',id,summary:'No qualifying signal in eligible 30–400-day cells',action:'Retain result; consider independent data or a separately defined new scope',mpta:'SEARCHED'});
}
for(const t of ['J1719-1438','J2322-2650','J1544+4937']) {
  const r=comp.results[t],id=`COMPANION-${t}-run01`,isL=t==='J1544+4937';
  await addRun({id,target:t,method:isL?'LOFAR; model-assisted known companion':'MPTA 4.5 yr; model-assisted known companion',status:r.status,period:r.period_days,periodMeaning:'Refined circular period (TDB)',amplitude:r.amplitude_us,stat:r.grid_peak_statistic,threshold:r.threshold,toas:isL?245:t==='J1719-1438'?2659:1967,epochs:isL?51:t==='J1719-1438'?100:76,min:r.reference.period_days*.99,max:r.reference.period_days*1.01,grid:r.calibration.frequency_count,masked:r.calibration.excluded_cells,sensitivity:r.calibration.median_worst_phase_amplitude_us,note:'Published pulse connection and ±1% period window; conditional recovery, not blind rediscovery. '+(isL?'245 of 330 TOAs retained by uncertainty cut; black-widow companion.':'Companion classification is not established by this timing recovery.'),file:path.join(data,`five-companion-benchmark-20260908/${t}/run01/result.json`),expected:comp.numerical_verification[t].result_sha256,binding:`observed=${r.observed_sha256}; profile=${r.profile_sha256}; calibration=${r.calibration.cache_key}`});
  observed.set(t,{status:'KNOWN_COMPANION_RECOVERED',id,summary:isL?'Known black-widow companion recovered':'Known companion recovered; model-assisted',action:'Retain benchmark; no automatic blind-discovery claim',mpta:isL?'NOT IN RELEASE':'COMPANION BENCHMARK ONLY'});
}
const bPath=path.join(data,'operational-20260908/observed-runs/pilot2-ioc-observed-b1937-20260908-01/result.json');
const b=await read(bPath);
await addRun({id:'B1937-20260908-01',target:'J1939+2134',method:'NANOGrav 15 yr v2.1.0 wideband; original search',status:b.disposition,period:b.selected_peak.period_days,periodMeaning:'Strongest eligible grid peak; not a detected orbit',stat:b.selected_peak.statistic,threshold:b.threshold,toas:660,min:30,max:2000,grid:953,masked:1,note:'Original qualification-02 annual mask and threshold. Later automatic calibration does not replace this search.',file:bPath,binding:`observed=${b.residual_vector_sha256}; package=${b.package_sha256}`});
observed.set('J1939+2134',{status:'NO_TRIGGER',id:'B1937-20260908-01',summary:'No qualifying signal in eligible 30–2,000-day cells',action:'Preserve original threshold and annual mask with this result',mpta:'NOT IN RELEASE'});
const bRoot=path.join(data,'b1257-benchmark-20260908');
await addRun({id:'B1257-run01',target:'J1300+1240',method:'I-LOFAR; initial known-system search',status:'RETAINED_FIT_BOUNDARY',threshold:23.179773012212713,toas:310,epochs:37,min:10,max:400,grid:360,masked:16,note:'Original two detections retained. Joint refinement reached its bound; superseded by refinement01. Not a new dataset.',file:path.join(bRoot,'run01/result.json'),expected:b1257.original_result_sha256,binding:b1257.calibration_sha256});
const fit=b1257.final_result.joint_orbit_fit;
await addRun({id:'B1257-refinement01',target:'J1300+1240',method:'I-LOFAR; joint refinement of original detections',status:'TWO_KNOWN_PLANETS_RECOVERED',threshold:23.179773012212713,toas:310,epochs:37,min:10,max:400,grid:360,masked:16,note:`c: ${fit.periods_days[1].toFixed(6)} d, ${fit.amplitudes_us[1].toFixed(3)} µs. d: ${fit.periods_days[0].toFixed(6)} d, ${fit.amplitudes_us[0].toFixed(3)} µs. Inner b not recovered. Independent Keplerian approximation; conditional errors.`,previous:'B1257-run01',file:path.join(bRoot,'refinement01/result.json'),expected:b1257.final_result_sha256,binding:b1257.calibration_sha256});
observed.set('J1300+1240',{status:'PARTIAL_KNOWN_SYSTEM_RECOVERY',id:'B1257-refinement01',summary:'Two larger known planets recovered; inner planet below sensitivity',action:'Higher-precision TOAs needed for inner planet; no threshold retuning',mpta:'NOT IN RELEASE'});
const targetHeaders=['Target ID','Aliases','Current research status','Latest record ID','Recorded finding','Next work / repeat rule','MPTA dataset status','MPTA TOAs','MPTA epochs','MPTA span (days)','Batch 01 selection','Batch 01 exclusion reason','JBO inventory','NANOGrav 11 inventory','EPTA DR2 inventory','Operator notes','Inventory evidence','Evidence SHA-256','MPTA PAR SHA-256','MPTA TIM SHA-256'];
const targetRows=[];
for(const r of selection.rows) {
  const o=observed.get(r.target), eligible=!r.exclusion_reasons.length;
  targetRows.push([r.target,aliases[r.target]??'',o?.status??'NOT_SEARCHED',o?.id??'',o?.summary??'Inventory only; no Recherche observed search recorded',o?.action??(eligible?'Eligible but outside first batch; select only in a new planned batch':'Different model or data scope needed before selection'),o?.mpta??'AVAILABLE; NOT SEARCHED',r.toas,r.epochs,r.span_days,r.selected?'SELECTED':eligible?'ELIGIBLE; NOT SELECTED':'EXCLUDED FROM BATCH 01',r.exclusion_reasons.join('; '),...['JBO800','NANOGrav11','EPTA_DR2'].map(k=>r.prior_search_membership[k]?'LISTED':'NOT LISTED'),'',...selSource,r.par_sha256,r.tim_sha256]);
}
for(const [t,o] of observed) if(!targetRows.some(r=>r[0]===t)) {
  const rr=runs.find(r=>r[0]===o.id);
  targetRows.push([t,aliases[t]??'',o.status,o.id,o.summary,o.action,o.mpta,null,null,null,'NOT IN MPTA INVENTORY','', 'NOT CHECKED','NOT CHECKED','NOT CHECKED','',rr[19],rr[20],null,null]);
}
const compSrc=await source(path.join(repo,'results/observed/five-companion-20260908-closeout.json'));
for(const [t,key,note,next] of [
 ['J1623-2631','B1620-26','No suitable public phase-connected long-span TOAs located','Obtain long-span TOAs and inner-stellar / outer-planet model'],
 ['J1701-3006H','J1701-3006H','No suitable public TOA release located; paper offers data on request','Obtain phase-connected TOAs, timing model and corrections']
]) targetRows.push([t,aliases[t],'DATA_GAP','',note,next,'NOT IN RELEASE',null,null,null,'NOT IN MPTA INVENTORY','', 'NOT CHECKED','NOT CHECKED','NOT CHECKED','',...compSrc,null,null]);
targetRows.sort((a,b)=>{const order=s=>s==='DATA_GAP'?1:s==='NOT_SEARCHED'?2:0;return order(a[2])-order(b[2])||a[0].localeCompare(b[0]);});
if(new Set(targetRows.map(r=>r[0])).size!==targetRows.length) throw new Error('Duplicate target IDs');
if(new Set(runs.map(r=>r[0])).size!==runs.length) throw new Error('Duplicate record IDs');

const workHeaders=['Work ID','Date','Work type','Target / scope','Status','Recorded outcome','Next action / closure','Evidence file','Evidence SHA-256'];
const work=[];
async function task(id,date,type,scope,status,outcome,next,file){work.push([id,new Date(date+'T00:00:00Z'),type,scope,status,outcome,next,...await source(path.join(repo,file))]);}
await task('REHAB-01-04','2026-09-07','Engineering','Runtime / development','COMPLETE','Recovery, input setup, localized repairs and development fixtures complete','Use pinned Intel runtime; preserve fixtures','docs/REHABILITATION_STATUS_2026-09-07.md');
await task('QUALIFICATION-01','2026-09-08','Synthetic qualification','344 cases','FAIL_PRESERVED','20 of 21 gates passed; annual solver disagreement failed','Consumed attempt; retain original failure','results/qualification/stage5-terminal-verification.json');
await task('ANNUAL-REPAIR','2026-09-08','Engineering','Annual solver','COMPLETE','Signal/Jacobian and spin-phase precision repairs retained','Preserve qualified numerical implementation','docs/SOLVER_PRECISION_REPAIR_2026-09-08.md');
await task('QUALIFICATION-02','2026-09-08','Synthetic qualification','344 cases','PASS','21 of 21 gates passed; 688 primary fits, 35 audits','Consumed attempt; retain qualification scope','results/qualification/qualification02-terminal-verification.json');
await task('STAGE-06','2026-09-08','Engineering','Operational release','COMPLETE','Canonical host/path release packaged and restored','Different host or path needs environment binding','results/qualification/stage6-operational-verification.json');
await task('B1257-INNER-INJECTIONS','2026-09-08','Simulation','J1300+1240','COMPLETE','0 of 256 injections recovered the 3 µs inner planet','Higher-precision observed data needed','results/observed/b1257-20260908-closeout.json');
await task('B1257-LARGE-INJECTIONS','2026-09-08','Simulation','J1300+1240','COMPLETE','Both larger planets recovered in 31 of 32 simulations','Retain the sampling/interference miss','results/observed/b1257-20260908-closeout.json');
await task('AUTO-CALIBRATION','2026-09-08','Engineering','Prepared target profiles','COMPLETE','Automatic threshold, projection mask, sensitivity and cache reuse verified','Reuse bound cache. Raw-radio ingestion and unknown-noise estimation are not implemented','results/calibration/automatic-calibration-20260908.json');
await task('MPTA-BATCH01','2026-09-08','Observed campaign','10 original-search targets','COMPLETE','10 NO_TRIGGER; 0 candidates; 0 execution failures','Retain 10 consumed run01 records','results/observed/mpta-batch01-20260908-closeout.json');
await task('M62H-DATA','2026-09-08','Data acquisition','J1701-3006H','OPEN','Public TOA release not located; no observed scan','Public release or separately authorized author request needed','docs/FIVE_COMPANION_BENCHMARK_2026-09-08.md');
await task('B1620-DATA-MODEL','2026-09-08','Data acquisition','J1623-2631','OPEN','Long-span phase-connected TOAs not located; no observed scan','Long-span TOAs and outer-orbit model needed','docs/FIVE_COMPANION_BENCHMARK_2026-09-08.md');
await task('LEGACY-ARCHIVE','2026-09-07','Historical archive','Earlier Pilot 0/1 and recovery history','RETAINED','Pre-rehabilitation work remains in repository and recovery archives; not individually re-adjudicated here','Consult archived results before repeating legacy work','docs/OPERATIONAL_REHABILITATION_ROADMAP_2026-09-07.md');

const wb=Workbook.create();
const overview=wb.worksheets.add('Overview');
const targets=wb.worksheets.add('Targets');
const searches=wb.worksheets.add('Searches');
const history=wb.worksheets.add('Work log');
const col=i=>{let x=i+1,s='';while(x){x--;s=String.fromCharCode(65+x%26)+s;x=Math.floor(x/26);}return s;};
function grid(sheet,headers,rows,widths,name) {
  const end=col(headers.length-1), n=rows.length+1;
  sheet.getRange(`A1:${end}${n}`).values=[headers,...rows];
  sheet.showGridLines=false;
  sheet.getRange(`A1:${end}${n}`).format={font:{name:'Arial',size:10,color:'#243447'},verticalAlignment:'center',rowHeight:42,wrapText:true};
  sheet.getRange(`A1:${end}1`).format={fill:'#29465B',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},rowHeight:42,horizontalAlignment:'center',wrapText:true};
  for(let c=0;c<headers.length;c++) sheet.getRange(`${col(c)}1:${col(c)}${n}`).format.columnWidth=widths[c]??20;
  const table=sheet.tables.add(`A1:${end}${n}`,true,name);table.showFilterButton=true;
  sheet.getRange(`A2:${end}${n}`).format.autofitRows();
  sheet.freezePanes.freezeRows(1);sheet.freezePanes.freezeColumns(2);
  return table;
}
grid(targets,targetHeaders,targetRows,[19,22,30,36,51,54,28,14,14,16,30,48,18,22,20,35,75,68,68,68],'TargetRegister');
grid(searches,runHeaders,runs,[37,19,44,34,18,46,20,20,20,15,14,18,18,14,14,22,85,28,52,85,68,100],'SearchRegister');
grid(history,workHeaders,work,[32,15,25,30,25,75,75,85,68],'WorkRegister');
targets.getRange(`H2:I${targetRows.length+1}`).setNumberFormat('#,##0');
targets.getRange(`J2:J${targetRows.length+1}`).setNumberFormat('0.0');
targets.getRange(`P2:P${targetRows.length+1}`).format.fill='#FFF4D6';
for(const c of ['E','G','H','I','L','M','P']) searches.getRange(`${c}2:${c}${runs.length+1}`).setNumberFormat(c==='E'?'0.000000':'0.000');
for(const c of ['J','K','N','O']) searches.getRange(`${c}2:${c}${runs.length+1}`).setNumberFormat('#,##0');
history.getRange(`B2:B${work.length+1}`).setNumberFormat('yyyy-mm-dd');
for(const [sheet,column,n] of [[targets,'C',targetRows.length],[searches,'D',runs.length],[history,'E',work.length]]) {
  const r=sheet.getRange(`${column}2:${column}${n+1}`);
  for(const t of ['DATA_GAP','OPEN','FAIL_PRESERVED','RETAINED_FIT_BOUNDARY'])r.conditionalFormats.add('containsText',{text:t,format:{fill:'#FFF0D5',font:{color:'#804B12'}}});
}
targets.getRange(`A2:A${targetRows.length+1}`).conditionalFormats.add('duplicateValues',{format:{fill:'#FFDCDC'}});
searches.getRange(`A2:A${runs.length+1}`).conditionalFormats.add('duplicateValues',{format:{fill:'#FFDCDC'}});
overview.showGridLines=false;overview.tabColor='#29465B';
overview.getRange('A1:H33').format={font:{name:'Arial',size:10,color:'#243447'},rowHeight:24,verticalAlignment:'center'};
overview.getRange('A2').values=[['Project Recherche master register']];
overview.getRange('A2').format.font={name:'Arial',size:16,bold:true,color:'#243447'};
overview.getRange('A2:H2').format.borders={bottom:{style:'thin',color:'#AAB9C3'}};
overview.getRange('A4').values=[['Records through']];overview.getRange('B4').values=[[new Date('2026-09-08T00:00:00Z')]];overview.getRange('B4').setNumberFormat('yyyy-mm-dd');
overview.getRange('D4').values=[['Publication edition: v0.1.0']];
overview.getRange('A6:B6').values=[['Recorded work','Count']];
const stats=[
 ['Unique targets in register','=COUNTA(TargetRegister[Target ID])'],
 ['Targets with observed searches','=COUNTIF(TargetRegister[Current research status],"NO_TRIGGER")+COUNTIF(TargetRegister[Current research status],"KNOWN_COMPANION_RECOVERED")+COUNTIF(TargetRegister[Current research status],"PARTIAL_KNOWN_SYSTEM_RECOVERY")'],
 ['Original-search targets with no trigger','=COUNTIF(TargetRegister[Current research status],"NO_TRIGGER")'],
 ['Known-system targets with recovery','=COUNTIF(TargetRegister[Current research status],"KNOWN_COMPANION_RECOVERED")+COUNTIF(TargetRegister[Current research status],"PARTIAL_KNOWN_SYSTEM_RECOVERY")'],
 ['Targets awaiting data','=COUNTIF(TargetRegister[Current research status],"DATA_GAP")'],
 ['Inventoried targets not searched','=COUNTIF(TargetRegister[Current research status],"NOT_SEARCHED")'],
 ['Search / refinement records','=COUNTA(SearchRegister[Record ID])'],
 ['Periodic-signal candidates','=COUNTIF(SearchRegister[Result],"PERIODIC_SIGNAL_CANDIDATE")'],
 ['Confirmed new discoveries','=COUNTIF(SearchRegister[Result],"CONFIRMED_NEW_DISCOVERY")']
];
const summaryRanges={'TargetRegister[Target ID]':'Targets!$A$2:$A$1001','TargetRegister[Current research status]':'Targets!$C$2:$C$1001','SearchRegister[Record ID]':'Searches!$A$2:$A$1001','SearchRegister[Result]':'Searches!$D$2:$D$1001'};
for(let i=0;i<stats.length;i++){let f=stats[i][1];for(const [a,b] of Object.entries(summaryRanges))f=f.replaceAll(a,b);overview.getRange(`A${7+i}`).values=[[stats[i][0]]];overview.getRange(`B${7+i}`).formulas=[[f]];}
overview.getRange('A6:B6').format={fill:'#29465B',font:{color:'#FFFFFF',bold:true}};
overview.getRange('B7:B15').setNumberFormat('#,##0');
const notes=[
 ['Before starting work','Search Targets by canonical ID and alias, then inspect the latest Searches record and its input binding.'],
 ['Add future work','Append a unique record ID in the Excel tables. Summaries cover the first 1,000 records per table; extend ranges beyond that. Keep predecessor IDs.'],
 ['Editable notes','Targets: amber Operator notes cells are for follow-up notes. Preserve imported scientific results and evidence hashes.'],
 ['Reusing a target','A target can have multiple datasets. A completed target is not a blanket claim that all of its public data were searched.'],
 ['Data gaps','M62H and B1620-26 have no observed search here. Missing data is neither a nondetection nor a successful test.'],
 ['Interpretation','NO_TRIGGER means no qualifying signal in the recorded scope. Known-companion recovery is separate from new discovery.'],
 ['Sensitivity','Amplitude limits shown in Searches mean 95% detection probability for circular on-grid signals under fixed noise, not posterior upper limits.'],
 ['Prior coverage','LISTED / NOT LISTED refers only to three saved study inventories. JBO supplement contains 794 named targets despite the paper’s 800-target description.'],
 ['Source records','Evidence filenames and SHA-256 digests are at the right of each table. All existing run records were read without new scans.'],
 ['History scope','Detailed register starts with September rehabilitation and observed campaigns. Earlier Pilot 0/1 work remains indexed by the legacy archive entry.']
];
overview.getRange('D6:E15').values=notes;overview.getRange('D6:D15').format.font={bold:true};overview.getRange('E6:E15').format.wrapText=true;overview.getRange('D6:E15').format.rowHeight=48;
overview.getRange('A18').values=[['Current focus']];overview.getRange('A18').format.font={bold:true};
overview.getRange('A20').values=[['First original MPTA batch']];overview.getRange('B20').values=[['Complete: 10 NO_TRIGGER']];
overview.getRange('A22').values=[['B1257+12 benchmark']];overview.getRange('B22').values=[['Two larger planets recovered; inner planet below sensitivity']];
overview.getRange('A24').values=[['Five additional companions']];overview.getRange('B24').values=[['Three model-assisted recoveries; two data gaps']];
overview.getRange('A26').values=[['Scientific qualification']];overview.getRange('B26').values=[['Attempt 01 FAIL retained; attempt 02 PASS, 21/21 gates']];
overview.getRange('A28').values=[['Maintenance']];overview.getRange('B28').values=[['Update this master in place after completed work; do not create competing masters.']];
overview.getRange('B20:C28').format.wrapText=true;overview.getRange('A20:C28').format.rowHeight=38;
for(const [c,w] of Object.entries({A:47,B:30,C:3,D:24,E:83,F:3,G:3,H:3}))overview.getRange(`${c}1:${c}33`).format.columnWidth=w;
wb.recalculate();
const expectedCounts=[targetRows.length,15,11,4,2,targetRows.length-17,runs.length,0,0];
const actual=overview.getRange('B7:B15').values.flat();
if(JSON.stringify(actual)!==JSON.stringify(expectedCounts))throw new Error('Summary mismatch '+JSON.stringify({actual,expectedCounts}));
// Check a representative status edit before delivery.
const saved=targets.getRange('C2').values;
targets.getRange('C2').values=[['PERIODIC_SIGNAL_CANDIDATE']];
if(overview.getRange('B8').values[0][0]!==14)throw new Error('Summary did not respond to target status change');
targets.getRange('C2').values=saved;
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'Overview!A6:B15',include:'values,formulas',tableMaxRows:10,tableMaxCols:2,maxChars:2300})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},summary:'Final formula error scan'})).ndjson);
for(const [name,range] of [['Overview','A1:E29'],['Targets','A1:F10'],['Searches','A1:I8'],['Work log','A1:G9']]) {
  const png=await wb.render({sheetName:name,range,scale:1,format:'png'});
  await fs.writeFile(path.join(out,name.replaceAll(' ','-')+'.png'),new Uint8Array(await png.arrayBuffer()));
}
const file=path.join(out,'Project-Recherche-Master.xlsx');
await (await SpreadsheetFile.exportXlsx(wb)).save(file);
// Verify the next table row in memory after export; never save this temporary row.
const temporary=Array(targetHeaders.length).fill(null);
temporary[0]='TEMP_EXTENSION_CHECK';temporary[2]='NOT_SEARCHED';
targets.tables.items[0].rows.add(null,[temporary]);
wb.recalculate();
if(overview.getRange('B7').values[0][0]!==targetRows.length+1 || overview.getRange('B12').values[0][0]!==targetRows.length-16)throw new Error('Table extension did not update summary: '+JSON.stringify(overview.getRange('B7:B12').values));
await fs.writeFile(path.join(out,'source-manifest.json'),JSON.stringify({as_of:'2026-09-08',workbook:file,workbook_sha256:await hash(file),targets:targetRows.length,observed_targets:15,search_records:runs.length,work_records:work.length,sources:evidence},null,2)+'\n');
console.log(JSON.stringify({file,targets:targetRows.length,searchRecords:runs.length,workRecords:work.length}));
