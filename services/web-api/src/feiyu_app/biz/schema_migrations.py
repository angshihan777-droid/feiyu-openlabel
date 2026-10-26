"""Idempotent PostgreSQL migrations for existing tortoise schemas."""

from pathlib import Path

from tortoise import connections

from ..log import logger


CHALLENGE_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "20261025_challenge_refactor.sql"
)


async def apply_challenge_schema_migration() -> None:
    if not CHALLENGE_MIGRATION.is_file():
        logger.warning(f"challenge migration not found: {CHALLENGE_MIGRATION}")
        return
    connection = connections.get("default")
    dialect = getattr(connection.capabilities, "dialect", "")
    if dialect != "postgres":
        logger.debug(f"challenge migration skipped for dialect={dialect}")
        return
    await connection.execute_script(CHALLENGE_MIGRATION.read_text(encoding="utf-8"))
    logger.info("challenge schema migration applied")
