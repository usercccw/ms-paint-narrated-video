#!/usr/bin/env python3
"""Read-only storyboard audit, with an explicit optional delivery ZIP."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import zipfile

from PIL import Image


def digest(path):
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def compact(text):
    return ''.join(c for c in text if not c.isspace())


def contained(root, name):
    candidate = root / name
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f'Path leaves asset root: {name}')
    return resolved


def prepare_output(path, overwrite, protected):
    if path is None:
        return
    if path in protected:
        raise ValueError(f'Output would overwrite an input: {path}')
    if path.exists() and not overwrite:
        raise ValueError(f'Output exists; use --overwrite: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)


def run(args):
    root = args.root.resolve()
    manifest_path, script_path = args.manifest.resolve(), args.script.resolve()
    data = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    frames = data['frames']
    if not isinstance(frames, list) or not frames:
        raise ValueError('frames must be a nonempty list')
    errors, warnings, results, captions = [], [], [], []
    selected = {}
    ids = [f.get('id') for f in frames]
    if ids != list(range(1, len(frames) + 1)) or any(type(i) is not int for i in ids):
        errors.append('Frame IDs must be ordered consecutive integers starting at 1')
    for frame in frames:
        entry = {'id': frame.get('id'), 'file': frame.get('file')}
        results.append(entry)
        caption = frame.get('caption')
        if not isinstance(caption, str) or not compact(caption):
            errors.append(f'Frame {entry["id"]}: empty or invalid caption')
        else:
            captions.append(caption)
        try:
            name = frame['file']
            if not isinstance(name, str):
                raise ValueError('file must be a string')
            if type(frame.get('id')) is not int:
                raise ValueError('id must be an integer')
            if Path(name).stem != str(frame['id']).zfill(3):
                raise ValueError('filename stem must match the zero-padded ID')
            source = contained(root, name)
            if not source.is_file():
                raise ValueError('selected file is missing')
            logical_name = (root / name).relative_to(root).as_posix()
            if logical_name in selected:
                raise ValueError('duplicate selected filename')
            with Image.open(source) as image:
                image.verify()
            with Image.open(source) as image:
                image.load()
                entry['dimensions'] = list(image.size)
                entry['format'] = image.format
            actual_hash = digest(source)
            entry['sha256'] = actual_hash
            selected[logical_name] = (source, actual_hash)
            recorded_hash = frame.get('sha256')
            if recorded_hash and actual_hash != recorded_hash:
                errors.append(f'{name}: selected image hash differs from the manifest')
            if not recorded_hash:
                warnings.append(f'{name}: no recorded selected-image hash')
            reviewed = frame.get('visual_review') == 'passed'
            entry['visual_review'] = 'passed' if reviewed else 'pending'
            if not reviewed:
                (errors if args.require_reviewed else warnings).append(f'{name}: visual review is not passed')
        except (KeyError, ValueError, OSError, TypeError) as exc:
            errors.append(f'Frame {entry["id"]}: {exc}')
    expected = compact(script_path.read_text(encoding='utf-8-sig'))
    actual = compact(''.join(captions))
    coverage = expected == actual
    if not coverage:
        limit = min(len(expected), len(actual))
        offset = next((i for i in range(limit) if expected[i] != actual[i]), limit)
        errors.append('Caption coverage differs at character ' + str(offset) + ': ' +
                      repr(expected[max(0, offset - 12):offset + 24]) + ' vs ' +
                      repr(actual[max(0, offset - 12):offset + 24]))
    for name, expected_hash in data.get('approved_hashes', {}).items():
        try:
            source = contained(root, name)
            if digest(source) != expected_hash:
                errors.append(f'{name}: previously approved asset changed')
        except (ValueError, OSError) as exc:
            errors.append(f'{name}: approved asset could not be checked: {exc}')
    if root.is_dir():
        for path in root.iterdir():
            if path.is_file() and path.stem.isdigit() and path.suffix.lower() in ('.png', '.jpg', '.jpeg'):
                if path.name not in selected:
                    warnings.append(f'{path.name}: numbered image not selected by the manifest')

    package_files = dict(selected)

    def add_file(path, name):
        path = path.resolve()
        if name in package_files and package_files[name][0] != path:
            raise ValueError(f'ZIP name collision: {name}')
        package_files[name] = (path, digest(path))

    if args.zip:
        for source in (manifest_path, script_path):
            name = source.relative_to(root).as_posix() if source.is_relative_to(root) else source.name
            add_file(source, name)
        for name in args.include:
            source = contained(root, name)
            if not source.exists():
                raise ValueError(f'Included path does not exist: {name}')
            candidates = sorted(source.rglob('*')) if source.is_dir() else [source]
            for path in candidates:
                resolved = contained(root, path.relative_to(root))
                if resolved.is_file():
                    add_file(resolved, path.relative_to(root).as_posix())

    report_path = args.report.resolve() if args.report else None
    zip_path = args.zip.resolve() if args.zip else None
    protected = {manifest_path, script_path} | {p[0] for p in package_files.values()}
    if report_path and zip_path and report_path == zip_path:
        raise ValueError('Report and ZIP outputs must be different')
    prepare_output(report_path, args.overwrite, protected)
    prepare_output(zip_path, args.overwrite, protected)
    report = {'expected_count': len(frames), 'decoded_count': sum('sha256' in r for r in results),
              'caption_coverage_exact_ignoring_whitespace': coverage, 'errors': errors,
              'warnings': warnings, 'frames': results}
    if report_path:
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if errors:
        print(json.dumps({'ok': False, 'errors': errors, 'warnings': warnings}, ensure_ascii=False))
        return 1
    if zip_path:
        handle, temporary_name = tempfile.mkstemp(prefix='storyboard-', suffix='.zip', dir=zip_path.parent)
        os.close(handle)
        temporary = Path(temporary_name)
        try:
            with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                for name, (source, _) in package_files.items():
                    archive.write(source, name)
            with zipfile.ZipFile(temporary) as archive:
                bad_file = archive.testzip()
                if bad_file:
                    raise ValueError(f'ZIP integrity failure: {bad_file}')
                for name, (_, expected_hash) in package_files.items():
                    if hashlib.sha256(archive.read(name)).hexdigest() != expected_hash:
                        raise ValueError(f'Input changed while packaging: {name}')
            os.replace(temporary, zip_path)
        finally:
            if temporary.exists():
                temporary.unlink()
    print(json.dumps({'ok': True, 'count': len(frames), 'caption_coverage': coverage,
                      'warnings': warnings, 'zip': str(zip_path) if zip_path else None}, ensure_ascii=False))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--script', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--zip', type=Path)
    parser.add_argument('--include', action='append', default=[])
    parser.add_argument('--require-reviewed', action='store_true')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    try:
        return run(args)
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
