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

def build_gold(config):
    conn = get_db_connection(config)
    cursor = conn.cursor()

    print("Populating Gold dimensions...")
    cursor.execute("""
        -- Refresh Dimensions
        TRUNCATE TABLE dim_port CASCADE;
        INSERT INTO dim_port (port_sk, port_code, port_name, country, region, timezone)
        SELECT port_sk, port_code, port_name, country, region, timezone
        FROM silver_ports
        WHERE is_active = TRUE;

        INSERT INTO dim_customer (customer_id)
        SELECT DISTINCT customer_id FROM silver_shipments WHERE customer_id IS NOT NULL
        ON CONFLICT (customer_id) DO NOTHING;

        INSERT INTO dim_vessel (vessel_id)
        SELECT DISTINCT vessel_id FROM silver_shipments WHERE vessel_id IS NOT NULL
        ON CONFLICT (vessel_id) DO NOTHING;
    """)

    print("Populating fact_shipment...")
    cursor.execute("""
        TRUNCATE TABLE fact_shipment;
        INSERT INTO fact_shipment (
            shipment_sk, shipment_id, customer_sk, vessel_sk,
            origin_port_sk, destination_port_sk, status,
            actual_delay_hours, on_time_flag
        )
        SELECT 
            ss.shipment_sk,
            ss.shipment_id,
            dc.customer_sk,
            dv.vessel_sk,
            dp_orig.port_sk,
            dp_dest.port_sk,
            ss.status,
            ss.actual_delay_hours,
            ss.on_time_flag
        FROM silver_shipments ss
        LEFT JOIN dim_customer dc ON ss.customer_id = dc.customer_id
        LEFT JOIN dim_vessel dv ON ss.vessel_id = dv.vessel_id
        LEFT JOIN dim_port dp_orig ON ss.origin_port = dp_orig.port_code
        LEFT JOIN dim_port dp_dest ON ss.destination_port = dp_dest.port_code
        WHERE ss.is_active = TRUE;
    """)

    print("Populating fact_route_stats...")
    cursor.execute("""
        TRUNCATE TABLE fact_route_stats;
        INSERT INTO fact_route_stats (
            route_key, origin_port_sk, destination_port_sk,
            shipment_count, average_delay_hours, on_time_rate_pct
        )
        SELECT 
            ss.route_key,
            dp_orig.port_sk,
            dp_dest.port_sk,
            COUNT(ss.shipment_sk) AS shipment_count,
            ROUND(AVG(ss.actual_delay_hours), 2) AS average_delay_hours,
            ROUND((SUM(CASE WHEN ss.on_time_flag = TRUE THEN 1 ELSE 0 END)::DECIMAL / NULLIF(COUNT(ss.shipment_sk), 0)) * 100, 2) AS on_time_rate_pct
        FROM silver_shipments ss
        JOIN dim_port dp_orig ON ss.origin_port = dp_orig.port_code
        JOIN dim_port dp_dest ON ss.destination_port = dp_dest.port_code
        WHERE ss.is_active = TRUE
        GROUP BY ss.route_key, dp_orig.port_sk, dp_dest.port_sk;
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("Gold stage completed successfully.")

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read("settings.config")
    build_gold(config)