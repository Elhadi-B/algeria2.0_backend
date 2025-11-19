# Production Hosting Requirements

This document outlines all requirements and configurations needed to deploy the Pitch Judging application to production.

## 🖥️ Server Requirements

### Backend (Django)
- **Python**: 3.10 or higher (3.11+ recommended)
- **Python Package Manager**: pip
- **WSGI/ASGI Server**: 
  - Gunicorn (for WSGI/HTTP)
  - Uvicorn or Daphne (for ASGI/WebSocket support)
- **Process Manager**: 
  - systemd (Linux)
  - Supervisor
  - PM2 (Node.js process manager)

### Frontend (React/Vite)
- **Node.js**: 18.x or higher (20.x recommended)
- **Package Manager**: npm or yarn
- **Build Tool**: Vite (included in dependencies)
- **Web Server**: Nginx or Apache (for serving static files)

### Database
- **PostgreSQL**: 12+ (recommended for production)
  - Alternative: SQLite (only for small deployments, not recommended for production)

### Cache/Message Broker (Optional but Recommended)
- **Redis**: 6.0+ (required for WebSocket real-time updates)
  - Used for Django Channels WebSocket support
  - Can also be used for caching

## 📦 Dependencies

### Backend Python Packages
All listed in `requirements.txt`:
- Django==5.2.7
- djangorestframework==3.15.2
- channels==4.2.0
- channels-redis==4.2.1
- Pillow==11.0.0
- python-dotenv==1.0.1
- psycopg2-binary==2.9.10
- reportlab==4.2.5
- django-cors-headers==4.6.0
- dj-database-url==2.1.0
- drf-spectacular==0.27.2

### Frontend Node Packages
All listed in `package.json` - install via `npm install`

## 🔐 Environment Variables (.env file)

Create a `.env` file in `backend/pitching_day/pitching_day/` with the following:

```env
# SECURITY - REQUIRED
# Generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY=your-generated-secret-key-here

# DEBUG - MUST BE FALSE IN PRODUCTION
DEBUG=False

# ALLOWED HOSTS - Add your domain(s)
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,api.yourdomain.com

# DATABASE - PostgreSQL (recommended)
DATABASE_URL=postgresql://username:password@localhost:5432/pitching_day
# OR use individual settings:
# DB_NAME=pitching_day
# DB_USER=postgres
# DB_PASSWORD=your_secure_password
# DB_HOST=localhost
# DB_PORT=5432

# REDIS - For WebSocket support (required for real-time updates)
REDIS_URL=redis://localhost:6379/0

# CORS - Frontend domain(s)
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# CSRF - Trusted origins
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# BASE URL - Your production API URL
BASE_URL=https://api.yourdomain.com
```

## 🔒 Security Settings for Production

Update these in `settings.py` or via environment variables:

1. **DEBUG**: Must be `False`
2. **SECRET_KEY**: Must be a strong, randomly generated key
3. **ALLOWED_HOSTS**: Must include your domain(s)
4. **CSRF_COOKIE_SECURE**: Set to `True` (requires HTTPS)
5. **SESSION_COOKIE_SECURE**: Set to `True` (requires HTTPS)
6. **CORS_ALLOW_ALL_ORIGINS**: Must be `False` in production
7. **CORS_ALLOWED_ORIGINS**: Must specify exact frontend domain(s)

## 📁 Static & Media Files

### Static Files
- Run: `python manage.py collectstatic`
- Serve via Nginx/Apache or CDN (AWS S3, CloudFront, etc.)
- Set `STATIC_ROOT` in settings

### Media Files
- Store in `MEDIA_ROOT` directory
- Serve via Nginx/Apache or cloud storage (AWS S3, etc.)
- Ensure proper permissions (read/write for Django, read for web server)

## 🌐 Web Server Configuration

### Nginx Example Configuration

```nginx
# Backend API
server {
    listen 80;
    server_name api.yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    # Static files
    location /static/ {
        alias /path/to/pitching_day/pitching_day/staticfiles/;
    }
    
    # Media files
    location /media/ {
        alias /path/to/pitching_day/pitching_day/media/;
    }
    
    # Django API
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
    }
    
    # WebSocket support
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Frontend
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    root /path/to/frontend/score-shuttle/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass https://api.yourdomain.com;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🚀 Deployment Steps

### 1. Backend Setup

```bash
# Install Python dependencies
cd backend/pitching_day/pitching_day
pip install -r requirements.txt

