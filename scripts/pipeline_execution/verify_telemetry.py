import duckdb

db_path = "outputs/pipeline_workspace/pipeline_telemetry.duckdb"
with duckdb.connect(db_path) as con:
    res = con.execute("""
        SELECT stage, status, count(*) 
        FROM pipeline_events 
        GROUP BY stage, status
        ORDER BY stage, status
    """).fetchall()
    
    print("Telemetry Events Summary:")
    for row in res:
        print(f"Stage: {row[0]}, Status: {row[1]}, Count: {row[2]}")
