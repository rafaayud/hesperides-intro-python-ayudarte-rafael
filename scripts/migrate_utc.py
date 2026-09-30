"""Convert legacy timestamps without deleting data; requires the original timezone."""
import argparse
import asyncio
import os
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

TIME_COLUMNS = {
    'candles': ['open_time'],
    'portfolios': ['created_at'],
    'positions': ['entry_time', 'created_at'],
    'trades': ['entry_time', 'exit_time', 'created_at'],
}


async def migrate(connection, source_timezone, created_timezone='UTC'):
    zones = {}
    for zone in {source_timezone, created_timezone}:
        if not await connection.fetchval('SELECT EXISTS(SELECT 1 FROM pg_timezone_names WHERE name = $1)', zone):
            raise ValueError(f'Unknown PostgreSQL timezone: {zone}')
        zones[zone] = await connection.fetchval('SELECT quote_literal($1::text)', zone)
    async with connection.transaction():
        for table, columns in TIME_COLUMNS.items():
            for column in columns:
                data_type = await connection.fetchval(
                    'SELECT data_type FROM information_schema.columns '
                    'WHERE table_schema = current_schema() AND table_name = $1 AND column_name = $2',
                    table, column,
                )
                if data_type == 'timestamp without time zone':
                    # created_at came from PostgreSQL NOW(), not the backend's local clock.
                    zone_literal = zones[created_timezone if column == 'created_at' else source_timezone]
                    # Identifiers come only from TIME_COLUMNS; timezone is quoted by PostgreSQL.
                    await connection.execute(
                        f'ALTER TABLE {table} ALTER COLUMN {column} TYPE TIMESTAMPTZ '
                        f'USING {column} AT TIME ZONE {zone_literal}'
                    )
                    print(f'Migrated {table}.{column}')


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-timezone', required=True, help='Original backend timezone, e.g. UTC or Europe/Madrid')
    parser.add_argument('--created-timezone', default='UTC', help='Original PostgreSQL session timezone for created_at (default: UTC)')
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
    connection = await asyncpg.connect(os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/trading'))
    try:
        await migrate(connection, args.source_timezone, args.created_timezone)
    finally:
        await connection.close()


if __name__ == '__main__':
    asyncio.run(main())
