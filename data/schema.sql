CREATE TABLE IF NOT EXISTS interseccion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    fila TEXT NOT NULL,
    columna INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sensor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seq INTEGER UNIQUE,
    codigo TEXT NOT NULL UNIQUE,
    tipo_sensor TEXT NOT NULL,
    interseccion_id INTEGER NOT NULL,
    frecuencia_seg INTEGER,
    FOREIGN KEY (interseccion_id) REFERENCES interseccion(id)
);

CREATE TABLE IF NOT EXISTS semaforo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interseccion_id INTEGER NOT NULL,
    codigo TEXT NOT NULL UNIQUE,
    estado_actual TEXT NOT NULL DEFAULT 'ROJO',
    duracion_base_seg INTEGER NOT NULL DEFAULT 15,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (interseccion_id) REFERENCES interseccion(id)
);

CREATE TABLE IF NOT EXISTS evento_sensor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seq INTEGER CHECK (seq IS NULL OR seq > 0),
    sensor_id INTEGER NOT NULL,
    interseccion_id INTEGER NOT NULL,
    tipo_evento TEXT NOT NULL,
    ts_evento TEXT NOT NULL,
    payload_json TEXT,
    recibido_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sensor_id) REFERENCES sensor(id),
    FOREIGN KEY (interseccion_id) REFERENCES interseccion(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_evento_sensor_seq
ON evento_sensor(seq)
WHERE seq IS NOT NULL;

CREATE TABLE IF NOT EXISTS evento_camara (
    evento_id INTEGER PRIMARY KEY,
    volumen INTEGER NOT NULL,
    velocidad_promedio REAL,
    FOREIGN KEY (evento_id) REFERENCES evento_sensor(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evento_espira (
    evento_id INTEGER PRIMARY KEY,
    vehiculos_contados INTEGER NOT NULL,
    intervalo_segundos INTEGER NOT NULL,
    timestamp_inicio TEXT NOT NULL,
    timestamp_fin TEXT NOT NULL,
    FOREIGN KEY (evento_id) REFERENCES evento_sensor(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evento_gps (
    evento_id INTEGER PRIMARY KEY,
    nivel_congestion TEXT NOT NULL,
    velocidad_promedio REAL,
    FOREIGN KEY (evento_id) REFERENCES evento_sensor(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS estado_trafico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interseccion_id INTEGER NOT NULL,
    ts_estado TEXT NOT NULL,
    longitud_cola INTEGER,
    conteo_vehicular INTEGER,
    densidad_trafico REAL,
    velocidad_promedio REAL,
    clasificacion TEXT NOT NULL,
    regla_aplicada TEXT,
    origen TEXT NOT NULL DEFAULT 'ANALITICA',
    FOREIGN KEY (interseccion_id) REFERENCES interseccion(id)
);

CREATE TABLE IF NOT EXISTS comando_semaforo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    semaforo_id INTEGER NOT NULL,
    interseccion_id INTEGER NOT NULL,
    tipo_comando TEXT NOT NULL,
    valor_segundos INTEGER,
    motivo TEXT,
    origen TEXT NOT NULL DEFAULT 'ANALITICA',
    estado_ejecucion TEXT NOT NULL DEFAULT 'PENDIENTE',
    solicitado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ejecutado_en TEXT,
    FOREIGN KEY (semaforo_id) REFERENCES semaforo(id),
    FOREIGN KEY (interseccion_id) REFERENCES interseccion(id)
);

CREATE TABLE IF NOT EXISTS solicitud_usuario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_solicitud TEXT NOT NULL,
    interseccion_id INTEGER,
    detalle TEXT,
    resultado_resumen TEXT,
    solicitada_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atendida_en TEXT,
    FOREIGN KEY (interseccion_id) REFERENCES interseccion(id)
);

CREATE TABLE IF NOT EXISTS solicitud_comando (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    solicitud_id INTEGER,
    comando_id INTEGER,
    FOREIGN KEY (solicitud_id) REFERENCES solicitud_usuario(id),
    FOREIGN KEY (comando_id) REFERENCES comando_semaforo(id)
);

CREATE TABLE IF NOT EXISTS evento_failover (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_evento TEXT NOT NULL,
    nodo_origen TEXT NOT NULL,
    descripcion TEXT,
    ocurrido_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_estado_interseccion_ts
ON estado_trafico(interseccion_id, ts_estado);

CREATE INDEX IF NOT EXISTS idx_evento_sensor_interseccion_ts
ON evento_sensor(interseccion_id, ts_evento);
