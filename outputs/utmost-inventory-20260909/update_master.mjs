// Append UTMOST inventory bookkeeping to the existing master. No scientific runs.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const repo=path.resolve(import.meta.dirname,'../..');
const output=import.meta.dirname;
const master=path.join(repo,'outputs/recherche-master-20260908/Project-Recherche-Master.xlsx');
const evidence=path.join(repo,'results/research/utmost-inventory-20260909/inventory.json');
const hash=async p=>crypto.createHash('sha256').update(await fs.readFile(p)).digest('hex');
const info=JSON.parse(await fs.readFile(evidence,'utf8'));
const beforeHash=await hash(master);
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(master));
const target=wb.worksheets.getItem('Targets'),work=wb.worksheets.getItem('Work log');
const searches=wb.worksheets.getItem('Searches'),overview=wb.worksheets.getItem('Overview');
const before={targets:target.getUsedRange().values,work:work.getUsedRange().values,
 searches:searches.getUsedRange().values,overviewFormulas:overview.getUsedRange().formulas};
const render=async(sheetName,range,name)=>fs.writeFile(path.join(output,name),
 new Uint8Array(await (await wb.render({sheetName,range,scale:1,format:'png'})).arrayBuffer()));
if(process.argv.includes('--refresh-date')){
 const receiptPath=path.join(repo,'results/research/utmost-inventory-20260909/master-workbook-update.json');
 const receipt=JSON.parse(await fs.readFile(receiptPath,'utf8'));
 if(beforeHash!==receipt.after_sha256)throw Error('Master differs from assessment receipt');
 overview.getRange('B4').values=[[new Date('2026-09-09T00:00:00Z')]];
 wb.recalculate();
 await render('Overview','A1:E15','inventory-overview.png');
 await (await SpreadsheetFile.exportXlsx(wb)).save(master+'.pending');
 if(await hash(master)!==beforeHash)throw Error('Master changed during date refresh');
 await fs.rename(master+'.pending',master);
 receipt.after_sha256=await hash(master);receipt.records_through='2026-09-09';
 await fs.writeFile(receiptPath,JSON.stringify(receipt,null,2)+'\n');
 console.log('Updated assessment date; inventory and scientific rows unchanged.');process.exit(0);
}
if(process.argv.includes('--preview')){
 await render('Targets','A689:G693','before-targets.png');
 await render('Work log','C89:G91','before-worklog.png');
 console.log(JSON.stringify({targetRows:before.targets.length,workRows:before.work.length,
  overview:overview.getRange('A6:B14').values}));
 process.exit(0);
}
if(!process.argv.includes('--apply'))throw Error('Use --preview or --apply');
const lock=master+'.update-lock';
const handle=await fs.open(lock,'wx');
try{
 if(await hash(master)!==beforeHash)throw Error('Master changed during import');
 const id='UTMOST-20260909-INVENTORY';
 if(before.work.some(r=>r[0]===id))throw Error('Assessment already registered');
 const backup=path.resolve(repo,'../Recherche Recovery/20260907T223404/master-workbook-history',beforeHash+'.xlsx');
 await fs.mkdir(path.dirname(backup),{recursive:true});await fs.copyFile(master,backup);
 if(await hash(backup)!==beforeHash)throw Error('Workbook backup mismatch');
 const existing=new Set(before.targets.slice(1).map(r=>r[0]));
 const sha=await hash(evidence);
 const additions=info.rows.filter(r=>r.preferred_inventory_variant&&!existing.has(r.target)).map(r=>[
  r.target,r.aliases.join(', ')||null,'NOT_SEARCHED',null,'No observed search',
  r.passes_target_and_coverage_screen?'Needs UTMOST preparation and single-band noise policy':'Retain current-scope exclusion',
  r.passes_target_and_coverage_screen?'UTMOST CONDITIONAL':'UTMOST EXCLUDED',
  r.toas_in_model_window,r.observing_days,r.span_days,'INVENTORIED; NOT SELECTED',
  r.screen_exclusion_reasons.join(', ')||null,
  ...['JBO800','NANOGrav11','EPTA_DR2'].map(k=>r.prior_search_membership[k]?'Present':'Absent from named inventory'),
  null,evidence,sha,r.par_sha256,r.tim_sha256]);
 const first=before.targets.length+1;
 if(additions.length){
  target.tables.items[0].rows.add(null,additions);
  for(let i=0;i<additions.length;i++){
   const row=first+i;
   target.getRange(`A${row}:T${row}`).copyFrom(target.getRange('A693:T693'),'all');
   target.getRange(`A${row}:T${row}`).values=[additions[i]];
  }
  target.getRange(`A${first}:T${first+additions.length-1}`).format.wrapText=true;
  target.getRange(`A${first}:T${first+additions.length-1}`).format.rowHeight=90;
  target.getRange(`H${first}:I${first+additions.length-1}`).setNumberFormat('#,##0');
  target.getRange(`J${first}:J${first+additions.length-1}`).setNumberFormat('0.0');
 }
 const date=new Date('2026-09-09T12:00:00+08:00');
 overview.getRange('B4').values=[[date]];
 const s=info.summary;
 const entries=[
  [id,date,'Source inventory','300 UTMOST pulsars','ASSESSED; NOT SEARCHED',
   `304 variants. ${s.target_coverage_candidates} conditional targets: ${s.candidate_not_previously_searched_targets} unsearched by Recherche and ${s.candidate_previously_searched_targets} with prior searches.`,
   'No selections, calibration or observed runs. Per-dataset coverage and exclusions are in the inventory.',evidence,sha],
  ['UTMOST-20260909-COMPATIBILITY',date,'Compatibility assessment','86 conditional datasets','PREPARATION REQUIRED',
   'All 86 PAR models parse, but global EFAC/EQUAD are ignored by a direct import. All lack useful multi-band epoch coverage.',
   'Bind released clock and time conventions, translate noise, verify phase connection, and define single-band noise treatment before calibration.',
   path.join(repo,'results/research/utmost-inventory-20260909/model-parser-check.json'),
   await hash(path.join(repo,'results/research/utmost-inventory-20260909/model-parser-check.json'))],
  ['UTMOST-20260909-PRIOR-COVERAGE',date,'Prior search cross-match','86 conditional targets','PARTIAL LITERATURE COVERAGE',
   `${s.candidate_absent_from_three_named_prior_inventories} absent from the named JBO800, NG11 and EPTA inventories. This is not proof of an unsearched target.`,
   'Reconcile Kerr 151 and newer searches before novelty claims. Extended variants are not additional pulsars.',evidence,sha],
  ['UTMOST-20260909-SCOPE',date,'Source queue','UTMOST DR1; binary support deferred','ASSESSMENT COMPLETE',
   'Current queue extended with UTMOST. Earlier scientific records and target dispositions remain intact.',
   'Next proposal: a bounded UTMOST adapter and single-band noise preparation. Binary / white-dwarf support remains deferred.',
   path.join(repo,'docs/UTMOST_INVENTORY_2026-09-09.md'),await hash(path.join(repo,'docs/UTMOST_INVENTORY_2026-09-09.md'))]
 ];
 const firstWork=before.work.length+1;
 work.tables.items[0].rows.add(null,entries);
 for(let i=0;i<entries.length;i++){
  const row=firstWork+i;
  work.getRange(`A${row}:I${row}`).copyFrom(work.getRange(`A${firstWork-1}:I${firstWork-1}`),'all');
  work.getRange(`A${row}:I${row}`).values=[entries[i]];
  work.getRange(`A${row}:I${row}`).format.wrapText=true;
  work.getRange(`A${row}:I${row}`).format.autofitRows();
  work.getRange(`B${row}`).setNumberFormat('yyyy-mm-dd');
 }
 wb.recalculate();
 const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
 if(!equal(before.targets,target.getUsedRange().values.slice(0,before.targets.length)))throw Error('Historical targets changed');
 if(!equal(before.searches,searches.getUsedRange().values))throw Error('Historical searches changed');
 if(!equal(before.work,work.getUsedRange().values.slice(0,before.work.length)))throw Error('Historical work log changed');
 if(!equal(before.overviewFormulas,overview.getUsedRange().formulas))throw Error('Overview formulas changed');
 await render('Targets',`A${first}:G${first+3}`,'inventory-targets.png');
 await render('Work log',`C${firstWork}:G${firstWork+3}`,'inventory-worklog.png');
 await render('Overview','A1:E15','inventory-overview.png');
 const inspection=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:20},summary:'UTMOST bookkeeping formula check'});
 await fs.writeFile(path.join(output,'formula-check.ndjson'),inspection.ndjson);
 const pending=master+'.pending';await (await SpreadsheetFile.exportXlsx(wb)).save(pending);
 if(await hash(master)!==beforeHash)throw Error('Master changed during update');
 await fs.rename(pending,master);
 const receipt={status:'UPDATED',before_sha256:beforeHash,after_sha256:await hash(master),backup,
  targets_added:additions.length,work_log_rows_added:entries.length,historical_targets_preserved:true,
  historical_searches_preserved:true,historical_work_log_preserved:true,overview_formulas_preserved:true,
  inventory_sha256:sha,overview:overview.getRange('A6:B14').values};
 await fs.writeFile(path.join(repo,'results/research/utmost-inventory-20260909/master-workbook-update.json'),JSON.stringify(receipt,null,2)+'\n');
 console.log(JSON.stringify(receipt,null,2));
}finally{await handle.close();await fs.unlink(lock);}
