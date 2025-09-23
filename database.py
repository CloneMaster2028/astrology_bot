"""
Enhanced Database Management for Astrology Bot with Advanced Features
"""
import os
import sqlite3
import logging
import json
import hashlib
import threading
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import asyncio
import aiofiles
from collections import defaultdict
import pickle

# Configure logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Enhanced constants
DEFAULT_DB_PATH = "db/astrology_bot.db"
BACKUP_DIR = "backups"
CACHE_EXPIRY = 3600  # 1 hour in seconds


class FactType(Enum):
    """Enumeration for fact types"""
    GENERAL = "general"
    PSYCHOLOGY = "psychology"
    SCIENCE = "science"
    MYTHOLOGY = "mythology"
    NUMEROLOGY = "numerology"
    COMPATIBILITY = "compatibility"
    DAILY = "daily"
    PERSONALITY = "personality"


class UserStatus(Enum):
    """User status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PREMIUM = "premium"


@dataclass
class UserProfile:
    """Enhanced user profile data structure"""
    user_id: int
    dob: Optional[str] = None
    zodiac_sign: Optional[str] = None
    life_path_number: Optional[int] = None
    status: str = UserStatus.ACTIVE.value
    preferences: Dict[str, Any] = None
    timezone: Optional[str] = None
    language: str = "en"
    created_at: Optional[str] = None
    last_active: Optional[str] = None
    premium_until: Optional[str] = None

    def __post_init__(self):
        if self.preferences is None:
            self.preferences = {}


@dataclass
class Fact:
    """Fact data structure"""
    id: Optional[int] = None
    day: Optional[int] = None
    month: Optional[int] = None
    fact_type: str = FactType.GENERAL.value
    fact_text: str = ""
    tags: List[str] = None
    difficulty: str = "beginner"  # beginner, intermediate, advanced
    rating: float = 0.0
    view_count: int = 0
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class QueryCache:
    """Simple in-memory cache for database queries"""

    def __init__(self, expiry_seconds: int = CACHE_EXPIRY):
        self._cache = {}
        self._expiry = expiry_seconds
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                data, timestamp = self._cache[key]
                if time.time() - timestamp < self._expiry:
                    return data
                else:
                    del self._cache[key]
            return None

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = (value, time.time())

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate cache entries matching a pattern"""
        with self._lock:
            keys_to_remove = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self._cache[key]


