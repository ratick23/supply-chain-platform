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

def transform_silver(config):
    conn = get_db_connection(config)
    cursor = conn.cursor()

    # 1. Transform Ports (SCD2)
    print("Transforming silver_ports...")
    cursor.execute("""
        UPDATE silver_ports
        SET valid_to = CURRENT_TIMESTAMP, is_active = FALSE
        WHERE is_active = TRUE
          AND port_code IN (
              SELECT bp.port_code FROM bronze_ports bp
              JOIN silver_ports sp ON bp.port_code = sp.port_code AND sp.is_active = TRUE
              WHERE COALESCE(NULLIF(TRIM(bp.country), ''), 'UNKNOWN') != sp.country
                 OR bp.region != sp.region
                 OR bp.timezone != sp.timezone
                 OR NULLIF(TRIM(bp.avg_congestion_score), '')::NUMERIC != sp.avg_congestion_score
          );

        INSERT INTO silver_ports (
            port_code, port_name, country, region, timezone, avg_congestion_score,
            valid_from, valid_to, is_active
        )
        SELECT 
            bp.port_code,
            bp.port_name,
            COALESCE(NULLIF(TRIM(bp.country), ''), 'UNKNOWN') AS country,
            bp.region,
            bp.timezone,
            NULLIF(TRIM(bp.avg_congestion_score), '')::NUMERIC,
            CURRENT_TIMESTAMP,
            '9999-12-31 23:59:59'::TIMESTAMP,
            TRUE
        FROM bronze_ports bp
        LEFT JOIN silver_ports sp ON bp.port_code = sp.port_code AND sp.is_active = TRUE
        WHERE sp.port_sk IS NULL;
    """)

    # 2. Transform Shipments (SCD2 + Status Standardization + Derived Metrics)
    print("Transforming silver_shipments...")
    cursor.execute("""
        CREATE TEMP TABLE clean_shipments_staging AS
        SELECT 
            bs.shipment_id,
            bs.customer_id,
            bs.origin_port,
            bs.destination_port,
            bs.vessel_id,
            NULLIF(TRIM(bs.booking_date), '')::TIMESTAMP AS booking_date,
            NULLIF(TRIM(bs.planned_departure), '')::TIMESTAMP AS planned_departure,
            NULLIF(TRIM(bs.actual_departure), '')::TIMESTAMP AS actual_departure,
            NULLIF(TRIM(bs.planned_arrival), '')::TIMESTAMP AS planned_arrival,
            NULLIF(TRIM(bs.actual_arrival), '')::TIMESTAMP AS actual_arrival,
            NULLIF(TRIM(bs.container_count), '')::INT AS container_count,
            COALESCE(NULLIF(TRIM(bs.cargo_type), ''), 'UNKNOWN') AS cargo_type,
            ABS(NULLIF(TRIM(bs.weight_tons), '')::NUMERIC) AS weight_tons,
            CASE 
                WHEN UPPER(TRIM(bs.status)) IN ('DELIVERED', 'COMPLETE', 'COMPLETED') THEN 'COMPLETED'
                WHEN UPPER(TRIM(bs.status)) = 'DELAYED' THEN 'DELAYED'
                WHEN UPPER(TRIM(bs.status)) = 'CANCELLED' THEN 'CANCELLED'
                ELSE 'UNKNOWN'
            END AS status,
            (bs.origin_port || '->' || bs.destination_port) AS route_key,
            ROUND(
                EXTRACT(EPOCH FROM (NULLIF(TRIM(bs.actual_arrival), '')::TIMESTAMP - NULLIF(TRIM(bs.planned_arrival), '')::TIMESTAMP)) / 3600.0, 
                2
            ) AS actual_delay_hours,
            CASE 
                WHEN (EXTRACT(EPOCH FROM (NULLIF(TRIM(bs.actual_arrival), '')::TIMESTAMP - NULLIF(TRIM(bs.planned_arrival), '')::TIMESTAMP)) / 3600.0) <= 24.0 THEN TRUE
                ELSE FALSE 
            END AS on_time_flag,
            EXTRACT(DAY FROM (NULLIF(TRIM(bs.planned_arrival), '')::TIMESTAMP - NULLIF(TRIM(bs.planned_departure), '')::TIMESTAMP))::INT AS transit_days_planned,
            EXTRACT(DAY FROM (NULLIF(TRIM(bs.actual_arrival), '')::TIMESTAMP - NULLIF(TRIM(bs.actual_departure), '')::TIMESTAMP))::INT AS transit_days_actual
        FROM bronze_shipments bs
        JOIN silver_ports p1 ON bs.origin_port = p1.port_code AND p1.is_active = TRUE
        JOIN silver_ports p2 ON bs.destination_port = p2.port_code AND p2.is_active = TRUE
        WHERE NULLIF(TRIM(bs.container_count), '')::INT > 0
          AND bs.shipment_id IS NOT NULL;

        UPDATE silver_shipments
        SET valid_to = CURRENT_TIMESTAMP, is_active = FALSE
        WHERE is_active = TRUE
          AND shipment_id IN (
              SELECT cs.shipment_id FROM clean_shipments_staging cs
              JOIN silver_shipments ss ON cs.shipment_id = ss.shipment_id AND ss.is_active = TRUE
              WHERE cs.status != ss.status
                 OR cs.weight_tons != ss.weight_tons
                 OR cs.actual_arrival IS DISTINCT FROM ss.actual_arrival
          );

        INSERT INTO silver_shipments (
            shipment_id, customer_id, origin_port, destination_port, vessel_id,
            booking_date, planned_departure, actual_departure, planned_arrival, actual_arrival,
            container_count, cargo_type, weight_tons, status, route_key,
            actual_delay_hours, on_time_flag, transit_days_planned, transit_days_actual,
            valid_from, valid_to, is_active
        )
        SELECT 
            cs.shipment_id, cs.customer_id, cs.origin_port, cs.destination_port, cs.vessel_id,
            cs.booking_date, cs.planned_departure, cs.actual_departure, cs.planned_arrival, cs.actual_arrival,
            cs.container_count, cs.cargo_type, cs.weight_tons, cs.status, cs.route_key,
            cs.actual_delay_hours, cs.on_time_flag, cs.transit_days_planned, cs.transit_days_actual,
            CURRENT_TIMESTAMP, '9999-12-31 23:59:59'::TIMESTAMP, TRUE
        FROM clean_shipments_staging cs
        LEFT JOIN silver_shipments ss ON cs.shipment_id = ss.shipment_id AND ss.is_active = TRUE
        WHERE ss.shipment_sk IS NULL;

        DROP TABLE clean_shipments_staging;
    """)

    # 3. Transform Events (SCD2)
    print("Transforming silver_events...")
    cursor.execute("""
        INSERT INTO silver_events (
            event_id, event_timestamp, port_code, vessel_id, event_type,
            delay_minutes, notes, valid_from, valid_to, is_active
        )
        SELECT 
            be.event_id,
            NULLIF(TRIM(be.event_timestamp), '')::TIMESTAMP,
            be.port_code,
            be.vessel_id,
            be.event_type,
            NULLIF(TRIM(be.delay_minutes), '')::INT,
            be.notes,
            CURRENT_TIMESTAMP,
            '9999-12-31 23:59:59'::TIMESTAMP,
            TRUE
        FROM bronze_events be
        LEFT JOIN silver_events se ON be.event_id = se.event_id AND se.is_active = TRUE
        WHERE se.event_sk IS NULL;
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("Silver stage completed successfully.")

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read("settings.config")
    transform_silver(config)