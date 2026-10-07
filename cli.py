#!/usr/bin/env python3
import sys
import argparse
import json
from pathlib import Path
from vocalis.analyzer import AudioAnalyzer

def main():
    parser = argparse.ArgumentParser(
        description="Vocalis - Acoustic Speech Delivery & Vocal Dynamics Analyzer"
    )
    parser.add_argument(
        "audio_file",
        type=str,
        help="Path to speech audio recording (.wav, .mp3, .ogg, .flac, etc.)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw analysis results as formatted JSON",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Print extended metrics alongside the summary card",
    )

    args = parser.parse_args()
    audio_path = Path(args.audio_file)

    if not audio_path.exists():
        print(f"Error: Audio file '{audio_path}' not found.", file=sys.stderr)
        sys.exit(1)

    try:
        analyzer = AudioAnalyzer()
        result = analyzer.analyze(str(audio_path))
    except Exception as e:
        print(f"Error analyzing audio: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        # Dump json (excluding dense timeline arrays for clean stdout)
        data = result.model_dump()
        del data["timeline"]
        print(json.dumps(data, indent=2))
    else:
        print("\n" + result.formatted_card + "\n")
        if args.details:
            c = result.characteristics
            print("Extended Analytics:")
            print(f" • Articulation Rate:    {c.articulation_rate} syllables/sec")
            print(f" • Pause Frequency:      {c.pause_frequency} pauses/min")
            print(f" • Speech/Silence Ratio: {c.speech_to_silence_ratio}x")
            print(f" • Pitch Variance:       ±{c.pitch_variation_semitones} semitones SD")
            print(f" • Dynamic Loudness:     ±{c.energy_variation_db} dB SD")
            print(f" • Coaching Insight:     {c.style_description}\n")

if __name__ == "__main__":
    main()

