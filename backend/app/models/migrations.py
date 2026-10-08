"""
Automatic database schema migration utility.
Safely adds missing columns and tables to PostgreSQL/SQLite without data loss,
ensuring existing production databases stay in sync with SQLAlchemy models.
"""

import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

# List of columns to ensure exist on existing tables: (table_name, column_name, sql_type_and_defaults)
COLUMNS_TO_ENSURE = [
    # products table
    ("products", "previous_price", "NUMERIC(12, 2)"),
    ("products", "price_change", "NUMERIC(12, 2)"),
    ("products", "price_change_percentage", "DOUBLE PRECISION"),
    ("products", "lowest_price", "NUMERIC(12, 2)"),
    ("products", "highest_price", "NUMERIC(12, 2)"),
    ("products", "normalized_price", "NUMERIC(12, 2)"),
    ("products", "normalized_currency", "VARCHAR(10)"),
    ("products", "exchange_rate", "DOUBLE PRECISION"),
    ("products", "cloudinary_url", "TEXT"),
    ("products", "cloudinary_public_id", "VARCHAR(255)"),
    ("products", "s3_url", "TEXT"),
    ("products", "s3_key", "VARCHAR(500)"),
    ("products", "supabase_url", "TEXT"),
    ("products", "supabase_path", "VARCHAR(500)"),
    ("products", "match_cluster_id", "VARCHAR(100)"),
    ("products", "match_confidence", "DOUBLE PRECISION"),
    # alert_configs table
    ("alert_configs", "events_subscribed", "JSON"),
    ("alert_configs", "store_domains", "JSON"),
    ("alert_configs", "hmac_secret", "VARCHAR(255)"),
    ("alert_configs", "custom_headers", "JSON"),
    ("alert_configs", "min_rank_shift", "INTEGER"),
    # alert_notification_logs table
    ("alert_notification_logs", "store_domain", "VARCHAR(255)"),
]


async def run_auto_migrations(engine: AsyncEngine) -> None:
    """Inspect database dialect and add any missing columns automatically."""
    dialect_name = engine.dialect.name.lower()
    logger.info(f"Checking database schema migrations for dialect: {dialect_name}...")

    async with engine.begin() as conn:
        for table, column, col_type in COLUMNS_TO_ENSURE:
            try:
                if "postgres" in dialect_name:
                    # Check if column exists in postgres
                    check_stmt = text(f"""
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = '{table}' AND column_name = '{column}';
                    """)
                    exists = (await conn.execute(check_stmt)).scalar()
                    if not exists:
                        # Table might not exist yet if fresh, check table
                        table_check = text(f"SELECT 1 FROM information_schema.tables WHERE table_name = '{table}';")
                        table_exists = (await conn.execute(table_check)).scalar()
                        if table_exists:
                            logger.info(f"Adding missing column '{column}' to '{table}' table...")
                            await conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS "{column}" {col_type};'))
                elif "sqlite" in dialect_name:
                    # Check sqlite table columns via pragma
                    pragma_res = await conn.execute(text(f"PRAGMA table_info({table});"))
                    existing_cols = [row[1] for row in pragma_res.fetchall()]
                    if existing_cols and column not in existing_cols:
                        sqlite_type = col_type.replace("DOUBLE PRECISION", "REAL").replace("JSON", "TEXT")
                        logger.info(f"Adding missing column '{column}' to SQLite table '{table}'...")
                        await conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {sqlite_type};'))
            except Exception as e:
                logger.warning(f"Auto-migration check notice for {table}.{column}: {e}")

    logger.info("Database schema migration checks completed.")
