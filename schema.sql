-- schema.sql — creación idempotente (sin DROP TABLE)
-- Se puede ejecutar múltiples veces sin borrar datos existentes.

PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS interseccion (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo     TEXT NOT NULL UNIQUE,
    fila       TEXT NOT NULL,
    columna    INTEGER NOT NULL,
    activa     INTEGER NOT NULL DEFAULT 1 CHECK (activa IN (0,1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (length(trim(fila)) = 1),
    CHECK (columna > 0)
);

CREATE TABLE IF NOT EXISTS sensor (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo          TEXT NOT NULL UNIQUE,
    tipo_sensor     TEXT NOT NULL CHECK (tipo_sensor IN ('CAMARA','ESPIRA_INDUCTIVA','GPS')),
    interseccion_id INTEGER NOT NULL,
    frecuencia_seg  INTEGER CHECK (frecuencia_seg IS NULL OR frecuencia_seg > 0),
    activo          INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (interseccion_id) REFERENCES interseccion(id) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS semaforo (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    interseccion_id  INTEGER NOT NULL,
    codigo           TEXT NOT NULL UNIQUE,
    via              TEXT,
    estado_actual    TEXT NOT NULL CHECK (estado_actual IN ('ROJO','VERDE')),
    duracion_base_seg INTEGER NOT NULL DEFAULT 15 CHECK (duracion_base_seg > 0),
    activo           INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    updated_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (interseccion_id) REFERENCES interseccion(id) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS evento_sensor (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    seq             INTEGER NOT NULL UNIQUE CHECK (seq > 0),
    sensor_id       INTEGER NOT NULL,
    interseccion_id INTEGER NOT NULL,
    tipo_evento     TEXT NOT NULL CHECK (tipo_evento IN ('LONGITUD_COLA','CONTEO_VEHICULAR','DENSIDAD_TRAFICO')),
    ts_evento       TEXT NOT NULL,
    recibido_en     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    payload_json    TEXT,
    FOREIGN KEY (sensor_id) REFERENCES sensor(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (interseccion_id) REFERENCES interseccion(id) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS evento_camara (
    evento_id          INTEGER PRIMARY KEY,
    volumen            INTEGER NOT NULL CHECK (volumen >= 0),
    velocidad_promedio REAL NOT NULL CHECK (velocidad_promedio >= 0),
    FOREIGN KEY (evento_id) REFERENCES evento_sensor(id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evento_espira (
    evento_id          INTEGER PRIMARY KEY,
    vehiculos_contados INTEGER NOT NULL CHECK (vehiculos_contados >= 0),
    intervalo_segundos INTEGER NOT NULL CHECK (intervalo_segundos > 0),
    timestamp_inicio   TEXT NOT NULL,
    timestamp_fin      TEXT NOT NULL,
    FOREIGN KEY (evento_id) REFERENCES evento_sensor(id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evento_gps (
    evento_id          INTEGER PRIMARY KEY,
    nivel_congestion   TEXT NOT NULL CHECK (nivel_congestion IN ('BAJA','NORMAL','ALTA')),
    velocidad_promedio REAL NOT NULL CHECK (velocidad_promedio >= 0),
    FOREIGN KEY (evento_id) REFERENCES evento_sensor(id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS estado_trafico (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    interseccion_id    INTEGER NOT NULL,
    ts_estado          TEXT NOT NULL,
    longitud_cola      INTEGER CHECK (longitud_cola IS NULL OR longitud_cola >= 0),
    conteo_vehicular   INTEGER CHECK (conteo_vehicular IS NULL OR conteo_vehicular >= 0),
    densidad_trafico   REAL CHECK (densidad_trafico IS NULL OR densidad_trafico >= 0),
    velocidad_promedio REAL CHECK (velocidad_promedio IS NULL OR velocidad_promedio >= 0),
    clasificacion      TEXT NOT NULL CHECK (clasificacion IN ('NORMAL','CONGESTION','PRIORIZACION')),
    regla_aplicada     TEXT,
    origen             TEXT NOT NULL CHECK (origen IN ('ANALITICA','MANUAL')),
    FOREIGN KEY (interseccion_id) REFERENCES interseccion(id) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS comando_semaforo (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    semaforo_id      INTEGER NOT NULL,
    interseccion_id  INTEGER NOT NULL,
    tipo_comando     TEXT NOT NULL CHECK (tipo_comando IN (
                         'CAMBIAR_A_VERDE','CAMBIAR_A_ROJO','EXTENDER_VERDE','PRIORIZAR_VIA','RESET_CICLO'
                     )),
    valor_segundos   INTEGER CHECK (valor_segundos IS NULL OR valor_segundos >= 0),
    motivo           TEXT,
    origen           TEXT NOT NULL CHECK (origen IN ('ANALITICA','USUARIO','SISTEMA')),
    estado_ejecucion TEXT NOT NULL DEFAULT 'PENDIENTE' CHECK (estado_ejecucion IN ('PENDIENTE','EJECUTADO','FALLIDO')),
    solicitado_en    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ejecutado_en     TEXT,
    FOREIGN KEY (semaforo_id) REFERENCES semaforo(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (interseccion_id) REFERENCES interseccion(id) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS solicitud_usuario (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_solicitud  TEXT NOT NULL CHECK (tipo_solicitud IN (
                        'CONSULTA_HISTORICA','CONSULTA_PUNTUAL','CAMBIO_MANUAL','PRIORIZAR_AMBULANCIA'
                    )),
    interseccion_id INTEGER,
    fecha_inicio    TEXT,
    fecha_fin       TEXT,
    detalle         TEXT,
    solicitada_en   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atendida_en     TEXT,
    resultado_resumen TEXT,
    FOREIGN KEY (interseccion_id) REFERENCES interseccion(id) ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS solicitud_comando (
    solicitud_id INTEGER NOT NULL,
    comando_id   INTEGER NOT NULL,
    PRIMARY KEY (solicitud_id, comando_id),
    FOREIGN KEY (solicitud_id) REFERENCES solicitud_usuario(id) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (comando_id) REFERENCES comando_semaforo(id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evento_failover (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_evento TEXT NOT NULL CHECK (tipo_evento IN (
                    'HEALTHCHECK_OK','HEALTHCHECK_FAIL','SWITCH_TO_REPLICA','RETURN_TO_PRIMARY'
                )),
    nodo_origen TEXT NOT NULL CHECK (nodo_origen IN ('PC1','PC2','PC3')),
    descripcion TEXT,
    ocurrido_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_interseccion_codigo ON interseccion(codigo);
CREATE INDEX IF NOT EXISTS idx_sensor_interseccion ON sensor(interseccion_id);
CREATE INDEX IF NOT EXISTS idx_sensor_tipo ON sensor(tipo_sensor);
CREATE INDEX IF NOT EXISTS idx_semaforo_interseccion ON semaforo(interseccion_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_evento_sensor_seq ON evento_sensor(seq);
CREATE INDEX IF NOT EXISTS idx_evento_sensor_interseccion_ts ON evento_sensor(interseccion_id, ts_evento);
CREATE INDEX IF NOT EXISTS idx_evento_sensor_sensor_ts ON evento_sensor(sensor_id, ts_evento);
CREATE INDEX IF NOT EXISTS idx_estado_trafico_interseccion_ts ON estado_trafico(interseccion_id, ts_estado);
CREATE INDEX IF NOT EXISTS idx_comando_semaforo_interseccion_fecha ON comando_semaforo(interseccion_id, solicitado_en);
CREATE INDEX IF NOT EXISTS idx_comando_semaforo_semaforo_fecha ON comando_semaforo(semaforo_id, solicitado_en);
CREATE INDEX IF NOT EXISTS idx_solicitud_usuario_fecha ON solicitud_usuario(solicitada_en);
CREATE INDEX IF NOT EXISTS idx_failover_fecha ON evento_failover(ocurrido_en);

DROP TRIGGER IF EXISTS trg_comando_ejecutado_actualiza_semaforo;
CREATE TRIGGER trg_comando_ejecutado_actualiza_semaforo
AFTER UPDATE OF estado_ejecucion ON comando_semaforo
FOR EACH ROW
WHEN NEW.estado_ejecucion = 'EJECUTADO'
     AND NEW.tipo_comando IN ('CAMBIAR_A_VERDE','CAMBIAR_A_ROJO')
BEGIN
    UPDATE semaforo
    SET estado_actual = CASE
        WHEN NEW.tipo_comando = 'CAMBIAR_A_VERDE' THEN 'VERDE'
        WHEN NEW.tipo_comando = 'CAMBIAR_A_ROJO'  THEN 'ROJO'
        ELSE estado_actual
    END,
    updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.semaforo_id;
END;

DROP TRIGGER IF EXISTS trg_semaforo_updated_at;
CREATE TRIGGER trg_semaforo_updated_at
AFTER UPDATE ON semaforo
FOR EACH ROW
BEGIN
    UPDATE semaforo SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

COMMIT;
PRAGMA foreign_keys = ON;
