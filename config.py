"""
Enhanced Configuration management for Astrology Bot
Fixes compatibility issues with python-telegram-bot 21.x
"""
import os
import logging
import sys
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    print("Warning: python-dotenv not installed. Using system environment variables.")


@dataclass
class Config:
    """Enhanced bot configuration with better validation and defaults."""

    # Required settings
    token: str
    admin_ids: List[int]

    # Optional settings with sensible defaults
    db_path: str = "db/astrology_bot.db"
    log_level: str = "INFO"
    log_file: str = "logs/astrology_bot.log"
    upi_id: str = ""
    support_message: str = "Support our bot development! ⭐"
    max_broadcast_users: int = 1000
    conversation_timeout: int = 300  # 5 minutes

    # Bot behavior settings
    enable_markdown: bool = True
    fallback_mode: bool = True  # Use fallback messages when markdown fails
    rate_limit_enabled: bool = True
    debug_mode: bool = False

    # Connection settings
    request_timeout: float = 30.0
    connection_pool_size: int = 8
    retry_attempts: int = 3

    # Admin settings
    admin_commands_enabled: bool = True
    broadcast_enabled: bool = True
    health_check_enabled: bool = True

    @classmethod
    def from_env(cls) -> 'Config':
        """Create configuration from environment variables with enhanced validation."""

        # Check for required environment variables
        token = os.getenv('TELEGRAM_TOKEN', '').strip()
        if not token:
            raise ValueError(
                "TELEGRAM_TOKEN environment variable is required!\n"
                "Get your token from @BotFather on Telegram and set it in .env file"
            )

        # Validate token format
        if not token.count(':') == 1 or len(token) < 20:
            raise ValueError(
                "Invalid bot token format!\n"
                "Token should look like: 123456789:ABCDEF...\n"
                "Get a valid token from @BotFather"
            )

        admin_ids_str = os.getenv('ADMIN_IDS', '').strip()
        if not admin_ids_str:
            raise ValueError(
                "ADMIN_IDS environment variable is required!\n"
                "Get your user ID from @userinfobot and set it in .env file\n"
                "Format: ADMIN_IDS=123456789,987654321"
            )

        # Parse admin IDs with better error handling
        try:
            admin_ids = []
            for id_str in admin_ids_str.split(','):
                id_str = id_str.strip()
                if id_str:  # Skip empty strings
                    admin_id = int(id_str)
                    if admin_id <= 0:
                        raise ValueError(f"Admin ID must be positive: {admin_id}")
                    admin_ids.append(admin_id)

            if not admin_ids:
                raise ValueError("At least one valid admin ID is required!")

        except ValueError as e:
            raise ValueError(
                f"Invalid ADMIN_IDS format: {e}\n"
                "Use comma-separated positive numbers: 123456789,987654321"
            )

        # Parse optional boolean settings
        def parse_bool(env_var: str, default: bool = False) -> bool:
            """Parse boolean environment variable."""
            value = os.getenv(env_var, '').lower().strip()
            return value in ('true', '1', 'yes', 'on', 'enabled')

        def parse_float(env_var: str, default: float) -> float:
            """Parse float environment variable with fallback."""
            try:
                return float(os.getenv(env_var, str(default)))
            except ValueError:
                return default

        def parse_int(env_var: str, default: int) -> int:
            """Parse integer environment variable with fallback."""
            try:
                return int(os.getenv(env_var, str(default)))
            except ValueError:
                return default

        # Create configuration instance
        return cls(
            token=token,
            admin_ids=admin_ids,
            db_path=os.getenv('DB_PATH', 'db/astrology_bot.db'),
            log_level=os.getenv('LOG_LEVEL', 'INFO').upper(),
            log_file=os.getenv('LOG_FILE', 'logs/astrology_bot.log'),
            upi_id=os.getenv('UPI_ID', '').strip(),
            support_message=os.getenv('SUPPORT_MESSAGE', 'Support our bot development!'),
            max_broadcast_users=parse_int('MAX_BROADCAST_USERS', 1000),
            conversation_timeout=parse_int('CONVERSATION_TIMEOUT', 300),

            # Enhanced settings
            enable_markdown=parse_bool('ENABLE_MARKDOWN', True),
            fallback_mode=parse_bool('FALLBACK_MODE', True),
            rate_limit_enabled=parse_bool('RATE_LIMIT_ENABLED', True),
            debug_mode=parse_bool('DEBUG_MODE', False),

            # Connection settings
            request_timeout=parse_float('REQUEST_TIMEOUT', 30.0),
            connection_pool_size=parse_int('CONNECTION_POOL_SIZE', 8),
            retry_attempts=parse_int('RETRY_ATTEMPTS', 3),

            # Admin settings
            admin_commands_enabled=parse_bool('ADMIN_COMMANDS_ENABLED', True),
            broadcast_enabled=parse_bool('BROADCAST_ENABLED', True),
            health_check_enabled=parse_bool('HEALTH_CHECK_ENABLED', True),
        )

    def validate(self) -> None:
        """Comprehensive configuration validation."""
        errors = []

        # Validate token
        if not self.token or len(self.token) < 10:
            errors.append("Invalid bot token format!")

        if ':' not in self.token:
            errors.append("Bot token must contain ':' separator!")

        # Validate admin IDs
        if not self.admin_ids:
            errors.append("At least one admin ID is required!")

        for admin_id in self.admin_ids:
            if not isinstance(admin_id, int) or admin_id <= 0:
                errors.append(f"Invalid admin ID: {admin_id}")

        # Validate paths
        try:
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create database directory: {e}")

        try:
            log_dir = Path(self.log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create log directory: {e}")

        # Validate numeric ranges
        if self.conversation_timeout <= 0:
            errors.append("Conversation timeout must be positive!")

        if self.max_broadcast_users <= 0:
            errors.append("Max broadcast users must be positive!")

        if self.request_timeout <= 0:
            errors.append("Request timeout must be positive!")

        if self.connection_pool_size <= 0:
            errors.append("Connection pool size must be positive!")

        if self.retry_attempts < 0:
            errors.append("Retry attempts cannot be negative!")

        # Validate log level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level not in valid_levels:
            errors.append(f"Invalid log level: {self.log_level}. Use one of: {valid_levels}")

        # Raise all errors at once
        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors)
            raise ValueError(error_message)

    def get_log_level(self) -> int:
        """Get numeric log level."""
        return getattr(logging, self.log_level, logging.INFO)

    def is_debug_enabled(self) -> bool:
        """Check if debug mode is enabled."""
        return self.debug_mode or self.log_level == 'DEBUG'

    def create_directories(self) -> None:
        """Create necessary directories."""
        directories = [
            Path(self.db_path).parent,
            Path(self.log_file).parent
        ]

        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ValueError(f"Could not create directory {directory}: {e}")

    def __str__(self) -> str:
        """String representation without sensitive data."""
        return (
            f"Config(token=***{self.token[-4:]}, "
            f"admins={len(self.admin_ids)}, "
            f"db_path='{self.db_path}', "
            f"log_level='{self.log_level}')"
        )


