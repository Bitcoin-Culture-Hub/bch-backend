import redis
import os

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST"),#update
    port=os.getenv("REDIS_PORT"), #update
    password=os.getenv("REDIS_PASSWORD"), #update
    decode_responses=True   # bytes to strings
)