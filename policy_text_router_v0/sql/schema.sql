CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS sources (
    source_id smallserial PRIMARY KEY,
    source_key text NOT NULL UNIQUE,
    display_name text NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    ingestion_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_key text NOT NULL,
    mode text NOT NULL CHECK (mode IN ('backfill', 'realtime', 'probe')),
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    status text NOT NULL DEFAULT 'running',
    fetched_count integer NOT NULL DEFAULT 0,
    inserted_count integer NOT NULL DEFAULT 0,
    updated_count integer NOT NULL DEFAULT 0,
    error_count integer NOT NULL DEFAULT 0,
    parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
    error_summary jsonb NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS news_items (
    news_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id smallint NOT NULL REFERENCES sources(source_id),
    source_news_id text NOT NULL,
    source_type text NOT NULL CHECK (source_type IN ('flash', 'article')),
    title text NOT NULL,
    content text NOT NULL,
    summary text NOT NULL DEFAULT '',
    url text NOT NULL,
    published_at timestamptz NOT NULL,
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    is_paid boolean NOT NULL DEFAULT false,
    content_hash char(64) NOT NULL,
    current_version integer NOT NULL DEFAULT 1,
    raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (source_id, source_news_id)
);

CREATE INDEX IF NOT EXISTS idx_news_items_published_at ON news_items (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_items_content_hash ON news_items (content_hash);
CREATE INDEX IF NOT EXISTS idx_news_items_source_type ON news_items (source_id, source_type, published_at DESC);

CREATE TABLE IF NOT EXISTS news_versions (
    news_id uuid NOT NULL REFERENCES news_items(news_id) ON DELETE CASCADE,
    version_no integer NOT NULL,
    title text NOT NULL,
    content text NOT NULL,
    summary text NOT NULL DEFAULT '',
    content_hash char(64) NOT NULL,
    raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    observed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (news_id, version_no),
    UNIQUE (news_id, content_hash)
);

CREATE TABLE IF NOT EXISTS event_clusters (
    event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_title text NOT NULL,
    event_time timestamptz,
    first_news_id uuid REFERENCES news_items(news_id),
    best_content_news_id uuid REFERENCES news_items(news_id),
    dedup_status text NOT NULL DEFAULT 'automatic'
        CHECK (dedup_status IN ('automatic', 'manual_confirmed', 'needs_review')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS event_members (
    event_id uuid NOT NULL REFERENCES event_clusters(event_id) ON DELETE CASCADE,
    news_id uuid NOT NULL REFERENCES news_items(news_id) ON DELETE CASCADE,
    match_method text NOT NULL,
    similarity double precision,
    is_first boolean NOT NULL DEFAULT false,
    is_best_content boolean NOT NULL DEFAULT false,
    PRIMARY KEY (event_id, news_id)
);

CREATE TABLE IF NOT EXISTS news_embeddings (
    news_id uuid NOT NULL REFERENCES news_items(news_id) ON DELETE CASCADE,
    embedding_model text NOT NULL,
    embedding_dimension integer NOT NULL,
    embedding vector NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (news_id, embedding_model)
);

CREATE TABLE IF NOT EXISTS sw_industries (
    classification_version text NOT NULL,
    industry_l2_code text NOT NULL,
    industry_l2_name text NOT NULL,
    industry_l1_name text NOT NULL,
    source text NOT NULL,
    active boolean NOT NULL DEFAULT true,
    PRIMARY KEY (classification_version, industry_l2_code),
    UNIQUE (classification_version, industry_l2_name)
);

CREATE TABLE IF NOT EXISTS prompt_versions (
    prompt_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    task text NOT NULL,
    version text NOT NULL,
    prompt_sha256 char(64) NOT NULL,
    prompt_text text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (task, version)
);

CREATE TABLE IF NOT EXISTS model_runs (
    model_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider text NOT NULL,
    model text NOT NULL,
    measure_prompt_version_id uuid REFERENCES prompt_versions(prompt_version_id),
    routing_prompt_version_id uuid REFERENCES prompt_versions(prompt_version_id),
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
    usage jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS measures (
    measure_row_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    news_id uuid NOT NULL REFERENCES news_items(news_id),
    event_id uuid REFERENCES event_clusters(event_id),
    model_run_id uuid NOT NULL REFERENCES model_runs(model_run_id),
    measure_id text NOT NULL,
    schema_version text NOT NULL,
    summary text NOT NULL,
    policy_action text NOT NULL,
    target text NOT NULL,
    mechanism text NOT NULL,
    evidence text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (news_id, model_run_id, measure_id)
);

CREATE TABLE IF NOT EXISTS routing_results (
    routing_result_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    measure_row_id uuid NOT NULL REFERENCES measures(measure_row_id) ON DELETE CASCADE,
    schema_version text NOT NULL,
    all_a boolean NOT NULL,
    style boolean NOT NULL,
    industry boolean NOT NULL,
    style_dimensions text[] NOT NULL DEFAULT '{}',
    primary_route text NOT NULL,
    confidence double precision NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    rationale text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (measure_row_id)
);

CREATE TABLE IF NOT EXISTS routing_industries (
    routing_result_id uuid NOT NULL REFERENCES routing_results(routing_result_id) ON DELETE CASCADE,
    classification_version text NOT NULL,
    industry_l2_code text NOT NULL,
    PRIMARY KEY (routing_result_id, classification_version, industry_l2_code),
    FOREIGN KEY (classification_version, industry_l2_code)
        REFERENCES sw_industries(classification_version, industry_l2_code)
);

CREATE TABLE IF NOT EXISTS human_annotations (
    annotation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    measure_row_id uuid NOT NULL REFERENCES measures(measure_row_id),
    annotator text NOT NULL,
    measure_valid boolean,
    all_a boolean,
    style boolean,
    industry boolean,
    correct_industry_l2_codes text[] NOT NULL DEFAULT '{}',
    error_types text[] NOT NULL DEFAULT '{}',
    notes text NOT NULL DEFAULT '',
    annotated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (measure_row_id, annotator)
);

INSERT INTO sources (source_key, display_name)
VALUES ('wallstreetcn', '华尔街见闻'), ('sina_finance', '新浪财经')
ON CONFLICT (source_key) DO UPDATE SET display_name = EXCLUDED.display_name;

