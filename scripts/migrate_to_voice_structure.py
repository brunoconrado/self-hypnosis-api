#!/usr/bin/env python3
"""
Migration script: Move to voice-based audio structure

This script:
1. Seeds the VoiceModel with Harrison voice
2. Moves existing audio files to voices/{voice_id}/affirmations/{category}/
3. Updates database to use the new audio field structure

Usage:
    python scripts/migrate_to_voice_structure.py
    python scripts/migrate_to_voice_structure.py --dry-run  # Preview changes
"""

import os
import sys
import shutil
import argparse
import re
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Initialize Flask app context
from app import create_app
app = create_app()

from app.services.database import get_db
from app.models import VoiceModel, CategoryModel
from bson import ObjectId


# Voice to migrate to
VOICE_ID = 'fCxG8OHm4STbIsWe4aT9'  # Harrison Gale
VOICE_SLUG = 'harrison'
VOICE_NAME = 'Harrison Gale'


def sanitize_filename(text, max_length=50):
    """Convert affirmation text to a clean filename (matches existing logic)"""
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ASCII', 'ignore').decode('ASCII')
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', '_', text)
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


def migrate(dry_run=False):
    with app.app_context():
        db = get_db()
        storage_path = Path(app.config.get('STORAGE_LOCAL_PATH', './storage/audio'))

        print("=" * 60)
        print("MIGRATION: Voice-based Audio Structure")
        print("=" * 60)

        if dry_run:
            print("\n⚠️  DRY RUN MODE - No changes will be made\n")

        # Step 1: Seed voice
        print("\n📌 Step 1: Seed VoiceModel")
        print("-" * 40)

        existing_voice = VoiceModel.find_by_elevenlabs_id(VOICE_ID)
        if existing_voice:
            print(f"  ✓ Voice already exists: {existing_voice['name']}")
        else:
            if not dry_run:
                VoiceModel.create(
                    elevenlabs_id=VOICE_ID,
                    slug=VOICE_SLUG,
                    name=VOICE_NAME,
                    display_name='Voz Masculina Suave',
                    gender='male',
                    is_default=True
                )
                print(f"  ✓ Created voice: {VOICE_NAME}")
            else:
                print(f"  Would create voice: {VOICE_NAME}")

        # Step 2: Get categories and affirmations
        print("\n📌 Step 2: Load categories and affirmations")
        print("-" * 40)

        categories = CategoryModel.get_all()
        category_map = {str(c['id']): c for c in categories}
        print(f"  Found {len(categories)} categories")

        affirmations = list(db.affirmations.find())
        print(f"  Found {len(affirmations)} affirmations")

        # Step 3: Find existing audio files
        print("\n📌 Step 3: Find existing audio files")
        print("-" * 40)

        # Get files in root of storage (old flat structure)
        existing_files = list(storage_path.glob('*.mp3'))
        # Filter out any already in voices/ subdirectory
        existing_files = [f for f in existing_files if 'voices' not in str(f)]
        print(f"  Found {len(existing_files)} audio files to migrate")

        # Build filename -> affirmation map
        aff_by_filename = {}
        for aff in affirmations:
            filename = sanitize_filename(aff['text'])
            aff_by_filename[filename] = aff

        # Step 4: Move files and update database
        print("\n📌 Step 4: Migrate files and update database")
        print("-" * 40)

        migrated = 0
        skipped = 0
        errors = 0

        for audio_file in existing_files:
            filename_stem = audio_file.stem  # without extension

            # Find matching affirmation
            aff = aff_by_filename.get(filename_stem)
            if not aff:
                print(f"  ⚠️  No match: {filename_stem[:40]}...")
                skipped += 1
                continue

            # Get category for path
            category_id = str(aff['category_id'])
            category = category_map.get(category_id)
            if not category:
                print(f"  ⚠️  No category: {filename_stem[:40]}...")
                skipped += 1
                continue

            category_slug = get_category_slug(category['name'])

            # New path
            new_relative_path = f"voices/{VOICE_ID}/affirmations/{category_slug}/{audio_file.name}"
            new_full_path = storage_path / new_relative_path
            new_url = f"/api/audio/file/{new_relative_path}"

            print(f"  {audio_file.name}")
            print(f"    → {new_relative_path}")

            if not dry_run:
                try:
                    # Create directory
                    new_full_path.parent.mkdir(parents=True, exist_ok=True)

                    # Move file
                    shutil.move(str(audio_file), str(new_full_path))

                    # Update database - add to audio map
                    db.affirmations.update_one(
                        {'_id': aff['_id']},
                        {
                            '$set': {
                                f'audio.{VOICE_ID}': {
                                    'path': new_relative_path,
                                    'url': new_url
                                }
                            }
                        }
                    )

                    migrated += 1
                    print(f"    ✓ Migrated")

                except Exception as e:
                    errors += 1
                    print(f"    ✗ Error: {e}")
            else:
                migrated += 1

        # Step 5: Initialize audio field for affirmations without it
        print("\n📌 Step 5: Initialize audio field for remaining affirmations")
        print("-" * 40)

        if not dry_run:
            result = db.affirmations.update_many(
                {'audio': {'$exists': False}},
                {'$set': {'audio': {}}}
            )
            print(f"  Initialized {result.modified_count} affirmations")
        else:
            count = db.affirmations.count_documents({'audio': {'$exists': False}})
            print(f"  Would initialize {count} affirmations")

        # Summary
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"  Files migrated: {migrated}")
        print(f"  Files skipped:  {skipped}")
        print(f"  Errors:         {errors}")

        if dry_run:
            print("\n💡 Run without --dry-run to apply changes")
        else:
            print("\n✅ Migration complete!")
            print("\n💡 Next steps:")
            print("   1. Run: python scripts/generate_and_link.py --voice-id fCxG8OHm4STbIsWe4aT9 --all")
            print("   2. This will generate audio for remaining affirmations")


def main():
    parser = argparse.ArgumentParser(description='Migrate to voice-based audio structure')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    args = parser.parse_args()

    migrate(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
