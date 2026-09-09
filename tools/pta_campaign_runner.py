"""Finish the authorized campaign sequentially after the active calibration pass."""
import os
import subprocess
import sys
import time
import traceback
import pta_campaign as p


def progress(stage, **fields):
    p.cal.write(p.ROOT/'runner-progress.json', {'pid':os.getpid(),'stage':stage,'updated_utc':p.mpta.now(),**fields})


def command(*args):
    print('COMMAND', ' '.join(map(str,args)),flush=True)
    subprocess.run(list(map(str,args)),cwd=p.mpta.REPO,check=True)


def finish_docs(closeout):
    report='docs/PTA_CAMPAIGN_01_REPORT_2026-09-09.md'
    master=p.cal.read(p.ROOT/'inpta/master-workbook-update.json')
    readme=p.mpta.REPO/'README.md';text=readme.read_text()
    text=text.replace('**Status — 8 September 2026:**','**Status — 9 September 2026:**')
    text=text.replace('The master now records 220 observed targets and 231 searches or\nrefinements', 'At that closeout, the master recorded 220 observed targets and 231 searches or\nrefinements')
    paragraph=(f"The [PPTA, EPTA and InPTA campaign]({report}) completed **18 source datasets\n"
               f"from 12 isolated pulsars: {closeout['no_trigger_datasets']} NO_TRIGGER results and {closeout['candidate_datasets']} threshold-crossing datasets**.\n"
               f"Candidate diagnostics and cross-source comparisons are documented in the report;\n"
               f"no planet is confirmed. The master now records **{master['counts'][1]} observed targets\n"
               f"and {master['counts'][6]} searches or refinements**. All previous results are preserved.\n\n")
    anchor='The [NANOGrav 15-year batch]'
    if report not in text:text=text.replace(anchor,paragraph+anchor,1)
    readme.write_text(text)
    queue=p.mpta.REPO/'docs/FUTURE_DATA_SOURCES.md';text=queue.read_text()
    text=text.replace('| DR3, 32 pulsars | QUEUED |','| DR3, 32 pulsars | ELIGIBLE POOL COMPLETE: 7 datasets searched; 25 excluded for binary/wide-companion or coverage criteria |')
    text=text.replace('| DR2, 25 pulsars | QUEUED |','| DR2, 25 pulsars | ELIGIBLE POOL COMPLETE: 8 DR2full datasets searched; 17 binary/wide-companion exclusions |')
    if '| 5 | Indian Pulsar' not in text:
        line='| 4 | European Pulsar Timing Array'
        start=text.index(line);end=text.index('\n',start)
        text=text[:end]+ '\n| 5 | Indian Pulsar Timing Array | DR2, 27 pulsars | ELIGIBLE POOL COMPLETE: 3 datasets searched; 24 excluded for binary/wide-companion or coverage criteria | https://github.com/inpta/InPTA.DR2 |'+text[end:]
    text+='\nCombined source-separated campaign closeout: [report](PTA_CAMPAIGN_01_REPORT_2026-09-09.md). The owner authorized these three source batches together; all 18 conditional searches share the same campaign allowance.\n'
    queue.write_text(text)
    method=p.mpta.REPO/'docs/PTA_CAMPAIGN_01_2026-09-09.md';text=method.read_text().replace('Acquisition complete. Preparation and calibration in progress. No campaign observed searches executed at this document\'s initial creation.',f"All four steps are complete. All 18 source datasets were calibrated, frozen and searched. {closeout['no_trigger_datasets']} yielded NO_TRIGGER and {closeout['candidate_datasets']} crossed threshold. Candidate diagnostics, cross-source comparisons and the master workbook are complete. See [combined report](PTA_CAMPAIGN_01_REPORT_2026-09-09.md).")
    method.write_text(text)


def main():
    lock=p.ROOT/'runner.lock'
    with lock.open('x') as f:f.write(str(os.getpid()))
    try:
        parent=int(sys.argv[1])
        progress('WAITING_FOR_CALIBRATION',calibration_pid=parent)
        while not (p.ROOT/'calibration-pass.json').exists():
            try:os.kill(parent,0)
            except ProcessLookupError:raise RuntimeError('Calibration coordinator stopped without its completion record')
            time.sleep(30)
        # The first pass may list a repaired failure. Current per-target receipts
        # and the campaign readiness checks determine whether we can proceed.
        progress('FREEZING')
        command('tools/recherche','pta-campaign','freeze')
        progress('REGISTERING_PREPARATION')
        for source in p.SOURCES:command('tools/recherche','master-workbook',p.ROOT/source,'--pta-preparation')
        completed=0
        for source in p.SOURCES:
            for target in p.cal.read(p.ROOT/source/'selection.json')['selected']:
                progress('OBSERVED_SEARCH',source=source,target=target,completed_datasets=completed)
                command('tools/recherche','pta-campaign','run','--source',source,'--target',target)
                completed+=1
        progress('CANDIDATE_REVIEW',completed_datasets=completed)
        command(sys.executable,p.mpta.REPO/'tools/pta_campaign_review.py')
        progress('WORKBOOK_CLOSEOUT')
        command('tools/recherche','master-workbook',p.ROOT/'inpta','--pta-observed')
        closeout=p.cal.read(p.ROOT/'closeout.json')
        finish_docs(closeout)
        progress('COMPLETE',completed_datasets=completed,candidate_datasets=closeout['candidate_datasets'],no_trigger_datasets=closeout['no_trigger_datasets'],report=closeout['report_path'])
        print('CAMPAIGN COMPLETE',flush=True)
    except BaseException as error:
        progress('NEEDS_DIAGNOSIS',error=str(error))
        traceback.print_exc()
        raise
    finally:lock.unlink(missing_ok=True)

if __name__=='__main__':main()
