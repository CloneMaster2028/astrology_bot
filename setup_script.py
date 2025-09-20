#!/usr/bin/env python3
"""
Setup script for Astrology Bot
Helps with initial setup and configuration
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header():
    """Print setup header."""
    print("=" * 60)
    print("🌟 ASTROLOGY BOT SETUP 🌟")
    print("=" * 60)
    print()

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8+ required!")
        print(f"Current version: {sys.version}")
        print("Please upgrade Python and try again.")
        return False
    
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def create_directories():
    """Create necessary directories."""
    directories = ['db', 'logs']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}/")

def create_env_file():
    """Create .env file from template."""
    if os.path.exists('.env'):
        print("⚠️  .env file already exists. Skipping creation.")
        return
    
    if not os.path.exists('.env.example'):
        print("❌ .env.example file not found!")
        return
    
    # Copy example to .env
    with open('.env.example', 'r') as source:
        content = source.read()
    
    with open('.env', 'w') as target:
        target.write(content)
    
    print("✅ Created .env file from template")
    print("⚠️  IMPORTANT: Edit .env file with your actual bot token and admin IDs!")

def install_dependencies():
    """Install Python dependencies."""
    print("📦 Installing dependencies...")
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ], capture_output=True, text=True, check=True)
        
        print("✅ Dependencies installed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print("❌ Error installing dependencies:")
        print(e.stderr)
        return False
    except FileNotFoundError:
        print("❌ requirements.txt not found!")
        return False

def validate_files():
    """Validate that all required files exist."""
    required_files = [
        'astrology_bot_improved.py',
        'config.py',
        'database.py',
        'astrology_utils.py',
        'constants.py',
        'requirements.txt'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
        else:
            print(f"✅ Found: {file}")
    
    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        return False
    
    return True

def print_next_steps():
    """Print next steps for the user."""
    print()
    print("=" * 60)
    print("🎉 SETUP COMPLETE!")
    print("=" * 60)
    print()
    print("📝 NEXT STEPS:")
    print("1. Edit .env file with your bot token:")
    print("   - Get token from @BotFather on Telegram")
    print("   - Get your user ID from @userinfobot")
    print()
    print("2. Run the bot:")
    print("   python astrology_bot_improved.py")
    print()
    print("3. Test the bot by messaging it on Telegram")
    print()
    print("🔧 Configuration file: .env")
    print("📊 Database location: db/astrology_bot.db")
    print("📁 Log files: logs/astrology_bot.log")
    print()
    print("❓ Need help? Check the README.md file!")
    print()

def main():
    """Main setup function."""
    print_header()
    
    # Check Python version
    if not check_python_version():
        return 1
    
    # Validate required files
    if not validate_files():
        print("\n❌ Setup failed: Missing required files")
        return 1
    
    # Create directories
    create_directories()
    
    # Create .env file
    create_env_file()
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Setup failed: Could not install dependencies")
        return 1
    
    # Show next steps
    print_next_steps()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())