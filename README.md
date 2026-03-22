# GreenWatch

**AI-powered climate equity platform that helps cities invest in climate resilience without displacing vulnerable communities.**

Cities spend billions on parks, transit, and urban greening to fight climate change. But these investments often drive up property values and rents, pushing out the very communities they're meant to protect. This is called **green gentrification**.

GreenWatch predicts, simulates, and optimizes climate investments for both environmental impact and social equity.

---

## The Problem

Every year, billions are spent on climate infrastructure with good intentions. But:
- Parks increase nearby property values by 8-20%
- Transit investments trigger rapid gentrification
- Tree planting programs correlate with rising rents
- Vulnerable populations are displaced under the guise of sustainability

**No tool existed to predict this before the money is spent.**

## The Solution

GreenWatch is a decision tool that lets city planners answer one question:

> *"If we build this park here — who benefits, who gets displaced, and what can we do to prevent it?"*

### How It Works

1. **Score every neighborhood** — 85,000+ US census tracts scored for displacement risk (DRS) and environmental benefit (EBS) using real federal data
2. **Simulate interventions** — Place a park, transit stop, or greenway on the map. Instantly see how displacement risk changes across surrounding communities
3. **Optimize with AI** — Let the system recommend locations that maximize climate benefit while minimizing displacement
4. **Add policy protections** — Toggle rent stabilization, community land trusts, or affordable housing mandates. Watch displacement risk drop in real-time

---

## Features

| Feature | Description |
|---------|-------------|
| **Displacement Risk Score (DRS)** | Composite score (0-100) combining rent burden, poverty, demographics, eviction risk, and social vulnerability |
| **Environmental Benefit Score (EBS)** | Composite score (0-100) measuring air quality, green infrastructure, climate resilience, and health outcomes |
| **Simulation Engine** | Place parks, transit, trees, flood protection, greenways, or green roofs. Predict DRS/EBS changes for all affected tracts |
| **AI Optimize** | Find the optimal location that maximizes environmental benefit while minimizing displacement risk |
| **Policy Protections** | Simulate the effect of rent stabilization, community land trusts, affordable housing mandates, and community benefit agreements |
| **Equity Alerts** | Automatic warnings when interventions threaten vulnerable communities |
| **85K+ Census Tracts** | Full US coverage with real federal data |
| **PMTiles Vector Map** | Fast, interactive map rendering 85,000 tract polygons via Cloudflare R2 CDN |

---

## Data Sources

All data is from real federal sources — no synthetic or proxy data for core indicators.

| Source | Data | Tracts |
|--------|------|--------|
| **US Census ACS** (5-year) | Income, rent, demographics, housing, education | 85,396 |
| **EPA EJScreen** | PM2.5, ozone, diesel PM, traffic proximity, lead paint | 85,396 |
| **FEMA National Risk Index** | Flood, heat wave, hurricane risk scores | 85,154 |
| **CDC/ATSDR SVI** | Social vulnerability across 4 themes | 84,120 |
| **CDC PLACES** | Asthma prevalence, mental health indicators | 83,522 |
| **CEJST (Justice40)** | Federal disadvantaged community designations | 66,987 |
| **Eviction Proxy** | Eviction risk derived from ACS housing stress indicators | 85,381 |

---

## Scoring Methodology

### Displacement Risk Score (DRS)

