"""Reconcile immutable portal downloads; no timing fit, calibration or search."""
import json, pathlib, collections, hashlib, datetime, csv
from decimal import Decimal
REPO=pathlib.Path.cwd(); DATA=REPO.parent/'Project Recherche Data/utmost-ns-inventory-20260909'
AUTH=DATA/'authenticated'; OUT=REPO/'results/research/utmost-ns-authenticated-20260909'
initial=json.loads((REPO/'results/research/utmost-ns-inventory-20260909/inventory.json').read_text())
ew=json.loads((REPO/'results/research/utmost-inventory-20260909/inventory.json').read_text())
EWROOT=REPO.parent/'Project Recherche Data/utmost-inventory-20260909/TimingDataRelease1-e6c36c26b54749d89d29c148da98f0919b3ce5a8'
ewrows={r['target']:r for r in ew['rows'] if r['preferred_inventory_variant']}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def decode(node):
 m=node['ephemerisData']
 for _ in range(4):
  if not isinstance(m,str):break
  m=json.loads(m)
 if not isinstance(m,dict):raise ValueError('Unsupported model serialization')
 return {k.upper():v for k,v in m.items()}
models={}
for p in (AUTH/'linked-models').glob('*.json'):
 n=json.loads(p.read_text());models[n['id']]={'node':n,'fields':decode(n),'path':str(p),'sha256':digest(p)}
