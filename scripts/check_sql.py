import sqlite3

def check_db():
    conn = sqlite3.connect(r"runs\test_run_bd1177c4\Maintain\eplusout.sql")
    cursor = conn.cursor()
    cursor.execute("SELECT ReportDataDictionaryIndex, Name, Units, ReportingFrequency FROM ReportDataDictionary WHERE ReportingFrequency='Hourly'")
    rows = cursor.fetchall()
    
    print("Meters/Variables found:")
    for row in rows:
        if 'electricity' in row[1].lower() or 'temperature' in row[1].lower() or 'hvac' in row[1].lower():
            print(row)
            
    # Check Time
    cursor.execute("SELECT Month, Day, COUNT(*) FROM Time GROUP BY Month, Day")
    print("\nDates simulated:")
    for row in cursor.fetchall():
        print(row)
        
    conn.close()

if __name__ == '__main__':
    check_db()
