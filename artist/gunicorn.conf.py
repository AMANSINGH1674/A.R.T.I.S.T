"""
Gunicorn configuration for production deployment.
"""

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
backlog = 2048

# Static file serving
forwarded_allow_ips = '*'
proxy_allow_ips = '*'

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'uvicorn.workers.UvicornWorker'
worker_connections = 1000
worker_tmp_dir = '/dev/shm'
timeout = 120
keepalive = 2

# Restart workers after this many requests, to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Restart workers that haven't responded within this timeout
worker_timeout = 120

# Logging
loglevel = os.getenv('LOG_LEVEL', 'info')
accesslog = '-'
errorlog = '-'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(M)s'

# Process naming
proc_name = 'artist'

# Environment
raw_env = [
    f"DATABASE_URL={os.getenv('DATABASE_URL', 'sqlite:///./artist.db')}",
    f"REDIS_URL={os.getenv('REDIS_URL', 'redis://localhost:6379')}",
]

# Server mechanics
daemon = False
pidfile = os.getenv('GUNICORN_PID_FILE', '/var/run/artist/artist.pid')
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed in production)
keyfile = os.getenv('SSL_KEYFILE')
certfile = os.getenv('SSL_CERTFILE')

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
