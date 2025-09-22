#!/usr/bin/env python3
"""
Startup script for Astrology Bot with error prevention
Handles the weak reference issue and provides better error reporting
"""

import sys
import os
import subprocess
import signal
import time
from pathlib import Path


def check_python_version():
    """Check Python version compatibility."""
    if sys.version_info < (3, 8):
        print(f"❌ Error: Python 3.8+ required!")
        print(f"Current version: {sys.version}")
        print("Please upgrade Python and try again.")
        return False

    print(f"✅ Python version: {sys.version.split()[0]}")
    return True


def check_dependencies():
    """Check and install dependencies if needed."""
    required_packages = [
        'python-telegram-bot',
        'python-dotenv'
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")

        response = input("Install missing packages? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            try:
                subprocess.check_call([
                                          sys.executable, '-m', 'pip', 'install', '--upgrade'
                                      ] + missing_packages)
                print("✅ Dependencies installed successfully!")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install dependencies: {e}")
                return False
        else:
            print("Please install missing packages manually:")
            print(f"pip install {' '.join(missing_packages)}")
            return False

    print("✅ All dependencies available")
    return True


def check_configuration():
    """Check configuration files and environment."""
    # Check for required files
    required_files = [
        'astrology_bot_improved.py',
        'config.py',
        'database.py',
        'astrology_utils.py',
        'constants.py'
    ]

    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)

    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        return False

    # Check .env file
    if not Path('.env').exists():
        print("❌ .env file not found!")
        print("Create .env file with your bot token and admin IDs")

        if Path('.env.example').exists():
            print("Copy .env.example to .env and edit it with your values")

        return False

    # Try to load and validate config
    try:
        from config import Config
        config = Config.from_env()
        config.validate()
        print("✅ Configuration valid")
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False


def clear_cache():
    """Clear Python cache files to prevent import issues."""
    try:
        cache_dirs = []
        for root, dirs, files in os.walk('.'):
            for dir in dirs:
                if dir == '__pycache__':
                    cache_dirs.append(os.path.join(root, dir))

        for cache_dir in cache_dirs:
            import shutil
            shutil.rmtree(cache_dir)
            print(f"🧹 Cleared cache: {cache_dir}")

        # Remove .pyc files
        pyc_files = []
        for root, dirs, files in os.walk('.'):
            for file in files:
                if file.endswith('.pyc'):
                    pyc_files.append(os.path.join(root, file))

        for pyc_file in pyc_files:
            os.remove(pyc_file)
            print(f"🧹 Removed: {pyc_file}")

        if cache_dirs or pyc_files:
            print("✅ Python cache cleaned")

    except Exception as e:
        print(f"⚠️ Cache cleaning failed (non-critical): {e}")


def create_directories():
    """Create necessary directories."""
    directories = ['db', 'logs']

    for directory in directories:
        try:
            Path(directory).mkdir(exist_ok=True)
            print(f"✅ Directory ready: {directory}/")
        except Exception as e:
            print(f"❌ Could not create {directory}: {e}")
            return False

    return True


def run_bot():
    """Run the bot with proper error handling."""
    print("\n🚀 Starting Astrology Bot...")
    print("Press Ctrl+C to stop the bot")
    print("-" * 50)

    try:
        # Import and run the bot
        from astrology_bot_improved import run_bot
        run_bot()

    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
        return True

    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("Make sure all required files are present and dependencies installed")
        return False

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        print("\nTroubleshooting tips:")
        print("1. Check your .env file configuration")
        print("2. Verify your bot token is correct")
        print("3. Ensure admin IDs are set properly")
        print("4. Check the logs/astrology_bot.log file for details")
        return False


def main():
    """Main startup function with comprehensive checks."""
    print("=" * 60)
    print("🌟 ASTROLOGY BOT STARTUP 🌟")
    print("=" * 60)

    # Step 1: Check Python version
    if not check_python_version():
        sys.exit(1)

    # Step 2: Clear cache (helps with weak reference issues)
    clear_cache()

    # Step 3: Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Step 4: Create directories
    if not create_directories():
        sys.exit(1)

    # Step 5: Check configuration
    if not check_configuration():
        sys.exit(1)

    # Step 6: Run the bot
    print("\n✅ All checks passed!")
    success = run_bot()

    if success:
        print("\n✅ Bot shutdown completed successfully")
        sys.exit(0)
    else:
        print("\n❌ Bot encountered errors")
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Startup interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Startup script error: {e}")
        print("Try running the bot directly with: python astrology_bot_improved.py")
        sys.exit(1)
