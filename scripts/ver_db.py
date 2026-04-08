import sqlite3

conn = sqlite3.connect("data/traffic.db")
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
print("Tablas:", cur.fetchall())

cur.execute("""
SELECT id, interseccion, estado_circulacion, accion, regla_aplicada, timestamp_evento, creado_en
FROM decisiones_trafico
ORDER BY id DESC
LIMIT 20
""")

filas = cur.fetchall()
print("Registros:")
for fila in filas:
    print(fila)

conn.close()