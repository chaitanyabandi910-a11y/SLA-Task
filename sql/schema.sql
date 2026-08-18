-- =========================================================
-- SLA MONITORING DASHBOARD DATABASE SCHEMA
-- =========================================================


-- =========================================================
-- 1. UPLOADS
-- Tracks every CSV uploaded into the system
-- =========================================================

CREATE TABLE IF NOT EXISTS uploads (
    upload_id BIGSERIAL PRIMARY KEY,

    filename VARCHAR(255) NOT NULL,

    uploaded_at TIMESTAMPTZ DEFAULT NOW(),

    total_rows INTEGER NOT NULL DEFAULT 0,

    duplicate_rows INTEGER NOT NULL DEFAULT 0,

    invalid_status_rows INTEGER NOT NULL DEFAULT 0,

    invalid_latency_rows INTEGER NOT NULL DEFAULT 0,

    cleaned_rows INTEGER NOT NULL DEFAULT 0,

    status VARCHAR(30) NOT NULL DEFAULT 'processing'
);


-- =========================================================
-- 2. SERVICES
-- Stores unique services found in uploaded data
-- =========================================================

CREATE TABLE IF NOT EXISTS services (
    service_id VARCHAR(100) PRIMARY KEY,

    service_name VARCHAR(150) NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW()
);


-- =========================================================
-- 3. MONITORING LOGS
-- Stores cleaned/normalized health-check observations
-- =========================================================

CREATE TABLE IF NOT EXISTS monitoring_logs (
    id BIGSERIAL PRIMARY KEY,

    upload_id BIGINT
        REFERENCES uploads(upload_id),

    service_id VARCHAR(100) NOT NULL
        REFERENCES services(service_id),

    service_name VARCHAR(150) NOT NULL,

    timestamp_utc TIMESTAMPTZ NOT NULL,

    status_code INTEGER,

    latency_ms DOUBLE PRECISION,

    agent VARCHAR(100) NOT NULL,

    region VARCHAR(100) NOT NULL,

    source_file VARCHAR(255),

    status_valid BOOLEAN NOT NULL DEFAULT TRUE,

    latency_valid BOOLEAN NOT NULL DEFAULT TRUE,

    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);


-- =========================================================
-- 4. SLA SLOTS
-- Stores the derived 15-minute service-level results
-- =========================================================

CREATE TABLE IF NOT EXISTS sla_slots (
    id BIGSERIAL PRIMARY KEY,

    upload_id BIGINT
        REFERENCES uploads(upload_id),

    service_id VARCHAR(100) NOT NULL
        REFERENCES services(service_id),

    timestamp_utc TIMESTAMPTZ NOT NULL,

    agent_count INTEGER NOT NULL DEFAULT 0,

    successful_agents INTEGER NOT NULL DEFAULT 0,

    failed_agents INTEGER NOT NULL DEFAULT 0,

    observed_records INTEGER NOT NULL DEFAULT 0,

    slot_status VARCHAR(20) NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(service_id, timestamp_utc)
);


-- =========================================================
-- 5. INDEXES
-- Improve dashboard query performance
-- =========================================================

CREATE INDEX IF NOT EXISTS idx_monitoring_logs_timestamp
ON monitoring_logs(timestamp_utc);


CREATE INDEX IF NOT EXISTS idx_monitoring_logs_service
ON monitoring_logs(service_id);


CREATE INDEX IF NOT EXISTS idx_monitoring_logs_service_timestamp
ON monitoring_logs(service_id, timestamp_utc);


CREATE INDEX IF NOT EXISTS idx_monitoring_logs_upload
ON monitoring_logs(upload_id);


CREATE INDEX IF NOT EXISTS idx_sla_slots_timestamp
ON sla_slots(timestamp_utc);


CREATE INDEX IF NOT EXISTS idx_sla_slots_service
ON sla_slots(service_id);


CREATE INDEX IF NOT EXISTS idx_sla_slots_service_timestamp
ON sla_slots(service_id, timestamp_utc);


CREATE INDEX IF NOT EXISTS idx_sla_slots_upload
ON sla_slots(upload_id);