import { NextResponse } from "next/server";
import { Pool } from "pg";

const pool = new Pool({
  connectionString:
    process.env.DATABASE_URL ||
    "postgresql://greenwatch:greenwatch@localhost:5432/greenwatch",
});

export const revalidate = 60; // cache for 60 seconds

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const state = searchParams.get("state"); // optional state FIPS filter
    const bbox = searchParams.get("bbox"); // optional bbox: minLng,minLat,maxLng,maxLat

    // Build WHERE clause
    const conditions: string[] = [];
    const params: (string | number)[] = [];
    let paramIdx = 1;

    if (state) {
      conditions.push(`ct.state_fips = $${paramIdx}`);
      params.push(state);
      paramIdx++;
    }

    if (bbox) {
      const [minLng, minLat, maxLng, maxLat] = bbox.split(",").map(Number);
      conditions.push(`ST_Intersects(ct.geom, ST_MakeEnvelope($${paramIdx}, $${paramIdx + 1}, $${paramIdx + 2}, $${paramIdx + 3}, 4326))`);
      params.push(minLng, minLat, maxLng, maxLat);
      paramIdx += 4;
    }

    // Default: if no filter, return all tracts (may be large)
    const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "";

    const { rows } = await pool.query(`
      SELECT
        ct.geoid,
        ct.county_name,
        ct.name,
        ST_AsGeoJSON(ct.geom) AS geometry,
        COALESCE(s.drs_composite, 0)        AS drs_composite,
        COALESCE(s.drs_vulnerability, 0)    AS drs_vulnerability,
        COALESCE(s.drs_market_pressure, 0)  AS drs_market_pressure,
        COALESCE(s.drs_green_proximity, 0)  AS drs_green_proximity,
        COALESCE(s.drs_classification, 'low') AS drs_classification,
        COALESCE(s.ebs_composite, 0)        AS ebs_composite,
        COALESCE(s.ebs_air_quality, 0)      AS ebs_air_quality,
        COALESCE(s.ebs_green_infra, 0)      AS ebs_green_infra,
        COALESCE(s.ebs_climate_resilience, 0) AS ebs_climate_resilience,
        COALESCE(s.ebs_health, 0)           AS ebs_health,
        COALESCE(s.accelerating_risk, false) AS accelerating_risk,
        i.median_rent,
        i.median_home_value,
        i.median_household_income,
        i.pct_renters,
        i.pct_rent_burdened,
        i.pct_nonwhite,
        i.total_population,
        i.asthma_prevalence,
        i.eviction_rate,
        i.cejst_disadvantaged
      FROM census_tracts ct
      LEFT JOIN (
        SELECT DISTINCT ON (geoid)
          geoid AS sg,
          drs_composite, drs_vulnerability, drs_market_pressure,
          drs_green_proximity, drs_classification,
          ebs_composite, ebs_air_quality, ebs_green_infra,
          ebs_climate_resilience, ebs_health, accelerating_risk
        FROM tract_scores
        ORDER BY geoid, score_version DESC
      ) s ON ct.geoid = s.sg
      LEFT JOIN (
        SELECT DISTINCT ON (geoid)
          geoid AS ig,
          median_rent, median_home_value, median_household_income,
          pct_renters, pct_rent_burdened, pct_nonwhite,
          total_population, asthma_prevalence, eviction_rate,
          cejst_disadvantaged
        FROM tract_indicators
        WHERE source = 'acs'
        ORDER BY geoid, data_year DESC
      ) i ON ct.geoid = i.ig
      ${whereClause}
    `, params);

    const features = rows.map((row) => ({
      type: "Feature" as const,
      geometry: JSON.parse(row.geometry),
      properties: {
        geoid: row.geoid,
        county_name: row.county_name,
        name: row.name,
        drs_composite: Number(row.drs_composite),
        drs_vulnerability: Number(row.drs_vulnerability),
        drs_market_pressure: Number(row.drs_market_pressure),
        drs_green_proximity: Number(row.drs_green_proximity),
        drs_classification: row.drs_classification,
        ebs_composite: Number(row.ebs_composite),
        ebs_air_quality: Number(row.ebs_air_quality),
        ebs_green_infra: Number(row.ebs_green_infra),
        ebs_climate_resilience: Number(row.ebs_climate_resilience),
        ebs_health: Number(row.ebs_health),
        median_rent: row.median_rent != null ? Number(row.median_rent) : null,
        median_home_value:
          row.median_home_value != null
            ? Number(row.median_home_value)
            : null,
        median_household_income:
          row.median_household_income != null
            ? Number(row.median_household_income)
            : null,
        pct_renters:
          row.pct_renters != null ? Number(row.pct_renters) : null,
        pct_rent_burdened:
          row.pct_rent_burdened != null
            ? Number(row.pct_rent_burdened)
            : null,
        pct_nonwhite:
          row.pct_nonwhite != null ? Number(row.pct_nonwhite) : null,
        total_population:
          row.total_population != null
            ? Number(row.total_population)
            : null,
        asthma_prevalence:
          row.asthma_prevalence != null
            ? Number(row.asthma_prevalence)
            : null,
        eviction_rate:
          row.eviction_rate != null ? Number(row.eviction_rate) : null,
        tree_canopy_pct: null,
        cejst_disadvantaged: row.cejst_disadvantaged ?? false,
        accelerating_risk: row.accelerating_risk ?? false,
      },
    }));

    const collection = {
      type: "FeatureCollection" as const,
      features,
    };

    return NextResponse.json(collection);
  } catch (error) {
    console.error("Failed to fetch tracts:", error);
    return NextResponse.json(
      { error: "Failed to fetch tract data" },
      { status: 500 }
    );
  }
}
