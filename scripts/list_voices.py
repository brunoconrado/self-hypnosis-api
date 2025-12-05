#!/usr/bin/env python3
"""
List available ElevenLabs voices

Usage:
    python scripts/list_voices.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.services.elevenlabs import ElevenLabsService


def main():
    api_key = os.getenv('ELEVENLABS_API_KEY')

    if not api_key:
        print("❌ ELEVENLABS_API_KEY not set")
        print("\n1. Go to https://elevenlabs.io")
        print("2. Click your profile → 'Profile + API key'")
        print("3. Copy your API key")
        print("4. Add to api/.env file:")
        print("   ELEVENLABS_API_KEY=your-key-here")
        return

    elevenlabs = ElevenLabsService(api_key)

    # User info (optional - may fail due to permissions)
    try:
        info = elevenlabs.get_user_info()
        print("\n📊 Your Account")
        print("─" * 40)
        print(f"  Plan: {info['tier']}")
        print(f"  Characters: {info['character_count']:,} / {info['character_limit']:,}")
        print(f"  Remaining: {info['remaining_characters']:,}")
    except Exception as e:
        print("\n📊 Account info not available (API key may lack user_read permission)")
        print("   This is fine - you can still list voices and generate audio!")

    # Voices
    print("\n\n🎤 Available Voices")
    print("═" * 60)

    try:
        voices = elevenlabs.get_voices()
    except Exception as e:
        print(f"❌ Error listing voices: {e}")
        return

    # Recommended for meditation/hypnosis
    recommended = ['Daniel', 'Charlotte', 'Antoni', 'Aria', 'Adam', 'Rachel', 'Domi', 'Sarah', 'Bill', 'George']

    print("\n⭐ RECOMMENDED FOR HYPNOSIS/MEDITATION:")
    print("─" * 60)

    found_recommended = False
    for voice in voices:
        if voice['name'] in recommended:
            found_recommended = True
            labels = voice.get('labels', {})
            gender = labels.get('gender', '?')
            accent = labels.get('accent', '')
            print(f"  {voice['name']:15} {gender:8} {accent:15} {voice['voice_id']}")

    if not found_recommended:
        print("  (No recommended voices found in your account)")

    print("\n\n📋 ALL VOICES:")
    print("─" * 60)

    # Group by category
    categories = {}
    for voice in voices:
        cat = voice.get('category', 'other')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(voice)

    for category in ['premade', 'cloned', 'generated', 'professional', 'other']:
        if category not in categories:
            continue

        print(f"\n  [{category.upper()}]")
        for voice in categories[category]:
            labels = voice.get('labels', {})
            gender = labels.get('gender', '?')
            accent = labels.get('accent', '')
            print(f"    {voice['name']:15} {gender:8} {accent:15} {voice['voice_id']}")

    print("\n\n💡 To generate audio, run:")
    print(f"   python scripts/generate_default_audio.py --voice-name \"Daniel\"")
    print("   or")
    print(f"   python scripts/generate_default_audio.py --voice-id <VOICE_ID>")
    print()


if __name__ == '__main__':
    main()
