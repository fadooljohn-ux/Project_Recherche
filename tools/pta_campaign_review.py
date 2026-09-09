"""Consolidate consumed campaign grids; bounded fixed-frequency candidate diagnostics."""
from pathlib import Path
import json
import numpy as np
from scipy.linalg import solve_triangular
import pta_campaign as campaign
from pulsar_pilot.pilot1_runtime import prepare_covariance_gls_scanner

cal, mpta, ROOT = campaign.cal, campaign.mpta, campaign.ROOT
REPORT = mpta.REPO / 'docs/PTA_CAMPAIGN_01_REPORT_2026-09-09.md'
EVIDENCE = mpta.REPO / 'results/research/pta-campaign01-20260908'


def fixed_fit(arrays, residuals, mask, frequency, epoch):
    rows = np.flatnonzero(mask)
    if len(rows) < 20:
        return {'status': 'INSUFFICIENT_ROWS', 'toas': len(rows)}
    covariance = arrays['covariance'][np.ix_(rows, rows)]
    design = arrays['design'][rows]
    scanner = prepare_covariance_gls_scanner(covariance, design, arrays['times'][rows], np.array([frequency]), epoch)
    if len(rows) <= scanner.timing_design_rank:
        return {'status':'UNIDENTIFIABLE','toas':len(rows),'reason':'No residual degrees of freedom after nuisance projection'}
    condition = float(scanner.template_condition_numbers[0])
    if not np.isfinite(condition) or condition > 1e10:
        return {'status':'UNIDENTIFIABLE','toas':len(rows)}
    y = scanner.whiten_and_project(residuals[rows])
    w = scanner.projected_whitened_templates[:,0]
    gram_inv = scanner.template_gram_pseudoinverse[0]
    beta = gram_inv @ (w.T @ y)
    error = y - w @ beta
    return {'status':'FIT','toas':len(rows),'period_days':1/frequency,'statistic':float(y@y-error@error),
            'amplitude_us':float(np.linalg.norm(beta)*1e6),'coefficients_us':(beta*1e6).tolist(),
            'coefficient_covariance_us2':(gram_inv*1e12).tolist(),'null_chi2':float(y@y),
            'null_dof':len(rows)-scanner.timing_design_rank,'null_reduced_chi2':float(y@y)/(len(rows)-scanner.timing_design_rank)}


def review_candidate(source, target, result, root=None):
    root = root or ROOT/source/target
    destination = root/'review01.json'
    if destination.exists():
        saved = cal.read(destination)
        assert saved['original_result_sha256'] == cal.digest(root/'run01/result.json')
        return saved
    profile, arrays = cal.load_profile(root/'profile/profile.json')
    with np.load(root/'prepared/observed.npz') as a: residuals=a['residuals']
    with np.load(root/'prepared/metadata.npz') as a: radio=a['radio']
    times=arrays['times']; frequency=1/result['peak_period_days']; epoch=profile['reference_epoch_mjd_tdb']
    middle=(times.min()+times.max())/2
    masks={'first_half':times<middle,'second_half':times>=middle,'below_1400_MHz':radio<1400,'at_or_above_1400_MHz':radio>=1400}
    fits={name:fixed_fit(arrays,residuals,mask,frequency,epoch) for name,mask in masks.items()}
    scanner=prepare_covariance_gls_scanner(arrays['covariance'],arrays['design'],times,np.array([frequency]),epoch)
    y=scanner.whiten_and_project(residuals)
    day=int(np.floor(times[np.argmax(np.abs(y))]))
    del scanner
    fits['remove_largest_whitened_residual_day']=fixed_fit(arrays,residuals,np.floor(times)!=day,frequency,epoch)
    output={'source':source,'target':target,'created_utc':mpta.now(),'original_result_sha256':cal.digest(root/'run01/result.json'),
            'original_peak_period_days':result['peak_period_days'],'removed_day_mjd_tdb':day,'removed_toas':int(np.sum(np.floor(times)==day)),
            'diagnostics':fits,'noise_adequacy_flag':result['noise_adequacy_flag'],
            'disposition':'INCONCLUSIVE_NOISE_SENSITIVE' if result['noise_adequacy_flag'] else 'UNCONFIRMED_PERIODIC_CANDIDATE',
            'scope':'Descriptive fixed-frequency fits at the consumed grid peak; no new grid or threshold calibration. Split statistics are not judged against the full-data threshold.',
            'limitations':'Fixed source noise, source timing conversion and finite observing span; no planet confirmation or independent orbital validation.',
            'code_sha256':cal.digest(__file__)}
    cal.write(destination,output)
    cal.write(EVIDENCE/(source+'-'+target+'-review.json'),output)
    print('REVIEWED',source,target,output['disposition'],flush=True)
    return output


