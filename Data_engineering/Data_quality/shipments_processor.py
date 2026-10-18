def check_shipments(conn, shipments_view, ports_view):
    issues = []
    total_rows = conn.execute(f"SELECT COUNT(*) FROM {shipments_view}").fetchone()[0]

    checks = [
        # Hard Checks
        # --- 1. Conflicting Duplicates (HARD CHECK) ---
        # If we take DISTINCT rows and STILL have duplicate shipment_ids, 
        # it means the same ID has contradictory data in other columns.
        {
            "name": "Shipments - Conflicting Duplicate IDs",
            "query": f"""
                SELECT COUNT(*) FROM (
                    SELECT shipment_id 
                    FROM (SELECT DISTINCT * FROM {shipments_view}) unique_rows
                    GROUP BY shipment_id 
                    HAVING COUNT(*) > 1
                )
            """,
            "check_type": "hard",
            "severity": "critical",
            "action": "halt and resolve conflicting records"
        },

        # --- 2. Exact Duplicates (SOFT CHECK) ---
        # The entire row is duplicated exactly. We can safely drop these in the Silver layer.
        {
            "name": "Shipments - Exact Duplicates",
            "query": f"""
                SELECT COUNT(DISTINCT shipment_id) FROM (
                    SELECT * FROM {shipments_view}
                    GROUP BY ALL
                    HAVING COUNT(*) > 1
                )
            """,
            "check_type": "soft",
            "severity": "warning",
            "action": "deduplicate (drop identical rows) during ingestion"
        },
        {
            "name": "Shipments - Invalid Origin Port (FK)",
            "query": f"""
                SELECT COUNT(*) 
                FROM {shipments_view} s 
                LEFT JOIN {ports_view} p ON s.origin_port = p.port_code 
                WHERE p.port_code IS NULL
            """,
            "check_type": "hard",
            "severity": "critical",
            "action": "quarantine"
        },
        {
            "name": "Shipments - Invalid Destination Port (FK)",
            "query": f"""
                SELECT COUNT(*) 
                FROM {shipments_view} s 
                LEFT JOIN {ports_view} p ON s.destination_port = p.port_code 
                WHERE p.port_code IS NULL
            """,
            "check_type": "hard",
            "severity": "critical",
            "action": "quarantine"
        },
        {
            "name": "Shipments - Arrival Before Departure",
            "query": f"""
                SELECT COUNT(*) 
                FROM {shipments_view} 
                WHERE TRY_CAST(planned_arrival AS TIMESTAMP) < TRY_CAST(planned_departure AS TIMESTAMP)
            """,
            "check_type": "hard",
            "severity": "critical",
            "action": "flag for review"
        },
        # Soft Checks
        {
            "name": "Shipments - Negative Weights",
            "query": f"SELECT COUNT(*) FROM {shipments_view} WHERE weight_tons < 0",
            "check_type": "soft",
            "severity": "warning",
            "action": "flag and investigate"
        },
        {
            "name": "Shipments - Invalid Containers (<=0)",
            "query": f"SELECT COUNT(*) FROM {shipments_view} WHERE container_count <= 0",
            "check_type": "soft",
            "severity": "warning",
            "action": "drop"
        },
        {
            "name": "Shipments - Missing Cargo Type",
            "query": f"SELECT COUNT(*) FROM {shipments_view} WHERE cargo_type IS NULL",
            "check_type": "soft",
            "severity": "warning",
            "action": "fill with 'UNKNOWN'"
        },
        {
            "name": "Shipments - Inconsistent Status Case",
            "query": f"SELECT COUNT(*) FROM {shipments_view} WHERE status != UPPER(status)",
            "check_type": "soft",
            "severity": "warning",
            "action": "convert to UPPERCASE"
        }
    ]

    for check in checks:
        count = conn.execute(check["query"]).fetchone()[0]
        if count > 0:
            issues.append({
                "check_name": check["name"],
                "rows_affected": count,
                "percentage": round((count / total_rows) * 100, 2),
                "check_type": check["check_type"],
                "severity": check["severity"],
                "action": check["action"]
            })

    return issues