class DatabaseManager:
    """Enhanced database manager with advanced features"""

    def __init__(self, db_path: str = DEFAULT_DB_PATH, enable_cache: bool = True):
        self.db_path = db_path
        self.enable_cache = enable_cache
        self.cache = QueryCache() if enable_cache else None
        self._connection_pool = []
        self._pool_lock = threading.Lock()
        self._stats = defaultdict(int)

        # Ensure directories exist
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(BACKUP_DIR).mkdir(exist_ok=True)

        self.init_database()
        self._start_maintenance_thread()

    @contextmanager
    def get_connection(self):
        """Enhanced context manager with connection pooling."""
        conn = None
        try:
            with self._pool_lock:
                if self._connection_pool:
                    conn = self._connection_pool.pop()
                else:
                    conn = sqlite3.connect(
                        self.db_path,
                        timeout=30.0,
                        check_same_thread=False
                    )
                    conn.row_factory = sqlite3.Row
                    # Enable WAL mode for better concurrency
                    conn.execute('PRAGMA journal_mode=WAL')
                    conn.execute('PRAGMA synchronous=NORMAL')
                    conn.execute('PRAGMA cache_size=10000')
                    conn.execute('PRAGMA temp_store=MEMORY')

            yield conn

        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            self._stats['errors'] += 1
            raise
        finally:
            if conn:
                with self._pool_lock:
                    if len(self._connection_pool) < 5:  # Max pool size
                        self._connection_pool.append(conn)
                    else:
                        conn.close()

    def init_database(self):
        """Initialize enhanced database schema."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Enhanced users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        dob TEXT,
                        zodiac_sign TEXT,
                        life_path_number INTEGER,
                        status TEXT DEFAULT 'active',
                        preferences TEXT DEFAULT '{}',
                        timezone TEXT,
                        language TEXT DEFAULT 'en',
                        premium_until TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        profile_hash TEXT
                    )
                ''')

                # Enhanced facts table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS facts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        day INTEGER,
                        month INTEGER,
                        type TEXT DEFAULT 'general',
                        fact_text TEXT NOT NULL,
                        tags TEXT DEFAULT '[]',
                        difficulty TEXT DEFAULT 'beginner',
                        rating REAL DEFAULT 0.0,
                        view_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        content_hash TEXT UNIQUE
                    )
                ''')

                # User interactions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_interactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        fact_id INTEGER,
                        interaction_type TEXT,  -- view, like, dislike, share
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT DEFAULT '{}',
                        FOREIGN KEY (user_id) REFERENCES users(user_id),
                        FOREIGN KEY (fact_id) REFERENCES facts(id)
                    )
                ''')

                # Enhanced subscriptions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS subscriptions (
                        user_id INTEGER PRIMARY KEY,
                        subscription_type TEXT DEFAULT 'daily',
                        frequency TEXT DEFAULT 'daily',  -- daily, weekly, monthly
                        preferred_time TEXT DEFAULT '09:00',
                        subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_sent TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')

                # Analytics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS analytics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT NOT NULL,
                        user_id INTEGER,
                        data TEXT DEFAULT '{}',
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # User sessions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        session_end TIMESTAMP,
                        activity_count INTEGER DEFAULT 0,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')

                # Create comprehensive indexes
                indexes = [
                    'CREATE INDEX IF NOT EXISTS idx_facts_day ON facts(day)',
                    'CREATE INDEX IF NOT EXISTS idx_facts_type ON facts(type)',
                    'CREATE INDEX IF NOT EXISTS idx_facts_rating ON facts(rating)',
                    'CREATE INDEX IF NOT EXISTS idx_facts_difficulty ON facts(difficulty)',
                    'CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)',
                    'CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at)',
                    'CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active)',
                    'CREATE INDEX IF NOT EXISTS idx_interactions_user ON user_interactions(user_id)',
                    'CREATE INDEX IF NOT EXISTS idx_interactions_fact ON user_interactions(fact_id)',
                    'CREATE INDEX IF NOT EXISTS idx_interactions_type ON user_interactions(interaction_type)',
                    'CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(is_active)',
                    'CREATE INDEX IF NOT EXISTS idx_analytics_event ON analytics(event_type)',
                    'CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id)'
                ]

                for index_sql in indexes:
                    cursor.execute(index_sql)

                # Create views for common queries
                cursor.execute('''
                    CREATE VIEW IF NOT EXISTS user_stats AS
                    SELECT 
                        u.user_id,
                        u.zodiac_sign,
                        u.status,
                        u.created_at,
                        COUNT(ui.id) as total_interactions,
                        MAX(ui.timestamp) as last_interaction
                    FROM users u
                    LEFT JOIN user_interactions ui ON u.user_id = ui.user_id
                    GROUP BY u.user_id
                ''')

                cursor.execute('''
                    CREATE VIEW IF NOT EXISTS fact_popularity AS
                    SELECT 
                        f.*,
                        COUNT(ui.id) as interaction_count,
                        AVG(CASE WHEN ui.interaction_type = 'like' THEN 1 
                                WHEN ui.interaction_type = 'dislike' THEN -1 
                                ELSE 0 END) as like_ratio
                    FROM facts f
                    LEFT JOIN user_interactions ui ON f.id = ui.fact_id
                    GROUP BY f.id
                ''')

                # Insert sample data if needed
                self._insert_sample_data_if_needed(cursor)

                conn.commit()
                logger.info("Enhanced database initialized successfully")
                self._stats['initializations'] += 1

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _insert_sample_data_if_needed(self, cursor):
        """Insert sample data if tables are empty."""
        cursor.execute('SELECT COUNT(*) FROM facts')
        if cursor.fetchone()[0] == 0:
            sample_facts = [
                (1, 1, FactType.DAILY.value, "Capricorns born on January 1st often possess natural leadership qualities.",
                 '["leadership", "capricorn", "personality"]', "beginner"),
                (15, 2, FactType.PSYCHOLOGY.value, "Aquarians tend to be more creative when working in groups.",
                 '["creativity", "aquarius", "teamwork"]', "intermediate"),
                (None, None, FactType.SCIENCE.value, "The gravitational pull of the moon affects human behavior subtly.",
                 '["moon", "behavior", "science"]', "advanced"),
            ]

            for day, month, fact_type, text, tags, difficulty in sample_facts:
                content_hash = hashlib.md5(text.encode()).hexdigest()
                cursor.execute('''
                    INSERT INTO facts (day, month, type, fact_text, tags, difficulty, content_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (day, month, fact_type, text, tags, difficulty, content_hash))

    def save_user_profile(self, profile: UserProfile) -> bool:
        """Save enhanced user profile."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Create profile hash for change detection
                profile_data = {
                    'dob': profile.dob,
                    'zodiac_sign': profile.zodiac_sign,
                    'preferences': profile.preferences
                }
                profile_hash = hashlib.md5(json.dumps(profile_data, sort_keys=True).encode()).hexdigest()

                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (user_id, dob, zodiac_sign, life_path_number, status, preferences, 
                     timezone, language, premium_until, last_active, profile_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    profile.user_id, profile.dob, profile.zodiac_sign,
                    profile.life_path_number, profile.status,
                    json.dumps(profile.preferences), profile.timezone,
                    profile.language, profile.premium_until,
                    datetime.now().isoformat(), profile_hash
                ))

                conn.commit()

                # Clear related cache entries
                if self.cache:
                    self.cache.invalidate_pattern(f"user_{profile.user_id}")

                logger.info(f"Saved profile for user {profile.user_id}")
                self._stats['profile_saves'] += 1
                return True

        except Exception as e:
            logger.error(f"Failed to save user profile: {e}")
            return False

    def get_user_profile(self, user_id: int) -> Optional[UserProfile]:
        """Get enhanced user profile."""
        cache_key = f"user_profile_{user_id}"

        if self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                return cached

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, dob, zodiac_sign, life_path_number, status, 
                           preferences, timezone, language, created_at, 
                           last_active, premium_until
                    FROM users WHERE user_id = ?
                ''', (user_id,))

                result = cursor.fetchone()
                if result:
                    profile = UserProfile(
                        user_id=result[0],
                        dob=result[1],
                        zodiac_sign=result[2],
                        life_path_number=result[3],
                        status=result[4],
                        preferences=json.loads(result[5] or '{}'),
                        timezone=result[6],
                        language=result[7],
                        created_at=result[8],
                        last_active=result[9],
                        premium_until=result[10]
                    )

                    if self.cache:
                        self.cache.set(cache_key, profile)

                    return profile

        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")

        return None

    def get_personalized_facts(self, user_id: int, limit: int = 5) -> List[Fact]:
        """Get personalized facts based on user profile and history."""
        try:
            profile = self.get_user_profile(user_id)
            if not profile:
                return self.get_random_facts(limit)

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get facts the user hasn't seen recently
                cursor.execute('''
                    SELECT f.id, f.day, f.month, f.type, f.fact_text, 
                           f.tags, f.difficulty, f.rating, f.view_count
                    FROM facts f
                    LEFT JOIN user_interactions ui ON f.id = ui.fact_id 
                        AND ui.user_id = ? 
                        AND ui.timestamp > datetime('now', '-7 days')
                    WHERE ui.id IS NULL
                    AND (f.difficulty = ? OR f.difficulty = 'beginner')
                    ORDER BY f.rating DESC, RANDOM()
                    LIMIT ?
                ''', (user_id, profile.preferences.get('difficulty', 'beginner'), limit))

                results = cursor.fetchall()
                facts = []

                for row in results:
                    fact = Fact(
                        id=row[0], day=row[1], month=row[2], fact_type=row[3],
                        fact_text=row[4], tags=json.loads(row[5] or '[]'),
                        difficulty=row[6], rating=row[7], view_count=row[8]
                    )
                    facts.append(fact)

                return facts

        except Exception as e:
            logger.error(f"Failed to get personalized facts: {e}")
            return self.get_random_facts(limit)

    def get_random_facts(self, limit: int = 5) -> List[Fact]:
        """Get random facts from the database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, day, month, type, fact_text, tags, difficulty, rating, view_count
                    FROM facts ORDER BY RANDOM() LIMIT ?
                ''', (limit,))

                facts = []
                for row in cursor.fetchall():
                    fact = Fact(
                        id=row[0], day=row[1], month=row[2], fact_type=row[3],
                        fact_text=row[4], tags=json.loads(row[5] or '[]'),
                        difficulty=row[6], rating=row[7], view_count=row[8]
                    )
                    facts.append(fact)

                return facts

        except Exception as e:
            logger.error(f"Failed to get random facts: {e}")
            return []

    def record_interaction(self, user_id: int, fact_id: int, interaction_type: str, metadata: Dict = None) -> bool:
        """Record user interaction with content."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_interactions 
                    (user_id, fact_id, interaction_type, metadata)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, fact_id, interaction_type, json.dumps(metadata or {})))

                # Update fact view count if it's a view
                if interaction_type == 'view':
                    cursor.execute('UPDATE facts SET view_count = view_count + 1 WHERE id = ?', (fact_id,))

                conn.commit()
                self._stats['interactions'] += 1
                return True

        except Exception as e:
            logger.error(f"Failed to record interaction: {e}")
            return False

    def get_user_recommendations(self, user_id: int, limit: int = 3) -> List[Fact]:
        """Get AI-powered recommendations based on user behavior."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get user's interaction patterns
                cursor.execute('''
                    SELECT f.type, f.tags, COUNT(*) as interaction_count
                    FROM user_interactions ui
                    JOIN facts f ON ui.fact_id = f.id
                    WHERE ui.user_id = ? AND ui.interaction_type IN ('like', 'view')
                    GROUP BY f.type, f.tags
                    ORDER BY interaction_count DESC
                    LIMIT 3
                ''', (user_id,))

                preferences = cursor.fetchall()
                if not preferences:
                    return self.get_random_facts(limit)

                # Find similar facts
                preferred_types = [p[0] for p in preferences]
                type_placeholders = ','.join(['?' for _ in preferred_types])

                cursor.execute(f'''
                    SELECT id, day, month, type, fact_text, tags, difficulty, rating, view_count
                    FROM facts
                    WHERE type IN ({type_placeholders})
                    AND id NOT IN (
                        SELECT fact_id FROM user_interactions 
                        WHERE user_id = ? AND timestamp > datetime('now', '-30 days')
                    )
                    ORDER BY rating DESC, RANDOM()
                    LIMIT ?
                ''', preferred_types + [user_id, limit])

                facts = []
                for row in cursor.fetchall():
                    fact = Fact(
                        id=row[0], day=row[1], month=row[2], fact_type=row[3],
                        fact_text=row[4], tags=json.loads(row[5] or '[]'),
                        difficulty=row[6], rating=row[7], view_count=row[8]
                    )
                    facts.append(fact)

                return facts

        except Exception as e:
            logger.error(f"Failed to get recommendations: {e}")
            return self.get_random_facts(limit)

    def get_advanced_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get advanced analytics and insights."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                analytics = {}

                # User engagement metrics
                cursor.execute('''
                    SELECT 
                        COUNT(DISTINCT user_id) as active_users,
                        COUNT(*) as total_interactions,
                        AVG(activity_count) as avg_session_activity
                    FROM user_interactions ui
                    LEFT JOIN user_sessions us ON ui.user_id = us.user_id
                    WHERE ui.timestamp > datetime('now', '-{} days')
                '''.format(days))

                engagement = cursor.fetchone()
                analytics['engagement'] = {
                    'active_users': engagement[0],
                    'total_interactions': engagement[1],
                    'avg_session_activity': round(engagement[2] or 0, 2)
                }

                # Content performance
                cursor.execute('''
                    SELECT 
                        f.type,
                        COUNT(ui.id) as interactions,
                        AVG(f.rating) as avg_rating,
                        SUM(f.view_count) as total_views
                    FROM facts f
                    LEFT JOIN user_interactions ui ON f.id = ui.fact_id
                        AND ui.timestamp > datetime('now', '-{} days')
                    GROUP BY f.type
                    ORDER BY interactions DESC
                '''.format(days))

                content_performance = []
                for row in cursor.fetchall():
                    content_performance.append({
                        'type': row[0],
                        'interactions': row[1],
                        'avg_rating': round(row[2] or 0, 2),
                        'total_views': row[3]
                    })

                analytics['content_performance'] = content_performance

                # User retention
                cursor.execute('''
                    SELECT 
                        DATE(created_at) as date,
                        COUNT(*) as new_users
                    FROM users
                    WHERE created_at > datetime('now', '-{} days')
                    GROUP BY DATE(created_at)
                    ORDER BY date
                '''.format(days))

                analytics['user_growth'] = [
                    {'date': row[0], 'new_users': row[1]}
                    for row in cursor.fetchall()
                ]

                return analytics

        except Exception as e:
            logger.error(f"Failed to get analytics: {e}")
            return {}

    def export_user_data(self, user_id: int) -> Dict[str, Any]:
        """Export all user data for GDPR compliance."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get user profile
                cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                user_data = dict(cursor.fetchone() or {})

                # Get interactions
                cursor.execute('SELECT * FROM user_interactions WHERE user_id = ?', (user_id,))
                interactions = [dict(row) for row in cursor.fetchall()]

                # Get subscriptions
                cursor.execute('SELECT * FROM subscriptions WHERE user_id = ?', (user_id,))
                subscriptions = [dict(row) for row in cursor.fetchall()]

                return {
                    'user_profile': user_data,
                    'interactions': interactions,
                    'subscriptions': subscriptions,
                    'export_timestamp': datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Failed to export user data: {e}")
            return {}

    def delete_user_data(self, user_id: int) -> bool:
        """Delete all user data for GDPR compliance."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Delete in correct order (foreign key constraints)
                cursor.execute('DELETE FROM user_interactions WHERE user_id = ?', (user_id,))
                cursor.execute('DELETE FROM user_sessions WHERE user_id = ?', (user_id,))
                cursor.execute('DELETE FROM subscriptions WHERE user_id = ?', (user_id,))
                cursor.execute('DELETE FROM analytics WHERE user_id = ?', (user_id,))
                cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))

                conn.commit()

                # Clear cache
                if self.cache:
                    self.cache.invalidate_pattern(f"user_{user_id}")

                logger.info(f"Deleted all data for user {user_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to delete user data: {e}")
            return False

    def create_automated_backup(self, retention_days: int = 30) -> bool:
        """Create automated backup with rotation."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = Path(BACKUP_DIR) / f"astrology_bot_{timestamp}.db"

            # Create backup
            with self.get_connection() as conn:
                backup_conn = sqlite3.connect(str(backup_path))
                conn.backup(backup_conn)
                backup_conn.close()

            # Clean old backups
            backup_files = list(Path(BACKUP_DIR).glob("astrology_bot_*.db"))
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            for backup_file in backup_files:
                file_date = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_date < cutoff_date:
                    backup_file.unlink()
                    logger.info(f"Deleted old backup: {backup_file}")

            logger.info(f"Created backup: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False

    def _start_maintenance_thread(self):
        """Start background maintenance thread."""
        def maintenance_worker():
            while True:
                try:
                    # Run maintenance every 24 hours
                    time.sleep(86400)  # 24 hours

                    # Create daily backup
                    self.create_automated_backup()

                    # Clean up old sessions
                    with self.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            DELETE FROM user_sessions 
                            WHERE session_start < datetime('now', '-30 days')
                        ''')
                        conn.commit()

                    # Update statistics
                    logger.info(f"Maintenance completed. Stats: {dict(self._stats)}")

                except Exception as e:
                    logger.error(f"Maintenance error: {e}")

        maintenance_thread = threading.Thread(target=maintenance_worker, daemon=True)
        maintenance_thread.start()

    def close(self):
        """Clean shutdown of database manager."""
        try:
            # Close all pooled connections
            with self._pool_lock:
                for conn in self._connection_pool:
                    conn.close()
                self._connection_pool.clear()

            # Clear cache
            if self.cache:
                self.cache.clear()

            logger.info("Database manager closed successfully")

        except Exception as e:
            logger.error(f"Error closing database manager: {e}")

    def get_stats(self) -> Dict[str, int]:
        """Get internal statistics."""
        return dict(self._stats)

    def __str__(self) -> str:
        return f"EnhancedDatabaseManager(db_path='{self.db_path}', cache_enabled={self.enable_cache})"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Usage example and testing
if __name__ == "__main__":
    # Example usage
    db_manager = DatabaseManager("test_astrology.db")

    # Create a user profile
    profile = UserProfile(
        user_id=12345,
        dob="1990-01-15",
        zodiac_sign="Capricorn",
        life_path_number=7,
        preferences={"difficulty": "intermediate", "topics": ["psychology", "science"]},
        timezone="UTC",
        language="en"
    )

    # Save profile
    success = db_manager.save_user_profile(profile)
    print(f"Profile saved: {success}")

    # Get personalized facts
    facts = db_manager.get_personalized_facts(12345, limit=3)
    print(f"Got {len(facts)} personalized facts")

    # Record interaction
    if facts:
        db_manager.record_interaction(12345, facts[0].id, "view")
        print("Recorded interaction")

    # Get analytics
    analytics = db_manager.get_advanced_analytics()
    print("Analytics:", analytics)

    # Close database
    db_manager.close()