missing=[r['portal_name'] for r in initial['rows'] if not (AUTH/('target-'+r['portal_name'])/'receipt.json').exists()]
if missing:raise SystemExit('Incomplete target acquisitions: '+','.join(missing))
if OUT.exists():raise SystemExit('Refusing to overwrite authenticated closeout')
rows=[];all_ids=set();all_physical=set();all_target_rows={};manifest=[];noise_reused=0
for source in initial['rows']:
 target=source['portal_name'];root=AUTH/('target-'+target);receipt=json.loads((root/'receipt.json').read_text())
 rr=[]
 for entry in receipt['pages']:
  p=AUTH/entry['file']
  if digest(p)!=entry['sha256']:raise ValueError('Download hash mismatch')
  manifest.append({'path':str(p),'bytes':p.stat().st_size,'sha256':entry['sha256']})
  rr.extend(x['node'] for x in json.loads(p.read_text())['data']['toa']['edges'])
 if len(rr)!=receipt['rows']:raise ValueError('Download row count mismatch')
 if len({r['id'] for r in rr})!=len(rr):raise ValueError('Duplicate paginated TOA IDs')
 if all_ids.intersection(r['id'] for r in rr):raise ValueError('TOA ID assigned to multiple pulsars')
 all_ids.update(r['id'] for r in rr);all_target_rows[target]=rr
 for r in rr:
  if not isinstance(r['mjd'],str):raise ValueError('MJD precision was not preserved')
  if r['telescope']!='mons' or r['obsNchan']!=1 or r['obsNpol']!=1 or r['nsubType']!='1' or r['dmCorrected']:raise ValueError('Unexpected timing product')
  if Decimal(r['mjd'])<=0 or r['freqMhz']<=0 or r['mjdErr']<=0:raise ValueError('Invalid TOA')
 physical=[(r['archive'],r['mjd'],r['freqMhz'],r['telescope']) for r in rr]
 good=[r for r in rr if r['snr'] is not None and r['snr']>7]
 def coverage(rs):
  ts=[Decimal(r['mjd']) for r in rs]
  return {'toas':len(rs),'observing_days':len({int(t) for t in ts}), 'first_mjd':str(min(ts)) if ts else None,'last_mjd':str(max(ts)) if ts else None,'span_days':float(max(ts)-min(ts)) if ts else None}
 raw=coverage(rr);sn=coverage(good);model_ids=sorted({r['ephemeris']['id'] for r in rr if r['ephemeris']})
 if any(i not in models for i in model_ids):raise ValueError('Linked models missing: '+target)
 binding=[]
 for i in model_ids:
  m=models[i];n=m['node'];f=m['fields']
  generic=n['validFrom'].startswith('1970-01-01') and n['validTo'].startswith('2106-02-07')
  start=datetime.datetime.fromisoformat(n['validFrom']);end=datetime.datetime.fromisoformat(n['validTo'])
  duration=(end-start).total_seconds()/86400
  noise={k:f[k] for k in ['TNGLOBALEF','TNGLOBALEQ','TNREDAMP','TNREDGAM','TNREDC'] if k in f}
  binding.append({'id':i,'sha256':m['sha256'],'valid_from':n['validFrom'],'valid_to':n['validTo'],'generic_placeholder_validity':generic,'actual_validity_span_days':None if generic else duration,'declared_ntoa':f.get('NTOA'),'track':f.get('TRACK'),'tzrsite':f.get('TZRSITE'),'noise_parameters':noise,'fit_flags_or_supplied_pulse_numbers_available':False})
 er=ewrows.get(source['target']);combined=None
 if er and rr:
  dates=[Decimal(raw['first_mjd']),Decimal(raw['last_mjd']),Decimal(er['start_mjd']),Decimal(er['finish_mjd'])]
  overlap=0
  ew_keys=set()
  for line in (EWROOT/er['tim_path']).read_text().splitlines():
   a=line.split()
   if len(a)<5 or line.lstrip().startswith(('C ','#','FORMAT','MODE','INCLUDE')):continue
   try:ew_keys.add((Decimal(a[2]),a[4]))
   except Exception:pass
  overlap=sum((Decimal(r['mjd']),r['telescope']) in ew_keys for r in rr)
  ef={}
  for line in (EWROOT/er['par_path']).read_text().splitlines():
   a=line.split()
   if len(a)>1:ef[a[0].upper()]=a[1]
  equal=[]
  for b in binding:
   for k,v in b['noise_parameters'].items():
    if k in ef:
     try:
      if Decimal(str(v))==Decimal(ef[k]):equal.append(k)
     except Exception:pass
  noise_reused+=bool(equal)
  covering=[b['id'] for b in binding if not b['generic_placeholder_validity'] and Decimal(str(datetime.datetime.fromisoformat(b['valid_from']).timestamp()/86400+40587))<=min(dates) and Decimal(str(datetime.datetime.fromisoformat(b['valid_to']).timestamp()/86400+40587))>=max(dates)]
  combined={'linked_models_covering_full_union_window':covering,'ew_dataset':er['dataset_id'],'ew_toas':er['toas_in_model_window'],'ew_start_mjd':er['start_mjd'],'ew_finish_mjd':er['finish_mjd'],'union_span_days':float(max(dates)-min(dates)),'same_mjd_and_site_as_ew':overlap,'ew_passed_original_coverage_screen':er['passes_target_and_coverage_screen'],'same_numeric_noise_keys_as_ew':sorted(set(equal)),'phase_connected_combined_model_verified':False,'search_ready':False}
 rows.append({'target':source['target'],'portal_name':target,'identity_resolved':source['catalogue_identity_resolved'],'known_binary_or_wide_companion':source['known_binary_or_wide_companion'],'raw_one_channel':raw,'snr_gt7_before_manual_exclusions':sn,'duplicate_physical_toa_rows':len(rr)-len(set(physical)),'linked_models':binding,'combined_ew_ns':combined,'published_manual_rfi_mask_verified':False,'standalone_disposition':'EXCLUDED_SPAN_BELOW_1200_DAYS' if rr else 'NO_ONE_CHANNEL_TOAS','preparation_disposition':'COMBINED_TIMING_PACKAGE_REQUIRED' if combined else 'NO_COMPATIBLE_BASELINE','follow_up_deferred':source['follow_up_deferred']})
