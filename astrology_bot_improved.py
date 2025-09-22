#!/usr/bin/env python3
"""
Enhanced and Fixed Astrology Bot - Production Ready Version
Fixes critical issues and adds robust error handling
"""

import os
import sys
import logging
import random
import calendar
import asyncio
import signal
import traceback
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
import weakref
import gc

# Import our modules with better error handling
try:
    from config import Config, setup_logging
    from database import DatabaseManager
    from astrology_utils import AstrologyCalculator
    from constants import (
        Messages, Emoji, MAIN_KEYBOARD,
        SET_DOB_DAY, SET_DOB_MONTH, SET_DOB_YEAR,
        ADD_FACT_DAY, ADD_FACT_TEXT
    )
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all required files are in the same directory")
    sys.exit(1)

# Telegram imports with version checking
try:
    from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
    from telegram.ext import (
        Application, CommandHandler, MessageHandler,
        filters, ContextTypes, ConversationHandler
    )
    from telegram.error import TelegramError, NetworkError, TimedOut, BadRequest
    import telegram

    # Check telegram version
    telegram_version = tuple(map(int, telegram.__version__.split('.')))
    if telegram_version < (21, 0):
        print(f"Warning: python-telegram-bot version {telegram.__version__} may not be compatible")
        print("Recommended: python-telegram-bot==21.0.1")

except ImportError:
    print("Error: python-telegram-bot not installed!")
    print("Install with: pip install python-telegram-bot==21.0.1")
    sys.exit(1)

# Initialize logger
logger = logging.getLogger(__name__)


class EnhancedAstrologyBot:
    """Enhanced bot class with improved lifecycle management and error handling."""

    def __init__(self, config: Config):
        self.config = config
        self.db = None
        self.astro = None
        self.application = None
        self._shutdown_event = asyncio.Event()
        self._running = False
        self._startup_time = datetime.now()
        self._error_count = 0
        self._last_health_check = datetime.now()

        # Initialize components
        try:
            self.db = DatabaseManager(config.db_path)
            self.astro = AstrologyCalculator()
            logger.info("Bot components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize bot components: {e}")
            raise

    def get_main_keyboard(self):
        """Create main menu keyboard with error handling."""
        try:
            return ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)
        except Exception as e:
            logger.error(f"Failed to create keyboard: {e}")
            # Fallback simple keyboard
            return ReplyKeyboardMarkup([["Help", "Start"]], resize_keyboard=True)

    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin with logging."""
        is_admin = user_id in self.config.admin_ids
        if is_admin:
            logger.debug(f"Admin access granted for user {user_id}")
        return is_admin

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Enhanced global error handler."""
        self._error_count += 1
        error = context.error

        # Log detailed error information
        logger.error("Exception while handling an update:", exc_info=error)

        # Log update details for debugging
        if update:
            logger.error(f"Update that caused error: {update}")

        # Try to inform the user about the error
        error_message = "Sorry, something went wrong. Please try again."

        if isinstance(error, NetworkError):
            error_message = "Network error occurred. Please try again in a moment."
        elif isinstance(error, TimedOut):
            error_message = "Request timed out. Please try again."
        elif isinstance(error, BadRequest):
            error_message = "Invalid request. Please check your input."

        try:
            if update and isinstance(update, Update) and update.effective_message:
                await update.effective_message.reply_text(
                    error_message,
                    reply_markup=self.get_main_keyboard()
                )
        except Exception as reply_error:
            logger.error(f"Could not send error message: {reply_error}")

    async def post_init(self, application: Application) -> None:
        """Enhanced post initialization hook."""
        logger.info("Bot post-initialization starting...")

        # Force garbage collection
        gc.collect()

        # Set up periodic health checks
        if self.config.health_check_enabled:
            asyncio.create_task(self._periodic_health_check())

        logger.info("Bot post-initialization complete")

    async def post_shutdown(self, application: Application) -> None:
        """Enhanced post shutdown hook."""
        logger.info("Bot post-shutdown starting...")

        # Clean up resources
        if hasattr(self, 'db') and self.db:
            # Close any open connections
            logger.info("Cleaning up database connections")

        # Force garbage collection
        gc.collect()

        logger.info("Bot post-shutdown complete")

    async def _periodic_health_check(self):
        """Periodic health check task."""
        while self._running:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes

                # Update last health check
                self._last_health_check = datetime.now()

                # Log health status
                uptime = datetime.now() - self._startup_time
                logger.info(f"Health check - Uptime: {uptime}, Errors: {self._error_count}")

                # Reset error count periodically
                if self._error_count > 100:
                    logger.warning(f"High error count: {self._error_count}, resetting counter")
                    self._error_count = 0

                # Force garbage collection
                gc.collect()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    def setup_application(self) -> Application:
        """Enhanced application setup with better configuration."""
        try:
            # Create application builder
            builder = Application.builder()
            builder.token(self.config.token)

            # Configure connection settings
            builder.connection_pool_size(self.config.connection_pool_size)
            builder.read_timeout(self.config.request_timeout)
            builder.write_timeout(self.config.request_timeout)

            # Set up hooks
            builder.post_init(self.post_init)
            builder.post_shutdown(self.post_shutdown)

            application = builder.build()

            # Add global error handler
            application.add_error_handler(self.error_handler)

            # Store application reference
            self.application = application
            self._running = True

            logger.info("Application setup completed successfully")
            return application

        except Exception as e:
            logger.error(f"Failed to setup application: {e}")
            raise

    async def get_bot_stats(self) -> dict:
        """Get comprehensive bot statistics."""
        try:
            stats = {
                'uptime': str(datetime.now() - self._startup_time),
                'error_count': self._error_count,
                'last_health_check': self._last_health_check.isoformat(),
                'user_count': self.db.get_user_count() if self.db else 0,
                'fact_count': self.db.get_fact_count() if self.db else 0,
                'database_stats': self.db.get_database_stats() if self.db else {}
            }
            return stats
        except Exception as e:
            logger.error(f"Failed to get bot stats: {e}")
            return {'error': str(e)}


