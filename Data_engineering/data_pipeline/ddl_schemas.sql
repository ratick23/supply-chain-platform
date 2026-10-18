-- ==========================================
-- BRONZE LAYER (Staging / Truncate & Load)
-- Note: Bronze tables are truncated in the Python loader, not dropped here.
-- ==========================================
CREATE TABLE IF NOT EXISTS bronze_ports (
    port_code VARCHAR(50),
    port_name VARCHAR(255),
    country VARCHAR(100),
    region VARCHAR(100),
    timezone VARCHAR(50),
    avg_congestion_score VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS bronze_shipments (
    shipment_id VARCHAR(50),
    customer_id VARCHAR(50),
    origin_port VARCHAR(50),
    destination_port VARCHAR(50),
    vessel_id VARCHAR(50),
    booking_date VARCHAR(50),
    planned_departure VARCHAR(50),
    actual_departure VARCHAR(50),
    planned_arrival VARCHAR(50),
    actual_arrival VARCHAR(50),
    container_count VARCHAR(50),
    cargo_type VARCHAR(100),
    weight_tons VARCHAR(50),
    status VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS bronze_events (
    event_id VARCHAR(50),
    event_timestamp VARCHAR(50),
    port_code VARCHAR(50),
    vessel_id VARCHAR(50),
    event_type VARCHAR(100),
    delay_minutes VARCHAR(50),
    notes TEXT
);

-- ==========================================
-- SILVER LAYER (Curated Master Tables with SCD2)
-- ==========================================
CREATE TABLE IF NOT EXISTS silver_ports (
    port_sk SERIAL PRIMARY KEY,
    port_code VARCHAR(50) NOT NULL,
    port_name VARCHAR(255),
    country VARCHAR(100),
    region VARCHAR(100),
    timezone VARCHAR(50),
    avg_congestion_score NUMERIC(5,2),
    valid_from TIMESTAMP NOT NULL,
    valid_to TIMESTAMP NOT NULL,
    is_active BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS silver_shipments (
    shipment_sk SERIAL PRIMARY KEY,
    shipment_id VARCHAR(50) NOT NULL,
    customer_id VARCHAR(50),
    origin_port VARCHAR(50),
    destination_port VARCHAR(50),
    vessel_id VARCHAR(50),
    booking_date TIMESTAMP,
    planned_departure TIMESTAMP,
    actual_departure TIMESTAMP,
    planned_arrival TIMESTAMP,
    actual_arrival TIMESTAMP,
    container_count INT,
    cargo_type VARCHAR(100),
    weight_tons NUMERIC(10,2),
    status VARCHAR(50),
    route_key VARCHAR(100),
    actual_delay_hours NUMERIC(10,2),
    on_time_flag BOOLEAN,
    transit_days_planned INT,
    transit_days_actual INT,
    valid_from TIMESTAMP NOT NULL,
    valid_to TIMESTAMP NOT NULL,
    is_active BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS silver_events (
    event_sk SERIAL PRIMARY KEY,
    event_id VARCHAR(50) NOT NULL,
    event_timestamp TIMESTAMP,
    port_code VARCHAR(50),
    vessel_id VARCHAR(50),
    event_type VARCHAR(100),
    delay_minutes INT,
    notes TEXT,
    valid_from TIMESTAMP NOT NULL,
    valid_to TIMESTAMP NOT NULL,
    is_active BOOLEAN NOT NULL
);

-- ==========================================
-- GOLD LAYER (Star Schema / Serving)
-- ==========================================
CREATE TABLE IF NOT EXISTS dim_port (
    port_sk INT PRIMARY KEY,
    port_code VARCHAR(50),
    port_name VARCHAR(255),
    country VARCHAR(100),
    region VARCHAR(100),
    timezone VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS dim_customer (
    customer_sk SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_vessel (
    vessel_sk SERIAL PRIMARY KEY,
    vessel_id VARCHAR(50) UNIQUE
);

CREATE TABLE IF NOT EXISTS fact_shipment (
    shipment_sk INT PRIMARY KEY,
    shipment_id VARCHAR(50),
    customer_sk INT REFERENCES dim_customer(customer_sk),
    vessel_sk INT REFERENCES dim_vessel(vessel_sk),
    origin_port_sk INT REFERENCES dim_port(port_sk),
    destination_port_sk INT REFERENCES dim_port(port_sk),
    status VARCHAR(50),
    actual_delay_hours NUMERIC(10,2),
    on_time_flag BOOLEAN
);

CREATE TABLE IF NOT EXISTS fact_route_stats (
    route_key VARCHAR(100) PRIMARY KEY,
    origin_port_sk INT REFERENCES dim_port(port_sk),
    destination_port_sk INT REFERENCES dim_port(port_sk),
    shipment_count INT,
    average_delay_hours NUMERIC(10,2),
    on_time_rate_pct NUMERIC(5,2)
);