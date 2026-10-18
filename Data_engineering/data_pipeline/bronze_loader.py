import os
import psycopg2
import configparser

def get_db_connection(config):
    db = config["database"]
    return psycopg2.connect(
        host=db["host"],
        port=db["port"],
        dbname=db["dbname"],
        user=db["user"],
        password=db["password"]
    )

def load_bronze(config):
    raw_dir = config["paths"]["raw_data_dir"]
    conn = get_db_connection(config)
    cursor = conn.cursor()

    files_and_tables = [
        (os.path.join(raw_dir, "ports 2.csv"), "bronze_ports"),
        (os.path.join(raw_dir, "shipments 2.csv"), "bronze_shipments"),
        (os.path.join(raw_dir, "port_events 2.csv"), "bronze_events")
    ]

    for file_path, table_name in files_and_tables:
        print(f"Loading {file_path} into {table_name}...")
        cursor.execute(f"TRUNCATE TABLE {table_name};")
        
        with open(file_path, "r", encoding="utf-8") as f:
            cursor.copy_expert(f"COPY {table_name} FROM STDIN WITH CSV HEADER", f)
            
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        count = cursor.fetchone()[0]
        print(f"Loaded {count} rows into {table_name}.")

    conn.commit()
    cursor.close()
    conn.close()
    print("Bronze stage completed successfully.")

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read("settings.config")
    load_bronze(config)