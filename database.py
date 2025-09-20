"""
Database management for Astrology Bot
"""
import os
import sqlite3
import logging
from contextlib import contextmanager
from datetime import date, datetime
from typing import Optional, Tuple, List
from constants import SAMPLE_FACTS

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Handles all database operations for the astrology bot."""
    
    def __init__(self, db_path: str = "db/astrology_bot.db"):
        self.db_path = db_path
        # Ensure db directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def init_database(self):
        """Initialize SQLite database and create tables if they don't exist."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        dob TEXT,
                        zodiac_sign TEXT,
                        life_path_number INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create facts table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS facts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        day INTEGER,
                        month INTEGER,
                        type TEXT DEFAULT 'general',
                        fact_text TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create subscriptions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS subscriptions (
                        user_id INTEGER PRIMARY KEY,
                        subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_facts_day ON facts(day)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_facts_type ON facts(type)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at)')
                
                # Insert sample facts if table is empty
                cursor.execute('SELECT COUNT(*) FROM facts')
                if cursor.fetchone()[0] == 0:
                    cursor.executemany(
                        'INSERT INTO facts (day, month, type, fact_text) VALUES (?, ?, ?, ?)',
                        SAMPLE_FACTS
                    )
                    logger.info(f"Inserted {len(SAMPLE_FACTS)} sample facts")
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def save_user_dob(self, user_id: int, dob: date, zodiac: str, life_path: int) -> bool:
        """Save user's date of birth and calculated astro data."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users (user_id, dob, zodiac_sign, life_path_number)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, dob.isoformat(), zodiac, life_path))
                conn.commit()
                logger.info(f"Saved DOB for user {user_id}: {dob}")
                return True
        except Exception as e:
            logger.error(f"Failed to save user DOB: {e}")
            return False
    
    def get_user_data(self, user_id: int) -> Optional[Tuple[str, str, int]]:
        """Retrieve user's stored data."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT dob, zodiac_sign, life_path_number FROM users WHERE user_id = ?',
                    (user_id,)
                )
                result = cursor.fetchone()
                return tuple(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get user data: {e}")
            return None
    
    def get_fact_by_day(self, day: int) -> Optional[Tuple[str, str]]:
        """Get a random fact for a specific day."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT fact_text, type
                    FROM facts
                    WHERE day = ? OR (day IS NULL AND ? % 7 = id % 7)
                    ORDER BY RANDOM() LIMIT 1
                ''', (day, day))
                result = cursor.fetchone()
                return (result[0], result[1]) if result else None
        except Exception as e:
            logger.error(f"Failed to get fact for day {day}: {e}")
            return None
    
    def get_random_fact(self) -> Optional[Tuple[str, str]]:
        """Get a random fact from the database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT fact_text, type FROM facts ORDER BY RANDOM() LIMIT 1')
                result = cursor.fetchone()
                return (result[0], result[1]) if result else None
        except Exception as e:
            logger.error(f"Failed to get random fact: {e}")
            return None
    
    def get_facts_by_type(self, fact_type: str) -> List[Tuple[str, str]]:
        """Get facts by type (psychology, science, etc.)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT fact_text, type FROM facts WHERE type = ? ORDER BY RANDOM() LIMIT 2',
                    (fact_type,)
                )
                return [tuple(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get facts by type {fact_type}: {e}")
            return []
    
    def add_fact(self, day: Optional[int], month: Optional[int], fact_type: str, fact_text: str) -> bool:
        """Add a new fact to the database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO facts (day, month, type, fact_text) VALUES (?, ?, ?, ?)',
                    (day, month, fact_type, fact_text)
                )
                conn.commit()
                logger.info(f"Added new fact: {fact_text[:50]}...")
                return True
        except Exception as e:
            logger.error(f"Failed to add fact: {e}")
            return False
    
    def get_all_user_ids(self) -> List[int]:
        """Get all registered user IDs for broadcasting."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT user_id FROM users')
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get user IDs: {e}")
            return []
    
    def get_user_count(self) -> int:
        """Get total number of users."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM users')
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get user count: {e}")
            return 0
    
    def get_fact_count(self) -> int:
        """Get total number of facts."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM facts')
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get fact count: {e}")
            return 0
    
    def subscribe_user(self, user_id: int) -> bool:
        """Subscribe a user to notifications."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT OR IGNORE INTO subscriptions (user_id) VALUES (?)',
                    (user_id,)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to subscribe user {user_id}: {e}")
            return False
    
    def unsubscribe_user(self, user_id: int) -> bool:
        """Unsubscribe a user from notifications."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM subscriptions WHERE user_id = ?', (user_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to unsubscribe user {user_id}: {e}")
            return False
    
    def is_subscribed(self, user_id: int) -> bool:
        """Check if user is subscribed to notifications."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1 FROM subscriptions WHERE user_id = ?', (user_id,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Failed to check subscription for user {user_id}: {e}")
            return False
    
    def get_subscribed_users(self) -> List[int]:
        """Get all subscribed user IDs."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT user_id FROM subscriptions')
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get subscribed users: {e}")
            return []
    
    def cleanup_old_data(self, days: int = 365) -> bool:
        """Clean up old data (optional maintenance function)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Clean up old subscription records if needed
                cursor.execute('''
                    DELETE FROM subscriptions 
                    WHERE user_id NOT IN (SELECT user_id FROM users)
                ''')
                cleaned_rows = cursor.rowcount
                conn.commit()
                logger.info(f"Cleaned up {cleaned_rows} orphaned subscription records")
                return True
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return False
    
    def backup_database(self, backup_path: str) -> bool:
        """Create a backup of the database."""
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            return False
    
    def get_database_stats(self) -> dict:
        """Get database statistics."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # User count
                cursor.execute('SELECT COUNT(*) FROM users')
                stats['users'] = cursor.fetchone()[0]
                
                # Fact count
                cursor.execute('SELECT COUNT(*) FROM facts')
                stats['facts'] = cursor.fetchone()[0]
                
                # Subscription count
                cursor.execute('SELECT COUNT(*) FROM subscriptions')
                stats['subscriptions'] = cursor.fetchone()[0]
                
                # Facts by type
                cursor.execute('SELECT type, COUNT(*) FROM facts GROUP BY type')
                stats['facts_by_type'] = dict(cursor.fetchall())
                
                # Recent users (last 7 days)
                cursor.execute('''
                    SELECT COUNT(*) FROM users 
                    WHERE created_at >= datetime('now', '-7 days')
                ''')
                stats['recent_users'] = cursor.fetchone()[0]
                
                return stats
                
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}
    
    def __str__(self) -> str:
        """String representation of the database manager."""
        return f"DatabaseManager(db_path='{self.db_path}')"