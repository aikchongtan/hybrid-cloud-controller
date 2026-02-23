# Database Migrations

This directory contains Alembic database migrations for the Hybrid Cloud Controller.

## Setup

Alembic is configured to automatically detect model changes and generate migrations.

## Usage

### Initialize Alembic (already done)

The migrations directory is already set up with the necessary configuration files.

### Create a new migration

To create a new migration after modifying models:

```bash
alembic -c packages/database/migrations/alembic.ini revision --autogenerate -m "Description of changes"
```

### Apply migrations

To upgrade the database to the latest version:

```bash
alembic -c packages/database/migrations/alembic.ini upgrade head
```

### Rollback migrations

To downgrade by one revision:

```bash
alembic -c packages/database/migrations/alembic.ini downgrade -1
```

### View migration history

To see the current migration status:

```bash
alembic -c packages/database/migrations/alembic.ini current
```

To see all migrations:

```bash
alembic -c packages/database/migrations/alembic.ini history
```

## Environment Variables

- `DATABASE_URL`: Database connection string (defaults to `sqlite:///hybrid_cloud_controller.db`)

## Migration Files

Migration files are stored in the `versions/` subdirectory and are automatically generated with timestamps.