# Global bot instance - initialized in main()
bot: Optional[EnhancedAstrologyBot] = None


# Enhanced command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced start command handler."""
    try:
        if not update.effective_user or not update.message:
            logger.warning("Start command called without user or message")
            return

        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        first_name = update.effective_user.first_name or "User"

        logger.info(f"User {user_id} (@{username}) started the bot")

        # Personalized welcome message
        welcome_msg = Messages.WELCOME.format(name=first_name)

        try:
            await update.message.reply_text(
                welcome_msg,
                reply_markup=bot.get_main_keyboard(),
                parse_mode='Markdown'
            )
        except (TelegramError, Exception) as e:
            logger.warning(f"Markdown failed in start, using fallback: {e}")
            # Fallback without markdown
            fallback_msg = f"Welcome {first_name}! I'm your astrology bot. Use the menu below to get started!"
            await update.message.reply_text(
                fallback_msg,
                reply_markup=bot.get_main_keyboard()
            )

    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await safe_reply(update, "Welcome! Something went wrong, but I'm here to help!")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced help command handler."""
    try:
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id
        logger.info(f"User {user_id} requested help")

        try:
            await update.message.reply_text(Messages.HELP_TEXT, parse_mode='Markdown')
        except (TelegramError, Exception) as e:
            logger.warning(f"Markdown failed in help, using fallback: {e}")
            # Comprehensive fallback help
            fallback_help = """
🌟 ASTROLOGY BOT HELP 🌟

Available Features:
• Set DOB - Configure your birth date
• Today's Reading - Daily horoscope & lucky number
• Numerology - Life path number analysis
• Date Facts - Interesting facts about dates
• Compatibility - Zodiac compatibility check
• Random Fact - Surprise insights
• Support - Help support the bot

Commands you can type:
/setdob - Set your birth date
/today - Get today's reading
/numerology - Your numerology profile
/fact <number> - Facts for specific day
/compatibility - Check compatibility
/randomfact - Get a random fact
/help - Show this help

Use the menu buttons below for easy access!
            """
            await update.message.reply_text(fallback_help)

    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await safe_reply(update, "Help is available! Use the menu buttons below.")


# Enhanced DOB conversation handlers
async def start_set_dob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced start DOB conversation."""
    try:
        if not update.effective_user or not update.message:
            return ConversationHandler.END

        user_id = update.effective_user.id
        logger.info(f"User {user_id} starting DOB setup")

        # Clear any existing DOB data
        context.user_data.clear()

        await update.message.reply_text(
            Messages.DOB_SETUP_START,
            reply_markup=ReplyKeyboardRemove()
        )
        return SET_DOB_DAY

    except Exception as e:
        logger.error(f"Error starting DOB setup: {e}")
        await safe_reply(update, "Let's set your birth date! Please enter the day (1-31):")
        return SET_DOB_DAY


