import psycopg2
from psycopg2 import pool
import configparser
import os

config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(__file__), "settings.config")
if os.path.exists(config_path):
    config.read(config_path)

# Use environment variables if available (for Docker), otherwise fallback to settings.config
db_host = os.getenv("DB_HOST", config.get("database", "host", fallback="localhost"))
db_port = os.getenv("DB_PORT", config.get("database", "port", fallback="5432"))
db_name = os.getenv("DB_NAME", config.get("database", "dbname", fallback="postgres"))
db_user = os.getenv("DB_USER", config.get("database", "user", fallback="postgres"))
db_password = os.getenv("DB_PASSWORD", config.get("database", "password", fallback="postgres"))

# Connection pool for FastAPI
db_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    host=db_host,
    port=db_port,
    dbname=db_name,
    user=db_user,
    password=db_password
)

def get_db():
    conn = db_pool.getconn()
    try:
        yield conn
    finally:
        db_pool.putconn(conn)