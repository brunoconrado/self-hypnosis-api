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

        # Get affirmations for this category
        affirmations = AffirmationModel.get_by_category(category['id'])

        if count:
            affirmations = affirmations[:count]

        print(f"\n📂 {category_name} ({len(affirmations)} affirmations)")
        print("-" * 50)

        generated = 0
        for i, aff in enumerate(affirmations):
            # Skip if already has audio
            if aff.get('default_audio_url'):
                print(f"  [{i+1}/{len(affirmations)}] ⏭️  Already has audio")
                continue

            try:
                text = aff['text']
                print(f"  [{i+1}/{len(affirmations)}] {text[:40]}...", end=" ", flush=True)

                # Generate audio
                audio_bytes = elevenlabs.generate_audio(
                    text=text,
                    voice_id=voice_id
                )

                # Create filename from affirmation text
                filename = sanitize_filename(text) + '.mp3'

                # Save to storage
                audio_file = io.BytesIO(audio_bytes)
                audio_path = storage.save_audio(audio_file, filename, 'audio/mpeg', preserve_filename=True)
                audio_url = storage.get_audio_url(audio_path)

                # Update affirmation in database
                db.affirmations.update_one(
                    {'_id': ObjectId(aff['id'])},
                    {'$set': {'default_audio_url': audio_url, 'audio_path': audio_path}}
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


def link_existing_files():
    """Link existing audio files in storage to affirmations in database"""

    with app.app_context():
        storage = get_storage()
        db = get_db()

        # Get storage path
        storage_path = Path(app.config.get('STORAGE_LOCAL_PATH', './storage/audio'))

        if not storage_path.exists():
            print(f"❌ Storage path not found: {storage_path}")
            return 0

        # Get all mp3 files
        audio_files = list(storage_path.glob('*.mp3'))
        print(f"\n🔍 Found {len(audio_files)} audio files in storage")

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

                # Skip if already linked
                if aff.get('default_audio_url'):
                    print(f"⏭️  {filename[:40]}... (already linked)")
                    continue

                # Get audio URL
                audio_path = audio_file.name
                audio_url = storage.get_audio_url(audio_path)

                # Update database
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

    # Handle --link-existing first (doesn't need voice-id or API key)
    if args.link_existing:
        print("\n🔗 Linking existing audio files to database...")
        linked = link_existing_files()
        print(f"\n{'='*50}")
        print(f"✅ Total linked: {linked}")
        return

    # For generation, voice-id is required
    if not args.voice_id:
        print("❌ --voice-id is required for generation")
        return

    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        print("❌ ELEVENLABS_API_KEY not set")
        return

    elevenlabs = ElevenLabsService(api_key)

    print(f"\n🎤 Voice ID: {args.voice_id}")

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
    print(f"\n💡 Audio is now linked in the database!")
    print(f"   Fetch affirmations from API to see audio URLs")


if __name__ == '__main__':
    main()
