import os

def check_ports(conn, ports_view, unlocode_view, data_dir, unlocode_pattern):
    issues = []
    total_rows = conn.execute(f"SELECT COUNT(*) FROM {ports_view}").fetchone()[0]

    # --- 1. Soft Check: Missing Country ---
    missing_country_query = f"SELECT COUNT(*) FROM {ports_view} WHERE country IS NULL"
    missing_country = conn.execute(missing_country_query).fetchone()[0]
    if missing_country > 0:
        issues.append({
            "check_name": "Ports - Missing Country",
            "rows_affected": missing_country,
            "percentage": round((missing_country / total_rows) * 100, 2),
            "check_type": "soft",
            "severity": "warning",
            "action": "impute"
        })

    # --- 2. Hard Check: Timezone Format Validation (Regex in DuckDB) ---
    invalid_tz_query = f"""
        SELECT COUNT(*)
        FROM {ports_view}
        WHERE timezone IS NULL
           OR NOT regexp_matches(timezone, '^UTC[+-](1[0-4]|[0-9])(:[0-5][0-9])?$')
    """
    invalid_tz = conn.execute(invalid_tz_query).fetchone()[0]
    if invalid_tz > 0:
        issues.append({
            "check_name": "Ports - Invalid Timezone Format",
            "rows_affected": invalid_tz,
            "percentage": round((invalid_tz / total_rows) * 100, 2),
            "check_type": "hard",
            "severity": "critical",
            "action": "standardize to UTC±H:MM format"
        })

    # --- 3. Dynamic UN/LOCODE Check via DuckDB View ---
    unlocode_glob_path = os.path.join(data_dir, unlocode_pattern)
    try:
        # Load raw UN/LOCODE CSVs into a unified DuckDB view without Pandas
        # Column 1 = Country Code (e.g. TH), Column 2 = Location (e.g. BKK), Column 3 = Name (e.g. Bangkok)
        # Load raw UN/LOCODE CSVs into a unified DuckDB view without Pandas
        # column01 = Country Code, column02 = Location Code, column03 = Port Name
        conn.execute(f"""
            CREATE OR REPLACE VIEW {unlocode_view} AS
            SELECT 
                TRIM(column01) || TRIM(column02) AS locode,
                LOWER(TRIM(column03)) AS official_name
            FROM read_csv(
                '{unlocode_glob_path}',
                header=false,
                auto_detect=true,
                all_varchar=true,
                ignore_errors=true
            )
            WHERE column01 IS NOT NULL AND column02 IS NOT NULL
        """)

        # Cross-join match against official names
        mismatch_query = f"""
            SELECT COUNT(*)
            FROM {ports_view} p
            JOIN {unlocode_view} u ON p.port_code = u.locode
            WHERE NOT (
                contains(LOWER(p.port_name), u.official_name) 
                OR contains(u.official_name, LOWER(p.port_name))
            )
        """
        mismatches = conn.execute(mismatch_query).fetchone()[0]

        if mismatches > 0:
            issues.append({
                "check_name": "Ports - Code & Name Mismatch (UN/LOCODE Violation)",
                "rows_affected": mismatches,
                "percentage": round((mismatches / total_rows) * 100, 2),
                "check_type": "hard",
                "severity": "critical",
                "action": "halt and fix reference data mapping"
            })

    except Exception as e:
        print(f"Skipping dynamic UN/LOCODE verification: {e}")

    return issues