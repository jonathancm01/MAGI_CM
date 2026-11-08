"""Compare two project results using the same explicit local verification scripts."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time


def compare(single, council, checks, timeout=120):
    folders = [Path(folder).resolve(strict=True) for folder in (single, council)]
    scripts = [Path(check).resolve(strict=True) for check in checks]
    if folders[0] == folders[1] or not all(folder.is_dir() for folder in folders):
        raise ValueError('Selecciona dos carpetas de resultados diferentes.')
    if not scripts or not all(script.is_file() and script.suffix == '.py' for script in scripts):
        raise ValueError('Indica al menos una comprobación Python local.')
    report = {'scope': 'Comprobaciones ejecutadas; no mide por sí solo diseño ni calidad general.', 'results': {}}
    for label, folder in zip(('single', 'council'), folders):
        results = []
        for script in scripts:
            started = time.monotonic()
            try:
                result = subprocess.run([sys.executable, str(script), str(folder)], cwd=folder,
                                        capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
                entry = {'passed': result.returncode == 0, 'exit_code': result.returncode,
                         'output': (result.stdout + result.stderr)[-12000:]}
            except (OSError, subprocess.TimeoutExpired) as error:
                entry = {'passed': False, 'error': str(error)}
            results.append({'check': str(script), 'seconds': round(time.monotonic() - started, 3), **entry})
        report['results'][label] = {'project': str(folder), 'passed': sum(item['passed'] for item in results),
                                   'total': len(results), 'checks': results}
    report['passed_difference'] = report['results']['council']['passed'] - report['results']['single']['passed']
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--single', required=True, type=Path)
    parser.add_argument('--council', required=True, type=Path)
    parser.add_argument('--check', required=True, action='append', type=Path,
                        help='Trusted Python script: receives the project path; exit 0 means pass. Repeat for multiple checks.')
    args = parser.parse_args()
    try:
        print(json.dumps(compare(args.single, args.council, args.check), ensure_ascii=False, indent=2))
    except (ValueError, OSError) as error:
        parser.error(str(error))