def main():
    EVIDENCE.mkdir(exist_ok=True,parents=True)
    intake=cal.read(ROOT/'intake.json'); rows=[]; reviews=[]
    replacement_path=ROOT/'replacement-closeout.json'
    replacements=cal.read(replacement_path) if replacement_path.exists() else None
    for item in intake['datasets']:
        source,target=item['source'],item['target'];root=ROOT/source/target
        replacement=next((r for r in replacements['datasets'] if r['source']==source and r['target']==target),None) if replacements else None
        if replacement:
            assert cal.digest(replacement['superseded_result_path'])==replacement['superseded_result_sha256']
            root=Path(replacements['data_root'])/source/target
            assert cal.digest(root/'run01/result.json')==replacement['replacement_result_sha256']
        result=cal.read(root/'run01/result.json');receipt=cal.read(root/'prepared/receipt.json')
        assert result['execution_freeze_sha256']==cal.digest(root.parent/'execution-freeze.json')
        assert result['periodogram_sha256']==cal.digest(root/'run01/periodogram.npz')
        rows.append({**item,**result,'data_root':str(root),'toas':receipt['toas'],'epochs':receipt['epochs'],'span_days':receipt['span_days'],'maximum_period_days':receipt['policy']['maximum_period_days']})
        if result['candidate']: reviews.append(review_candidate(source,target,result,root))
    comparisons=[]
    for target in sorted({r['target'] for r in rows}):
        target_rows=[r for r in rows if r['target']==target]
        if len(target_rows)<2: continue
        for candidate in [r for r in target_rows if r['candidate']]:
            frequency=1/candidate['peak_period_days']
            for other in target_rows:
                if other['source']==candidate['source']: continue
                with np.load(Path(other['data_root'])/'run01/periodogram.npz') as grid:
                    i=int(np.argmin(np.abs(grid['frequencies']-frequency)))
                    comparisons.append({'target':target,'candidate_source':candidate['source'],'candidate_period_days':candidate['peak_period_days'],
                      'comparison_source':other['source'],'nearest_grid_period_days':float(1/grid['frequencies'][i]),'nearest_grid_statistic':float(grid['statistic'][i]),
                      'eligible':bool(grid['eligible'][i]) and bool(grid['frequencies'].min() <= frequency <= grid['frequencies'].max()),
                      'within_comparison_period_range':bool(grid['frequencies'].min() <= frequency <= grid['frequencies'].max()),
                      'comparison_threshold':other['threshold'],'comparison_strongest_period_days':other['peak_period_days'],
                      'scope':'Existing grid comparison only; nearest-bin statistic is not an independent search or phase-coherence test.'})
    original=intake['historical_result_hashes']
    for path,sha in original.items(): assert cal.digest(path)==sha
    summary={'campaign':'pta-campaign01-20260908','completed_utc':mpta.now(),'status':'COMPLETE','datasets':len(rows),'unique_targets':len({r['target'] for r in rows}),
             'candidate_datasets':sum(r['candidate'] for r in rows),'candidate_targets':len({r['target'] for r in rows if r['candidate']}),
             'no_trigger_datasets':sum(not r['candidate'] for r in rows),'confirmed_planets':0,'rows':rows,'reviews':reviews,'cross_source_comparisons':comparisons,
             'campaign_freeze_sha256':cal.digest(ROOT/'campaign-freeze.json'),'historical_json_records_preserved':len(original),
             'superseded_import_attempts':replacements['datasets'] if replacements else [],
             'replacement_closeout_sha256':cal.digest(replacement_path) if replacements else None,
             'report_path':str(REPORT),'limitations':'One valid conditional circular search per source dataset; sensitivity is not a posterior planet upper limit.'}
    lines=['# A source-separated search of PPTA, EPTA and InPTA timing data','', 'Project Recherche · Campaign 01 · 9 September 2026','',
      '## Abstract','',f"We searched {len(rows)} public timing datasets covering 12 isolated pulsars. The seven PPTA DR3, eight EPTA DR2full and three InPTA DR2 datasets were calibrated with a shared 1% conditional false-alarm allowance. {summary['no_trigger_datasets']} datasets produced no qualifying trigger and {summary['candidate_datasets']} crossed their frozen thresholds. No planet is confirmed by this campaign.",'',
      '## Data and method','',
      'Each source was processed separately with its released timing model, clock corrections and available noise terms. EPTA DR2full+ was excluded to avoid including its InPTA observations twice. The latest Parkes revision was reconciled against the original files; all seven selected PAR/TIM pairs were identical. InPTA DR2 was pinned to its source commit. All original observations remain outside Git, with input and output hashes in the campaign receipts.','',
      'A circular sinusoidal timing delay was searched from 30 days to the smaller of 2,000 days and half the observing span. Timing, astrometry and dispersion/instrument nuisance parameters were projected with the existing covariance GLS runtime. For each dataset, 4,096 fixed-noise simulations established calibration diagnostics. The trigger threshold is at least 2 ln(18 F / 0.01), where F is the full number of grid frequencies; a larger empirical threshold is retained if necessary. This union bound does not require the 18 datasets to be independent. Projection masks and sensitivity were frozen before the observed searches.','',
      'The quoted amplitude sensitivity is the median worst-phase circular on-grid amplitude needed for 95% detection probability under the fixed covariance. It is not a posterior upper limit on planets. No observed peak was used to select the original period grids or thresholds.','',
      ('Three initial EPTA attempts were invalidated by an import defect found during review: uppercase-C excluded rows were accepted as observations, and two released J1730 site-arrival offsets were ignored. J1730-2304, J1744-1134 and J1911+1347 were re-prepared, calibrated and searched in separate replacement directories using the corrected Tempo2 conventions. The 18 valid results below use those replacements. All three original attempts, including their two spurious threshold crossings, remain unchanged in the evidence and workbook history. The correction is based on source syntax, not observed-peak selection; the period policy and 18-dataset allowance remain fixed.' if replacements else 'Initial pass: any subsequently identified import corrections must supersede the affected results before final scientific interpretation.'),'',
      '## Dataset results','',
      '| Source | Pulsar | TOAs | Peak period (d) | Statistic | Threshold | Peak amplitude (µs) | Null reduced χ² | Outcome |',
      '|---|---|---:|---:|---:|---:|---:|---:|---|']
    for r in rows:
        lines.append(f"| {r['source'].upper()} | {r['target']} | {r['toas']} | {r['peak_period_days']:.3f} | {r['peak_statistic']:.3f} | {r['threshold']:.3f} | {r['peak_amplitude_us']:.4f} | {r['null_reduced_chi2']:.3f} | {r['status']} |")
    lines+=['','The peak is the strongest eligible grid cell, including for NO_TRIGGER datasets. A large null reduced chi-square flags a mismatch with the fixed noise/timing model and limits interpretation of its conditional threshold.','',
      '## Candidate review','']
    if not reviews: lines+=['No threshold-crossing candidate required additional fixed-frequency review.']
    for review in reviews:
        lines += [f"### {review['target']} ({review['source'].upper()})",'',f"Disposition: **{review['disposition']}**. The original grid peak is {review['original_peak_period_days']:.3f} days. We held this period fixed and fitted the time halves, radio-frequency subsets, and a sample excluding the day containing the largest whitened null residual. These are diagnostic fits, with no new grid search or re-use of the full-data threshold for a subset.",'','| Diagnostic | TOAs | Statistic | Amplitude (µs) |','|---|---:|---:|---:|']
        for name,f in review['diagnostics'].items():
            statistic=f"{f['statistic']:.3f}" if f['status']=='FIT' else f['status']
            amplitude=f"{f['amplitude_us']:.4f}" if f['status']=='FIT' else '—'
            lines.append(f"| {name.replace('_',' ')} | {f['toas']} | {statistic} | {amplitude} |")
        lines+=['',f"The removed day was TDB MJD {review['removed_day_mjd_tdb']} ({review['removed_toas']} TOAs). A candidate remains unconfirmed; these diagnostics do not establish a planetary orbit.",'']
    lines+=['## Cross-source comparison','', 'The 18 datasets represent 12 distinct pulsars. Source overlap is retained in the workbook as separate search records, not as additional unique targets.']
    if comparisons:
        lines+=['','| Pulsar | Candidate source / period (d) | Other source | Nearest saved cell (d) | Statistic / threshold | Eligible |','|---|---|---|---:|---|---|']
        for c in comparisons: lines.append(f"| {c['target']} | {c['candidate_source'].upper()} / {c['candidate_period_days']:.3f} | {c['comparison_source'].upper()} | {c['nearest_grid_period_days']:.3f} | {c['nearest_grid_statistic']:.3f} / {c['comparison_threshold']:.3f} | {c['eligible']} |")
        lines+=['','Different durations, sampling and sensitivity can produce different outcomes. Nearest-grid comparisons are descriptive and do not establish phase coherence or an independent planet confirmation.']
    else: lines+=['','No candidate required a same-period cross-source check. All overlapping source results remain individually tabulated above.']
    lines+=['','## Limits and reproducibility','',
      'Noise amplitudes and spectral slopes are treated as fixed. InPTA DMX models provide EFAC scaling but no complete correlated-noise model; its thresholds are therefore conditional on a more limited noise description. PINT uses approximate TCB-to-TDB conversion followed here by linear nuisance projection, rather than a newly converged nonlinear timing solution. Those limitations matter especially for any flagged candidate.','',
      'The adapter normalizes Tempo2 formatting and phase flags, retains the source-specific clock corrections, handles Parkes band noise, converts EPTA DM amplitude units, and implements the published EFAC/EQUAD ordering. Preparation errors and earlier preparation artifacts were retained. Direct covariance checks and noiseless circular-signal recovery checks verify the new adapter; historical formal qualification was not rerun.','',
      f"All {len(original)} historical JSON result/evidence files in the intake baseline retain their original hashes. The campaign freeze, 18 consumed terminal records and any diagnostic reviews are retained. The master workbook preserves prior searches, including the J1453+1902 noise-sensitive candidate review.",'',
      '## References','',
      '- [PPTA DR3 data and analysis](https://github.com/danielreardon/PPTA-DR3); [CSIRO data release](https://doi.org/10.25919/j4xr-wp05).',
      '- [EPTA DR2 data, noise and clock files](https://doi.org/10.5281/zenodo.8164425); [customised noise models](https://arxiv.org/abs/2306.16225).',
      '- [InPTA DR2](https://github.com/inpta/InPTA.DR2), commit e2806fcb2c238ec38dd80784dfcb1e6c82f54728.',
      '- [Campaign method and compatibility notes](PTA_CAMPAIGN_01_2026-09-09.md).','']
    REPORT.write_text('\n'.join(lines));summary['report_sha256']=cal.digest(REPORT)
    cal.write(ROOT/'closeout.json',summary);cal.write(EVIDENCE/'closeout.json',summary)
    print(json.dumps({k:summary[k] for k in ['status','datasets','unique_targets','candidate_datasets','no_trigger_datasets','confirmed_planets']}),flush=True)

if __name__=='__main__': main()
