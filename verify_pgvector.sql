-- Run this in Neon SQL Editor to verify pgvector extension
-- If it doesn't exist, it will be created

CREATE EXTENSION IF NOT EXISTS vector;

-- Verify it's installed
SELECT * FROM pg_extension WHERE extname = 'vector';
