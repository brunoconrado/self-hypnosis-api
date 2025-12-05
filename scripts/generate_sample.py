#!/usr/bin/env python3
"""
Generate a sample of affirmations for testing

Usage:
    python scripts/generate_sample.py --voice-id YOUR_VOICE_ID --count 10
    python scripts/generate_sample.py --voice-id YOUR_VOICE_ID --category financeiro --count 10
"""

import os
import sys
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.data.affirmations import AFFIRMATIONS
from app.services.elevenlabs import ElevenLabsService


def main():
    parser = argparse.ArgumentParser(description='Generate sample affirmations')
    parser.add_argument('--voice-id', type=str, required=True, help='Voice ID')
    parser.add_argument('--category', type=str, default='Financeiro',
                        help='Category (Financeiro, Saúde, Sono, Autoestima, Produtividade)')
    parser.add_argument('--count', type=int, default=10, help='Number of affirmations')
    parser.add_argument('--output', type=str, default='./storage/sample_audio', help='Output directory')

    args = parser.parse_args()

    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        print("❌ ELEVENLABS_API_KEY not set")
        return

    # Find category
    category = None
    for cat_name in AFFIRMATIONS.keys():
        if cat_name.lower() == args.category.lower():
            category = cat_name
            break

    if not category:
        print(f"❌ Category '{args.category}' not found")
        print(f"   Available: {', '.join(AFFIRMATIONS.keys())}")
        return

    texts = AFFIRMATIONS[category][:args.count]

    print(f"\n🎤 Generating {len(texts)} affirmations from '{category}'")
    print(f"   Voice: {args.voice_id}")
    print(f"   Output: {args.output}\n")

    elevenlabs = ElevenLabsService(api_key)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    generated = 0
    for i, text in enumerate(texts):
        filename = f"{category.lower()}_{i+1:02d}.mp3"
        filepath = output_dir / filename

        try:
            print(f"  [{i+1}/{len(texts)}] {text[:50]}...", end=" ", flush=True)

            audio_bytes = elevenlabs.generate_audio(
                text=text,
                voice_id=args.voice_id
            )

            with open(filepath, 'wb') as f:
                f.write(audio_bytes)

            print(f"✓")
            generated += 1
            time.sleep(0.3)

        except Exception as e:
            print(f"✗ {e}")

    print(f"\n✅ Generated {generated} files in {output_dir}")
    print(f"\n📋 Files created:")
    for f in sorted(output_dir.glob("*.mp3")):
        print(f"   {f}")


if __name__ == '__main__':
    main()
