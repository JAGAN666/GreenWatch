"""GreenWatch Data Pipeline Orchestrator.

Runs all ETL ingesters in the correct order to populate the database
with Virginia census tract data from all sources.
"""

import os
import sys
import time

from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

sys.path.insert(0, os.path.dirname(__file__))

from etl import load_tracts, acs_ingester, svi_ingester, nri_ingester
from etl import places_ingester, cejst_ingester, ejscreen_ingester, eviction_ingester


def run_step(name: str, func):
    """Run a pipeline step with timing and error handling."""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    start = time.time()
    try:
        func()
        elapsed = time.time() - start
        print(f"  Completed in {elapsed:.1f}s")
        return True
    except Exception as e:
        elapsed = time.time() - start
        print(f"  FAILED after {elapsed:.1f}s: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the full data pipeline."""
    print("GreenWatch Data Pipeline")
    print("========================")
    print(f"Database: {os.getenv('DATABASE_URL', 'not set')[:50]}...")
    print()

    total_start = time.time()
    results = {}

    # Step 1: Load tract geometries (required before all other ingesters)
    results["tracts"] = run_step(
        "Step 1: Load Virginia Census Tract Geometries",
        load_tracts.run,
    )

    if not results["tracts"]:
        print("\nFATAL: Cannot continue without tract geometries.")
        sys.exit(1)

    # Step 2: ACS data (needed before eviction proxy)
    results["acs"] = run_step(
        "Step 2: Census ACS 5-Year Data (2019-2023)",
        acs_ingester.run,
    )

    # Steps 3-7 can run independently (but we run sequentially for simplicity)
    results["svi"] = run_step("Step 3: CDC/ATSDR Social Vulnerability Index", svi_ingester.run)
    results["nri"] = run_step("Step 4: FEMA National Risk Index", nri_ingester.run)
    results["places"] = run_step("Step 5: CDC PLACES Health Data", places_ingester.run)
    results["cejst"] = run_step("Step 6: CEJST (Justice40) Data", cejst_ingester.run)
    results["ejscreen"] = run_step("Step 7: EPA EJScreen Data", ejscreen_ingester.run)

    # Step 8: Eviction proxy (depends on ACS)
    if results.get("acs"):
        results["eviction"] = run_step(
            "Step 8: Eviction Risk Proxy (from ACS)",
            eviction_ingester.run,
        )

    # Summary
    total_elapsed = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"  Pipeline Complete — {total_elapsed:.1f}s total")
    print(f"{'='*60}")

    for step, success in results.items():
        status = "OK" if success else "FAILED"
        print(f"  {step:15s} [{status}]")

    # Verify final state
    print("\nVerification:")
    from sqlalchemy import create_engine, text
    from config import DATABASE_URL
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        tract_count = conn.execute(text("SELECT COUNT(*) FROM census_tracts")).scalar()
        indicator_count = conn.execute(text("SELECT COUNT(DISTINCT geoid) FROM tract_indicators")).scalar()
        source_counts = conn.execute(
            text("SELECT source, COUNT(DISTINCT geoid) FROM tract_indicators GROUP BY source ORDER BY source")
        ).fetchall()

        print(f"  Census tracts loaded: {tract_count}")
        print(f"  Tracts with indicators: {indicator_count}")
        print(f"  By source:")
        for source, count in source_counts:
            print(f"    {source:20s}: {count} tracts")


if __name__ == "__main__":
    main()