async def set_dob_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced day input handler with comprehensive validation."""
    try:
        if not update.effective_user or not update.message:
            return ConversationHandler.END

        user_id = update.effective_user.id
        day_text = update.message.text.strip()

        logger.debug(f"User {user_id} entered day: '{day_text}'")

        # Enhanced validation
        if not day_text.isdigit():
            await update.message.reply_text("Please enter only numbers for the day (1-31):")
            return SET_DOB_DAY

        if len(day_text) > 2:
            await update.message.reply_text("Please enter a valid day between 1 and 31:")
            return SET_DOB_DAY

        day = int(day_text)
        if not (1 <= day <= 31):
            await update.message.reply_text(Messages.DOB_INVALID_DAY)
            return SET_DOB_DAY

        context.user_data['dob_day'] = day

        confirmation_msg = f"Day: {day} ✅\n\nNow enter the MONTH (1-12 or name like 'January'):"
        await update.message.reply_text(confirmation_msg)
        return SET_DOB_MONTH

    except ValueError:
        await update.message.reply_text(Messages.DOB_INVALID_DAY)
        return SET_DOB_DAY
    except Exception as e:
        logger.error(f"Error in set_dob_day: {e}")
        await safe_reply(update, "Please enter a valid day number (1-31):")
        return SET_DOB_DAY


async def set_dob_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced month input handler with better parsing."""
    try:
        if not update.effective_user or not update.message:
            return ConversationHandler.END

        user_id = update.effective_user.id
        month_text = update.message.text.strip().lower()

        logger.debug(f"User {user_id} entered month: '{month_text}'")

        month = None

        # Try parsing as number first
        if month_text.isdigit():
            month_num = int(month_text)
            if 1 <= month_num <= 12:
                month = month_num

        # Extended month name parsing
        if month is None:
            month_names = {
                'january': 1, 'jan': 1, 'february': 2, 'feb': 2,
                'march': 3, 'mar': 3, 'april': 4, 'apr': 4,
                'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
                'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9,
                'october': 10, 'oct': 10, 'november': 11, 'nov': 11,
                'december': 12, 'dec': 12
            }
            month = month_names.get(month_text)

        if month is None:
            error_msg = "Please enter a valid month:\n• Number: 1-12\n• Name: January, February, etc.\n• Short: Jan, Feb, etc."
            await update.message.reply_text(error_msg)
            return SET_DOB_MONTH

        context.user_data['dob_month'] = month
        month_name = calendar.month_name[month]

        progress_msg = f"Day: {context.user_data['dob_day']}\nMonth: {month_name} ✅\n\nFinally, enter your birth YEAR (e.g., 1990):"
        await update.message.reply_text(progress_msg)
        return SET_DOB_YEAR

    except Exception as e:
        logger.error(f"Error in set_dob_month: {e}")
        await safe_reply(update, Messages.DOB_INVALID_MONTH)
        return SET_DOB_MONTH


async def set_dob_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced year input handler with comprehensive validation."""
    try:
        if not update.effective_user or not update.message:
            return ConversationHandler.END

        user_id = update.effective_user.id
        year_text = update.message.text.strip()

        logger.debug(f"User {user_id} entered year: '{year_text}'")

        # Enhanced year validation
        if not year_text.isdigit():
            await update.message.reply_text("Please enter only numbers for the year (e.g., 1990):")
            return SET_DOB_YEAR

        if len(year_text) != 4:
            await update.message.reply_text("Please enter a valid 4-digit year (e.g., 1990):")
            return SET_DOB_YEAR

        year = int(year_text)
        day = context.user_data['dob_day']
        month = context.user_data['dob_month']

        # Validate and create birth date using astrology utils
        birth_date = bot.astro.validate_birth_date(day, month, year)

        # Calculate astrology data
        zodiac = bot.astro.get_zodiac_sign(birth_date)
        life_path = bot.astro.calculate_life_path(birth_date)

        # Save to database
        if bot.db.save_user_dob(user_id, birth_date, zodiac, life_path):
            logger.info(f"User {user_id} DOB saved successfully: {birth_date}")

            success_message = Messages.DOB_SUCCESS.format(
                date=birth_date.strftime('%B %d, %Y'),
                zodiac=zodiac,
                life_path=life_path
            )

            try:
                await update.message.reply_text(
                    success_message,
                    parse_mode='Markdown',
                    reply_markup=bot.get_main_keyboard()
                )
            except (TelegramError, Exception):
                # Fallback without markdown
                fallback_msg = (
                    f"🎉 Birth date saved successfully!\n\n"
                    f"📅 Date: {birth_date.strftime('%B %d, %Y')}\n"
                    f"⭐ Zodiac Sign: {zodiac}\n"
                    f"🔢 Life Path Number: {life_path}\n\n"
                    f"You can now use all personalized features!"
                )
                await update.message.reply_text(
                    fallback_msg,
                    reply_markup=bot.get_main_keyboard()
                )
        else:
            await update.message.reply_text(
                "Sorry, couldn't save your birth date. Please try again later.",
                reply_markup=bot.get_main_keyboard()
            )

        # Clear conversation data
        context.user_data.clear()
        return ConversationHandler.END

    except ValueError as e:
        await update.message.reply_text(f"Error: {e}\nPlease enter the year again:")
        return SET_DOB_YEAR
    except Exception as e:
        logger.error(f"Error in set_dob_year: {e}")
        await safe_reply(update, "Please enter a valid 4-digit year:")
        return SET_DOB_YEAR


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced conversation cancellation."""
    try:
        if not update.effective_user or not update.message:
            return ConversationHandler.END

        user_id = update.effective_user.id
        logger.info(f"User {user_id} cancelled conversation")

        # Clear all conversation data
        context.user_data.clear()

        await update.message.reply_text(
            Messages.OPERATION_CANCELLED,
            reply_markup=bot.get_main_keyboard()
        )
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error cancelling conversation: {e}")
        return ConversationHandler.END