Based on the [Urban Displacement Project](https://www.urbandisplacement.org/) and [Urban Institute](https://www.urban.org/) methodologies.

**Three domains, percentile-ranked:**

| Domain | Weight | Indicators |
|--------|--------|------------|
| **Vulnerability** | 40% | % renters, rent burden, poverty, non-white population, education, eviction rate, SVI score |
| **Market Pressure** | 35% | 5-year changes in median rent, home value, income, demographics |
| **Green Proximity** | 25% | Distance to existing and proposed green infrastructure |

**Classification:** 0-25 Low | 25-50 Moderate | 50-75 High | 75-100 Critical

### Environmental Benefit Score (EBS)

| Domain | Weight | Indicators |
|--------|--------|------------|
| **Air Quality** | 30% | PM2.5, ozone, diesel PM (inverted — lower exposure = higher score) |
| **Green Infrastructure** | 30% | Tree canopy, park access, impervious surface |
| **Climate Resilience** | 25% | Flood, heat, hurricane risk (inverted) |
| **Health Outcomes** | 15% | Asthma prevalence, mental health |

### Simulation Engine

When a user places an intervention:
1. Finds all census tracts within the impact radius using PostGIS spatial queries
2. Predicts EBS improvement based on intervention type and scale
3. Predicts DRS increase based on vulnerability multiplier (more vulnerable = more displacement pressure)
4. Applies policy mitigation discounts (rent stabilization reduces DRS delta)
5. Flags equity warnings when high-DRS tracts face significant additional pressure

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 16, TypeScript, Tailwind CSS |
| **Map** | MapLibre GL JS, PMTiles (vector tiles) |
| **Tile Hosting** | Cloudflare R2 (CDN, zero egress) |
| **Scoring Engine** | Python 3.12, FastAPI |
| **Database** | PostgreSQL 16 + PostGIS 3.4 |
| **Data Pipeline** | Python ETL scripts |
| **Deployment** | Vercel (frontend), Docker (backend) |

---

## Architecture

```
┌─────────────────────────────────────────┐
│           Next.js Frontend              │
│  ┌─────────────┐  ┌──────────────────┐  │
│  │ MapLibre GL  │  │ Decision Panel   │  │
│  │ + PMTiles    │  │ + AI Optimize    │  │
│  └─────────────┘  └──────────────────┘  │
│           API Routes (Proxy)            │
└──────────────┬──────────────────────────┘
               │
       ┌───────▼───────┐     ┌──────────────────┐
       │ Python FastAPI │     │ Cloudflare R2    │
       │ Scoring Engine │     │ PMTiles (154 MB) │
       │ - DRS/EBS      │     │ 85K tract tiles  │
       │ - Simulation   │     └──────────────────┘
       │ - Optimize     │
       └───────┬───────┘
               │
       ┌───────▼───────┐
       │ PostgreSQL +   │
       │ PostGIS        │
       │ 85,529 tracts  │
       │ 7 data sources │
       └───────────────┘
```

---

## Getting Started

### Prerequisites

- **Node.js** 18+
- **Python** 3.12+
- **Docker** (for PostgreSQL + PostGIS)
- **tippecanoe** (`brew install tippecanoe`) — for rebuilding PMTiles

### 1. Clone and install

```bash
git clone https://github.com/JAGAN666/GreenWatch.git
cd GreenWatch

# Frontend
cd frontend && npm install && cd ..

# Python backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r scoring/requirements.txt
pip install psycopg2-binary pandas numpy scipy scikit-learn requests python-dotenv sqlalchemy geoalchemy2 pyshp
```

### 2. Set up environment

```bash
cp .env.example .env
# Edit .env with your Census API key (free: https://api.census.gov/data/key_signup.html)
```

### 3. Start the database

```bash
docker compose up -d db
```

### 4. Load data

Download census tract shapefiles (all 56 state ZIPs) from:
https://www2.census.gov/geo/tiger/TIGER2023/TRACT/

Place them in a folder and update the path in `pipeline/etl/load_tracts.py`.

```bash
source .venv/bin/activate
python pipeline/run_pipeline.py
```

This loads ~85,000 census tracts with data from 7 federal sources.

### 5. Compute scores

```bash
cd scoring
uvicorn app.main:app --port 8000 &
curl -X POST http://localhost:8000/scoring/recompute
```

### 6. Run locally

```bash
# Terminal 1 — Database
docker compose up -d db

# Terminal 2 — Scoring service
source .venv/bin/activate && cd scoring && uvicorn app.main:app --port 8000

# Terminal 3 — Frontend
cd frontend && npm run dev
```

Open **http://localhost:3000**

---

## Project Structure

```
GreenWatch/
├── frontend/                    # Next.js frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx            # Landing page
│   │   │   ├── map/page.tsx        # Main simulation workbench
│   │   │   └── api/               # API route proxies
│   │   │       ├── simulate/       # → scoring service
│   │   │       └── optimize/       # → scoring service
│   │   ├── components/
│   │   │   ├── map/
│   │   │   │   ├── TractMap.tsx    # MapLibre + PMTiles map
│   │   │   │   └── Legend.tsx
│   │   │   └── panels/
│   │   │       ├── InterventionBuilder.tsx
│   │   │       ├── DecisionPanel.tsx
│   │   │       └── TractDetail.tsx
│   │   └── lib/
│   │       ├── constants.ts        # Shared constants
│   │       ├── types.ts            # TypeScript interfaces
│   │       └── scoring-client.ts   # API client
│   └── public/                     # Static assets
│
├── scoring/                     # Python FastAPI backend
│   ├── app/
│   │   ├── main.py                # FastAPI app
│   │   ├── db.py                  # Database connection
│   │   ├── api/
│   │   │   ├── simulate.py        # POST /scoring/simulate
│   │   │   ├── optimize.py        # POST /scoring/optimize
│   │   │   ├── tract.py           # GET /scoring/tract/{geoid}
│   │   │   └── recompute.py       # POST /scoring/recompute
│   │   ├── scoring/
│   │   │   ├── displacement_risk.py
│   │   │   ├── environmental_benefit.py
│   │   │   └── simulation_engine.py
│   │   └── models/
│   │       └── tract.py           # SQLAlchemy ORM models
│   ├── requirements.txt
│   └── Dockerfile
│
├── pipeline/                    # Data ETL pipeline
│   ├── run_pipeline.py            # Orchestrator
│   ├── config.py                  # Weights, radii, API keys
│   └── etl/
│       ├── load_tracts.py         # Census TIGER geometries
│       ├── acs_ingester.py        # Census ACS 5-Year
│       ├── svi_ingester.py        # CDC Social Vulnerability
│       ├── nri_ingester.py        # FEMA National Risk Index
│       ├── places_ingester.py     # CDC PLACES health data
│       ├── cejst_ingester.py      # Justice40 designations
│       ├── ejscreen_ingester.py   # EPA EJScreen
│       └── eviction_ingester.py   # Eviction risk proxy
│
├── db/init.sql                  # PostgreSQL + PostGIS schema
├── docker-compose.yml           # Database + services
└── .env.example                 # Environment template
```

---

## API Endpoints

### Scoring Service (Python FastAPI — port 8000)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/scoring/health` | Health check |
| `GET` | `/scoring/tract/{geoid}` | Full tract detail with scores, indicators, time-series |
| `POST` | `/scoring/simulate` | Simulate interventions, predict DRS/EBS changes |
| `POST` | `/scoring/optimize` | Find optimal location for an intervention type |
| `POST` | `/scoring/recompute` | Recompute all DRS/EBS scores |

### Frontend API Routes (Next.js — port 3000)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/tracts` | GeoJSON FeatureCollection (with optional `?state=` filter) |
| `POST` | `/api/simulate` | Proxy to scoring service |
| `POST` | `/api/optimize` | Proxy to scoring service |

---

## Key Validation Results

Tested with 30 simulations across 20 US cities:

| Test | Result |
|------|--------|
| Core simulation (20 cities) | 20/20 pass |
| Mitigation effectiveness | Rent stabilization eliminates equity warnings |
| Intervention type ranking | Transit > Park > Trees > Flood (displacement impact) |
| Scale linearity | 1 acre → +0.6 DRS, 20 acres → +11.7 DRS |
| Vulnerability comparison | Same park: poor neighborhood +8.4 DRS vs wealthy +7.7 DRS |
| AI optimization | Finds locations with 3-4x better equity/environment ratio |

---

## Deployment

### Current Setup
- **Frontend**: Vercel — https://frontend-one-self-71.vercel.app
- **PMTiles**: Cloudflare R2 CDN
- **Backend**: Local only (Python FastAPI + PostgreSQL)

### Full Production (requires)
- **Frontend**: Vercel or Cloud Run
- **Backend**: Google Cloud Run, Railway, or Render
- **Database**: Cloud SQL (PostgreSQL + PostGIS) or Supabase
- **Tiles**: Cloudflare R2 (already set up)

---

## License

MIT

---

## References

- [Urban Displacement Project — Displacement Risk Methodology](https://www.urbandisplacement.org/)
- [Urban Institute — Guide to Measuring Neighborhood Change](https://www.urban.org/)
- [EPA EJScreen](https://www.epa.gov/ejscreen)
- [FEMA National Risk Index](https://hazards.fema.gov/nri/)
- [CDC/ATSDR Social Vulnerability Index](https://www.atsdr.cdc.gov/placeandhealth/svi/)
- [CEJST Justice40 Screening Tool](https://screeningtool.geoplatform.gov/)
- [Census ACS API](https://www.census.gov/data/developers/data-sets/acs-5year.html)

---

*GreenWatch — Built for equitable climate action.*
