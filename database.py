"""
Database management for Astrology Bot - Enhanced with better error handling
"""
import sqlite3
import logging
from datetime import date, datetime
from typing import Optional, Tuple, List
from pathlib import Path
from constants import SAMPLE_FACTS

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database operations with improved error handling."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        logger.info(f"Initializing database at: {db_path}")
        self._ensure_db_directory()
        self._init_database()

    def _ensure_db_directory(self):
        """Ensure database directory exists."""
        try:
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Database directory created/verified: {db_dir}")
        except Exception as e:
            logger.error(f"Failed to create database directory: {e}")
            raise

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with better error handling."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.row_factory = sqlite3.Row
            # Enable foreign keys and set journal mode
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def _init_database(self):
        """Initialize database tables with improved error handling."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Users table with better constraints
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    dob TEXT NOT NULL,
                    zodiac_sign TEXT NOT NULL,
                    life_path_number INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            logger.info("Users table created/verified")

            # Facts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    day INTEGER,
                    month INTEGER,
                    fact_type TEXT NOT NULL,
                    fact_text TEXT NOT NULL
                )
            ''')
            logger.info("Facts table created/verified")

            # Check if facts table is empty and populate
            cursor.execute('SELECT COUNT(*) as count FROM facts')
            count = cursor.fetchone()['count']

            if count == 0:
                logger.info("Populating facts table with sample data...")
                cursor.executemany(
                    'INSERT INTO facts (day, month, fact_type, fact_text) VALUES (?, ?, ?, ?)',
                    SAMPLE_FACTS
                )
                logger.info(f"Inserted {len(SAMPLE_FACTS)} facts into database")

            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Database initialization failed: {e}", exc_info=True)
            raise

    def save_user_dob(self, user_id: int, birth_date: date, zodiac: str, life_path: int) -> bool:
        """Save or update user's date of birth with enhanced error handling."""
        conn = None
        try:
            logger.info(f"Attempting to save DOB for user {user_id}")
            logger.debug(f"Data: date={birth_date}, zodiac={zodiac}, life_path={life_path}")

            conn = self._get_connection()
            cursor = conn.cursor()

            dob_str = birth_date.isoformat()

            # Check if user exists
            cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
            exists = cursor.fetchone()

            if exists:
                logger.info(f"Updating existing user {user_id}")
                cursor.execute('''
                    UPDATE users 
                    SET dob = ?, zodiac_sign = ?, life_path_number = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (dob_str, zodiac, life_path, user_id))
            else:
                logger.info(f"Inserting new user {user_id}")
                cursor.execute('''
                    INSERT INTO users (user_id, dob, zodiac_sign, life_path_number)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, dob_str, zodiac, life_path))

            conn.commit()

            # Verify the save
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            saved_user = cursor.fetchone()

            if saved_user:
                logger.info(f"Successfully saved DOB for user {user_id}: {zodiac}, Life Path {life_path}")
                return True
            else:
                logger.error(f"Save appeared to succeed but user not found in database")
                return False

        except sqlite3.IntegrityError as e:
            logger.error(f"Integrity error saving DOB for user {user_id}: {e}")
            return False
        except sqlite3.OperationalError as e:
            logger.error(f"Database operational error for user {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving DOB for user {user_id}: {e}", exc_info=True)
            return False
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass

    def get_user_data(self, user_id: int) -> Optional[Tuple[str, str, int]]:
        """Get user's data (dob, zodiac, life_path) with enhanced error handling."""
        conn = None
        try:
            logger.debug(f"Fetching data for user {user_id}")
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                'SELECT dob, zodiac_sign, life_path_number FROM users WHERE user_id = ?',
                (user_id,)
            )

            result = cursor.fetchone()

            if result:
                logger.debug(f"Found data for user {user_id}")
                return (result['dob'], result['zodiac_sign'], result['life_path_number'])
            else:
                logger.debug(f"No data found for user {user_id}")
                return None

        except Exception as e:
            logger.error(f"Failed to get data for user {user_id}: {e}", exc_info=True)
            return None
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass

    def get_random_fact(self, day: Optional[int] = None, month: Optional[int] = None) -> Optional[Tuple[str, str]]:
        """Get a random fact, optionally filtered by day/month."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            if day and month:
                cursor.execute('''
                    SELECT fact_text, fact_type FROM facts
                    WHERE (day = ? AND month = ?) OR (day IS NULL AND month IS NULL)
                    ORDER BY RANDOM()
                    LIMIT 1
                ''', (day, month))
            elif day:
                cursor.execute('''
                    SELECT fact_text, fact_type FROM facts
                    WHERE day = ? OR day IS NULL
                    ORDER BY RANDOM()
                    LIMIT 1
                ''', (day,))
            else:
                cursor.execute('''
                    SELECT fact_text, fact_type FROM facts
                    ORDER BY RANDOM()
                    LIMIT 1
                ''')

            result = cursor.fetchone()

            if result:
                return (result['fact_text'], result['fact_type'])
            return None

        except Exception as e:
            logger.error(f"Failed to get random fact: {e}")
            return None
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass

    def get_all_users(self) -> List[int]:
        """Get list of all user IDs."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT user_id FROM users')
            results = cursor.fetchall()

            return [row['user_id'] for row in results]

        except Exception as e:
            logger.error(f"Failed to get all users: {e}")
            return []
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass

    def get_user_count(self) -> int:
        """Get total number of users."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) as count FROM users')
            result = cursor.fetchone()

            return result['count'] if result else 0

        except Exception as e:
            logger.error(f"Failed to get user count: {e}")
            return 0
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass

    def delete_user(self, user_id: int) -> bool:
        """Delete a user from the database."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
            conn.commit()

            logger.info(f"Deleted user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            return False
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass

    def add_fact(self, fact_text: str, fact_type: str, day: Optional[int] = None, month: Optional[int] = None) -> bool:
        """Add a new fact to the database."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                'INSERT INTO facts (day, month, fact_type, fact_text) VALUES (?, ?, ?, ?)',
                (day, month, fact_type, fact_text)
            )

            conn.commit()

            logger.info(f"Added new {fact_type} fact")
            return True

        except Exception as e:
            logger.error(f"Failed to add fact: {e}")
            return False
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass

    def get_database_stats(self) -> dict:
        """Get database statistics."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            stats = {}

            cursor.execute('SELECT COUNT(*) as count FROM users')
            stats['total_users'] = cursor.fetchone()['count']

            cursor.execute('SELECT COUNT(*) as count FROM facts')
            stats['total_facts'] = cursor.fetchone()['count']

            cursor.execute('SELECT zodiac_sign, COUNT(*) as count FROM users GROUP BY zodiac_sign')
            stats['zodiac_distribution'] = {row['zodiac_sign']: row['count'] for row in cursor.fetchall()}

            cursor.execute('SELECT life_path_number, COUNT(*) as count FROM users GROUP BY life_path_number')
            stats['life_path_distribution'] = {row['life_path_number']: row['count'] for row in cursor.fetchall()}

            return stats

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass

    def test_connection(self) -> bool:
        """Test database connection and structure."""
        conn = None
        try:
            logger.info("Testing database connection...")
            conn = self._get_connection()
            cursor = conn.cursor()

            # Test users table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if not cursor.fetchone():
                logger.error("Users table does not exist!")
                return False

            # Test facts table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='facts'")
            if not cursor.fetchone():
                logger.error("Facts table does not exist!")
                return False

            # Test write permission
            cursor.execute("SELECT COUNT(*) as count FROM users")
            user_count = cursor.fetchone()['count']
            logger.info(f"Database test passed. Current users: {user_count}")

            return True

        except Exception as e:
            logger.error(f"Database test failed: {e}", exc_info=True)
            return False
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass