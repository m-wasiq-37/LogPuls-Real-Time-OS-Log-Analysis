import datetime, random
levels = ["INFO","WARNING","ERROR"]
sources = ["System","Auth","Kernel","App","Net","Service","DB","UI"]
messages = ["Service started","Connection lost","Disk nearing capacity","User login failed","Task completed","Unexpected error occurred","Configuration updated","Permission denied","Timeout reached","Resource created","Cache cleared","Background job ran"]
def sample_stream():
    while True:
        yield {'timestamp': datetime.datetime.utcnow().isoformat(), 'level': random.choice(levels), 'source': random.choice(sources), 'message': random.choice(messages)}
