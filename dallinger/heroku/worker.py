"""Heroku web worker."""

from future.builtins import map
import os
import redis


listen = ['high', 'default', 'low']
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
conn = redis.from_url(redis_url)

if __name__ == '__main__':
    from rq import (
        Worker,
        Queue,
        Connection
    )
    try:
        from rq_gevent_worker import GeventWorker as Worker
    except ImportError:
        pass

    with Connection(conn):
        worker = Worker(list(map(Queue, listen)))
        worker.work()
