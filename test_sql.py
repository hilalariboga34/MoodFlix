import pyodbc

try:
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=localhost\\SQLEXPRESS;'
        'DATABASE=MoodFlixDB;'
        'Trusted_Connection=yes;'
    )
    print("✅ Bağlantı başarılı!")

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sys.tables")
    tables = cursor.fetchall()
    print("Tablolar:", [t[0] for t in tables])

except Exception as e:
    print("❌ Bağlantı hatası:", e)

finally:
    if 'conn' in locals():
        conn.close()
