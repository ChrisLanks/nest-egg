"""
Script to enrich holdings with sector/industry data from Alpha Vantage.

This script runs the enrichment service to populate sector and industry fields
for all holdings that don't have this data yet.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.services.financial_data_service import financial_data_service
from sqlalchemy import select
from app.models.holding import Holding


async def main():
    """Run enrichment for all organizations."""
    async with AsyncSessionLocal() as db:
        # Get all unique organization IDs with holdings
        result = await db.execute(
            select(Holding.organization_id).distinct()
        )
        org_ids = [row[0] for row in result.all()]

        print(f"Found {len(org_ids)} organization(s) with holdings")

        for org_id in org_ids:
            print(f"\nEnriching holdings for organization {org_id}...")

            # Get count of unenriched holdings
            unenriched_query = select(Holding).where(
                Holding.organization_id == org_id,
                Holding.asset_type.in_(['stock', 'etf', 'mutual_fund']),
                (Holding.sector == None) | (Holding.industry == None)
            )
            result = await db.execute(unenriched_query)
            unenriched = result.scalars().all()

            print(f"Found {len(unenriched)} holdings needing enrichment")

            if len(unenriched) == 0:
                print("No holdings need enrichment. Skipping.")
                continue

            # Enrich in batches
            enriched_count = await financial_data_service.enrich_holdings_batch(
                db=db,
                organization_id=str(org_id),
                limit=50,  # Process up to 50 holdings
                force_refresh=False
            )

            print(f"Successfully enriched {enriched_count} holdings")

        print("\n✅ Enrichment complete!")


if __name__ == "__main__":
    asyncio.run(main())