# Enhanced feature handlers
async def today_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced today's reading with comprehensive error handling."""
    try:
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id
        logger.info(f"User {user_id} requested today's reading")

        user_data = bot.db.get_user_data(user_id)
        if not user_data:
            await update.message.reply_text(
                Messages.DOB_REQUIRED,
                reply_markup=bot.get_main_keyboard()
            )
            return

        dob_str, zodiac, life_path = user_data

        # Get personalized content
        horoscope = bot.astro.get_horoscope(zodiac)
        lucky_number = bot.astro.generate_lucky_number(life_path, date.today())

        # Get random fact
        fact_result = bot.db.get_random_fact()
        if fact_result:
            fact, _ = fact_result
        else:
            fact = "Your mind is capable of incredible things when you believe in yourself."

        reading = Messages.TODAYS_READING.format(
            zodiac=zodiac,
            horoscope=horoscope,
            lucky_number=lucky_number,
            fact=fact
        )

        try:
            await update.message.reply_text(reading, parse_mode='Markdown')
        except (TelegramError, Exception):
            # Fallback without markdown
            fallback_reading = (
                f"⭐ Today's Reading for {zodiac} ⭐\n\n"
                f"🔮 Horoscope:\n{horoscope}\n\n"
                f"🎲 Lucky Number: {lucky_number}\n\n"
                f"🧠 Daily Insight:\n{fact}"
            )
            await update.message.reply_text(fallback_reading)

    except Exception as e:
        logger.error(f"Error in today_reading: {e}")
        await safe_reply(update, "Sorry, couldn't generate your reading right now. Please try again.")


