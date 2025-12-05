#!/usr/bin/env python3
"""
Generate audio for affirmations and link them in the database

Usage:
    python scripts/generate_and_link.py --voice-id YOUR_VOICE_ID --category financeiro --count 10
    python scripts/generate_and_link.py --voice-id YOUR_VOICE_ID --all
    python scripts/generate_and_link.py --link-existing  # Link existing audio files to database
"""

import os
import sys
import time
import argparse
import re
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Initialize Flask app context for database access
from app import create_app
app = create_app()

from app.data.affirmations import AFFIRMATIONS
from app.services.elevenlabs import ElevenLabsService
from app.services.storage import get_storage
from app.models import CategoryModel, AffirmationModel
from app.services.database import get_db
from bson import ObjectId
import io


def sanitize_filename(text, max_length=50):
    """Convert affirmation text to a clean filename"""
    # Remove accents
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ASCII', 'ignore').decode('ASCII')

    # Lowercase and replace spaces with underscores
    text = text.lower().strip()

    # Remove punctuation except underscores
    text = re.sub(r'[^\w\s]', '', text)

    # Replace spaces with underscores
    text = re.sub(r'\s+', '_', text)

    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length].rstrip('_')

    return text


def get_category_slug(category_name):
    """Convert category name to URL-friendly slug"""
    slugs = {
        'Financeiro': 'financeiro',
        'Saúde': 'saude',
        'Sono': 'sono',
        'Autoestima': 'autoestima',
        'Produtividade': 'produtividade'
    }
    return slugs.get(category_name, category_name.lower())


def generate_for_category(elevenlabs, voice_id, category_name, count=None):
    """Generate audio for affirmations in a category"""

    with app.app_context():
        storage = get_storage()
        db = get_db()

        # Find category in database
        categories = CategoryModel.get_all()
        category = next((c for c in categories if c['name'].lower() == category_name.lower()), None)

        if not category:
            print(f"❌ Category '{category_name}' not found in database")
            print(f"   Available: {[c['name'] for c in categories]}")
            return 0

        # Get category slug for folder structure
        category_slug = get_category_slug(category['name'])

        # Get affirmations for this category (with voice_id to check existing audio)
        affirmations = AffirmationModel.get_by_category(category['id'], voice_id=voice_id)

        if count:
            affirmations = affirmations[:count]

        print(f"\n📂 {category_name} ({len(affirmations)} affirmations)")
        print("-" * 50)

        generated = 0
        for i, aff in enumerate(affirmations):
            # Skip if already has audio for this voice
            if AffirmationModel.has_audio_for_voice(aff['id'], voice_id):
                print(f"  [{i+1}/{len(affirmations)}] ⏭️  Already has audio for this voice")
                continue

            try:
                text = aff['text']
                print(f"  [{i+1}/{len(affirmations)}] {text[:40]}...", end=" ", flush=True)

                # Generate audio
                audio_bytes = elevenlabs.generate_audio(
                    text=text,
                    voice_id=voice_id
                )

                # Create path: voices/{voice_id}/affirmations/{category}/{filename}.mp3
                filename = sanitize_filename(text) + '.mp3'
                relative_path = f"voices/{voice_id}/affirmations/{category_slug}/{filename}"

                # Save to storage (with nested path)
                audio_file = io.BytesIO(audio_bytes)
                audio_path = storage.save_audio(audio_file, relative_path, 'audio/mpeg', preserve_filename=True)
                audio_url = storage.get_audio_url(audio_path)

                # Update affirmation in database using new multi-voice structure
                AffirmationModel.set_audio_for_voice(
                    affirmation_id=aff['id'],
                    voice_id=voice_id,
                    path=audio_path,
                    url=audio_url
                )

                print(f"✓")
                generated += 1
                time.sleep(0.3)

            except Exception as e:
                print(f"✗ {e}")
                if "rate" in str(e).lower() or "429" in str(e):
                    print("  ⏳ Rate limited, waiting 30s...")
                    time.sleep(30)

        return generated


