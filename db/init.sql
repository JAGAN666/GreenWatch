-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- ============ GEOGRAPHIC BASE ============

CREATE TABLE census_tracts (
    geoid VARCHAR(11) PRIMARY KEY,
    state_fips VARCHAR(2) NOT NULL DEFAULT '51',
    county_fips VARCHAR(3) NOT NULL,
    tract_fips VARCHAR(6) NOT NULL,
    name VARCHAR(100),
    county_name VARCHAR(100),
    aland BIGINT,
    awater BIGINT,
    geom GEOMETRY(MultiPolygon, 4326),
    centroid GEOMETRY(Point, 4326),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_tracts_geom ON census_tracts USING GIST (geom);

-- ============ INDICATOR DATA (TIME-SERIES) ============

CREATE TABLE tract_indicators (
    id SERIAL PRIMARY KEY,
    geoid VARCHAR(11) REFERENCES census_tracts(geoid),
    data_year INTEGER NOT NULL,
    source VARCHAR(50) NOT NULL,

    -- ACS
    median_rent NUMERIC,
    median_home_value NUMERIC,
    median_household_income NUMERIC,
    pct_renters NUMERIC,
    pct_rent_burdened NUMERIC,
    pct_below_poverty NUMERIC,
    pct_nonwhite NUMERIC,
    pct_bachelors_plus NUMERIC,
    total_population INTEGER,
    total_households INTEGER,

    -- EJScreen
    pm25 NUMERIC,
    ozone NUMERIC,
    diesel_pm NUMERIC,
    traffic_proximity NUMERIC,
    lead_paint NUMERIC,

    -- SVI
    svi_overall NUMERIC,
    svi_socioeconomic NUMERIC,
    svi_household_comp NUMERIC,
    svi_minority NUMERIC,
    svi_housing_transport NUMERIC,

    -- FEMA NRI
    nri_risk_score NUMERIC,
    nri_flood_score NUMERIC,
    nri_heat_score NUMERIC,
    nri_hurricane_score NUMERIC,

    -- CDC PLACES
    asthma_prevalence NUMERIC,
    mental_health_not_good NUMERIC,

    -- CEJST
    cejst_disadvantaged BOOLEAN,

    -- Eviction Lab
    eviction_rate NUMERIC,
    eviction_filing_rate NUMERIC,

    -- Spatial overlay results
    tree_canopy_pct NUMERIC,
    impervious_surface_pct NUMERIC,
    park_access_10min BOOLEAN,
    flood_zone_pct NUMERIC,

    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (geoid, data_year, source)
);
CREATE INDEX idx_indicators_geoid_year ON tract_indicators(geoid, data_year);

-- ============ COMPUTED SCORES ============

CREATE TABLE tract_scores (
    id SERIAL PRIMARY KEY,
    geoid VARCHAR(11) REFERENCES census_tracts(geoid),
    score_version VARCHAR(20) NOT NULL,
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    data_year INTEGER NOT NULL,

    drs_vulnerability NUMERIC,
    drs_market_pressure NUMERIC,
    drs_green_proximity NUMERIC,
    drs_composite NUMERIC,
    drs_classification VARCHAR(20),

    ebs_air_quality NUMERIC,
    ebs_green_infra NUMERIC,
    ebs_climate_resilience NUMERIC,
    ebs_health NUMERIC,
    ebs_composite NUMERIC,

    accelerating_risk BOOLEAN DEFAULT FALSE,
    data_quality_flag BOOLEAN DEFAULT FALSE,

    UNIQUE (geoid, score_version, data_year)
);
CREATE INDEX idx_scores_geoid ON tract_scores(geoid);

-- ============ GREEN INFRASTRUCTURE REGISTRY ============

CREATE TABLE green_investments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    location GEOMETRY(Geometry, 4326),
    scale_value NUMERIC,
    scale_unit VARCHAR(20),
    completion_year INTEGER,
    source VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_investments_geom ON green_investments USING GIST (location);

-- ============ USERS ============

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    password_hash VARCHAR(255),
    role VARCHAR(20) NOT NULL DEFAULT 'policy_maker',
    organization VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============ SCENARIOS ============

CREATE TABLE scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_by UUID REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'draft',
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE interventions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id UUID REFERENCES scenarios(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    location GEOMETRY(Geometry, 4326),
    scale_value NUMERIC,
    scale_unit VARCHAR(20),
    parameters JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_interventions_geom ON interventions USING GIST (location);

CREATE TABLE mitigations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id UUID REFERENCES scenarios(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    target_geoids VARCHAR(11)[],
    parameters JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============ SIMULATION RESULTS ============

CREATE TABLE simulation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id UUID REFERENCES scenarios(id) ON DELETE CASCADE,
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    model_version VARCHAR(20),
    total_population_affected INTEGER,
    total_tracts_affected INTEGER,
    equity_score NUMERIC,
    equity_warnings INTEGER,
    summary_text TEXT
);

CREATE TABLE simulation_tract_results (
    id SERIAL PRIMARY KEY,
    simulation_id UUID REFERENCES simulation_results(id) ON DELETE CASCADE,
    geoid VARCHAR(11) REFERENCES census_tracts(geoid),
    current_drs NUMERIC,
    predicted_drs NUMERIC,
    delta_drs NUMERIC,
    current_ebs NUMERIC,
    predicted_ebs NUMERIC,
    delta_ebs NUMERIC,
    confidence_lower NUMERIC,
    confidence_upper NUMERIC,
    equity_warning BOOLEAN DEFAULT FALSE,
    UNIQUE (simulation_id, geoid)
);
