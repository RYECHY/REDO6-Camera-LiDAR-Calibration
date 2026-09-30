#!/usr/bin/env python3
"""Collect selected modified sources for private review, without changing them.

This tool does not publish anything. Its output may contain internal material
and must be reviewed before any file is added to a public repository.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

SELECTED = {
    'fast_calib': ['include/common_lib.h', 'src/qr_detect.hpp', 'src/lidar_detect.hpp'],
    'fast_livo2': ['include/LIVMapper.h', 'src/LIVMapper.cpp', 'src/vio.cpp'],
}


def run_git(root, arguments):
    try:
        result = subprocess.run(['git', '--no-optional-locks', '-C', str(root)] + arguments,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
        return result.returncode, result.stdout, result.stderr.decode(errors='replace')
    except (OSError, subprocess.TimeoutExpired) as error:
        return -1, b'', str(error)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fast-calib-root', type=Path, required=True)
    parser.add_argument('--fast-livo2-root', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, default=Path.home())
    args = parser.parse_args()
    roots = {'fast_calib': args.fast_calib_root.expanduser().resolve(),
             'fast_livo2': args.fast_livo2_root.expanduser().resolve()}
    for label, root in roots.items():
        if not root.is_dir():
            parser.error(label + ' source root does not exist')
    output_root = args.output_root.expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix='repro_private_review_', dir=str(output_root)))
    bundle = run_dir / 'REPRO_PRIVATE_REVIEW'
    result = []
    for label, root in roots.items():
        directory = bundle / label
        directory.mkdir(parents=True)
        entry = {'repository': label, 'files': []}
        code, content, error = run_git(root, ['rev-parse', 'HEAD'])
        entry['head'] = content.decode().strip() if code == 0 else None
        if code != 0:
            entry['git_error'] = error
        for name in SELECTED[label] + ['LICENSE']:
            source = root / name
            target = directory / name
            record = {'relative_path': name}
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                record.update(status='copied', sha256=hashlib.sha256(target.read_bytes()).hexdigest())
            except OSError as problem:
                record.update(status='missing_or_unreadable', error=str(problem))
            entry['files'].append(record)
            print(label + '/' + name + ': ' + record['status'], flush=True)
        code, content, error = run_git(root, ['diff', '--no-ext-diff', '--no-textconv', '--binary', 'HEAD', '--'] + SELECTED[label])
        entry['diff_returncode'] = code
        if code == 0:
            (directory / 'selected_changes.patch').write_bytes(content)
        else:
            entry['diff_error'] = error
        result.append(entry)
    (bundle / 'REVIEW_MANIFEST.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (bundle / 'DO_NOT_PUBLISH.txt').write_text(
        'PRIVATE REVIEW ONLY. Source and diff contents have not been screened for internal material.\n'
        'Do not add this archive to the public repository.\n', encoding='utf-8')
    archive = run_dir / 'REDO6_REPRO_PRIVATE_REVIEW.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
        for path in sorted(bundle.rglob('*')):
            if path.is_file():
                output.write(path, path.relative_to(run_dir))
    missing = sum(row['status'] != 'copied' for entry in result for row in entry['files'])
    print('Private review archive:', archive)
    print('Missing/unreadable selected files:', missing)
    print('No source file was modified. Review the archive before publication.')


if __name__ == '__main__':
    main()
