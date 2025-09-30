"""
Database management for Astrology Bot - Enhanced with better error handling and structure
"""
import sqlite3
import logging
from datetime import date, datetime
from typing import Optional, Tuple, List, Dict
from pathlib import Path
from contextlib import contextmanager
from constants import SAMPLE_FACTS

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass


class DatabaseManager:
    """Manages SQLite database operations with improved error handling and structure."""

    def __init__(self, db_path: str):
        """
        Initialize database manager.

        Args:
            db_path: Path to SQLite database file

        Raises:
            DatabaseError: If initialization fails
        """
        self.db_path = db_path
        self._connection_timeout = 10.0
        logger.info(f"Initializing database at: {db_path}")

        try:
            self._ensure_db_directory()
            self._init_database()
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise DatabaseError(f"Failed to initialize database: {e}") from e

    def _ensure_db_directory(self) -> None:
        """
        Ensure database directory exists.

        Raises:
            OSError: If directory creation fails
        """
        try:
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Database directory verified: {db_dir}")
        except Exception as e:
            logger.error(f"Failed to create database directory: {e}")
            raise

    @contextmanager
    def _get_connection(self):
        """
        Context manager for database connections.

        Yields:
            sqlite3.Connection: Database connection

        Raises:
            DatabaseError: If connection fails
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=self._connection_timeout)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise DatabaseError(f"Failed to connect to database: {e}") from e
        finally:
            if conn:
                try:
                    conn.close()
                except sqlite3.Error as e:
                    logger.warning(f"Error closing connection: {e}")

    def _init_database(self) -> None:
        """
        Initialize database tables and populate with sample data.

        Raises:
            DatabaseError: If initialization fails
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Users table with comprehensive constraints
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        dob TEXT NOT NULL,
                        zodiac_sign TEXT NOT NULL CHECK(length(zodiac_sign) > 0),
                        life_path_number INTEGER NOT NULL CHECK(life_path_number BETWEEN 1 AND 33),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                logger.info("Users table created/verified")

                # Facts table with validation
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS facts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        day INTEGER CHECK(day IS NULL OR (day BETWEEN 1 AND 31)),
                        month INTEGER CHECK(month IS NULL OR (month BETWEEN 1 AND 12)),
                        fact_type TEXT NOT NULL CHECK(length(fact_type) > 0),
                        fact_text TEXT NOT NULL CHECK(length(fact_text) > 0),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                logger.info("Facts table created/verified")

                # Index for faster queries
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_facts_date 
                    ON facts(day, month)
                ''')

                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_users_zodiac 
                    ON users(zodiac_sign)
                ''')

                # Populate facts if empty
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
                logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Database initialization failed: {e}", exc_info=True)
            raise DatabaseError(f"Failed to initialize database tables: {e}") from e

    def save_user_dob(self, user_id: int, birth_date: date, zodiac: str, life_path: int) -> bool:
        """
        Save or update user's date of birth with comprehensive validation.

        Args:
            user_id: Telegram user ID
            birth_date: User's birth date
            zodiac: Zodiac sign
            life_path: Life path number

        Returns:
            bool: True if successful, False otherwise
        """
        if not isinstance(user_id, int) or user_id <= 0:
            logger.error(f"Invalid user_id: {user_id}")
            return False

        if not isinstance(birth_date, date):
            logger.error(f"Invalid birth_date type: {type(birth_date)}")
            return False

        if not zodiac or not isinstance(zodiac, str):
            logger.error(f"Invalid zodiac: {zodiac}")
            return False

        if not isinstance(life_path, int) or not (1 <= life_path <= 33):
            logger.error(f"Invalid life_path: {life_path}")
            return False

        try:
            logger.info(f"Saving DOB for user {user_id}")
            logger.debug(f"Data: date={birth_date}, zodiac={zodiac}, life_path={life_path}")

            with self._get_connection() as conn:
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
                    logger.error("Save appeared to succeed but user not found in database")
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

    def get_user_data(self, user_id: int) -> Optional[Tuple[str, str, int]]:
        """
        Get user's data (dob, zodiac, life_path).

        Args:
            user_id: Telegram user ID

        Returns:
            Optional[Tuple]: (dob_str, zodiac_sign, life_path_number) or None
        """
        if not isinstance(user_id, int) or user_id <= 0:
            logger.error(f"Invalid user_id: {user_id}")
            return None

        try:
            logger.debug(f"Fetching data for user {user_id}")

            with self._get_connection() as conn:
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

    def get_random_fact(self, day: Optional[int] = None, month: Optional[int] = None) -> Optional[Tuple[str, str]]:
        """
        Get a random fact, optionally filtered by day/month.

        Args:
            day: Day of month (1-31)
            month: Month (1-12)

        Returns:
            Optional[Tuple]: (fact_text, fact_type) or None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if day and month:
                    if not (1 <= day <= 31 and 1 <= month <= 12):
                        logger.warning(f"Invalid day/month: {day}/{month}")
                        day, month = None, None

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
                return (result['fact_text'], result['fact_type']) if result else None

        except Exception as e:
            logger.error(f"Failed to get random fact: {e}")
            return None

    def get_all_users(self) -> List[int]:
        """
        Get list of all user IDs.

        Returns:
            List[int]: List of user IDs
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT user_id FROM users ORDER BY user_id')
                results = cursor.fetchall()
                return [row['user_id'] for row in results]

        except Exception as e:
            logger.error(f"Failed to get all users: {e}")
            return []

    def get_user_count(self) -> int:
        """
        Get total number of users.

        Returns:
            int: Number of users
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) as count FROM users')
                result = cursor.fetchone()
                return result['count'] if result else 0

        except Exception as e:
            logger.error(f"Failed to get user count: {e}")
            return 0

    def delete_user(self, user_id: int) -> bool:
        """
        Delete a user from the database.

        Args:
            user_id: Telegram user ID

        Returns:
            bool: True if successful, False otherwise
        """
        if not isinstance(user_id, int) or user_id <= 0:
            logger.error(f"Invalid user_id: {user_id}")
            return False

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
                conn.commit()

                deleted_count = cursor.rowcount
                if deleted_count > 0:
                    logger.info(f"Deleted user {user_id}")
                    return True
                else:
                    logger.warning(f"User {user_id} not found for deletion")
                    return False

        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            return False

    def add_fact(self, fact_text: str, fact_type: str, day: Optional[int] = None, month: Optional[int] = None) -> bool:
        """
        Add a new fact to the database.

        Args:
            fact_text: The fact content
            fact_type: Type of fact (e.g., 'psychology', 'science')
            day: Optional day (1-31)
            month: Optional month (1-12)

        Returns:
            bool: True if successful, False otherwise
        """
        if not fact_text or not fact_type:
            logger.error("Fact text and type are required")
            return False

        if day and not (1 <= day <= 31):
            logger.error(f"Invalid day: {day}")
            return False

        if month and not (1 <= month <= 12):
            logger.error(f"Invalid month: {month}")
            return False

        try:
            with self._get_connection() as conn:
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

    def get_database_stats(self) -> Dict:
        """
        Get comprehensive database statistics.

        Returns:
            Dict: Statistics dictionary
        """
        try:
            with self._get_connection() as conn:
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

                # Database size
                db_path = Path(self.db_path)
                if db_path.exists():
                    stats['db_size_bytes'] = db_path.stat().st_size
                    stats['db_size_mb'] = round(stats['db_size_bytes'] / (1024 * 1024), 2)

                return stats

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}

    def test_connection(self) -> bool:
        """
        Test database connection and structure.

        Returns:
            bool: True if test passes, False otherwise
        """
        try:
            logger.info("Testing database connection...")

            with self._get_connection() as conn:
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

                # Test read operation
                cursor.execute("SELECT COUNT(*) as count FROM users")
                user_count = cursor.fetchone()['count']

                cursor.execute("SELECT COUNT(*) as count FROM facts")
                fact_count = cursor.fetchone()['count']

                logger.info(f"Database test passed. Users: {user_count}, Facts: {fact_count}")
                return True

        except Exception as e:
            logger.error(f"Database test failed: {e}", exc_info=True)
            return False

    def backup_database(self, backup_path: str) -> bool:
        """
        Create a backup of the database.

        Args:
            backup_path: Path for backup file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            return False

    def cleanup_old_users(self, days: int = 365) -> int:
        """
        Remove users inactive for specified days.

        Args:
            days: Number of days of inactivity

        Returns:
            int: Number of users removed
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM users 
                    WHERE updated_at < datetime('now', '-' || ? || ' days')
                ''', (days,))
                conn.commit()

                deleted = cursor.rowcount
                logger.info(f"Cleaned up {deleted} inactive users")
                return deleted

        except Exception as e:
            logger.error(f"Failed to cleanup old users: {e}")
            return 0