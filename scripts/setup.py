#!/usr/bin/env python3
"""
ARTIST Setup Script
Complete setup for development and production environments.
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path


def run_command(args: list, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command as a list — never uses shell=True to avoid injection."""
    print(f"Running: {' '.join(str(a) for a in args)}")
    return subprocess.run(args, check=check)


def setup_environment():
    """Set up Python virtual environment"""
    print("Setting up Python virtual environment...")

    if not os.path.exists("venv"):
        run_command([sys.executable, "-m", "venv", "venv"])

    pip_path = Path("venv") / ("Scripts" if os.name == "nt" else "bin") / "pip"

    run_command([str(pip_path), "install", "--upgrade", "pip"])
    run_command([str(pip_path), "install", "-r", "requirements.txt"])


def setup_database():
    """Set up database"""
    print("Setting up database...")

    python_path = Path("venv") / ("Scripts" if os.name == "nt" else "bin") / "python"
    run_command([
        str(python_path), "-c",
        "from artist.database.session import create_all_tables; create_all_tables()",
    ])

    print("Database setup complete!")


def setup_env_file():
    """Set up environment file"""
    print("Setting up environment file...")

    if not os.path.exists(".env"):
        shutil.copy(".env.example", ".env")
        print("Created .env from template — please fill in your secrets!")
    else:
        print(".env file already exists")


def setup_docker():
    """Set up Docker containers"""
    print("Setting up Docker containers...")

    docker_compose = shutil.which("docker-compose") or shutil.which("docker")
    if docker_compose is None:
        print("docker-compose not found on PATH — skipping Docker setup")
        return

    if "docker-compose" in docker_compose:
        run_command([docker_compose, "up", "-d", "postgres", "redis", "milvus"])
    else:
        run_command([docker_compose, "compose", "up", "-d", "postgres", "redis", "milvus"])

    print("Docker containers started!")


def run_tests():
    """Run tests"""
    print("Running tests...")

    python_path = Path("venv") / ("Scripts" if os.name == "nt" else "bin") / "python"
    run_command([str(python_path), "-m", "pytest", "tests/", "-v"])


def main():
    parser = argparse.ArgumentParser(description="ARTIST Setup Script")
    parser.add_argument("--env-only", action="store_true", help="Only set up environment")
    parser.add_argument("--docker", action="store_true", help="Set up Docker containers")
    parser.add_argument("--test", action="store_true", help="Run tests after setup")
    parser.add_argument("--full", action="store_true", help="Full setup including Docker")

    args = parser.parse_args()

    print("Setting up ARTIST (Agentic Tool-Integrated LLM)...")

    setup_environment()
    setup_env_file()

    if not args.env_only:
        setup_database()

    if args.docker or args.full:
        setup_docker()

    if args.test:
        run_tests()

    print("Setup complete!")
    print("\nNext steps:")
    print("1. Update .env file with your secrets (SECRET_KEY, POSTGRES_PASSWORD, etc.)")
    print("2. Run: python -m artist.main")
    print("3. Visit: http://localhost:8000/docs  (only available when DEBUG=true)")


if __name__ == "__main__":
    main()