def link_existing_files(voice_id=None):
    """Link existing audio files in storage to affirmations in database

    Args:
        voice_id: ElevenLabs voice ID. If provided, links files in voices/{voice_id}/ structure
    """

    with app.app_context():
        storage = get_storage()
        db = get_db()

        # Get storage path
        storage_path = Path(app.config.get('STORAGE_LOCAL_PATH', './storage/audio'))

        if not storage_path.exists():
            print(f"❌ Storage path not found: {storage_path}")
            return 0

        # Find audio files based on structure
        if voice_id:
            # New structure: voices/{voice_id}/affirmations/{category}/*.mp3
            voice_path = storage_path / 'voices' / voice_id / 'affirmations'
            audio_files = list(voice_path.glob('**/*.mp3'))
            print(f"\n🔍 Found {len(audio_files)} audio files for voice {voice_id}")
        else:
            # Legacy flat structure
            audio_files = [f for f in storage_path.glob('*.mp3') if 'voices' not in str(f)]
            print(f"\n🔍 Found {len(audio_files)} audio files in flat storage")

        if not audio_files:
            return 0

        # Get all affirmations from database
        affirmations = list(db.affirmations.find())
        print(f"📋 Found {len(affirmations)} affirmations in database")

        # Create lookup map: sanitized_text -> affirmation
        aff_map = {}
        for aff in affirmations:
            sanitized = sanitize_filename(aff['text'])
            aff_map[sanitized] = aff

        print(f"\n{'='*50}")
        linked = 0

        for audio_file in audio_files:
            filename = audio_file.stem  # filename without extension

            if filename in aff_map:
                aff = aff_map[filename]

                if voice_id:
                    # Check if already has audio for this voice
                    audio_data = aff.get('audio', {}).get(voice_id)
                    if audio_data and audio_data.get('path'):
                        print(f"⏭️  {filename[:40]}... (already linked)")
                        continue

                    # Calculate relative path from storage root
                    relative_path = str(audio_file.relative_to(storage_path))
                    audio_url = storage.get_audio_url(relative_path)

                    # Update database with new structure
                    db.affirmations.update_one(
                        {'_id': aff['_id']},
                        {'$set': {f'audio.{voice_id}': {'path': relative_path, 'url': audio_url}}}
                    )
                else:
                    # Legacy: check default_audio_url
                    if aff.get('default_audio_url'):
                        print(f"⏭️  {filename[:40]}... (already linked)")
                        continue

                    audio_path = audio_file.name
                    audio_url = storage.get_audio_url(audio_path)

                    db.affirmations.update_one(
                        {'_id': aff['_id']},
                        {'$set': {'default_audio_url': audio_url, 'audio_path': audio_path}}
                    )

                print(f"✓ Linked: {filename[:40]}...")
                linked += 1
            else:
                print(f"⚠️  No match: {filename[:40]}...")

        return linked


def main():
    parser = argparse.ArgumentParser(description='Generate and link audio to affirmations')
    parser.add_argument('--voice-id', type=str, help='ElevenLabs voice ID')
    parser.add_argument('--category', type=str, help='Category name (e.g., Financeiro)')
    parser.add_argument('--count', type=int, help='Number of affirmations per category')
    parser.add_argument('--all', action='store_true', help='Generate for all categories')
    parser.add_argument('--link-existing', action='store_true', help='Link existing audio files to database')

    args = parser.parse_args()

    # Handle --link-existing
    if args.link_existing:
        print("\n🔗 Linking existing audio files to database...")
        # If voice-id provided, link files in voice structure; otherwise link flat files
        linked = link_existing_files(voice_id=args.voice_id)
        print(f"\n{'='*50}")
        print(f"✅ Total linked: {linked}")
        return

    # For generation, voice-id is required
    if not args.voice_id:
        print("❌ --voice-id is required for generation")
        print("\n💡 Usage examples:")
        print("   python scripts/generate_and_link.py --voice-id YOUR_VOICE_ID --all")
        print("   python scripts/generate_and_link.py --voice-id YOUR_VOICE_ID --category Financeiro")
        print("   python scripts/generate_and_link.py --link-existing --voice-id YOUR_VOICE_ID")
        return

    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        print("❌ ELEVENLABS_API_KEY not set")
        return

    elevenlabs = ElevenLabsService(api_key)

    print(f"\n🎤 Voice ID: {args.voice_id}")
    print(f"📁 Audio path: voices/{args.voice_id}/affirmations/{{category}}/")

    total_generated = 0

    if args.all:
        # Generate for all categories
        for category_name in AFFIRMATIONS.keys():
            generated = generate_for_category(
                elevenlabs,
                args.voice_id,
                category_name,
                args.count
            )
            total_generated += generated
    elif args.category:
        # Generate for specific category
        total_generated = generate_for_category(
            elevenlabs,
            args.voice_id,
            args.category,
            args.count
        )
    else:
        print("❌ Please specify --category or --all")
        return

    print(f"\n{'='*50}")
    print(f"✅ Total generated: {total_generated}")
    print(f"\n💡 Audio files saved to: voices/{args.voice_id}/affirmations/")
    print(f"   Database updated with new audio.{args.voice_id} field")


if __name__ == '__main__':
    main()