async def numerology_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced numerology information handler."""
    try:
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id
        logger.info(f"User {user_id} requested numerology info")

        user_data = bot.db.get_user_data(user_id)
        if not user_data:
            await update.message.reply_text(
                Messages.DOB_REQUIRED,
                reply_markup=bot.get_main_keyboard()
            )
            return

        dob_str, zodiac, life_path = user_data
        birth_date = datetime.fromisoformat(dob_str).date()

        # Get detailed numerology information
        calculation = bot.astro.get_life_path_calculation_steps(birth_date)
        meaning = bot.astro.get_life_path_meaning(life_path)

        numerology_text = Messages.NUMEROLOGY_INFO.format(
            life_path=life_path,
            calculation=calculation,
            meaning=meaning
        )

        try:
            await update.message.reply_text(numerology_text, parse_mode='Markdown')
        except (TelegramError, Exception):
            # Fallback without markdown
            fallback_text = (
                f"🔢 Your Numerology Profile 🔢\n\n"
                f"Life Path Number: {life_path}\n\n"
                f"Calculation Steps:\n{calculation}\n\n"
                f"Meaning:\n{meaning}"
            )
            await update.message.reply_text(fallback_text)

    except Exception as e:
        logger.error(f"Error in numerology_info: {e}")
        await safe_reply(update, "Sorry, couldn't retrieve your numerology info. Please try again.")


# Utility functions
async def safe_reply(update: Update, message: str, keyboard=None):
    """Safe reply function with error handling."""
    try:
        if update and update.effective_message:
            reply_markup = keyboard or bot.get_main_keyboard()
            await update.effective_message.reply_text(message, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Failed to send safe reply: {e}")


# Enhanced text message handler
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced text message handler with better pattern matching."""
    try:
        if not update.effective_user or not update.message:
            return

        text = update.message.text
        user_id = update.effective_user.id

        logger.debug(f"User {user_id} sent text: '{text}'")

        # Enhanced pattern matching
        text_lower = text.lower().strip()

        # DOB related patterns
        if any(phrase in text_lower for phrase in ["set dob", "birth", "birthday", "date of birth"]):
            return await start_set_dob(update, context)

        # Reading patterns
        elif any(phrase in text_lower for phrase in ["today", "reading", "horoscope"]):
            return await today_reading(update, context)

        # Numerology patterns
        elif "numerology" in text_lower or "life path" in text_lower:
            return await numerology_info(update, context)

        # Fact patterns
        elif any(phrase in text_lower for phrase in ["fact", "random fact", "interesting"]):
            return await random_fact(update, context)

        # Support patterns
        elif "support" in text_lower or "donate" in text_lower:
            return await support_command(update, context)

        # Help patterns
        elif "help" in text_lower or "commands" in text_lower:
            return await help_command(update, context)

        # Default response with helpful suggestions
        default_msg = (
            "I didn't understand that. Here's what I can help with:\n\n"
            "• Set DOB - Configure your birth date\n"
            "• Today's Reading - Daily horoscope\n"
            "• Numerology - Life path analysis\n"
            "• Random Fact - Interesting insights\n"
            "• Help - Show all commands\n\n"
            "Use the menu buttons below!"
        )

        await update.message.reply_text(
            default_msg,
            reply_markup=bot.get_main_keyboard()
        )

    except Exception as e:
        logger.error(f"Error handling text message: {e}")
        await safe_reply(update, "Sorry, something went wrong. Please try the menu buttons!")


# Additional handlers (continuing from previous handlers...)
async def random_fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced random fact handler."""
    try:
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id
        logger.info(f"User {user_id} requested random fact")

        fact_result = bot.db.get_random_fact()

        if fact_result:
            fact_text, fact_type = fact_result
            emoji_map = {
                "psychology": "🧠",
                "science": "🔬",
                "numerology": "🔢",
                "general": "💡"
            }
            emoji = emoji_map.get(fact_type, "🎲")

            try:
                await update.message.reply_text(
                    f"🎲 **Random Fact** 🎲\n\n{emoji} {fact_text}",
                    parse_mode='Markdown'
                )
            except (TelegramError, Exception):
                await update.message.reply_text(f"🎲 Random Fact\n\n{emoji} {fact_text}")
        else:
            await update.message.reply_text(
                "🎲 The universe is full of infinite possibilities and mysteries!"
            )

    except Exception as e:
        logger.error(f"Error in random_fact: {e}")
        await safe_reply(update, "Here's a fact: You're awesome! ✨")


async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced support information handler."""
    try:
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id
        logger.info(f"User {user_id} requested support info")

        support_text = Messages.SUPPORT_INFO.format(
            upi_id=bot.config.upi_id or "your-upi-id@paytm",
            support_message=bot.config.support_message
        )

        try:
            await update.message.reply_text(support_text, parse_mode='Markdown')
        except (TelegramError, Exception):
            # Fallback without markdown
            fallback_text = (
                f"💰 Support the Bot 💰\n\n"
                f"This bot is developed with love! ❤️\n\n"
                f"Ways to support:\n"
                f"• Share with friends\n"
                f"• Provide feedback\n"
                f"• Consider a donation\n\n"
                f"UPI ID: {bot.config.upi_id or 'your-upi-id@paytm'}\n\n"
                f"{bot.config.support_message}\n\n"
                f"Thank you! ⭐"
            )
            await update.message.reply_text(fallback_text)

    except Exception as e:
        logger.error(f"Error in support_command: {e}")
        await safe_reply(update, "Thank you for considering supporting this bot! 💖")


