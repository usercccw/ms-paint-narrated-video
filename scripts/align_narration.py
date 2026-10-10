#!/usr/bin/env python3
"""Align approved captions to word timestamps without changing the manuscript."""
import argparse
from array import array
from bisect import bisect_left
import json
import math
from pathlib import Path
import sys


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def normalize(text, replacements):
    for old, new in replacements:
        text = text.replace(old, new)
    return ''.join(c for c in text.casefold() if c.isalnum())


def align(expected, actual):
    n, m = len(expected), len(actual)
    if (n + 1) * (m + 1) > 40000000:
        raise ValueError('Text is too large for this helper; align verified sections separately')
    directions = bytearray((n + 1) * (m + 1))
    previous = array('I', range(m + 1))
    for j in range(1, m + 1):
        directions[j] = 2
    for i in range(1, n + 1):
        current = array('I', [i])
        directions[i * (m + 1)] = 1
        for j in range(1, m + 1):
            options = (previous[j - 1] + (expected[i - 1] != actual[j - 1]),
                       previous[j] + 1, current[j - 1] + 1)
            cost = min(options)
            current.append(cost)
            directions[i * (m + 1) + j] = options.index(cost)
        previous = current
    distance = previous[m]
    mapping = {}
    i, j = n, m
    while i or j:
        direction = directions[i * (m + 1) + j]
        if i and j and direction == 0:
            mapping[i - 1] = j - 1
            i -= 1
            j -= 1
        elif i and (not j or direction == 1):
            i -= 1
        else:
            j -= 1
    return mapping, distance


def stamp(seconds):
    total = round(seconds * 1000)
    hours, total = divmod(total, 3600000)
    minutes, total = divmod(total, 60000)
    seconds, milliseconds = divmod(total, 1000)
    return f'{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}'


