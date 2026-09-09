// Workbook-only intake closeout. Imports and preserves the canonical master.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {FileBlob, SpreadsheetFile} from '@oai/artifact-tool';
const out = import.meta.dirname;
const repo = path.resolve(out, '../..');
const master = path.join(repo, 'outputs/recherche-master-20260908/Project-Recherche-Master.xlsx');
const reviewArg = process.argv.indexOf('--review');
const review = reviewArg < 0 ? null : JSON.parse(await fs.readFile(process.argv[reviewArg+1], 'utf8'));
const authenticated = process.argv.includes('--authenticated') || Boolean(review);
const evidence = review ? path.resolve(repo, review.evidence) : path.join(repo, authenticated ? 'results/research/utmost-ns-authenticated-20260909/reconciliation.json' : 'results/research/utmost-ns-inventory-20260909/inventory.json');
const previewOut = review ? path.dirname(path.resolve(process.argv[reviewArg+1])) : out;
const receiptPath = path.join(path.dirname(evidence), 'master-workbook-update.json');
const hash = async p => crypto.createHash('sha256').update(await fs.readFile(p)).digest('hex');
const info = JSON.parse(await fs.readFile(evidence, 'utf8'));
const beforeHash = await hash(master);
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(master));
const sheets = Object.fromEntries(['Overview','Targets','Searches','Work log','Candidate grades'].map(n => [n, wb.worksheets.getItem(n)]));
const before = Object.fromEntries(Object.entries(sheets).map(([n,s]) => [n, {values:s.getUsedRange().values, formulas:s.getUsedRange().formulas}]));
const work = sheets['Work log'], targets = sheets.Targets;
const render = async (sheetName, range, file) => fs.writeFile(path.join(previewOut,file),
  new Uint8Array(await (await wb.render({sheetName,range,scale:1,format:'png'})).arrayBuffer()));
