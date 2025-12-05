#!/usr/bin/env python3
"""
Test generating a single affirmation with ElevenLabs

Usage:
    python scripts/test_voice.py --voice-name "Daniel"
    python scripts/test_voice.py --voice-id YOUR_VOICE_ID
    python scripts/test_voice.py --voice-name "Daniel" --text "Seu texto aqui"
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import argparse
from app.services.elevenlabs import ElevenLabsService

# Default test text
DEFAULT_TEXT = "Eu me amo e me aceito completamente."


def main():
    parser = argparse.ArgumentParser(description='Test ElevenLabs voice generation')
    parser.add_argument('--voice-id', type=str, help='Voice ID')
    parser.add_argument('--voice-name', type=str, help='Voice name')
    parser.add_argument('--text', type=str, default=DEFAULT_TEXT, help='Text to generate')
    parser.add_argument('--output', type=str, default='./test_output.mp3', help='Output file')

    args = parser.parse_args()

    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        print("❌ ELEVENLABS_API_KEY not set")
        return

    elevenlabs = ElevenLabsService(api_key)

    # Get voice ID
    voice_id = args.voice_id
    if args.voice_name:
        voice = elevenlabs.get_voice_by_name(args.voice_name)
        if voice:
            voice_id = voice['voice_id']
            print(f"✓ Found voice: {args.voice_name} ({voice_id})")
        else:
            print(f"❌ Voice '{args.voice_name}' not found")
            return

    if not voice_id:
        print("❌ Please specify --voice-id or --voice-name")
        return

    print(f"\n🎤 Generating audio...")
    print(f"   Text: \"{args.text}\"")
    print(f"   Voice: {voice_id}")

    try:
        audio_bytes = elevenlabs.generate_audio(
            text=args.text,
            voice_id=voice_id
        )

        output_path = Path(args.output)
        with open(output_path, 'wb') as f:
            f.write(audio_bytes)

        print(f"\n✅ Success! Audio saved to: {output_path}")
        print(f"   Size: {len(audio_bytes):,} bytes")
        print(f"\n🎧 Play it with: open {output_path}")

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == '__main__':
    main()
