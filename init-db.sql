-- Create databases if they don't exist
CREATE DATABASE spec_atlas_analysis;
CREATE DATABASE spec_atlas_spec;

-- Enable pgvector extension on both databases
\c spec_atlas_analysis
CREATE EXTENSION IF NOT EXISTS vector;

\c spec_atlas_spec
CREATE EXTENSION IF NOT EXISTS vector;
