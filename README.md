# Hypnos API

Affirmation audio generation API with text-to-speech capabilities using ElevenLabs.

## Tech Stack

- **Framework:** Python Flask 3.0.0
- **Database:** MongoDB (with authentication)
- **Authentication:** JWT (Flask-JWT-Extended)
- **TTS:** ElevenLabs API
- **Server:** Gunicorn + Nginx
- **Process Manager:** Systemd

## Production Deployment

**Server IP:** `216.238.107.157`
**Base URL:** `http://216.238.107.157`

### Services Status

```bash
# Check API service
systemctl status hypnos-api

# Check Nginx
systemctl status nginx

# Check MongoDB
systemctl status mongod
```

### Useful Commands

```bash
# Restart API
sudo systemctl restart hypnos-api

# View API logs (live)
journalctl -u hypnos-api -f

# View Gunicorn logs
tail -f /home/bruno/hypnos/logs/error.log
tail -f /home/bruno/hypnos/logs/access.log

# Restart Nginx
sudo systemctl reload nginx
```

## API Endpoints

### Health Check
```
GET /api/health
Response: {"status": "ok"}
```

### Authentication
```
POST /api/auth/register    - Register new user
POST /api/auth/login       - Login user
POST /api/auth/refresh     - Refresh access token
GET  /api/auth/me          - Get current user (JWT required)
```

### Categories
```
GET /api/categories        - Get all affirmation categories
```

**Available Categories:**
- Financeiro (Financial)
- Saúde (Health)
- Sono (Sleep)
- Autoestima (Self-esteem)
- Produtividade (Productivity)

### Affirmations
```
GET  /api/affirmations/default              - Get default affirmations (public)
GET  /api/affirmations/default?voice_id=X   - Get affirmations with audio URLs for voice
GET  /api/affirmations                      - Get user's affirmations (JWT required)
POST /api/affirmations                      - Create custom affirmation (JWT required)
PUT  /api/affirmations/<id>                 - Update affirmation (JWT required)
```

### Audio Generation (Premium)
```
POST /api/generate/affirmation/<id>   - Generate audio for affirmation
POST /api/generate/preview            - Preview audio generation
POST /api/generate/batch              - Batch generate multiple affirmations
POST /api/generate/estimate           - Estimate character usage
```

### Voices
```
GET /api/voices          - Get available ElevenLabs voices
GET /api/voices/default  - Get default voice
```

### Audio Files
```
GET /api/audio/file/<path>  - Serve audio files
```

## Database

### MongoDB Connection
```
URI: mongodb://hypnos:hypno-pass@localhost:27017/hypnos?authSource=hypnos
Database: hypnos
```

### Collections
- `users` - User accounts
- `categories` - Affirmation categories (5 default)
- `affirmations` - System default affirmations (100 total)
- `user_affirmations` - User's personalized affirmations
- `user_configs` - User preferences
- `voices` - Cached ElevenLabs voice info

### MongoDB Commands
```bash
# Connect to database
mongosh -u hypnos -p hypno-pass --authenticationDatabase hypnos hypnos

# Count documents
db.affirmations.countDocuments()
db.categories.find().pretty()

# Admin access
mongosh -u admin -p admin-pass --authenticationDatabase admin
```

## File Structure

```
/home/bruno/hypnos/
├── app/                    # Flask application
│   ├── routes/             # API endpoints
│   ├── models/             # Database models
│   ├── services/           # Business logic (database, storage, elevenlabs)
│   └── data/               # Seed data
├── storage/audio/          # Audio files
│   └── voices/{voice_id}/affirmations/{category}/*.mp3
├── logs/                   # Application logs
├── deploy/                 # Deployment configs
│   ├── hypnos-api.service  # Systemd service
│   └── nginx-hypnos-api.conf
├── scripts/                # Utility scripts
├── venv/                   # Python virtual environment
├── .env                    # Environment variables
├── config.py               # Flask configuration
├── run.py                  # Application entry point
├── gunicorn.conf.py        # Gunicorn config
└── requirements.txt        # Python dependencies
```

## Audio Files

**Default Voice ID:** `fCxG8OHm4STbIsWe4aT9`
**Total Audio Files:** 100 (20 per category)

Audio files are stored at:
```
/home/bruno/hypnos/storage/audio/voices/{voice_id}/affirmations/{category}/
```

### Link Existing Audio Files
```bash
cd /home/bruno/hypnos
source venv/bin/activate
python scripts/generate_and_link.py --link-existing --voice-id fCxG8OHm4STbIsWe4aT9
```

### Generate New Audio
```bash
# Generate for all categories
python scripts/generate_and_link.py --voice-id YOUR_VOICE_ID --all

# Generate for specific category
python scripts/generate_and_link.py --voice-id YOUR_VOICE_ID --category Financeiro --count 10
```

## Environment Variables

Located at `/home/bruno/hypnos/.env`:

```bash
# Flask
FLASK_ENV=development
SECRET_KEY=your-secret-key

# JWT
JWT_SECRET_KEY=your-jwt-secret
JWT_ACCESS_TOKEN_EXPIRES=3600      # 1 hour
JWT_REFRESH_TOKEN_EXPIRES=2592000  # 30 days

# MongoDB
MONGODB_URI=mongodb://hypnos:hypno-pass@localhost:27017/hypnos?authSource=hypnos
MONGODB_DATABASE=hypnos

# Storage
STORAGE_TYPE=local
STORAGE_LOCAL_PATH=/home/bruno/hypnos/storage/audio

# ElevenLabs
ELEVENLABS_API_KEY=your-api-key
```

## Local Development

```bash
cd /home/bruno/hypnos
source venv/bin/activate

# Run development server
python run.py

# Or with Gunicorn
gunicorn --config gunicorn.conf.py run:app
```

## Deployment Files

### Systemd Service
Location: `/etc/systemd/system/hypnos-api.service`

```bash
# Enable on boot
sudo systemctl enable hypnos-api

# Start/Stop/Restart
sudo systemctl start hypnos-api
sudo systemctl stop hypnos-api
sudo systemctl restart hypnos-api
```

### Nginx Configuration
Location: `/etc/nginx/sites-enabled/hypnos-api`

- Listens on port 80
- Proxies to Gunicorn on 127.0.0.1:5000
- Serves static audio with 30-day cache

## Security Notes

For production, generate strong secrets:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Update these in `.env`:
- `SECRET_KEY`
- `JWT_SECRET_KEY`

## Troubleshooting

### API not responding
```bash
# Check if service is running
systemctl status hypnos-api

# Check logs for errors
journalctl -u hypnos-api --no-pager -n 50

# Restart service
sudo systemctl restart hypnos-api
```

### MongoDB connection issues
```bash
# Check MongoDB status
systemctl status mongod

# Test connection
mongosh -u hypnos -p hypno-pass --authenticationDatabase hypnos hypnos --eval "db.stats()"
```

### Audio files not loading
```bash
# Check file permissions
ls -la /home/bruno/hypnos/storage/audio/

# Verify Nginx config
sudo nginx -t
```
