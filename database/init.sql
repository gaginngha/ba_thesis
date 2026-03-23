-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Swiss Municipality Master Data
CREATE TABLE cantons (
    id SERIAL PRIMARY KEY,
    bfs_number SMALLINT UNIQUE NOT NULL,  -- BFS canton number (1-26)
    abbreviation VARCHAR(2) UNIQUE NOT NULL,  -- e.g. ZH, BE, LU
    name_de VARCHAR(100) NOT NULL,
    name_fr VARCHAR(100),
    name_it VARCHAR(100),
    name_rm VARCHAR(100)
);

CREATE TABLE districts (
    id SERIAL PRIMARY KEY,
    bfs_number SMALLINT UNIQUE NOT NULL,
    name_de VARCHAR(200) NOT NULL,
    canton_id INTEGER REFERENCES cantons(id) NOT NULL
);

CREATE TABLE municipalities (
    id SERIAL PRIMARY KEY,
    bfs_number INTEGER UNIQUE NOT NULL,  -- Official BFS municipality number
    name VARCHAR(200) NOT NULL,
    canton_id INTEGER REFERENCES cantons(id) NOT NULL,
    district_id INTEGER REFERENCES districts(id),
    population INTEGER,
    area_km2 NUMERIC(10, 2),
    altitude_m INTEGER,
    municipality_type VARCHAR(50),  -- urban, suburban, rural, etc.
    geometry GEOMETRY(MultiPolygon, 2056),  -- Swiss LV95 coordinate system
    is_active BOOLEAN DEFAULT TRUE,  -- FALSE for merged municipalities
    merged_into_bfs INTEGER,  -- BFS number of successor municipality
    valid_from DATE,
    valid_until DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_municipalities_bfs ON municipalities(bfs_number);
CREATE INDEX idx_municipalities_canton ON municipalities(canton_id);
CREATE INDEX idx_municipalities_geometry ON municipalities USING GIST(geometry);

-- Financial Data (EFV / Federal Finance Administration)
CREATE TABLE financial_data (
    id SERIAL PRIMARY KEY,
    municipality_bfs INTEGER NOT NULL REFERENCES municipalities(bfs_number),
    year SMALLINT NOT NULL,
    -- Revenue
    total_revenue NUMERIC(15, 2),       -- Gesamtertrag
    tax_revenue NUMERIC(15, 2),         -- Steuerertrag
    fiscal_equalization NUMERIC(15, 2), -- Finanzausgleich
    -- Expenditure
    total_expenditure NUMERIC(15, 2),   -- Gesamtaufwand
    personnel_expenditure NUMERIC(15, 2), -- Personalaufwand
    -- Balance
    operating_result NUMERIC(15, 2),    -- Ergebnis Erfolgsrechnung
    -- Balance sheet
    total_assets NUMERIC(15, 2),        -- Gesamtvermögen
    financial_assets NUMERIC(15, 2),    -- Finanzvermögen
    total_liabilities NUMERIC(15, 2),   -- Gesamtfremdkapital
    net_debt NUMERIC(15, 2),            -- Nettoschuld
    equity NUMERIC(15, 2),              -- Eigenkapital
    -- Key indicators (per capita)
    revenue_per_capita NUMERIC(10, 2),
    expenditure_per_capita NUMERIC(10, 2),
    net_debt_per_capita NUMERIC(10, 2),
    tax_revenue_per_capita NUMERIC(10, 2),
    -- HRM2 indicators
    self_financing_ratio NUMERIC(8, 4),     -- Selbstfinanzierungsgrad (%)
    self_financing_capacity NUMERIC(15, 2), -- Selbstfinanzierung
    debt_ratio NUMERIC(8, 4),               -- Verschuldungsgrad (%)
    interest_burden_ratio NUMERIC(8, 4),    -- Zinsbelastungsanteil (%)
    investment_ratio NUMERIC(8, 4),         -- Investitionsanteil (%)
    capital_service_ratio NUMERIC(8, 4),    -- Kapitaldienstanteil (%)
    net_debt_quota NUMERIC(8, 4),           -- Nettoverschuldungsquotient
    -- Metadata
    data_source VARCHAR(50) DEFAULT 'efv',
    accounting_standard VARCHAR(20),  -- HRM1, HRM2
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(municipality_bfs, year, data_source)
);

CREATE INDEX idx_financial_municipality ON financial_data(municipality_bfs);
CREATE INDEX idx_financial_year ON financial_data(year);

-- Tax Data
CREATE TABLE tax_data (
    id SERIAL PRIMARY KEY,
    municipality_bfs INTEGER NOT NULL REFERENCES municipalities(bfs_number),
    year SMALLINT NOT NULL,
    tax_multiplier NUMERIC(8, 2),         -- Steuerfuss (%)
    income_tax_index NUMERIC(8, 2),       -- Steuerbelastung Einkommen
    wealth_tax_index NUMERIC(8, 2),       -- Steuerbelastung Vermögen
    corporate_tax_index NUMERIC(8, 2),    -- Steuerbelastung juristische Personen
    tax_revenue_per_capita NUMERIC(10, 2),
    data_source VARCHAR(50) DEFAULT 'efv',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(municipality_bfs, year)
);

-- Demographic Data (BFS)
CREATE TABLE demographic_data (
    id SERIAL PRIMARY KEY,
    municipality_bfs INTEGER NOT NULL REFERENCES municipalities(bfs_number),
    year SMALLINT NOT NULL,
    population_total INTEGER,
    population_swiss INTEGER,
    population_foreign INTEGER,
    foreign_share NUMERIC(6, 2),
    population_male INTEGER,
    population_female INTEGER,
    -- Age structure
    age_0_19 INTEGER,
    age_20_39 INTEGER,
    age_40_64 INTEGER,
    age_65_plus INTEGER,
    dependency_ratio NUMERIC(8, 4),       -- Altersquotient
    youth_ratio NUMERIC(8, 4),            -- Jugendquotient
    -- Movement
    births INTEGER,
    deaths INTEGER,
    natural_change INTEGER,
    immigration INTEGER,
    emigration INTEGER,
    net_migration INTEGER,
    population_growth_rate NUMERIC(8, 4),
    data_source VARCHAR(50) DEFAULT 'bfs',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(municipality_bfs, year)
);

-- Economic Data (BFS STATENT)
CREATE TABLE economic_data (
    id SERIAL PRIMARY KEY,
    municipality_bfs INTEGER NOT NULL REFERENCES municipalities(bfs_number),
    year SMALLINT NOT NULL,
    total_establishments INTEGER,       -- Arbeitsstätten
    total_employment INTEGER,           -- Beschäftigte
    full_time_equivalents NUMERIC(12, 2), -- Vollzeitäquivalente
    -- Sector breakdown
    primary_sector_employment INTEGER,    -- Sektor 1 (Landwirtschaft)
    secondary_sector_employment INTEGER,  -- Sektor 2 (Industrie)
    tertiary_sector_employment INTEGER,   -- Sektor 3 (Dienstleistungen)
    -- Derived
    employment_per_capita NUMERIC(8, 4),
    sector_diversity_index NUMERIC(8, 4), -- Herfindahl index
    data_source VARCHAR(50) DEFAULT 'bfs_statent',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(municipality_bfs, year)
);

-- Composite Scores (calculated)
CREATE TABLE composite_scores (
    id SERIAL PRIMARY KEY,
    municipality_bfs INTEGER NOT NULL REFERENCES municipalities(bfs_number),
    year SMALLINT NOT NULL,
    -- Sub-scores (0-100 scale)
    financial_health_score NUMERIC(6, 2),
    tax_attractiveness_score NUMERIC(6, 2),
    demographic_vitality_score NUMERIC(6, 2),
    economic_strength_score NUMERIC(6, 2),
    -- Overall composite score
    composite_score NUMERIC(6, 2),
    -- Peer group
    peer_group VARCHAR(50),     -- e.g. "urban_large", "rural_small"
    peer_group_rank INTEGER,
    national_rank INTEGER,
    cantonal_rank INTEGER,
    -- Metadata
    scoring_version VARCHAR(20),
    calculated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(municipality_bfs, year, scoring_version)
);

-- Municipality mergers history
CREATE TABLE municipality_mergers (
    id SERIAL PRIMARY KEY,
    old_bfs_number INTEGER NOT NULL,
    old_name VARCHAR(200) NOT NULL,
    new_bfs_number INTEGER NOT NULL,
    new_name VARCHAR(200) NOT NULL,
    merge_date DATE NOT NULL,
    canton_bfs SMALLINT NOT NULL
);

CREATE INDEX idx_mergers_old ON municipality_mergers(old_bfs_number);
CREATE INDEX idx_mergers_new ON municipality_mergers(new_bfs_number);

-- Insert all 26 cantons
INSERT INTO cantons (bfs_number, abbreviation, name_de, name_fr, name_it) VALUES
(1, 'ZH', 'Zürich', 'Zurich', 'Zurigo'),
(2, 'BE', 'Bern', 'Berne', 'Berna'),
(3, 'LU', 'Luzern', 'Lucerne', 'Lucerna'),
(4, 'UR', 'Uri', 'Uri', 'Uri'),
(5, 'SZ', 'Schwyz', 'Schwyz', 'Svitto'),
(6, 'OW', 'Obwalden', 'Obwald', 'Obvaldo'),
(7, 'NW', 'Nidwalden', 'Nidwald', 'Nidvaldo'),
(8, 'GL', 'Glarus', 'Glaris', 'Glarona'),
(9, 'ZG', 'Zug', 'Zoug', 'Zugo'),
(10, 'FR', 'Freiburg', 'Fribourg', 'Friburgo'),
(11, 'SO', 'Solothurn', 'Soleure', 'Soletta'),
(12, 'BS', 'Basel-Stadt', 'Bâle-Ville', 'Basilea Città'),
(13, 'BL', 'Basel-Landschaft', 'Bâle-Campagne', 'Basilea Campagna'),
(14, 'SH', 'Schaffhausen', 'Schaffhouse', 'Sciaffusa'),
(15, 'AR', 'Appenzell Ausserrhoden', 'Appenzell Rhodes-Extérieures', 'Appenzello Esterno'),
(16, 'AI', 'Appenzell Innerrhoden', 'Appenzell Rhodes-Intérieures', 'Appenzello Interno'),
(17, 'SG', 'St. Gallen', 'Saint-Gall', 'San Gallo'),
(18, 'GR', 'Graubünden', 'Grisons', 'Grigioni'),
(19, 'AG', 'Aargau', 'Argovie', 'Argovia'),
(20, 'TG', 'Thurgau', 'Thurgovie', 'Turgovia'),
(21, 'TI', 'Ticino', 'Tessin', 'Ticino'),
(22, 'VD', 'Waadt', 'Vaud', 'Vaud'),
(23, 'VS', 'Wallis', 'Valais', 'Vallese'),
(24, 'NE', 'Neuenburg', 'Neuchâtel', 'Neuchâtel'),
(25, 'GE', 'Genf', 'Genève', 'Ginevra'),
(26, 'JU', 'Jura', 'Jura', 'Giura');