# Enhanced admin handlers
async def admin_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin health check command."""
    try:
        if not update.effective_user or not bot.is_admin(update.effective_user.id):
            await update.message.reply_text(Messages.ADMIN_ONLY)
            return

        stats = await bot.get_bot_stats()

        health_msg = Messages.HEALTH_CHECK_HEALTHY.format(
            user_count=stats.get('user_count', 0),
            fact_count=stats.get('fact_count', 0),
            uptime=stats.get('uptime', 'Unknown')
        )

        await update.message.reply_text(health_msg, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in admin_health: {e}")
        error_msg = Messages.HEALTH_CHECK_ERROR.format(error=str(e))
        await safe_reply(update, error_msg)


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        if bot and bot._running:
            bot._running = False
            bot._shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def compatibility_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced compatibility check handler."""
    try:
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id
        logger.info(f"User {user_id} requested compatibility check")

        user_data = bot.db.get_user_data(user_id)
        if not user_data:
            await update.message.reply_text(
                Messages.DOB_REQUIRED,
                reply_markup=bot.get_main_keyboard()
            )
            return

        dob_str, user_zodiac, user_life_path = user_data

        # Store user data in context for the next input
        context.user_data['compatibility_check'] = {
            'user_zodiac': user_zodiac,
            'user_life_path': user_life_path
        }

        check_msg = Messages.COMPATIBILITY_CHECK.format(
            user_zodiac=user_zodiac,
            user_life_path=user_life_path
        )

        await update.message.reply_text(
            check_msg,
            reply_markup=ReplyKeyboardRemove()
        )

    except Exception as e:
        logger.error(f"Error in compatibility_check: {e}")
        await safe_reply(update, "Sorry, couldn't start compatibility check. Please try again.")


async def process_compatibility_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process compatibility date input."""
    try:
        if not update.effective_user or not update.message:
            return

        # Check if we're in compatibility mode
        if 'compatibility_check' not in context.user_data:
            return

        date_text = update.message.text.strip()
        user_id = update.effective_user.id

        logger.debug(f"User {user_id} entered compatibility date: '{date_text}'")

        try:
            # Parse the date
            other_date = bot.astro.parse_date_input(date_text)

            # Calculate other person's astro data
            other_zodiac = bot.astro.get_zodiac_sign(other_date)
            other_life_path = bot.astro.calculate_life_path(other_date)

            # Get user data from context
            user_data = context.user_data['compatibility_check']
            user_zodiac = user_data['user_zodiac']
            user_life_path = user_data['user_life_path']

            # Calculate compatibility
            zodiac_score, numerology_score, overall_score, compatibility_level = \
                bot.astro.calculate_compatibility(
                    user_zodiac, user_life_path,
                    other_zodiac, other_life_path
                )

            # Get elements
            user_element = bot.astro.get_element(user_zodiac)
            other_element = bot.astro.get_element(other_zodiac)

            # Create result message
            result = Messages.COMPATIBILITY_RESULT.format(
                user_zodiac=user_zodiac,
                user_element=user_element,
                user_life_path=user_life_path,
                other_zodiac=other_zodiac,
                other_element=other_element,
                other_life_path=other_life_path,
                zodiac_score=zodiac_score,
                numerology_score=numerology_score,
                overall_score=overall_score,
                compatibility_level=compatibility_level
            )

            try:
                await update.message.reply_text(
                    result,
                    parse_mode='Markdown',
                    reply_markup=bot.get_main_keyboard()
                )
            except (TelegramError, Exception):
                # Fallback without markdown
                fallback_result = (
                    f"💕 Compatibility Analysis 💕\n\n"
                    f"You: {user_zodiac} ({user_element}) - Life Path {user_life_path}\n"
                    f"Partner: {other_zodiac} ({other_element}) - Life Path {other_life_path}\n\n"
                    f"Scores:\n"
                    f"⭐ Zodiac: {zodiac_score}%\n"
                    f"🔢 Numerology: {numerology_score}%\n\n"
                    f"Overall: {overall_score}% - {compatibility_level}"
                )
                await update.message.reply_text(
                    fallback_result,
                    reply_markup=bot.get_main_keyboard()
                )

            # Clear compatibility data
            context.user_data.pop('compatibility_check', None)

        except ValueError as e:
            await update.message.reply_text(
                f"Invalid date format: {e}\n\nPlease use DD-MM-YYYY format (e.g., 15-06-1990):"
            )

    except Exception as e:
        logger.error(f"Error processing compatibility date: {e}")
        await safe_reply(update, "Sorry, couldn't process the date. Please try again with DD-MM-YYYY format.")
        context.user_data.pop('compatibility_check', None)


async def date_facts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced date facts handler."""
    try:
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id
        text = update.message.text.strip()

        logger.info(f"User {user_id} requested date facts: '{text}'")

        # Handle different input types
        if text.lower() in ['my birthday', 'birthday', 'my birth']:
            # Get user's birthday facts
            user_data = bot.db.get_user_data(user_id)
            if not user_data:
                await update.message.reply_text(
                    Messages.DOB_REQUIRED,
                    reply_markup=bot.get_main_keyboard()
                )
                return

            dob_str = user_data[0]
            birth_date = datetime.fromisoformat(dob_str).date()
            day = birth_date.day

        elif text.lower() in ['today', 'today facts']:
            # Today's facts
            day = date.today().day

        elif text.isdigit():
            # Specific day number
            day = int(text)
            if not (1 <= day <= 31):
                await update.message.reply_text("Please enter a day between 1 and 31:")
                return
        else:
            # Show prompt
            await update.message.reply_text(Messages.DATE_FACTS_PROMPT)
            return

        # Get fact for the day
        fact_result = bot.db.get_fact_by_day(day)

        if fact_result:
            fact_text, fact_type = fact_result
            emoji_map = {
                "psychology": "🧠",
                "science": "🔬",
                "numerology": "🔢",
                "general": "💡"
            }
            emoji = emoji_map.get(fact_type, "📅")

            fact_msg = f"📅 **Fact for Day {day}** 📅\n\n{emoji} {fact_text}"

            try:
                await update.message.reply_text(fact_msg, parse_mode='Markdown')
            except (TelegramError, Exception):
                await update.message.reply_text(f"📅 Fact for Day {day}\n\n{emoji} {fact_text}")
        else:
            await update.message.reply_text(f"📅 Day {day} is special in its own unique way!")

    except Exception as e:
        logger.error(f"Error in date_facts: {e}")
        await safe_reply(update, "Sorry, couldn't get facts for that date. Please try again.")


