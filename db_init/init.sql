-- Create tables

-- This SQL script initializes the database schema for OpenSenseMap data storage.
CREATE TABLE IF NOT EXISTS sensor_values (
                    id SERIAL PRIMARY KEY,
                    sensor_id VARCHAR(100) NOT NULL,
                    box_id VARCHAR(100) NOT NULL,
                    value DECIMAL(10,4),
                    original_timestamp TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(sensor_id, box_id, original_timestamp)
                );

-- Create a table for events data
CREATE TABLE IF NOT EXISTS sensor_events (
                    id SERIAL PRIMARY KEY,
                    event_type VARCHAR(100) NOT NULL,
                    event_data JSONB,
                    sensor_id VARCHAR(100),
                    box_id VARCHAR(100),
                    status VARCHAR(50) DEFAULT 'new data',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );