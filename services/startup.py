"""Startup hooks for safe ERP database migrations."""

from services.migration_service import run_database_migration
from services.returns_service import initialize_returns
from services.returns_ui import install_return_buttons


def initialize_database():
    run_database_migration()
    initialize_returns()
    install_return_buttons()