# Create .env file with production values
cp env.example .env
# Edit .env with production values

# Run migrations
python manage.py migrate

# Create superuser (admin)
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Seed criteria (if needed)
python manage.py seed_criteria
```

### 2. Run Backend with Gunicorn + Uvicorn

```bash
# Install Gunicorn and Uvicorn
pip install gunicorn uvicorn

# Run with Gunicorn (HTTP)
gunicorn pitching_day.wsgi:application --bind 0.0.0.0:8000 --workers 4

# OR run with Uvicorn (ASGI - supports WebSocket)
uvicorn pitching_day.asgi:application --host 0.0.0.0 --port 8000
```

### 3. Frontend Build

```bash
cd frontend/score-shuttle

# Install dependencies
npm install

# Build for production
npm run build

# Output will be in dist/ directory
```

### 4. Process Management (systemd example)

Create `/etc/systemd/system/pitching-day.service`:

```ini
[Unit]
Description=Pitch Judging Django Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/pitching_day/pitching_day
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn pitching_day.asgi:application --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable pitching-day
sudo systemctl start pitching-day
```

## 📋 Pre-Deployment Checklist

- [ ] Generate new `SECRET_KEY` for production
- [ ] Set `DEBUG=False` in `.env`
- [ ] Configure `ALLOWED_HOSTS` with production domain(s)
- [ ] Set up PostgreSQL database
- [ ] Configure Redis for WebSocket support
- [ ] Set `CORS_ALLOWED_ORIGINS` to frontend domain(s)
- [ ] Set `CSRF_TRUSTED_ORIGINS` to frontend domain(s)
- [ ] Enable HTTPS/SSL certificates
- [ ] Set `CSRF_COOKIE_SECURE=True`
- [ ] Set `SESSION_COOKIE_SECURE=True`
- [ ] Run database migrations
- [ ] Create admin superuser
- [ ] Collect static files
- [ ] Build frontend for production
- [ ] Configure web server (Nginx/Apache)
- [ ] Set up process manager (systemd/supervisor)
- [ ] Test API endpoints
- [ ] Test WebSocket connections
- [ ] Test file uploads
- [ ] Configure firewall rules
- [ ] Set up backup strategy
- [ ] Configure logging
- [ ] Set up monitoring/error tracking

## 🔍 Monitoring & Logging

### Recommended Tools
- **Error Tracking**: Sentry, Rollbar
- **Monitoring**: New Relic, Datadog, Prometheus
- **Logging**: ELK Stack, CloudWatch, Papertrail

### Django Logging Configuration
Add to `settings.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## 🌍 Cloud Hosting Options

### Recommended Platforms
1. **AWS**: EC2 + RDS + ElastiCache (Redis) + S3
2. **DigitalOcean**: Droplet + Managed Database + Managed Redis
3. **Heroku**: Easy deployment (add-ons for PostgreSQL, Redis)
4. **Railway**: Simple deployment with built-in PostgreSQL
5. **Render**: Easy deployment with PostgreSQL and Redis
6. **Vercel/Netlify**: For frontend (static hosting)
7. **Azure**: App Service + Azure Database + Azure Cache

### Docker Deployment (Optional)
Consider creating Docker containers for easier deployment:
- Dockerfile for Django backend
- Dockerfile for React frontend
- docker-compose.yml for orchestration

## 📞 Support & Troubleshooting

### Common Issues
1. **WebSocket not working**: Ensure Redis is running and `REDIS_URL` is set
2. **CORS errors**: Check `CORS_ALLOWED_ORIGINS` matches frontend domain
3. **Static files 404**: Run `collectstatic` and check Nginx configuration
4. **Database connection**: Verify PostgreSQL credentials and network access
5. **CSRF errors**: Check `CSRF_TRUSTED_ORIGINS` includes frontend domain

### Health Check Endpoint
The API includes health check endpoints that can be monitored.

---

**Last Updated**: 2025-01-20
**Version**: 1.0.0

