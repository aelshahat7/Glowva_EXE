"""Startup hooks for safe ERP database migrations."""

from services.migration_service import run_database_migration


def initialize_database():
    run_database_migration()
