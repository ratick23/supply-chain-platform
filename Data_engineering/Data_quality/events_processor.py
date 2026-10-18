def check_events(conn, events_view, ports_view, shipments_view):
    issues = []
    total_rows = conn.execute(f"SELECT COUNT(*) FROM {events_view}").fetchone()[0]

    checks = [
        # --- 1. Conflicting Duplicates (HARD CHECK) ---
        {
            "name": "Events - Conflicting Duplicate IDs",
            "query": f"""
                SELECT COUNT(*) FROM (
                    SELECT event_id 
                    FROM (SELECT DISTINCT * FROM {events_view}) unique_rows
                    GROUP BY event_id 
                    HAVING COUNT(*) > 1
                )
            """,
            "check_type": "hard",
            "severity": "critical",
            "action": "halt and resolve conflicting records"
        },
        
        # --- 2. Exact Duplicates (SOFT CHECK) ---
        {
            "name": "Events - Exact Duplicates",
            "query": f"""
                SELECT COUNT(DISTINCT event_id) FROM (
                    SELECT * FROM {events_view}
                    GROUP BY ALL
                    HAVING COUNT(*) > 1
                )
            """,
            "check_type": "soft",
            "severity": "warning",
            "action": "deduplicate (drop identical rows) during ingestion"
        },

        # --- 3. Invalid Port Code FK Violation (HARD CHECK) ---
        {
            "name": "Events - Invalid Port Code (FK)",
            "query": f"""
                SELECT COUNT(*) 
                FROM {events_view} e 
                LEFT JOIN {ports_view} p ON e.port_code = p.port_code 
                WHERE p.port_code IS NULL
            """,
            "check_type": "hard",
            "severity": "critical",
            "action": "quarantine"
        },

        # --- 4. Invalid Vessel ID FK Violation (HARD CHECK) ---
        # Note: We take DISTINCT vessel_id from shipments to avoid fan-out in the join
        {
            "name": "Events - Invalid Vessel ID (FK)",
            "query": f"""
                SELECT COUNT(*) 
                FROM {events_view} e 
                LEFT JOIN (SELECT DISTINCT vessel_id FROM {shipments_view}) s ON e.vessel_id = s.vessel_id 
                WHERE s.vessel_id IS NULL
            """,
            "check_type": "hard",
            "severity": "critical",
            "action": "quarantine"
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