# The broad query remains partial and is never counted as a second set of measurements.
partial=[x['node'] for p in (AUTH/'toas-one-channel').glob('page-*.json') for x in json.loads(p.read_text())['data']['toa']['edges']]
partial_by_id={r['id']:r for r in partial};core=['archive','mjd','mjdErr','freqMhz','telescope','snr','ephemeris']
for rr in all_target_rows.values():
 for r in rr:
  if r['id'] in partial_by_id and any(r[k]!=partial_by_id[r['id']][k] for k in core):raise ValueError('Snapshot content changed between broad and target query')
spans=[r['raw_one_channel']['span_days'] for r in rows if r['raw_one_channel']['toas']]
summary={'portal_targets':len(rows),'targets_with_one_channel_toas':sum(r['raw_one_channel']['toas']>0 for r in rows),'raw_toas':len(all_ids),'snr_gt7_before_manual_exclusions':sum(r['snr_gt7_before_manual_exclusions']['toas'] for r in rows),'distinct_linked_models':len({i['id'] for r in rows for i in r['linked_models']}),'raw_span_min_days':min(spans),'raw_span_max_days':max(spans),'standalone_eligible':sum(x>=1200 for x in spans),'targets_with_ew_overlap':sum(r['combined_ew_ns'] is not None for r in rows),'ew_overlap_with_union_span_ge1200':sum(r['combined_ew_ns'] is not None and r['combined_ew_ns']['union_span_days']>=1200 for r in rows),'targets_with_noise_values_equal_to_ew':noise_reused,'isolated_targets_with_nonplaceholder_model_covering_full_union':sum(bool(r['combined_ew_ns'] and r['combined_ew_ns']['linked_models_covering_full_union_window']) and not r['known_binary_or_wide_companion'] for r in rows),'verified_combined_packages':0,'calibrations':0,'observed_searches':0,'partial_download_toas_crosschecked':len(partial),'all_partial_ids_in_complete_download':set(partial_by_id)<=all_ids,'duplicate_physical_toa_rows':sum(r['duplicate_physical_toa_rows'] for r in rows)}
OUT.mkdir()
result={'status':'ACQUIRED_RECONCILED_PREPARATION_BLOCKED_ON_COMBINED_INPUTS','assessed_on':'2026-09-09','source':'UTMOST-NS MONSPSR_TIMING','master_before_sha256':digest(REPO/'outputs/recherche-master-20260908/Project-Recherche-Master.xlsx'),'policy':initial['scope'],'summary':summary,'limitations':['Raw one-channel portal TOAs are not asserted to reproduce the 17,990 cleaned TOAs in Dunn et al. 2025.','No complete publication combined EW+NS model, pulse-count/fit conventions, NS instrument noise binding or manual RFI mask was verified.','The authenticated filePulsarList query returned a permission error; no bypass or project membership change attempted.','Generic 1970-2106 model validity bounds are placeholders, not observation coverage.','J1752 candidate-specific follow-up remains deferred until the first observed run; acquisition includes metadata only for it.'],'rows':rows,'input_manifest':manifest,'linked_model_manifest':[{'path':v['path'],'sha256':v['sha256']} for v in models.values()]}
(OUT/'reconciliation.json').write_text(json.dumps(result,indent=2)+'\n')
with (OUT/'reconciliation.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['target','raw_toas','raw_days','raw_span_days','snr_gt7_toas_unvetted','models','ew_overlap','combined_union_span_days','search_ready','disposition'])
 for r in rows:w.writerow([r['target'],r['raw_one_channel']['toas'],r['raw_one_channel']['observing_days'],r['raw_one_channel']['span_days'],r['snr_gt7_before_manual_exclusions']['toas'],len(r['linked_models']),bool(r['combined_ew_ns']),r['combined_ew_ns']['union_span_days'] if r['combined_ew_ns'] else '',False,r['preparation_disposition']])
print(json.dumps(summary,indent=2))