if (process.argv.includes('--preview')) {
  await render('Targets','A741:G744','before-targets.png');
  await render('Work log','C130:G131','before-worklog.png');
  console.log(JSON.stringify({overview:sheets.Overview.getRange('A6:B14').values, targetRows:before.Targets.values.length}));
  process.exit(0);
}
if (!process.argv.includes('--apply')) throw Error('Use --preview or --apply');
if (beforeHash !== info.master_before_sha256) throw Error('Master changed since intake snapshot');
if (before['Work log'].values.some(r => r[0] === (review ? review.entries[0][0] : authenticated ? 'UTMOST-NS-20260909-AUTH-ACQUIRED' : 'UTMOST-NS-20260909-INVENTORY'))) throw Error('Intake already registered');
const lock = master+'.update-lock', handle = await fs.open(lock,'wx');
try {
  const backup = path.resolve(repo,'../Recherche Recovery/20260907T223404/master-workbook-history',beforeHash+'.xlsx');
  await fs.mkdir(path.dirname(backup),{recursive:true}); await fs.copyFile(master,backup);
  if (await hash(backup) !== beforeHash) throw Error('Backup mismatch');
  const sha = await hash(evidence);
  const known = new Set(before.Targets.values.slice(1).map(r=>r[0]));
  const additions = authenticated ? [] : info.rows.filter(r=>r.catalogue_identity_resolved&&!known.has(r.target)).map(r=>[
    r.target,r.aliases.join(', ')||null,'NOT_SEARCHED',null,'No observed search',
    'Obtain timing inputs; assess combined coverage','UTMOST-NS INPUTS PENDING',
    null,null,r.span_days_from_utc,'NOT SELECTED',
    r.standalone_disposition,null,null,null,null,evidence,sha,null,null]);
  if(additions.length!==(authenticated ? 0 : 11)) throw Error('Unexpected new identity count');
  const firstTarget=before.Targets.values.length+1;
  if(additions.length) targets.tables.items[0].rows.add(null,additions);
  for(let i=0;i<additions.length;i++){
    const row=firstTarget+i;
    targets.getRange(`A${row}:T${row}`).copyFrom(targets.getRange('A744:T744'),'all');
    targets.getRange(`A${row}:T${row}`).values=[additions[i]];
    targets.getRange(`A${row}:T${row}`).format.wrapText=true;
    targets.getRange(`A${row}:T${row}`).format.rowHeight=90;
    targets.getRange(`J${row}`).setNumberFormat('0.0');
  }
  const date=new Date('2026-09-09T00:00:00Z');
  const doc=path.join(repo,authenticated ? 'docs/UTMOST_NS_AUTHENTICATED_INTAKE_2026-09-09.md' : 'docs/UTMOST_NS_INTAKE_2026-09-09.md');
  const entries=review ? review.entries.map(r=>[r[0],date,...r.slice(1),evidence,sha]) : authenticated ? [
    ['UTMOST-NS-20260909-AUTH-ACQUIRED',date,'Input acquisition','MONSPSR_TIMING one-channel TOAs','ACQUIRED',
      `${info.summary.raw_toas.toLocaleString()} raw TOAs from ${info.summary.targets_with_one_channel_toas} targets; ${info.summary.distinct_linked_models} linked models. All 174 target queries closed.`,
      'Full-precision arrival times saved outside Git; partial broad-query attempt retained. Temporary API token revoked.',evidence,sha],
    ['UTMOST-NS-20260909-AUTH-RECONCILED',date,'Coverage assessment','UTMOST-NS and retained EW DR1','NO STANDALONE ELIGIBLE DATASETS',
      `${info.summary.targets_with_ew_overlap} EW overlaps; ${info.summary.ew_overlap_with_union_span_ge1200} raw unions reach 1,200 days. None has a verified complete combined timing package.`,
      'Shared EW data are previously used measurements, not independent confirmation. Raw S/N cuts do not reproduce the published manual exclusions.',evidence,sha],
    ['UTMOST-NS-20260909-AUTH-INPUT-GAP',date,'Preparation assessment','Representative isolated-pulsar models','COMBINED TIMING INPUTS REQUIRED',
      'No isolated linked model has a nonplaceholder validity window covering its full EW+NS union; publication pulse-count, fit and instrument-noise bindings remain unverified.',
      'Portal file index denied access. Obtain analysis-ready combined PAR/TIM/noise and exclusion products; request draft saved but not sent.',doc,await hash(doc)],
    ['UTMOST-NS-20260909-AUTH-SCOPE',date,'Campaign state','UTMOST-NS four-step route','AUTHORIZED; NOT LAUNCHED',
      'Acquisition and raw-data reconciliation complete. No calibration, observed search or J1752 candidate-specific follow-up performed.',
      'Resume with the missing combined inputs. Preserve period range, duration criterion and deferred binary support.',doc,await hash(doc)]
  ] : [
    ['UTMOST-NS-20260909-INVENTORY',date,'Source inventory','174 portal targets','METADATA INVENTORIED',
      '33,361 observations; 173 resolved identities; 11 new master identities. J1357-62 unresolved.',
      'Counts are portal observations, not verified TOAs. Preserve source snapshot.',evidence,sha],
    ['UTMOST-NS-20260909-COVERAGE',date,'Coverage assessment','174 portal targets','NO STANDALONE ELIGIBLE DATASETS',
      'Spans 99-819 days; all below 1,200 days. 104 previously searched targets; 146 overlap EW DR1.',
      'Combined EW+NS eligibility awaits complete timing inputs. Binary support deferred.',evidence,sha],
    ['UTMOST-NS-20260909-ACCESS',date,'Input acquisition','UTMOST-NS timing package','AWAITING PORTAL LOGIN',
      'Anonymous raw-TOA API denied access. Official NS clock acquired; combined PAR/TIM/noise package unverified.',
      'Use authenticated portal access or obtain publication timing products from authors.',doc,await hash(doc)],
    ['UTMOST-NS-20260909-SCOPE',date,'Campaign state','UTMOST-NS four-step route','AUTHORIZED; NOT LAUNCHED',
      'No calibration, observed search or candidate follow-up performed. Existing scientific records preserved.',
      'Resume preparation when inputs meet scope. J1752 follow-up deferred until first observed run completes.',doc,await hash(doc)]
  ];
  // Optional closeout routing for already-known identities. Prior scientific
  // status, result IDs and operator notes remain untouched.
  for(const update of review?.target_updates??[]){
    const index=before.Targets.values.findIndex(r=>r[0]===update.target);
    if(index<1) throw Error('Closeout target absent: '+update.target);
    for(const [column,value] of Object.entries({F:update.next_step,G:update.dataset_status,Q:evidence,R:sha})){
      targets.getRange(`${column}${index+1}`).values=[[value]];
    }
    targets.getRange(`F${index+1}:G${index+1}`).format.wrapText=true;
    targets.getRange(`A${index+1}:T${index+1}`).format.autofitRows();
  }
  const firstWork=before['Work log'].values.length+1;
  work.tables.items[0].rows.add(null,entries);
  for(let i=0;i<entries.length;i++){
    const row=firstWork+i;
    work.getRange(`A${row}:I${row}`).copyFrom(work.getRange('A131:I131'),'all');
    work.getRange(`A${row}:I${row}`).values=[entries[i]];
    work.getRange(`A${row}:I${row}`).format.wrapText=true;
    work.getRange(`A${row}:I${row}`).format.rowHeight=100;
    work.getRange(`B${row}`).setNumberFormat('yyyy-mm-dd');
  }
  wb.recalculate();
  const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
  for(const [n,s] of Object.entries(sheets)){
    const values=s.getUsedRange().values;
    const expected=before[n].values.map(r=>r.slice());
    if(n==='Targets')for(const update of review?.target_updates??[]){
      const index=expected.findIndex(r=>r[0]===update.target);
      for(const [column,value] of [[5,update.next_step],[6,update.dataset_status],[16,evidence],[17,sha]]) expected[index][column]=value;
    }
    if(n!=='Overview'&&!equal(expected,values.slice(0,before[n].values.length))) throw Error(`Historical ${n} changed`);
    if(!equal(before[n].formulas,s.getUsedRange().formulas.slice(0,before[n].formulas.length))) throw Error(`Historical ${n} formulas changed`);
  }
  if(!authenticated) await render('Targets',`A${firstTarget}:G${firstTarget+2}`,'intake-targets.png');
  await render('Work log',`C${firstWork}:G${firstWork+3}`,authenticated ? 'authenticated-worklog.png' : 'intake-worklog.png');
  if(!authenticated) await render('Overview','A1:E15','intake-overview.png');
  const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:20},summary:'Intake workbook formula scan'});
  await fs.writeFile(path.join(previewOut,authenticated ? 'authenticated-formula-check.ndjson' : 'formula-check.ndjson'),errors.ndjson);
  await (await SpreadsheetFile.exportXlsx(wb)).save(master+'.pending');
  if(await hash(master)!==beforeHash)throw Error('Master changed during update');
  await fs.rename(master+'.pending',master);
  const receipt={status:'UPDATED',before_sha256:beforeHash,after_sha256:await hash(master),backup,
    inventory_sha256:sha,targets_added:additions.length,work_log_rows_added:entries.length,searches_added:0,
    historical_targets_preserved:!(review?.target_updates?.length),
    target_routing_updates:review?.target_updates?.length??0,
    historical_target_science_preserved:true,historical_searches_preserved:true,historical_work_log_preserved:true,
    candidate_grades_preserved:true,overview:sheets.Overview.getRange('A6:B14').values};
  await fs.writeFile(receiptPath,JSON.stringify(receipt,null,2)+'\n');
  console.log(JSON.stringify(receipt,null,2));
} finally {await handle.close();await fs.unlink(lock);}
