#!/usr/bin/env python3
"""Build the offline motor-counterpoint study. No serial/device operations."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from lib.plotter_score import Profile, compose, write_csv, write_midi, write_svg, write_wav, write_vastish_sequence


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed', type=int, default=22)
    p.add_argument('--rows', type=int, default=32)
    p.add_argument('--columns', type=int, default=24)
    p.add_argument('--bpm', type=float, default=100.)
    p.add_argument('--root', type=int, default=48, help='MIDI note; default C3')
    p.add_argument('--profile', type=Path, help='JSON Profile fields; see demo profiles')
    p.add_argument('--disconnected', action='store_true')
    p.add_argument('--audio-seconds', type=float, default=30., help='audition excerpt, not plot duration')
    p.add_argument('--no-audio', action='store_true')
    p.add_argument('--out', type=Path, default=Path(__file__).parent/'out')
    args = p.parse_args()
    try:
        profile = Profile(**json.loads(args.profile.read_text())) if args.profile else Profile()
        score = compose(seed=args.seed, rows=args.rows, columns=args.columns,
                        bpm=args.bpm, root=args.root, profile=profile,
                        connected=not args.disconnected)
        args.out.mkdir(parents=True, exist_ok=True)
        write_svg(score, args.out/'counterpoint.svg')
        write_midi(score, args.out/'intended-notes.mid')
        write_csv(score, args.out/'events.csv')
        write_vastish_sequence(score, args.out/'vastish-excerpt.txt', seconds=args.audio_seconds)
        if not args.no_audio:
            duration = write_wav(score, args.out/'motor-model-excerpt.wav', seconds=args.audio_seconds)
            score['audition'] = dict(file='motor-model-excerpt.wav', duration_seconds=duration,
                                    kind='synthetic acoustic-rate surrogate; NOT a recording')
        (args.out/'score.json').write_text(json.dumps(score, indent=2)+'\n')
        print(json.dumps(dict(output=str(args.out), duration_seconds=score['duration_ms']/1000,
                              **score['metrics']), indent=2))
    except (ValueError, TypeError, OSError) as e:
        p.error(str(e))


if __name__ == '__main__':
    main()
