# GreenWatch

> AI-powered climate equity simulation platform — place green infrastructure without displacing vulnerable communities.

GreenWatch helps policymakers model the impact of green infrastructure investments (parks, greenways, transit, tree planting) on both **environmental quality** and **displacement risk** across 85,000+ US census tracts. It makes the tradeoffs of green gentrification visible *before* decisions are made.

Built for **HooHacks 2026**.

---

## Features

- **Interactive Map** — Visualize every US census tract colored by Displacement Risk Score (DRS) or Environmental Benefit Score (EBS)
- **Intervention Placement** — Place 6 types of green infrastructure with configurable scale and see their impact radius
- **What-If Simulation** — Predict how interventions affect surrounding tracts using a spatial distance decay model
- **Policy Mitigations** — Model rent stabilization, community land trusts, and affordable housing mandates to counteract displacement
- **AI Optimization** — Get recommended placement locations that maximize environmental benefit while minimizing displacement risk

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, TypeScript, React 19, Tailwind CSS |
| Mapping | MapLibre GL, Deck.gl, PMTiles |
| Charts | Recharts |
| Backend | FastAPI, Python, Uvicorn |
| Database | PostgreSQL 16 + PostGIS 3.4 |
| Caching | Redis |
| ML/Data | scikit-learn, pandas, NumPy, SciPy |
| ORM | SQLAlchemy, GeoAlchemy2 |
| Infra | Docker, Vercel, Cloudflare R2 |

---

## Architecture

```
greenwatch/
├── frontend/          # Next.js app (map UI, simulation controls, results)
├── scoring/           # FastAPI scoring & simulation service
├── pipeline/          # ETL data ingestion (Census, EPA, CDC, FEMA)
├── db/                # PostgreSQL/PostGIS schema & migrations
└── docker-compose.yml # Full-stack local orchestration
```

**Data flow:**
1. `pipeline/` ingests federal datasets → PostgreSQL
2. `scoring/` computes DRS & EBS for all tracts, runs simulations
3. `frontend/` proxies simulation requests to scoring service, renders results on map

---

## Data Sources

| Source | Data |
|--------|------|
| Census ACS 5-Year | Median rent, home value, income, renter %, poverty, race/ethnicity |
| CDC/ATSDR SVI | Social Vulnerability Index |
| EPA EJScreen | PM2.5, ozone, diesel particulate, traffic proximity, lead paint |
| FEMA NRI | Flood, heat, hurricane risk scores |
| CDC PLACES | Asthma & mental health prevalence |
| Justice40 / CEJST | Disadvantaged community flags |

---

## Scoring Methodology

### Displacement Risk Score (DRS) — 0 to 100, higher = more vulnerable
- **40%** Vulnerability: renter %, rent burden, poverty, race, education, eviction rate, SVI
- **35%** Market Pressure: 5-year % change in rent, home value, household income
- **25%** Green Proximity: proximity to existing green infrastructure

### Environmental Benefit Score (EBS) — 0 to 100, higher = more benefit
- **30%** Air Quality: PM2.5, ozone, diesel particulate
- **30%** Green Infrastructure: tree canopy, park access, impervious surface
- **25%** Climate Resilience: flood, heat, hurricane risk (inverted)
- **15%** Health: asthma & mental health prevalence (inverted)

All indicators are percentile-ranked before weighting to normalize across disparate units.

---

## Local Development

### Prerequisites
- Docker & Docker Compose
- Node.js 20+
- Python 3.11+
- Census API key ([get one free](https://api.census.gov/data/key_signup.html))

### 1. Clone & configure

```bash
git clone https://github.com/JAGAN666/GreenWatch.git
cd GreenWatch
cp .env.example .env
# Fill in your API keys in .env
```

### 2. Start all services

```bash
docker-compose up --build
```

This starts:
- PostgreSQL + PostGIS on port `5432`
- Redis on port `6380`
- FastAPI scoring service on port `8000`
- Next.js frontend on port `3000`

### 3. Run the data pipeline

```bash
cd pipeline
pip install -r requirements.txt
python run_pipeline.py
```

This ingests all federal datasets and computes initial DRS/EBS scores for all US census tracts (~85,000).

### 4. Open the app

Visit [http://localhost:3000](http://localhost:3000)

---

## API Reference

All scoring endpoints are available at `http://localhost:8000`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/scoring/simulate` | Run what-if simulation with interventions & mitigations |
| `POST` | `/scoring/optimize` | Find optimal intervention locations in a bounding box |
| `GET` | `/scoring/tract/{geoid}` | Fetch scores & indicators for a single census tract |
| `POST` | `/scoring/recompute` | Rebuild all DRS/EBS scores from raw indicators |

Interactive API docs available at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://greenwatch:greenwatch@localhost:5432/greenwatch

# Redis
REDIS_URL=redis://localhost:6379

# Scoring service (used by Next.js API routes)
SCORING_SERVICE_URL=http://localhost:8000

# Census API key
CENSUS_API_KEY=your_census_api_key_here
```

---

## Deployment

- **Frontend**: Deployed on [Vercel](https://vercel.com) — connect your repo and it deploys automatically
- **Map Tiles**: PMTiles file hosted on [Cloudflare R2](https://developers.cloudflare.com/r2/) — upload via `wrangler r2 object put`
- **Scoring Service**: Containerized FastAPI — deploy to any Docker-compatible host (Railway, Fly.io, GCP Cloud Run)

---

## Intervention Types

| Type | Impact Radius | Base EBS Gain | Base DRS Risk |
|------|--------------|---------------|---------------|
| Park | 1500m | +10 pts | +8 pts |
| Greenway | 1000m | +7 pts | +5 pts |
| Transit Stop | 800m | +5 pts | +10 pts |
| Tree Planting | 500m | +6 pts | +3 pts |
| Flood Infrastructure | 2000m | +8 pts | +2 pts |
| Green Roof | 300m | +4 pts | +2 pts |

---

## Policy Mitigations

| Policy | DRS Reduction |
|--------|--------------|
| Rent Stabilization | 15–25 pts |
| Community Land Trusts | 20–30 pts |
| Affordable Housing Mandates | 10–20 pts |
| Community Benefit Agreements | 5–15 pts |

---

## License

MIT
