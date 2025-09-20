"""
Configuration management for Astrology Bot
"""
import os
import logging
from dataclasses import dataclass
from typing import List

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Make sure to set environment variables manually.")


@dataclass
class Config:
    """Bot configuration from environment variables."""
    
    # Required settings
    token: str
    admin_ids: List[int]
    
    # Optional settings with defaults
    db_path: str = "db/astrology_bot.db"
    log_level: str = "INFO"
    upi_id: str = ""
    support_message: str = "Support our bot development!"
    max_broadcast_users: int = 1000
    conversation_timeout: int = 300  # 5 minutes
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create configuration from environment variables."""
        
        # Required settings
        token = os.getenv('TELEGRAM_TOKEN', '')
        if not token:
            raise ValueError("TELEGRAM_TOKEN environment variable is required!")
        
        admin_ids_str = os.getenv('ADMIN_IDS', '')
        if not admin_ids_str:
            raise ValueError("ADMIN_IDS environment variable is required!")
        
        try:
            admin_ids = [int(x.strip()) for x in admin_ids_str.split(',') if x.strip()]
            if not admin_ids:
                raise ValueError("At least one admin ID is required!")
        except ValueError as e:
            raise ValueError(f"Invalid ADMIN_IDS format. Use comma-separated numbers: {e}")
        
        # Optional settings
        return cls(
            token=token,
            admin_ids=admin_ids,
            db_path=os.getenv('DB_PATH', 'db/astrology_bot.db'),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            upi_id=os.getenv('UPI_ID', ''),
            support_message=os.getenv('SUPPORT_MESSAGE', 'Support our bot development!'),
            max_broadcast_users=int(os.getenv('MAX_BROADCAST_USERS', '1000')),
            conversation_timeout=int(os.getenv('CONVERSATION_TIMEOUT', '300'))
        )
    
    def validate(self) -> None:
        """Validate configuration values."""
        if len(self.token) < 10:
            raise ValueError("Invalid bot token format!")
        
        if not self.admin_ids:
            raise ValueError("At least one admin ID is required!")
        
        for admin_id in self.admin_ids:
            if not isinstance(admin_id, int) or admin_id <= 0:
                raise ValueError(f"Invalid admin ID: {admin_id}")
        
        if self.conversation_timeout <= 0:
            raise ValueError("Conversation timeout must be positive!")


def setup_logging(config: Config) -> None:
    """Setup logging configuration."""
    from logging.handlers import RotatingFileHandler
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Configure logging level
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    
    # Setup handlers
    handlers = [
        # File handler with rotation
        RotatingFileHandler(
            'logs/astrology_bot.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        ),
        # Console handler
        logging.StreamHandler()
    ]
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    # Reduce telegram library verbosity
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)