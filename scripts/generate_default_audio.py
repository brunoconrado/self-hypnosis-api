#!/usr/bin/env python3
"""
Generate audio for all default affirmations using ElevenLabs

Usage:
    python scripts/generate_default_audio.py --voice-id YOUR_VOICE_ID
    python scripts/generate_default_audio.py --list-voices
    python scripts/generate_default_audio.py --voice-name "Daniel"
"""

import os
import sys
import argparse
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.data.affirmations import AFFIRMATIONS
from app.services.elevenlabs import ElevenLabsService


def list_voices(elevenlabs: ElevenLabsService):
    """List all available voices"""
    print("\n📢 Available Voices:\n")
    print("-" * 80)

    voices = elevenlabs.get_voices()

    # Group by category
    categories = {}
    for voice in voices:
        cat = voice.get('category', 'other')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(voice)

    for category, voices_in_cat in categories.items():
        print(f"\n🏷️  {category.upper()}")
        print("-" * 40)
        for voice in voices_in_cat:
            labels = voice.get('labels', {})
            accent = labels.get('accent', '')
            gender = labels.get('gender', '')
            desc = f"({gender}, {accent})" if gender or accent else ""
            print(f"  • {voice['name']:20} {desc:30} ID: {voice['voice_id']}")

    print("\n")


def get_user_info(elevenlabs: ElevenLabsService):
    """Show user subscription info"""
    try:
        info = elevenlabs.get_user_info()

        print("\n📊 Account Info:")
        print("-" * 40)
        print(f"  Tier: {info['tier']}")
        print(f"  Characters used: {info['character_count']:,}")
        print(f"  Character limit: {info['character_limit']:,}")
        print(f"  Remaining: {info['remaining_characters']:,}")
        print()

        return info
    except Exception:
        print("\n📊 Account info not available (API key may lack user_read permission)")
        print("   You can still generate audio - just be mindful of your quota!")
        print()
        return None


def estimate_usage():
    """Estimate character usage for all affirmations"""
    total_chars = 0
    total_count = 0

    print("\n📝 Character Estimation:")
    print("-" * 40)

    for category, texts in AFFIRMATIONS.items():
        cat_chars = sum(len(t) for t in texts)
        total_chars += cat_chars
        total_count += len(texts)
        print(f"  {category}: {len(texts)} affirmations, {cat_chars:,} characters")

    print("-" * 40)
    print(f"  TOTAL: {total_count} affirmations, {total_chars:,} characters")

    return total_chars, total_count


def generate_all(elevenlabs: ElevenLabsService, voice_id: str, output_dir: Path):
    """Generate audio for all affirmations"""

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🎙️  Generating audio with voice: {voice_id}")
    print(f"📁 Output directory: {output_dir}\n")

    total_generated = 0
    total_errors = 0
    total_skipped = 0

    for category, texts in AFFIRMATIONS.items():
        # Sanitize category name for directory
        cat_dir_name = category.lower()
        for old, new in [('ú', 'u'), ('í', 'i'), ('ã', 'a'), ('é', 'e'), ('ç', 'c')]:
            cat_dir_name = cat_dir_name.replace(old, new)

        cat_dir = output_dir / cat_dir_name
        cat_dir.mkdir(exist_ok=True)

        print(f"\n📂 {category} ({len(texts)} affirmations)")
        print("-" * 50)

        for i, text in enumerate(texts):
            filename = f"{i+1:02d}.mp3"
            filepath = cat_dir / filename

            # Skip if already exists
            if filepath.exists():
                print(f"  ⏭️  {filename} (already exists)")
                total_skipped += 1
                continue

            try:
                print(f"  🔄 Generating {filename}...", end=" ", flush=True)

                audio_bytes = elevenlabs.generate_audio(
                    text=text,
                    voice_id=voice_id
                )

                with open(filepath, 'wb') as f:
                    f.write(audio_bytes)

                print(f"✓ ({len(audio_bytes):,} bytes)")
                total_generated += 1

                # Rate limiting - be nice to the API
                time.sleep(0.3)

            except Exception as e:
                print(f"✗ Error: {e}")
                total_errors += 1

                # If rate limited, wait longer
                if "rate" in str(e).lower() or "429" in str(e):
                    print("  ⏳ Rate limited, waiting 30 seconds...")
                    time.sleep(30)

    print("\n" + "=" * 50)
    print(f"✅ Generated: {total_generated}")
    print(f"⏭️  Skipped (existing): {total_skipped}")
    print(f"❌ Errors: {total_errors}")
    print(f"📁 Files saved to: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description='Generate audio for affirmations using ElevenLabs')
    parser.add_argument('--list-voices', action='store_true', help='List available voices')
    parser.add_argument('--voice-id', type=str, help='ElevenLabs voice ID to use')
    parser.add_argument('--voice-name', type=str, help='Voice name to search for')
    parser.add_argument('--output', type=str, default='./storage/default_audio', help='Output directory')
    parser.add_argument('--estimate', action='store_true', help='Estimate character usage only')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt')

    args = parser.parse_args()

    # Check API key
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        print("❌ Error: ELEVENLABS_API_KEY not set in environment")
        print("   Add it to your .env file or export it:")
        print("   export ELEVENLABS_API_KEY=your-api-key")
        sys.exit(1)

    elevenlabs = ElevenLabsService(api_key)

    # Show user info (may fail, that's ok)
    info = get_user_info(elevenlabs)

    # Just estimate?
    if args.estimate:
        total_chars, total_count = estimate_usage()
        if info and info.get('remaining_characters'):
            remaining = info['remaining_characters']
            if remaining < total_chars:
                print(f"\n⚠️  Warning: May not have enough characters!")
                print(f"   Need ~{total_chars:,}, have {remaining:,}")
            else:
                print(f"\n✓ Should have sufficient characters")
        return

    # List voices
    if args.list_voices:
        list_voices(elevenlabs)
        return

    # Get voice ID
    voice_id = args.voice_id

    if args.voice_name:
        try:
            voice = elevenlabs.get_voice_by_name(args.voice_name)
            if voice:
                voice_id = voice['voice_id']
                print(f"\n✓ Found voice '{args.voice_name}': {voice_id}")
            else:
                print(f"❌ Voice '{args.voice_name}' not found.")
                print("   Use --list-voices to see available voices")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Error finding voice: {e}")
            sys.exit(1)

    if not voice_id:
        print("❌ Please specify a voice with --voice-id or --voice-name")
        print("   Use --list-voices to see available voices")
        print("\n   Example:")
        print("   python scripts/generate_default_audio.py --voice-name \"Daniel\"")
        sys.exit(1)

    # Show estimation
    total_chars, total_count = estimate_usage()

    # Confirm generation
    if not args.yes:
        print("\n" + "=" * 50)
        response = input(f"\n🎤 Generate {total_count} audio files using ~{total_chars:,} characters? [y/N] ")
        if response.lower() != 'y':
            print("Cancelled.")
            return

    # Generate
    generate_all(elevenlabs, voice_id, Path(args.output))


if __name__ == '__main__':
    main()
