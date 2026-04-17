#!/usr/bin/env python3
"""
scripts/ops/setup_oss_lifecycle.py
Configure OSS lifecycle rules and cross-region replication for GovFlow.

Rules:
  1. Archive objects after 365 days.
  2. Delete objects after 2555 days (7 years) — NĐ 30/2020 retention.

Cross-region replication: Singapore → Hong Kong (requires manual policy JSON).

Run:
  GOVFLOW_ENV=cloud python scripts/ops/setup_oss_lifecycle.py

Idempotent: checks existing rules before creating.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("setup_oss_lifecycle")


def main() -> None:
    try:
        import oss2
    except ImportError:
        logger.error("oss2 not installed. Install with: pip install oss2")
        sys.exit(1)

    from backend.src.config import settings  # type: ignore[import]

    auth = oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
    bucket = oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket)

    # ---------------------------------------------------------------------------
    # Check existing lifecycle configuration
    # ---------------------------------------------------------------------------
    existing_rule_ids: set[str] = set()
    try:
        lifecycle = bucket.get_bucket_lifecycle()
        for rule in lifecycle.rules:
            existing_rule_ids.add(rule.id)
        logger.info("Existing lifecycle rules: %s", existing_rule_ids)
    except oss2.exceptions.NoSuchLifecycle:
        logger.info("No existing lifecycle rules found")
    except Exception as exc:
        logger.warning("Could not fetch existing lifecycle rules: %s", exc)

    rules: list[oss2.models.LifecycleRule] = []

    # Rule 1: Archive after 365 days
    if "govflow-archive-365d" not in existing_rule_ids:
        rule_archive = oss2.models.LifecycleRule(
            id="govflow-archive-365d",
            prefix="",  # all objects
            status="Enabled",
            storage_transitions=[
                oss2.models.StorageTransition(
                    days=365,
                    storage_class=oss2.BUCKET_STORAGE_CLASS_ARCHIVE,
                )
            ],
        )
        rules.append(rule_archive)
        logger.info("Adding archive rule: objects archived after 365 days")
    else:
        logger.info("Archive rule already exists — skipping")

    # Rule 2: Delete after 2555 days (7 years)
    if "govflow-delete-7yr" not in existing_rule_ids:
        rule_delete = oss2.models.LifecycleRule(
            id="govflow-delete-7yr",
            prefix="",
            status="Enabled",
            expiration=oss2.models.LifecycleExpiration(days=2555),
        )
        rules.append(rule_delete)
        logger.info("Adding delete rule: objects deleted after 2555 days (7 years)")
    else:
        logger.info("Delete rule already exists — skipping")

    if rules:
        bucket.put_bucket_lifecycle(oss2.models.BucketLifecycle(rules))
        logger.info("Lifecycle rules applied successfully")
    else:
        logger.info("All lifecycle rules already configured — nothing to do")

    # ---------------------------------------------------------------------------
    # Cross-region replication (Singapore → Hong Kong)
    # Placeholder: requires console/API configuration with specific policy JSON.
    # ---------------------------------------------------------------------------
    logger.info(
        "Cross-region replication (Singapore → Hong Kong): "
        "configure manually via Alibaba Cloud console with the following policy:\n"
        "{\n"
        '  "ReplicationConfiguration": {\n'
        '    "Rule": [{\n'
        '      "Action": { "Transfer": ["ALL"] },\n'
        '      "Destination": {\n'
        '        "Bucket": "govflow-prod-hk",\n'
        '        "TransferType": "oss_acc"\n'
        "      },\n"
        '      "HistoricalObjectReplication": "enabled",\n'
        '      "Status": "enabled"\n'
        "    }]\n"
        "  }\n"
        "}"
    )


if __name__ == "__main__":
    main()