async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced admin broadcast command."""
    try:
        if not update.effective_user or not bot.is_admin(update.effective_user.id):
            await update.message.reply_text(Messages.ADMIN_ONLY)
            return

        # Get message text
        message_text = ' '.join(context.args) if context.args else ''

        if not message_text:
            await update.message.reply_text(Messages.BROADCAST_USAGE)
            return

        # Get all users
        user_ids = bot.db.get_all_user_ids()

        if not user_ids:
            await update.message.reply_text("No users found for broadcast.")
            return

        # Limit broadcast size
        max_users = bot.config.max_broadcast_users
        if len(user_ids) > max_users:
            user_ids = user_ids[:max_users]
            logger.warning(f"Broadcast limited to {max_users} users")

        # Send broadcast
        sent_count = 0
        failed_count = 0

        status_msg = await update.message.reply_text(
            f"📢 Starting broadcast to {len(user_ids)} users..."
        )

        for i, user_id in enumerate(user_ids):
            try:
                await context.bot.send_message(user_id, message_text)
                sent_count += 1

                # Rate limiting
                if i % 10 == 0:
                    await asyncio.sleep(1)

                # Update progress every 50 users
                if i % 50 == 0:
                    progress = f"📢 Progress: {i + 1}/{len(user_ids)} users..."
                    await status_msg.edit_text(progress)

            except Exception as e:
                logger.warning(f"Broadcast failed for user {user_id}: {e}")
                failed_count += 1

        # Final status
        final_msg = Messages.BROADCAST_COMPLETE.format(
            sent=sent_count,
            failed=failed_count
        )
        await status_msg.edit_text(final_msg, parse_mode='Markdown')

        logger.info(f"Broadcast completed: {sent_count} sent, {failed_count} failed")

    except Exception as e:
        logger.error(f"Error in admin_broadcast: {e}")
        await safe_reply(update, f"Broadcast failed: {e}")


async def main():
    """Enhanced main function with comprehensive setup and error handling."""
    global bot

    startup_start = datetime.now()

    try:
        logger.info("=" * 60)
        logger.info("🌟 STARTING ENHANCED ASTROLOGY BOT 🌟")
        logger.info("=" * 60)

        # Load and validate configuration
        logger.info("Loading configuration...")
        config = Config.from_env()
        config.validate()
        logger.info("✅ Configuration loaded successfully")

        # Setup logging
        setup_logging(config)
        logger.info(f"✅ Logging configured (level: {config.log_level})")

        # Initialize bot
        logger.info("Initializing bot components...")
        bot = EnhancedAstrologyBot(config)
        logger.info("✅ Bot components initialized")

        # Create application
        logger.info("Setting up Telegram application...")
        application = bot.setup_application()
        logger.info("✅ Telegram application ready")

        # Setup conversation handlers
        logger.info("Configuring conversation handlers...")

        # DOB conversation handler with enhanced states
        set_dob_conv = ConversationHandler(
            entry_points=[
                CommandHandler('setdob', start_set_dob),
                MessageHandler(
                    filters.TEXT & filters.Regex(r'(?i).*(set|birth|dob).*'),
                    start_set_dob
                )
            ],
            states={
                SET_DOB_DAY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, set_dob_day)
                ],
                SET_DOB_MONTH: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, set_dob_month)
                ],
                SET_DOB_YEAR: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, set_dob_year)
                ],
            },
            fallbacks=[
                CommandHandler('cancel', cancel_conversation),
                MessageHandler(
                    filters.Regex(r'(?i)(cancel|stop|quit|back)'),
                    cancel_conversation
                )
            ],
            conversation_timeout=config.conversation_timeout,
        )

        # Add all handlers in order of precedence
        logger.info("Registering command handlers...")

        # Core commands
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('help', help_command))

        # Conversation handlers
        application.add_handler(set_dob_conv)

        # Feature commands
        application.add_handler(CommandHandler('today', today_reading))
        application.add_handler(CommandHandler('numerology', numerology_info))
        application.add_handler(CommandHandler('randomfact', random_fact))
        application.add_handler(CommandHandler('support', support_command))
        application.add_handler(CommandHandler('compatibility', compatibility_check))
        application.add_handler(CommandHandler('fact', date_facts))

        # Admin commands
        if config.admin_commands_enabled:
            application.add_handler(CommandHandler('health', admin_health))
            application.add_handler(CommandHandler('broadcast', admin_broadcast))

        # Special message handlers (before general text handler)
        application.add_handler(
            MessageHandler(
                filters.TEXT & filters.Regex(r'^\d{2}-\d{2}-\d{4}'),
        process_compatibility_date
        )
        )

        # General text message handler (must be last)
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
        )

        logger.info("✅ All handlers registered successfully")

        # Setup signal handlers
        setup_signal_handlers()
        logger.info("✅ Signal handlers configured")

        # Calculate startup time
        startup_time = datetime.now() - startup_start
        logger.info(f"🚀 Bot startup completed in {startup_time.total_seconds():.2f}s")
        logger.info(f"👥 Admin IDs: {config.admin_ids}")
        logger.info("📱 Bot is ready! Press Ctrl+C to stop.")

        # Start the application
        await application.initialize()
        await application.start()
        await application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

        # Main event loop
        try:
            while bot._running:
                await asyncio.sleep(1)

                # Check shutdown event
                if bot._shutdown_event.is_set():
                    break

        except KeyboardInterrupt:
            logger.info("🛑 Shutdown requested by user")
        finally:
            logger.info("🔄 Initiating graceful shutdown...")
            bot._running = False

            # Stop the application
            await application.updater.stop()
            await application.stop()
            await application.shutdown()

    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        print(f"Configuration error: {e}")
        print("Please check your .env file and fix the configuration.")
        sys.exit(1)

    except Exception as e:
        logger.error(f"💥 Fatal error: {e}", exc_info=True)
        print(f"Fatal error occurred: {e}")
        print("Check the logs for more details.")
        sys.exit(1)

    finally:
        # Final cleanup
        if bot:
            bot._running = False

        # Force garbage collection
        gc.collect()

        shutdown_time = datetime.now() - startup_start
        logger.info(f"🏁 Bot shutdown complete (total runtime: {shutdown_time})")


def run_bot():
    """Entry point with proper event loop handling and error recovery."""
    try:
        # Set event loop policy for better Windows compatibility
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        # Run the main coroutine
        asyncio.run(main())

    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
        print("\n✅ Bot stopped gracefully")

    except Exception as e:
        logger.error(f"💥 Fatal error in event loop: {e}", exc_info=True)
        print(f"Fatal error: {e}")
        print("Check logs/astrology_bot.log for details")

        # Attempt recovery
        print("\n🔄 Attempting recovery in 5 seconds...")
        import time
        time.sleep(5)

        # Try one more time
        try:
            logger.info("🔄 Attempting bot recovery...")
            asyncio.run(main())
        except Exception as recovery_error:
            logger.error(f"💀 Recovery failed: {recovery_error}")
            print("❌ Recovery failed. Please restart manually.")
            sys.exit(1)


if __name__ == '__main__':
    run_bot()