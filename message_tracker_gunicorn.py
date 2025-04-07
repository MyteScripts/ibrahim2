import multiprocessing

bind = "0.0.0.0:5000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
timeout = 60
keepalive = 5
capture_output = True
errorlog = "-"  # Log to stderr
accesslog = "-"  # Log to stdout
loglevel = "info"