// Append bounded UTMOST preparation to the canonical workbook, without search rows.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const repo=path.resolve(import.meta.dirname,'../..'),output=import.meta.dirname;
const master=path.join(repo,'outputs/recherche-master-20260908/Project-Recherche-Master.xlsx');
const evidence=path.join(repo,'results/research/utmost-preparation01-20260909');
const info=JSON.parse(await fs.readFile(path.join(evidence,'preparation.json'),'utf8'));
const hash=async p=>crypto.createHash('sha256').update(await fs.readFile(p)).digest('hex');
const beforeHash=await hash(master);
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(master));
const target=wb.worksheets.getItem('Targets'),work=wb.worksheets.getItem('Work log');
const searches=wb.worksheets.getItem('Searches'),overview=wb.worksheets.getItem('Overview');
const before={targets:target.getUsedRange().values,work:work.getUsedRange().values,
 searches:searches.getUsedRange().values,overviewFormulas:overview.getUsedRange().formulas};
const selected=info.results.map(r=>r.preparation.target);
const render=async(sheetName,range,name)=>fs.writeFile(path.join(output,name),
 new Uint8Array(await (await wb.render({sheetName,range,scale:1,format:'png'})).arrayBuffer()));
if(process.argv.includes('--preview')){
 await render('Work log','C92:G95','before-worklog.png');
 console.log(JSON.stringify({headers:before.targets[0],selected:before.targets.filter(r=>selected.includes(r[0])),
  counts:[before.targets.length,before.searches.length,before.work.length]}));process.exit(0);
}
if(!process.argv.includes('--apply'))throw Error('Use --preview or --apply');
const lock=master+'.update-lock',handle=await fs.open(lock,'wx');
try{
 if(before.work.some(r=>r[0]==='UTMOST-PREP01-20260909-CALIBRATION'))throw Error('Preparation already registered');
 const backup=path.resolve(repo,'../Recherche Recovery/20260907T223404/master-workbook-history',beforeHash+'.xlsx');
 await fs.mkdir(path.dirname(backup),{recursive:true});await fs.copyFile(master,backup);
 if(await hash(backup)!==beforeHash)throw Error('Workbook backup mismatch');
 const date=new Date('2026-09-09T00:00:00Z'),entries=[];
 for(const [i,f] of info.retained_failed_attempts.entries()){
  const file=path.join(repo,f.evidence);
  entries.push([`UTMOST-PREP01-20260909-ATTEMPT${i+1}`,date,'Adapter preparation','J1807-0847','RETAINED FAILED ATTEMPT',
   i===0?'PINT rejected the out-of-order released clock table.':'Derived clock endpoints needed original coverage bounds for time precision.',
   'Repaired in the final preparation. No observed search.',file,await hash(file)]);
 }
 for(const r of info.results){
  const p=r.preparation,c=r.calibration,file=path.join(evidence,p.target+'-prepare.json');
  entries.push([`UTMOST-PREP01-20260909-${p.target}`,date,'Dataset preparation',p.target,'PREPARED CONDITIONAL',
   `${p.toas} TOAs; ${p.observing_days} observing days. Phase connection passed. Null reduced chi-squared ${p.null_reduced_chi2.toFixed(3)}.`,
   'Released fixed single-band noise. Calibrated 30-400 days; no observed search or binary support.',file,await hash(file)]);
  const row=before.targets.findIndex(v=>v[0]===p.target)+1;
  if(row<2)throw Error('Selected target missing from master');
  target.getRange(`F${row}:G${row}`).values=[['UTMOST prepared; observed launch awaits direction','TPA EXCLUDED; UTMOST PREPARED CONDITIONAL']];
 }
 const preparation=path.join(evidence,'preparation.json');
 entries.push(['UTMOST-PREP01-20260909-CALIBRATION',date,'Noise-only calibration','Four UTMOST datasets','CALIBRATED CONDITIONAL',
  '16,384 null realizations and 12 deterministic template checks. Fixed-noise 1% four-target allowance, 30-400 days.',
  'Median worst-phase 95% sensitivity: 22.9-50.2 microseconds. This is simulated/analytic sensitivity, not observed detection.',preparation,await hash(preparation)]);
 entries.push(['UTMOST-PREP01-20260909-SCOPE',date,'Source queue','UTMOST DR1','PREPARATION COMPLETE',
  'Four selected datasets prepared; 82 other coverage candidates unprepared. Zero UTMOST observed searches.',
  'Keep private. No launch or binary support authorized. Single-band candidate interpretation requires later deep review.',
  path.join(repo,'docs/UTMOST_PREPARATION01_2026-09-09.md'),await hash(path.join(repo,'docs/UTMOST_PREPARATION01_2026-09-09.md'))]);
 const first=before.work.length+1;
 work.tables.items[0].rows.add(null,entries);
 for(let i=0;i<entries.length;i++){
  const row=first+i;
  work.getRange(`A${row}:I${row}`).copyFrom(work.getRange(`A${first-1}:I${first-1}`),'all');
  work.getRange(`A${row}:I${row}`).values=[entries[i]];
  work.getRange(`A${row}:I${row}`).format.wrapText=true;
  work.getRange(`A${row}:I${row}`).format.autofitRows();
  work.getRange(`B${row}`).setNumberFormat('yyyy-mm-dd');
 }
 overview.getRange('B4').values=[[date]];
 wb.recalculate();
 const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
 const expected=structuredClone(before.targets);
 for(const t of selected){const r=expected.find(v=>v[0]===t);r[5]='UTMOST prepared; observed launch awaits direction';r[6]='TPA EXCLUDED; UTMOST PREPARED CONDITIONAL';}
 if(!equal(expected,target.getUsedRange().values))throw Error('Unexpected target change');
 if(!equal(before.searches,searches.getUsedRange().values))throw Error('Historical search changed');
 if(!equal(before.work,work.getUsedRange().values.slice(0,before.work.length)))throw Error('Historical work log changed');
 if(!equal(before.overviewFormulas,overview.getUsedRange().formulas))throw Error('Overview formulas changed');
 await render('Work log',`C${first+2}:G${first+5}`,'prepared-worklog.png');
 await render('Work log',`C${first+6}:G${first+7}`,'calibration-worklog.png');
 await render('Overview','A1:E15','overview.png');
 const scan=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:20},summary:'Preparation bookkeeping formula check'});
 await fs.writeFile(path.join(output,'formula-check.ndjson'),scan.ndjson);
 await (await SpreadsheetFile.exportXlsx(wb)).save(master+'.pending');
 if(await hash(master)!==beforeHash)throw Error('Master changed during update');
 await fs.rename(master+'.pending',master);
 const receipt={status:'UPDATED',before_sha256:beforeHash,after_sha256:await hash(master),backup,
  target_rows_updated:selected.length,work_log_rows_added:entries.length,search_rows_added:0,
  historical_searches_preserved:true,historical_work_log_preserved:true,operator_notes_preserved:true,
  overview_formulas_preserved:true,overview:overview.getRange('A6:B14').values};
 await fs.writeFile(path.join(evidence,'master-workbook-update.json'),JSON.stringify(receipt,null,2)+'\n');
 console.log(JSON.stringify(receipt,null,2));
}finally{await handle.close();await fs.unlink(lock);}
