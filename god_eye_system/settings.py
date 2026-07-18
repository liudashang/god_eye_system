# -*- coding: utf-8 -*-
"""Application configuration.

Most configuration is set via environment variables.

For local development, use a .env file to set
environment variables.
"""
from environs import Env

env = Env()
env.read_env()

ENV = env.str("FLASK_ENV", default="production")
DEBUG = ENV == "development"
DATABASE_NAME = env.str("DATABASE_NAME")
DATABASE_USER = env.str("DATABASE_USER")
DATABASE_PASSWORD = env.str("DATABASE_PASSWORD")
DATABASE_HOST = env.str("DATABASE_HOST")
DATABASE_PORT = env.int("DATABASE_PORT")
SQLALCHEMY_DATABASE_URI = env.str("DATABASE_URL")
SECRET_KEY = env.str("SECRET_KEY")
SEND_FILE_MAX_AGE_DEFAULT = env.int("SEND_FILE_MAX_AGE_DEFAULT")
BCRYPT_LOG_ROUNDS = env.int("BCRYPT_LOG_ROUNDS", default=13)
DEBUG_TB_ENABLED = DEBUG
DEBUG_TB_INTERCEPT_REDIRECTS = False
CACHE_TYPE = (
    "flask_caching.backends.SimpleCache"  # Can be "MemcachedCache", "RedisCache", etc.
)
SQLALCHEMY_TRACK_MODIFICATIONS = False
DOWNLOAD_FILE_PATH = env.str("DOWNLOAD_FILE_PATH")
GRAFANA_PING_DELAY_URL = env.str("GRAFANA_PING_DELAY_URL")
GRAFANA_DROP_RATE_URL = env.str("GRAFANA_DROP_RATE_URL")
CLICKHOUSE_HOST = env.str("CLICKHOUSE_HOST")
CLICKHOUSE_USER = env.str("CLICKHOUSE_USER")
CLICKHOUSE_PASSWORD = env.str("CLICKHOUSE_PASSWORD")
CLICKHOUSE_PORT = env.int("CLICKHOUSE_PORT")
CLICKHOUSE_DATABASE = env.str("CLICKHOUSE_DATABASE")
