# Gunicorn configuration file
import multiprocessing

# Bind to localhost, nginx will handle external connections
bind = "127.0.0.1:5000"

# Number of worker processes
workers = multiprocessing.cpu_count() * 2 + 1

# Worker class
worker_class = "sync"

# Timeout for worker processes
timeout = 120

# Keep alive connections
keepalive = 5

# Logging
accesslog = "/home/bruno/hypnos/logs/access.log"
errorlog = "/home/bruno/hypnos/logs/error.log"
loglevel = "info"

# Process naming
proc_name = "hypnos-api"

# Daemonize (set to False when using systemd)
daemon = False
