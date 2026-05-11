import cx_Oracle

def get_tablespace_info(dsn, user, password):
    try:
        conn = cx_Oracle.connect(user, password, dsn)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT tablespace_name,
                   ROUND(SUM(bytes)/1024/1024, 2) total_mb,
                   ROUND(SUM(bytes - NVL(free,0))/1024/1024, 2) used_mb,
                   ROUND(SUM(NVL(free,0))/1024/1024, 2) free_mb,
                   ROUND((SUM(bytes - NVL(free,0))/SUM(bytes))*100, 2) pct_used
            FROM (SELECT tablespace_name, SUM(bytes) bytes FROM dba_data_files GROUP BY tablespace_name)
            LEFT JOIN (SELECT tablespace_name, SUM(bytes) free FROM dba_free_space GROUP BY tablespace_name)
                USING (tablespace_name)
            GROUP BY tablespace_name
            ORDER BY tablespace_name
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows
    except Exception as e:
        return [('ERROR', str(e))]
