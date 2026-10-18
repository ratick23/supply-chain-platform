import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import configparser
import os

def load_config():
    config = configparser.ConfigParser()
    config.read("settings.config")
    return config

def init_database():
    config = load_config()
    db = config["database"]
    
    # 1. Connect to the default 'postgres' database first using container credentials
    try:
        conn = psycopg2.connect(
            host=db["host"],
            port=db["port"],
            dbname="postgres",  # Connect to default system database
            user=db["user"],
            password=db["password"]
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db['dbname']}'")
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f"CREATE DATABASE {db['dbname']}")
            print(f"Database '{db['dbname']}' created successfully.")
        else:
            print(f"Database '{db['dbname']}' already exists.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error connecting to default PostgreSQL server: {e}")
        return

    # 2. Now connect to our newly created target database and execute the DDL script
    try:
        conn = psycopg2.connect(
            host=db["host"],
            port=db["port"],
            dbname=db["dbname"],
            user=db["user"],
            password=db["password"]
        )
        cursor = conn.cursor()
        
        ddl_path = "ddl_schemas.sql"
        if os.path.exists(ddl_path):
            with open(ddl_path, "r") as f:
                cursor.execute(f.read())
            conn.commit()
            print("DDL schemas executed successfully.")
        else:
            print(f"Error: {ddl_path} not found.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error executing DDL: {e}")

if __name__ == "__main__":
    init_database()