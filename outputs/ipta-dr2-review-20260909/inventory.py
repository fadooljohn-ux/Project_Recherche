"""Read-only release and observing-day comparison; never fits or searches TOAs."""
from pathlib import Path
from decimal import Decimal
from collections import Counter, defaultdict
import json, hashlib, csv, sys
REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'tools'))
from utmost_inventory import catalogue, fields
DATA=REPO.parent/'Project Recherche Data'
ROOT=DATA/'ipta-dr2-review-20260909'
RELEASE=next(ROOT.glob('DR2-*'))/'release'
OUT=REPO/'results/research/ipta-dr2-review-20260909'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
cat,aliases=catalogue(DATA/'tpa-batch01-20260908/research/psrcat.db')
master=json.loads((ROOT/'master-before.json').read_text())
manifest={}
# Physical sites, not backend IDs. Verified against pinned PINT observatories.json.
SITES={'ao':'arecibo','aoutc':'arecibo','3':'arecibo','gbt':'gbt','1':'gbt','pks':'parkes','7':'parkes','parkes':'parkes','ncy':'nancay','f':'nancay','nancay':'nancay','g':'effelsberg','eff':'effelsberg','effix':'effelsberg','effelsberg':'effelsberg','jb':'jodrell','jbdfb':'jodrell','jbo':'jodrell','jbroach':'jodrell','8':'jodrell','wsrt':'westerbork','w':'nancay','ncyobs':'nancay','nuppi':'nancay','meerkat':'meerkat','mk':'meerkat','gmrt':'gmrt','u':'gmrt','mo':'molonglo'}
def tim(p,state=None):
    state=state if state is not None else {'time':Decimal(0),'skip':False}
    p=p.resolve();manifest[str(p)]={'sha256':sha(p),'bytes':p.stat().st_size}
    rows=[];commands=Counter()
    for i,line in enumerate(p.read_text().splitlines(),1):
        v=line.split()
        if not v or line.lstrip().startswith(('C','#')) or v[0]=='c':continue
        key=v[0].upper()
        if key=='INCLUDE':
            rr,cc=tim(p.parent/v[1],state);rows+=rr;commands.update(cc);continue
        if key=='END':break
        if key=='TIME':state['time']+=Decimal(v[1]);commands[key]+=1;continue
        if key in ('SKIP','NOSKIP'):state['skip']=key=='SKIP';continue
        if key in ('FORMAT','MODE'):commands[key]+=1;continue
        if key=='-PADD':continue # continuation phase offset, not an extra TOA
        if state['skip']:continue
        try:freq,mjd,err=map(Decimal,v[1:4])
        except Exception as e:raise ValueError(f'Unsupported line {p}:{i}: {line}') from e
        if len(v)<5 or not all(x.is_finite() for x in (freq,mjd,err)) or freq<=0 or err<=0:raise ValueError(f'Invalid TOA {p}:{i}')
        flags={};j=5
        while j<len(v):
            k=v[j];val=v[j+1] if j+1<len(v) and (not v[j+1].startswith('-') or v[j+1][1:2].isdigit() or v[j+1][1:2]=='.') else '1'
            flags[k]=val;j+=2 if val!='1' or (j+1<len(v) and v[j+1]=='1') else 1
        mjd+=(state['time']+Decimal(flags.get('-addsat','0'))+Decimal(flags.get('-to','0')))/Decimal(86400)
        site=SITES.get(v[4].lower(),v[4].lower())
        rows.append({'mjd':mjd,'site':site,'frequency':freq,'flags':flags})
    return rows,commands

