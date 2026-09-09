"""Install/check a fresh macOS agent checkout without rewriting historical qualification."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as f:
        value = hashlib.sha256()
        for block in iter(lambda: f.read(1024 * 1024), b''):
            value.update(block)
        return value.hexdigest()


def check():
    python = REPO / '.pixi/envs/default/bin/python'
    operator = REPO / '.agent-venv/bin/python'
    missing = [str(p) for p in [python, operator, Path('/usr/bin/sandbox-exec')] if not p.exists()]
    if platform.system() != 'Darwin':
        missing.append('Supported macOS worker (current scientific lock is osx-64)')
    if missing:
        return {'status': 'SETUP_REQUIRED', 'missing': missing, 'scientific_fits_executed': 0}
    code = '''import json,platform,sys,numpy,scipy,pint,astropy
print(json.dumps({'python':sys.version.split()[0], 'machine':platform.machine(),
'longdouble_nmant':numpy.finfo(numpy.longdouble).nmant,'numpy':numpy.__version__,
'scipy':scipy.__version__,'pint':pint.__version__,'astropy':astropy.__version__}))'''
    environment = json.loads(subprocess.check_output([str(python), '-c', code], text=True))
    if environment['machine'] != 'x86_64' or environment['longdouble_nmant'] != 63 or environment['python'].split('.')[:2] != ['3','11'] or environment['pint'] != '1.1.5':
        raise RuntimeError('Scientific platform/precision differs: ' + json.dumps(environment))
    source_manifest = REPO / 'config/publication-source.json'
    if not source_manifest.exists():
        source_manifest = REPO / 'results/qualification/qualification02-readiness.json'
    expected = json.loads(source_manifest.read_text())['source_sha256']
    actual = {p.relative_to(REPO).as_posix(): digest(p) for p in (REPO / 'src').rglob('*.py')}
    if actual != expected:
        raise RuntimeError('Recorded scientific source differs; inspect the diff')
    version = subprocess.check_output([str(operator), '-c', 'import openpyxl; print(openpyxl.__version__)'], text=True).strip()
    if version != '3.1.5': raise RuntimeError('Operator dependency differs')
    return {'status': 'AGENT_RUNTIME_READY', 'checkout': str(REPO), 'environment': environment,
            'scientific_lock_sha256': digest(REPO / 'pixi.lock'),
            'operator_requirements_sha256': digest(REPO / 'tools/requirements-agent.txt'),
            'source_files_verified': len(expected), 'source_manifest': source_manifest.relative_to(REPO).as_posix(), 'workbook_backend': 'openpyxl 3.1.5',
            'historical_host_qualification_transferred': False, 'observed_inputs_included': False,
            'scientific_fits_executed': 0,
            'next': 'Acquire/restore the selected source inputs, verify their provenance, and follow AGENT_README.md. This is not scientific qualification.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--install', action='store_true')
    mode.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.install:
        if platform.system() != 'Darwin' or not Path('/usr/bin/sandbox-exec').exists():
            parser.error('Current scientific execution requires macOS. A Linux/Windows harness can use an SSH macOS worker; see AGENT_README.md.')
        pixi = os.environ.get('RECHERCHE_PIXI') or shutil.which('pixi')
        if not pixi: parser.error('Install Pixi first, or set RECHERCHE_PIXI to its executable')
        subprocess.run([pixi, 'install', '--locked', '--manifest-path', str(REPO / 'pixi.toml')], check=True)
        python = REPO / '.pixi/envs/default/bin/python'
        operator = REPO / '.agent-venv'
        if not operator.exists():
            subprocess.run([str(python), '-m', 'venv', str(operator)], check=True)
        subprocess.run([str(operator / 'bin/python'), '-m', 'pip', 'install', '--require-hashes',
                        '-r', str(REPO / 'tools/requirements-agent.txt')], check=True)
    result = check()
    print(json.dumps(result, indent=2))
    if result['status'] != 'AGENT_RUNTIME_READY': return 2
    if args.install:
        (REPO / '.agent-setup.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
