#!/usr/bin/env python3
"""
ARTIST Setup Script
Complete setup for development and production environments.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def run_command(command, check=True, shell=False):
    """Run a shell command"""
    print(f"Running: {command}")
    if shell:
        result = subprocess.run(command, shell=True, check=check)
    else:
        result = subprocess.run(command.split(), check=check)
    return result

def setup_environment():
    """Set up Python virtual environment"""
    print("Setting up Python virtual environment...")
    
    if not os.path.exists("venv"):
        run_command("python3 -m venv venv")
    
    # Activate virtual environment and install dependencies
    if os.name == 'nt':  # Windows
        pip_path = "venv\\Scripts\\pip"
    else:  # Unix/Linux/macOS
        pip_path = "venv/bin/pip"
    
    run_command(f"{pip_path} install --upgrade pip")
    run_command(f"{pip_path} install -r requirements.txt")

def setup_database():
    """Set up database"""
    print("Setting up database...")
    
    # Create tables
    run_command("python -c \"from artist.database.session import create_all_tables; create_all_tables()\"", shell=True)
    
    print("Database setup complete!")

def setup_env_file():
    """Set up environment file"""
    print("Setting up environment file...")
    
    if not os.path.exists(".env"):
        run_command("cp .env.example .env")
        print("Created .env file from template. Please update with your API keys!")
    else:
        print(".env file already exists")

def setup_docker():
    """Set up Docker containers"""
    print("Setting up Docker containers...")
    
    run_command("docker-compose up -d postgres redis milvus", shell=True)
    print("Docker containers started!")

def run_tests():
    """Run tests"""
    print("Running tests...")
    run_command("python -m pytest tests/ -v", shell=True)

def main():
    parser = argparse.ArgumentParser(description="ARTIST Setup Script")
    parser.add_argument("--env-only", action="store_true", help="Only set up environment")
    parser.add_argument("--docker", action="store_true", help="Set up Docker containers")
    parser.add_argument("--test", action="store_true", help="Run tests after setup")
    parser.add_argument("--full", action="store_true", help="Full setup including Docker")
    
    args = parser.parse_args()
    
    print("🎨 Setting up ARTIST (Agentic Tool-Integrated LLM)...")
    
    # Always set up environment
    setup_environment()
    setup_env_file()
    
    if not args.env_only:
        setup_database()
    
    if args.docker or args.full:
        setup_docker()
    
    if args.test:
        run_tests()
    
    print("✅ Setup complete!")
    print("\nNext steps:")
    print("1. Update .env file with your API keys")
    print("2. Run: python -m artist.main")
    print("3. Visit: http://localhost:8000/docs")

if __name__ == "__main__":
    main()