def run(args):
    if args.fps <= 0 or not math.isfinite(args.fps):
        raise ValueError('fps must be positive and finite')
    if any(not math.isfinite(v) or v < 0 for v in (args.lead, args.tail, args.min_scene)):
        raise ValueError('lead, tail and min-scene must be nonnegative and finite')
    if not math.isfinite(args.audio_duration) or args.audio_duration <= 0:
        raise ValueError('audio-duration must be positive and finite')
    inputs = {args.manifest.resolve(), args.words.resolve()}
    if args.normalization:
        inputs.add(args.normalization.resolve())
    outputs = [args.output.resolve()] + ([args.srt.resolve()] if args.srt else [])
    if len(set(outputs)) != len(outputs):
        raise ValueError('Timeline and SRT outputs must be different')
    for path in outputs:
        if path in inputs:
            raise ValueError(f'Output would overwrite an input: {path}')
        if path.exists() and not args.overwrite:
            raise ValueError(f'Output exists; use --overwrite: {path}')
    manifest = read_json(args.manifest)
    frames = manifest['frames']
    if not isinstance(frames, list) or not frames:
        raise ValueError('frames must be a nonempty ordered list')
    if [f.get('id') for f in frames] != list(range(1, len(frames) + 1)):
        raise ValueError('Frame IDs must be consecutive and ordered, starting at 1')
    if any(type(f.get('id')) is not int or not isinstance(f.get('caption'), str) or
           not isinstance(f.get('file'), str) for f in frames):
        raise ValueError('Each frame needs integer id, string caption and string file')
    replacements = read_json(args.normalization)['replacements'] if args.normalization else []
    if not isinstance(replacements, list) or any(not isinstance(pair, list) or len(pair) != 2 or
       any(not isinstance(s, str) for s in pair) or not pair[0] for pair in replacements):
        raise ValueError('replacements must be a list of nonempty-source string pairs')
    normalized_captions = [normalize(f['caption'], replacements) for f in frames]
    if any(not text for text in normalized_captions):
        raise ValueError('All frames must have spoken text; place unvoiced scenes manually')
    expected = ''.join(normalized_captions)
    word_data = read_json(args.words)
    words = word_data['words'] if isinstance(word_data, dict) else word_data
    recognized, previous_start = [], -1
    if not isinstance(words, list):
        raise ValueError('words must be a list')
    for word in words:
        text = word.get('word', word.get('text'))
        if not isinstance(text, str):
            raise ValueError('Each word must have string word/text and second-based start/end')
        start, end = float(word['start']), float(word['end'])
        if not all(math.isfinite(v) for v in (start, end)) or start < previous_start or start < 0 or end <= start:
            raise ValueError(f'Invalid or unordered timestamp for word: {text}')
        if end > args.audio_duration + .25:
            raise ValueError('Word timestamps exceed audio duration; check units and source file')
        previous_start = start
        chars = normalize(text, replacements)
        for offset, char in enumerate(chars):
            recognized.append({'char': char, 'start': start + (end - start) * offset / len(chars),
                               'end': start + (end - start) * (offset + 1) / len(chars)})
    if not recognized:
        raise ValueError('No recognized spoken characters')
    actual = ''.join(item['char'] for item in recognized)
    mapping, distance = align(expected, actual)
    positions = sorted(mapping)
    if not positions:
        raise ValueError('No usable alignment; check narration and manuscript versions')

    def estimate(position, endpoint='start'):
        if position in mapping:
            item = recognized[mapping[position]]
            return item[endpoint], 'matched' if expected[position] == item['char'] else 'substitution'
        index = bisect_left(positions, position)
        if index == 0:
            return recognized[mapping[positions[0]]]['start'], 'interpolated'
        if index == len(positions):
            return recognized[mapping[positions[-1]]]['end'], 'interpolated'
        before, after = positions[index - 1], positions[index]
        left, right = recognized[mapping[before]]['end'], recognized[mapping[after]]['start']
        return left + max(0, right - left) * (position - before) / (after - before), 'interpolated'

    total_frames = math.ceil((args.audio_duration + args.tail) * args.fps)
    timings, needs_review, position = [], [], 0
    warnings = []
    edit_ratio = distance / len(expected)
    if edit_ratio > .10:
        warnings.append('Alignment edit ratio exceeds 10%; verify source/manuscript versions')
    for frame, normalized in zip(frames, normalized_captions):
        length = len(normalized)
        speech_start, method = estimate(position)
        speech_end, end_method = estimate(position + length - 1, 'end')
        exact = sum(p in mapping and expected[p] == actual[mapping[p]]
                    for p in range(position, position + length))
        accuracy = exact / length
        mapped = mapping.get(position, mapping[positions[min(bisect_left(positions, position), len(positions) - 1)]])
        start_frame = 0 if not timings else round(max(0, speech_start - args.lead) * args.fps)
        item = {'id': frame['id'], 'file': frame['file'], 'caption': frame['caption'],
                'start_frame': start_frame, 'source_speech_start': speech_start,
                'source_speech_end': speech_end, 'start_method': method, 'end_method': end_method,
                'character_match_ratio': accuracy, 'expected_context': expected[position:position + 12],
                'recognized_context': actual[mapped:mapped + 12]}
        if method != 'matched' or end_method != 'matched' or accuracy < .85 or speech_end < speech_start:
            needs_review.append(frame['id'])
        timings.append(item)
        position += length
    for index, item in enumerate(timings):
        item['end_frame'] = timings[index + 1]['start_frame'] if index + 1 < len(timings) else total_frames
        if item['end_frame'] <= item['start_frame']:
            raise ValueError(f'Scene {item["id"]} has no positive duration; repair alignment before export')
        if item['start_frame'] >= math.ceil(args.audio_duration * args.fps):
            raise ValueError(f'Scene {item["id"]} starts after narration ends')
        item['start'] = item['start_frame'] / args.fps
        item['end'] = item['end_frame'] / args.fps
        item['duration'] = (item['end_frame'] - item['start_frame']) / args.fps
        if item['duration'] < args.min_scene:
            needs_review.append(item['id'])
            warnings.append(f'Scene {item["id"]} is shorter than {args.min_scene} seconds')
    timeline = {'fps': args.fps, 'audio_duration': args.audio_duration,
                'video_duration': total_frames / args.fps, 'video_frames': total_frames,
                'ending_hold_seconds': args.tail, 'cut_lead_seconds': args.lead,
                'alignment_edit_ratio': edit_ratio, 'normalization_replacements': replacements,
                'needs_review_ids': sorted(set(needs_review)), 'warnings': warnings, 'frames': timings}
    if isinstance(word_data, dict) and isinstance(word_data.get('source'), str):
        timeline['source_audio'] = word_data['source']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(timeline, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if args.srt:
        args.srt.parent.mkdir(parents=True, exist_ok=True)
        args.srt.write_text('\n\n'.join(f'{f["id"]}\n{stamp(f["start"])} --> {stamp(f["end"])}\n{f["caption"]}'
                                       for f in timings) + '\n', encoding='utf-8-sig')
    print(json.dumps({'ok': True, 'scene_count': len(timings), 'video_duration': timeline['video_duration'],
                      'edit_ratio': edit_ratio, 'needs_review_ids': timeline['needs_review_ids'],
                      'warnings': warnings}, ensure_ascii=False))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--words', type=Path, required=True)
    parser.add_argument('--audio-duration', type=float, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--srt', type=Path)
    parser.add_argument('--normalization', type=Path)
    parser.add_argument('--fps', type=float, default=30)
    parser.add_argument('--lead', type=float, default=.06)
    parser.add_argument('--tail', type=float, default=2)
    parser.add_argument('--min-scene', type=float, default=.4)
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    try:
        return run(args)
    except (ValueError, OSError, KeyError, TypeError, OverflowError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