def setup_logging(config: Config) -> None:
    """Enhanced logging setup with rotation and better formatting."""
    from logging.handlers import RotatingFileHandler
    import sys

    # Create directories
    config.create_directories()

    # Configure logging level
    log_level = config.get_log_level()

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # Setup file handler with rotation
    try:
        file_handler = RotatingFileHandler(
            config.log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(detailed_formatter)
    except Exception as e:
        print(f"Warning: Could not setup file logging: {e}")
        file_handler = None

    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter)

    # Configure root logger
    handlers = [console_handler]
    if file_handler:
        handlers.append(file_handler)

    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True  # Override any existing configuration
    )

    # Configure third-party library logging
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.INFO if config.is_debug_enabled() else logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    # Log configuration info
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={config.log_level}")
    if file_handler:
        logger.info(f"Log file: {config.log_file}")

    if config.is_debug_enabled():
        logger.debug("Debug mode enabled")
        logger.debug(f"Configuration: {config}")


def validate_environment() -> None:
    """Validate the runtime environment."""
    errors = []

    # Check Python version
    if sys.version_info < (3, 8):
        errors.append(f"Python 3.8+ required, got {sys.version_info}")

    # Check if dotenv is available when .env file exists
    if Path('.env').exists() and not DOTENV_AVAILABLE:
        errors.append(
            "Found .env file but python-dotenv is not installed. "
            "Install with: pip install python-dotenv"
        )

    # Check required directories can be created
    test_dirs = ['db', 'logs']
    for dir_name in test_dirs:
        try:
            Path(dir_name).mkdir(exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create {dir_name} directory: {e}")

    if errors:
        error_message = "Environment validation failed:\n" + "\n".join(f"- {error}" for error in errors)
        raise RuntimeError(error_message)


def create_example_env() -> None:
    """Create an example .env file if it doesn't exist."""
    env_example_path = Path('.env.example')
    if env_example_path.exists():
        return

    example_content = '''# Telegram Bot Configuration
# Get your bot token from @BotFather on Telegram
TELEGRAM_TOKEN=your_bot_token_here

# Admin user IDs (comma-separated)
# Get your user ID from @userinfobot on Telegram  
ADMIN_IDS=123456789,987654321

# Database and logging (optional)
DB_PATH=db/astrology_bot.db
LOG_LEVEL=INFO
LOG_FILE=logs/astrology_bot.log

# Support information (optional)
UPI_ID=your-upi-id@paytm
SUPPORT_MESSAGE=Support our bot development!

# Bot behavior settings (optional)
ENABLE_MARKDOWN=true
FALLBACK_MODE=true
DEBUG_MODE=false

# Performance settings (optional)
MAX_BROADCAST_USERS=1000
CONVERSATION_TIMEOUT=300
REQUEST_TIMEOUT=30.0
CONNECTION_POOL_SIZE=8
RETRY_ATTEMPTS=3

# Admin features (optional)
ADMIN_COMMANDS_ENABLED=true
BROADCAST_ENABLED=true
HEALTH_CHECK_ENABLED=true
'''

    try:
        with open('.env.example', 'w', encoding='utf-8') as f:
            f.write(example_content)
        print("Created .env.example file")
    except Exception as e:
        print(f"Could not create .env.example: {e}")


# Auto-create example env file when module is imported
if __name__ != '__main__':
    try:
        create_example_env()
    except Exception:
        pass  # Ignore errors during import