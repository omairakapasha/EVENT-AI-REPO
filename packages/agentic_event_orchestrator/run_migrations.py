#!/usr/bin/env python3
"""
Safe migration runner for AI Orchestrator.
Handles cases where tables already exist from manual runs.
"""
import subprocess
import sys

def run_migrations():
    """Run Alembic migrations, handling existing tables gracefully."""
    try:
        print("🔄 Running AI database migrations...")
        result = subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            print("✅ Migrations completed successfully")
            print(result.stdout)
            return 0
        
        # Check if error is due to existing tables
        if "already exists" in result.stderr or "DuplicateTableError" in result.stderr:
            print("⚠️  Tables already exist, stamping current version...")
            stamp_result = subprocess.run(
                ["uv", "run", "alembic", "stamp", "head"],
                capture_output=True,
                text=True,
                check=False
            )
            if stamp_result.returncode == 0:
                print("✅ Database marked as up-to-date")
                return 0
            else:
                print("❌ Failed to stamp database version")
                print(stamp_result.stderr)
                return 1
        else:
            # Some other migration error
            print("❌ Migration failed with unexpected error:")
            print(result.stderr)
            return 1
            
    except Exception as e:
        print(f"❌ Error running migrations: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(run_migrations())
