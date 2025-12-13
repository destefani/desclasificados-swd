#!/usr/bin/env python3
"""
Backfill script for schema v2.1.0 → v2.2.0 migration.

This script adds the new fields required by schema v2.2.0 to existing transcripts:
- organizations_mentioned (empty array - requires re-transcription for actual data)
- disappearance_references (new section with empty values)
- date_range (optional field, added with empty values)
- has_financial_content (computed from existing financial_references)
- Converts amounts from strings to structured objects (with null normalized_usd)

Note: This only adds structural fields. For full data extraction of new fields
(organizations, disappearances), documents need to be re-transcribed with the
new prompt.

Usage:
    uv run python scripts/backfill_schema_v2_2.py --dry-run  # Preview changes
    uv run python scripts/backfill_schema_v2_2.py            # Apply changes
    uv run python scripts/backfill_schema_v2_2.py --input-dir data/generated_transcripts/gpt-5-mini-v2.1.0
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Mapping of old purpose strings to new standardized enums
PURPOSE_MAPPING = {
    # Lowercase variations
    "election support": "ELECTION SUPPORT",
    "opposition support": "OPPOSITION SUPPORT",
    "propaganda": "PROPAGANDA",
    "media funding": "MEDIA FUNDING",
    "political action": "POLITICAL ACTION",
    "intelligence operations": "INTELLIGENCE OPERATIONS",
    "military aid": "MILITARY AID",
    "economic destabilization": "ECONOMIC DESTABILIZATION",
    "labor union support": "LABOR UNION SUPPORT",
    "civic action": "CIVIC ACTION",
    # Mixed case variations found in data
    "OPPOSITION SUPPORT": "OPPOSITION SUPPORT",
    "ELECTION SUPPORT": "ELECTION SUPPORT",
    "PROPAGANDA": "PROPAGANDA",
    "POST-COUP SUPPORT": "OPPOSITION SUPPORT",  # Map to closest
    "ANTI-ALLENDE ACTIVITY": "OPPOSITION SUPPORT",  # Map to closest
    "anti-FRAP propaganda": "PROPAGANDA",
}

# Valid incident types for v2.2.0
VALID_INCIDENT_TYPES = {
    "ASSASSINATION", "EXECUTION", "COUP", "MILITARY COUP", "BOMBING",
    "ARMED CONFLICT", "REPRESSION", "DEATH", "KIDNAPPING", "SHOOTING",
    "MASSACRE", "CIVIL UNREST", "OTHER"
}

# Mapping of old incident types to standardized ones
INCIDENT_MAPPING = {
    "OVERTHROW": "COUP",
    "INVASION": "ARMED CONFLICT",
    "CIVIL DISORDER": "CIVIL UNREST",
    "CIVIL WAR": "ARMED CONFLICT",
    "MILITARY UPRISING": "MILITARY COUP",
}


def migrate_transcript(data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """
    Migrate a transcript from v2.1.0 to v2.2.0 schema.

    Returns:
        Tuple of (migrated_data, list_of_changes)
    """
    changes: list[str] = []
    metadata = data.get("metadata", {})

    # 1. Add organizations_mentioned if missing
    if "organizations_mentioned" not in metadata:
        metadata["organizations_mentioned"] = []
        changes.append("Added organizations_mentioned (empty)")

    # 2. Add disappearance_references if missing
    if "disappearance_references" not in metadata:
        metadata["disappearance_references"] = {
            "victims": [],
            "perpetrators": [],
            "locations": [],
            "dates_mentioned": [],
            "has_disappearance_content": False
        }
        changes.append("Added disappearance_references")

    # 3. Add date_range if missing (optional field)
    if "date_range" not in metadata:
        metadata["date_range"] = {
            "start_date": "",
            "end_date": "",
            "is_approximate": False
        }
        changes.append("Added date_range (empty)")

    # 4. Handle financial_references migration
    fin_ref = metadata.get("financial_references", {})

    # Add has_financial_content boolean
    if "has_financial_content" not in fin_ref:
        has_content = bool(
            fin_ref.get("amounts") or
            fin_ref.get("financial_actors") or
            fin_ref.get("purposes")
        )
        fin_ref["has_financial_content"] = has_content
        changes.append(f"Added has_financial_content={has_content}")

    # Convert amounts from strings to structured objects
    old_amounts = fin_ref.get("amounts", [])
    if old_amounts and isinstance(old_amounts[0], str):
        new_amounts = []
        for amt in old_amounts:
            new_amounts.append({
                "value": amt,
                "normalized_usd": None,
                "context": ""
            })
        fin_ref["amounts"] = new_amounts
        changes.append(f"Converted {len(old_amounts)} amounts to structured format")

    # Standardize purposes
    old_purposes = fin_ref.get("purposes", [])
    new_purposes = []
    for purpose in old_purposes:
        mapped = PURPOSE_MAPPING.get(purpose, "OTHER")
        new_purposes.append(mapped)
    if new_purposes != old_purposes:
        fin_ref["purposes"] = new_purposes
        changes.append(f"Standardized {len(old_purposes)} purposes")

    metadata["financial_references"] = fin_ref

    # 5. Standardize violence_references incident_types
    viol_ref = metadata.get("violence_references", {})
    old_incidents = viol_ref.get("incident_types", [])
    new_incidents = []
    for incident in old_incidents:
        if incident in VALID_INCIDENT_TYPES:
            new_incidents.append(incident)
        elif incident in INCIDENT_MAPPING:
            new_incidents.append(INCIDENT_MAPPING[incident])
        else:
            new_incidents.append("OTHER")
    if new_incidents != old_incidents:
        viol_ref["incident_types"] = new_incidents
        changes.append(f"Standardized {len(old_incidents)} incident_types")
    metadata["violence_references"] = viol_ref

    # 6. Ensure torture methods are standardized (already empty in most cases)
    tort_ref = metadata.get("torture_references", {})
    # No changes needed if empty, but ensure structure
    metadata["torture_references"] = tort_ref

    data["metadata"] = metadata
    return data, changes


def process_directory(
    input_dir: Path,
    dry_run: bool = False,
) -> tuple[int, int, int]:
    """
    Process all JSON files in directory.

    Returns:
        Tuple of (total, migrated, errors)
    """
    json_files = [f for f in input_dir.glob("*.json") if f.name != "cost_history.jsonl"]

    total = len(json_files)
    migrated = 0
    errors = 0

    logger.info(f"Found {total} JSON files in {input_dir}")

    for json_file in json_files:
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            migrated_data, changes = migrate_transcript(data)

            if changes:
                migrated += 1
                if dry_run:
                    logger.info(f"[DRY RUN] {json_file.name}: {', '.join(changes)}")
                else:
                    json_file.write_text(
                        json.dumps(migrated_data, indent=4, ensure_ascii=False),
                        encoding="utf-8"
                    )
                    logger.info(f"Migrated {json_file.name}: {', '.join(changes)}")
        except Exception as e:
            errors += 1
            logger.error(f"Error processing {json_file.name}: {e}")

    return total, migrated, errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill schema v2.1.0 transcripts to v2.2.0"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/generated_transcripts/gpt-5-mini-v2.1.0"),
        help="Directory containing v2.1.0 transcripts"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files"
    )

    args = parser.parse_args()

    if not args.input_dir.exists():
        logger.error(f"Directory not found: {args.input_dir}")
        return 1

    logger.info(f"{'[DRY RUN] ' if args.dry_run else ''}Processing {args.input_dir}")

    total, migrated, errors = process_directory(args.input_dir, args.dry_run)

    logger.info(f"\nSummary:")
    logger.info(f"  Total files: {total}")
    logger.info(f"  Migrated: {migrated}")
    logger.info(f"  Errors: {errors}")

    if args.dry_run:
        logger.info("\n[DRY RUN] No files were modified. Run without --dry-run to apply changes.")

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