def days(rows):return {(r['site'],int(r['mjd'])) for r in rows}
def exact(rows):return {(r['site'],r['mjd'],r['frequency']) for r in rows}
rows=[]
for par in sorted((RELEASE/'VersionB').glob('*/*.TDB.par')):
    f=fields(par.read_text());target=aliases.get(f['PSRJ'][0],f['PSRJ'][0]);c=cat.get(target,{})
    manifest[str(par.resolve())]={'sha256':sha(par),'bytes':par.stat().st_size}
    obs,commands=tim(par.parent/(par.parent.name+'.IPTADR2.tim'))
    ds=days(obs);span=float(max(r['mjd'] for r in obs)-min(r['mjd'] for r in obs))
    reasons=[]
    if 'BINARY' in f or 'BINARY' in c or 'PB' in c:reasons.append('BINARY_OR_KNOWN_COMPANION')
    if target=='J1024-0719' and not reasons:reasons.append('KNOWN_WIDE_STELLAR_COMPANION')
    if span<1200:reasons.append('SPAN_LT_1200_DAYS')
    if len({d for s,d in ds})<40:reasons.append('OBSERVING_DAYS_LT_40')
    prior=[x for x in master['Searches'][1:] if x[1]==target]
    r={'target':target,'toa_count':len(obs),'declared_ntoa':int(f['NTOA'][0]),'span_days':span,'observing_days':len({d for s,d in ds}),'site_days':len(ds),'mjd_min':str(min(x['mjd'] for x in obs)),'mjd_max':str(max(x['mjd'] for x in obs)),'sites':dict(Counter(x['site'] for x in obs)),'pta_toas':dict(Counter(x['flags'].get('-pta','UNLABELED') for x in obs)),'selection_exclusions':reasons,'prior_search_ids':[x[0] for x in prior],'conventions':{k:f[k][0] for k in ('UNITS','TIMEEPH','DILATEFREQ','T2CMETHOD','CLK','EPHEM','PLANET_SHAPIRO','CORRECT_TROPOSPHERE')},'commands':dict(commands),'parameter_counts':dict(Counter(l.split()[0].upper() for l in par.read_text().splitlines() if l.split())),'par':str(par.resolve())}
    if 'BINARY_OR_KNOWN_COMPANION' not in reasons and 'KNOWN_WIDE_STELLAR_COMPANION' not in reasons:
        old=[];paths=[]
        for rec in prior:
            run=Path(rec[19]);orig=run.parent.parent/'original'
            p=orig/(target+'.tim')
            if not p.exists() and target=='J1939+2134' and rec[0].startswith('B1937-'):
                p=DATA/'operational-20260908/controlled/nanograv15yr-v2.1.0/wideband/tim/B1937+21_PINT_20230131.wb.tim'
            if not p.exists():raise FileNotFoundError(f'Missing prior input for {rec[0]}: {p}')
            if str(p) in paths:continue
            pp,_=tim(p);old+=pp;paths.append(str(p))
        od=days(old);oe=exact(old)
        # LEAP combines five European telescopes; conservatively mark all as possible overlap.
        for site,day in list(od):
            if site=='leap':
                od.update((s,day) for s in ('effelsberg','jodrell','nancay','westerbork','sardinia'))
        unmatched={(s,d) for s,d in ds if not any((s,d+offset) in od for offset in (-1,0,1))}
        r.update(prior_tim_paths=paths,prior_sites=sorted({s for s,d in od}),exact_site_mjd_frequency_matches=sum((o['site'],o['mjd'],o['frequency']) in oe for o in obs),site_days_without_prior_match_within_one_day=len(unmatched),new_site_days_by_site=dict(Counter(s for s,d in unmatched)),prior_mjd_min=str(min(o['mjd'] for o in old)),prior_mjd_max=str(max(o['mjd'] for o in old)))
        groups={o['flags'].get('-group') for o in obs};noise={k:[] for k in ('TNEF','TNEQ','TNECORR')}
        for l in par.read_text().splitlines():
            v=l.split()
            if v and v[0] in noise:noise[v[0]].append(v[2])
        r['noise_groups_missing_efac']=sorted(groups-set(noise['TNEF']))
        r['noise_groups_missing_equad']=sorted(groups-set(noise['TNEQ']))
    rows.append(r)
for p in (RELEASE/'clock').iterdir():
    if p.is_file():manifest[str(p.resolve())]={'sha256':sha(p),'bytes':p.stat().st_size}
singles=[r for r in rows if 'prior_tim_paths' in r]
eligible=[r for r in rows if not r['selection_exclusions']]
summary={'release_targets':len(rows),'binary_models':sum('BINARY' in r['parameter_counts'] for r in rows),'isolated_targets':len(singles),'isolated_coverage_eligible':len(eligible),'new_isolated_identities':sum(not r['prior_search_ids'] for r in singles),'compatible_without_timing_adapter':0,'eligible_with_unmatched_site_days':sum(r['site_days_without_prior_match_within_one_day']>0 for r in eligible),'calibrations_launched':0,'searches_launched':0}
out={'scope':'COMPATIBILITY_AND_OVERLAP_REVIEW_ONLY','master_before_sha256':json.loads((ROOT/'baseline.json').read_text())['master_sha256'],'acquisition':json.loads((ROOT/'acquisition.json').read_text()),'summary':summary,'overlap_method':'Active INCLUDEs only; cumulative TIME, addsat and to applied in Decimal; site-day matching within +/-1 day is conservative possible observation overlap, not proof of duplicate TOAs. Backend aliases effix/jbroach are grouped with their physical telescope; LEAP dates mark possible overlap for all five member sites. Original retained inputs may include rows excluded downstream, so unmatched counts are lower-bound opportunities. Exact match uses physical site, MJD and frequency only, not independent data claims.','rows':rows}
(OUT/'inventory.json').write_text(json.dumps(out,indent=2)+'\n')
(OUT/'input-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
with (OUT/'isolated-targets.csv').open('w') as f:
    keys=['target','toa_count','span_days','observing_days','site_days','site_days_without_prior_match_within_one_day','exact_site_mjd_frequency_matches','selection_exclusions']
    w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(singles)
print(json.dumps(summary,indent=2))
for r in singles:print(r['target'],r['toa_count'],round(r['span_days'],1),r['observing_days'],r['site_days_without_prior_match_within_one_day'],r['new_site_days_by_site'],r['selection_exclusions'])
