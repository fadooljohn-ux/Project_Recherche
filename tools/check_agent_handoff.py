"""Bounded operator checks on temporary workbook copies; no scientific runs."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile

import openpyxl
import agent_workbook as register


def rows(path, name):
    return list(openpyxl.load_workbook(path)[name].values)


def main():
    canonical = register.MASTER
    before = register.digest(canonical)
    source = register.REPO / 'results/observed/ipta-hold-release-20260909/J1939+2134'
    with tempfile.TemporaryDirectory(prefix='recherche-agent-check-') as tmp:
        root = Path(tmp)
        master = root / 'test-master.xlsx'
        shutil.copy2(canonical, master)
        historical = {name: rows(master, name) for name in ['Searches', 'Work log', 'Candidate grades', 'Targets']}
        for candidate in [False, True]:
            batch = root / ('candidate-fixture' if candidate else 'no-trigger-fixture')
            target = batch / 'J1939+2134'
            (target / 'run01').mkdir(parents=True)
            (target / 'prepared').mkdir()
            for name in ['selection.json', 'execution-freeze.json']:
                shutil.copy2(source / name, batch / name)
            shutil.copy2(source / 'receipt.json', target / 'prepared/receipt.json')
            shutil.copy2(source / 'periodogram.npz', target / 'run01/periodogram.npz')
            result = register.read(source / 'result.json')
            # Bind temporary bookkeeping fixtures to their copied publication bytes.
            # Never alter archived science receipts to make their old hashes pass.
            freeze = register.read(batch / 'execution-freeze.json')
            freeze['selection_sha256'] = register.digest(batch / 'selection.json')
            (batch / 'execution-freeze.json').write_text(json.dumps(freeze))
            result['execution_freeze_sha256'] = register.digest(batch / 'execution-freeze.json')
            result['candidate'] = candidate  # bookkeeping branch fixture; not scientific evidence
            result_path = target / 'run01/result.json'
            result_path.write_text(json.dumps(result))
            command = [sys.executable, str(register.REPO / 'tools/agent_workbook.py'), str(batch), '--ipta-observed', '--master', str(master)]
            executed = subprocess.run(command, capture_output=True, text=True)
            if executed.returncode: raise RuntimeError(executed.stderr)
            saved = register.digest(master)
            executed = subprocess.run(command, capture_output=True, text=True)
            if executed.returncode: raise RuntimeError(executed.stderr)
            assert register.digest(master) == saved, 'Idempotent update changed workbook'
            result['peak_statistic'] += 1
            result_path.write_text(json.dumps(result))
            failed = subprocess.run(command, capture_output=True, text=True)
            assert failed.returncode != 0 and register.digest(master) == saved, 'Conflicting result did not fail atomically'
            assert not master.with_name(master.name + '.update-lock').exists()
            if not candidate:
                old = next(r for r in historical['Targets'] if r[0] == 'J1939+2134')
                current = next(r for r in rows(master, 'Targets') if r[0] == old[0])
                assert current[2:5] == old[2:5], 'Prior candidate was demoted by new NO_TRIGGER'
        for name in ['Searches', 'Work log', 'Candidate grades']:
            assert rows(master, name)[:len(historical[name])] == historical[name]
        assert [r[15] for r in rows(master, 'Targets')] == [r[15] for r in historical['Targets']]
        assert rows(master, 'Candidate grades')[-1][2] == 'REVIEW_PENDING'
        evidence = root / 'review.json'
        evidence.write_text(json.dumps({'status': 'DEVELOPMENT_FIXTURE', 'master_before_sha256': register.digest(master)}))
        context = root / 'context.json'
        context.write_text(json.dumps({'evidence': str(evidence), 'entries': [['agent-fixture-review', 'Operator check', 'Temporary copy', 'PASS', 'No scientific execution', 'Discard fixture']]}))
        subprocess.run([sys.executable, str(register.REPO / 'tools/agent_workbook.py'), '--review', str(context), '--master', str(master)], check=True, capture_output=True, text=True)
        assert rows(master, 'Work log')[-1][0] == 'agent-fixture-review'
    assert register.digest(canonical) == before
    print(json.dumps({'status': 'PASS', 'temporary_observed_closeouts': 2, 'duplicate_updates_unchanged': 2,
                      'conflicting_evidence_rejections': 2, 'review_registration': 'PASS',
                      'historical_rows_notes_and_candidate_grades_preserved': True,
                      'canonical_master_sha256': before, 'scientific_runs_executed': 0}, indent=2))


if __name__ == '__main__':
    main()
