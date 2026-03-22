"""SQLAlchemy ORM models for GreenWatch census tract tables."""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text,
    ForeignKey, UniqueConstraint,
)
from geoalchemy2 import Geometry

from app.db import Base


class CensusTract(Base):
    __tablename__ = "census_tracts"

    geoid = Column(String, primary_key=True)
    county_name = Column(String)
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    centroid = Column(Geometry("POINT", srid=4326))


class TractIndicator(Base):
    __tablename__ = "tract_indicators"

    geoid = Column(String, ForeignKey("census_tracts.geoid"), primary_key=True)
    data_year = Column(Integer, primary_key=True)
    source = Column(String, primary_key=True)

    # Economic / housing
    median_rent = Column(Float)
    median_home_value = Column(Float)
    median_household_income = Column(Float)
    pct_renters = Column(Float)
    pct_rent_burdened = Column(Float)
    pct_below_poverty = Column(Float)
    pct_nonwhite = Column(Float)
    pct_bachelors_plus = Column(Float)
    total_population = Column(Integer)

    # Environmental
    pm25 = Column(Float)
    ozone = Column(Float)
    diesel_pm = Column(Float)

    # Social vulnerability
    svi_overall = Column(Float)

    # Natural hazard risk
    nri_risk_score = Column(Float)
    nri_flood_score = Column(Float)
    nri_heat_score = Column(Float)
    nri_hurricane_score = Column(Float)

    # Health
    asthma_prevalence = Column(Float)
    mental_health_not_good = Column(Float)

    # Other
    eviction_rate = Column(Float)
    cejst_disadvantaged = Column(Boolean)

    # Green infrastructure
    tree_canopy_pct = Column(Float)
    impervious_surface_pct = Column(Float)
    park_access_10min = Column(Boolean)
    flood_zone_pct = Column(Float)


class TractScore(Base):
    __tablename__ = "tract_scores"

    geoid = Column(String, ForeignKey("census_tracts.geoid"), primary_key=True)
    score_version = Column(String, primary_key=True)
    data_year = Column(Integer)

    # Displacement Risk Score domains
    drs_vulnerability = Column(Float)
    drs_market_pressure = Column(Float)
    drs_green_proximity = Column(Float)
    drs_composite = Column(Float)
    drs_classification = Column(String)

    # Environmental Benefit Score domains
    ebs_air_quality = Column(Float)
    ebs_green_infra = Column(Float)
    ebs_climate_resilience = Column(Float)
    ebs_health = Column(Float)
    ebs_composite = Column(Float)

    # Combined flag
    accelerating_risk = Column(Boolean)


class GreenInvestment(Base):
    __tablename__ = "green_investments"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    type = Column(String)
    status = Column(String)
    location = Column(Geometry("POINT", srid=4326))
    scale_value = Column(Float)
    completion_year = Column(Integer)
