#!/usr/bin/env python3
"""
Enhanced Astrology Bot - Production Ready Version with Improved Architecture
Comprehensive error handling, logging, and lifecycle management
"""

import os
import sys
import logging
import asyncio
import signal
import gc
from datetime import datetime, date
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

# Import modules with error handling
try:
    from config import Config, setup_logging
    from database import DatabaseManager
    from astrology_utils import AstrologyCalculator
    from constants import (
        Messages, Emoji, MAIN_KEYBOARD,
        SET_DOB_DAY, SET_DOB_MONTH, SET_DOB_YEAR
    )
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Ensure all required files are in the same directory")
    sys.exit(1)

# Telegram imports
try:
    from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
    from telegram.ext import (
        Application, CommandHandler, MessageHandler,
        filters, ContextTypes, ConversationHandler
    )
    from telegram.error import TelegramError, NetworkError, TimedOut, BadRequest
except ImportError:
    print("Error: python-telegram-bot not installed!")
    print("Install with: pip install python-telegram-bot==21.0.1")
    sys.exit(1)

logger = logging.getLogger(__name__)


class BotState(Enum):
    """Bot operational states."""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class BotMetrics:
    """Container for bot metrics."""
    startup_time: datetime
    total_commands: int = 0
    total_errors: int = 0
    active_conversations: int = 0

    def increment_commands(self):
        """Increment command counter."""
        self.total_commands += 1

    def increment_errors(self):
        """Increment error counter."""
        self.total_errors += 1

    def get_uptime(self) -> float:
        """Get uptime in seconds."""
        return (datetime.now() - self.startup_time).total_seconds()


class AstrologyBot:
    """
    Main bot class with improved lifecycle management and error handling.

    Features:
    - Comprehensive error handling
    - Metrics tracking
    - Graceful shutdown
    - Admin functionality
    """

    def __init__(self, config: Config):
        """
        Initialize bot with configuration.

        Args:
            config: Bot configuration object
        """
        self.config = config
        self.db = DatabaseManager(config.db_path)
        self.astro = AstrologyCalculator()
        self.application = None
        self.state = BotState.IDLE
        self.metrics = BotMetrics(startup_time=datetime.now())
        self._shutdown_event = asyncio.Event()

        logger.info("Bot components initialized")

    def get_main_keyboard(self) -> ReplyKeyboardMarkup:
        """
        Create main menu keyboard with error handling.

        Returns:
            ReplyKeyboardMarkup: Main keyboard layout
        """
        try:
            return ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)
        except Exception as e:
            logger.error(f"Keyboard creation failed: {e}")
            # Fallback minimal keyboard
            return ReplyKeyboardMarkup([["Help"]], resize_keyboard=True)

    def is_admin(self, user_id: int) -> bool:
        """
        Check if user is admin.

        Args:
            user_id: Telegram user ID

        Returns:
            bool: True if user is admin
        """
        return user_id in self.config.admin_ids

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Global error handler with comprehensive logging and user feedback.

        Args:
            update: Telegram update object
            context: Handler context
        """
        self.metrics.increment_errors()
        logger.error("Exception while handling update:", exc_info=context.error)

        # Determine error message based on error type
        error_message = "Sorry, something went wrong. Please try again."

        if isinstance(context.error, NetworkError):
            error_message = "Network error. Please check your connection and try again."
        elif isinstance(context.error, TimedOut):
            error_message = "Request timed out. Please try again."
        elif isinstance(context.error, BadRequest):
            error_message = "Invalid request. Please check your input."

        # Try to send error message to user
        try:
            if update and isinstance(update, Update) and update.effective_message:
                await update.effective_message.reply_text(
                    f"❌ {error_message}",
                    reply_markup=self.get_main_keyboard()
                )
        except Exception as e:
            logger.error(f"Could not send error message to user: {e}")

    def setup_application(self) -> Application:
        """
        Setup Telegram application with proper configuration.

        Returns:
            Application: Configured Telegram application

        Raises:
            Exception: If setup fails
        """
        try:
            self.state = BotState.STARTING

            builder = Application.builder()
            builder.token(self.config.token)
            builder.connection_pool_size(self.config.connection_pool_size)
            builder.read_timeout(self.config.request_timeout)
            builder.write_timeout(self.config.request_timeout)
            builder.connect_timeout(self.config.request_timeout)

            application = builder.build()
            application.add_error_handler(self.error_handler)

            self.application = application
            self.state = BotState.RUNNING

            logger.info("Application setup completed successfully")
            return application

        except Exception as e:
            self.state = BotState.ERROR
            logger.error(f"Application setup failed: {e}")
            raise


# Global bot instance
bot: Optional[AstrologyBot] = None


async def safe_reply(update: Update, message: str, keyboard=None) -> bool:
    """
    Safe reply with comprehensive error handling.

    Args:
        update: Telegram update object
        message: Message to send
        keyboard: Optional keyboard markup

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if update and update.effective_message:
            reply_markup = keyboard if keyboard is not None else bot.get_main_keyboard()
            await update.effective_message.reply_text(message, reply_markup=reply_markup)
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to send reply: {e}")
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start command with welcoming message.

    Args:
        update: Telegram update object
        context: Handler context
    """
    try:
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id
        first_name = update.effective_user.first_name or "User"
        bot.metrics.increment_commands()

        logger.info(f"User {user_id} ({first_name}) started the bot")

        welcome_msg = f"🌟 Welcome {first_name}! I'm your astrology companion.\n\n"
        welcome_msg += "✨ **What I can help you with:**\n"
        welcome_msg += "• Daily horoscopes and personalized readings\n"
        welcome_msg += "• Numerology and life path analysis\n"
        welcome_msg += "• Zodiac compatibility checks\n"
        welcome_msg += "• Lucky numbers and cosmic insights\n\n"
        welcome_msg += "👉 Use the menu below to get started!"

        await update.message.reply_text(
            welcome_msg,
            reply_markup=bot.get_main_keyboard()
        )

    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await safe_reply(update, "Welcome! Use the menu to explore features.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /help command with detailed feature information.

    Args:
        update: Telegram update object
        context: Handler context
    """
    try:
        if not update.effective_user or not update.message:
            return

        bot.metrics.increment_commands()

        help_text = "📚 **Available Features**\n\n"
        help_text += "🎂 **Set DOB** - Configure your birth date for personalized readings\n"
        help_text += "🔮 **Today's Reading** - Get your daily horoscope\n"
        help_text += "🔢 **Numerology** - Discover your life path number\n"
        help_text += "💕 **Compatibility** - Check relationship compatibility\n"
        help_text += "✨ **Zodiac Secret** - Random cosmic insights\n\n"
        help_text += "📋 **Commands:**\n"
        help_text += "`/setdob` - Set your birth date\n"
        help_text += "`/today` - Get daily reading\n"
        help_text += "`/numerology` - View numerology info\n"
        help_text += "`/compatibility` - Check compatibility\n"
        help_text += "`/help` - Show this help message"

        await update.message.reply_text(
            help_text,
            reply_markup=bot.get_main_keyboard(),
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await safe_reply(update, "Help is available via the menu buttons.")


async def start_set_dob(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Start date of birth conversation flow.

    Args:
        update: Telegram update object
        context: Handler context

    Returns:
        int: Next conversation state
    """
    try:
        if not update.effective_user or not update.message:
            return ConversationHandler.END

        bot.metrics.increment_commands()
        context.user_data.clear()

        msg = "🎂 **Let's set your birth date!**\n\n"
        msg += "Please enter the **DAY** of your birth (1-31):"

        await update.message.reply_text(
            msg,
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )
        return SET_DOB_DAY

    except Exception as e:
        logger.error(f"Error starting DOB conversation: {e}")
        await safe_reply(update, "Please enter the day (1-31):")
        return SET_DOB_DAY


async def set_dob_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle day input in DOB conversation.

    Args:
        update: Telegram update object
        context: Handler context

    Returns:
        int: Next conversation state
    """
    try:
        if not update.effective_user or not update.message:
            return ConversationHandler.END

        day_text = update.message.text.strip()

        # Validate input
        if not day_text.isdigit() or len(day_text) > 2:
            await update.message.reply_text(
                "❌ Please enter a valid day number (1-31):"
            )
            return SET_DOB_DAY

        day = int(day_text)
        if not (1 <= day <= 31):
            await update.message.reply_text(
                "❌ Day must be between 1 and 31.\n\nPlease try again:"
            )
            return SET_DOB_DAY

        context.user_data['dob_day'] = day

        msg = f"✅ Day: **{day}**\n\n"
        msg += "Now enter the **MONTH** (1-12 or name like 'January'):"

        await update.message.reply_text(msg, parse_mode='Markdown')
        return SET_DOB_MONTH

    except Exception as e:
        logger.error(f"Error in set_dob_day: {e}")
        await safe_reply(update, "Please enter a valid day (1-31):")
        return SET_DOB_DAY


async def set_dob_month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle month input in DOB conversation.

    Args:
        update: Telegram update object
        context: Handler context

    Returns:
        int: Next conversation state
    """
    try:
        if not update.effective_user or not update.message:
            return ConversationHandler.END

        month_text = update.message.text.strip().lower()
        month = None

        # Try numeric input
        if month_text.isdigit():
            month_num = int(month_text)
            if 1 <= month_num <= 12:
                month = month_num

        # Try month name
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
            await update.message.reply_text(
                "❌ Please enter a valid month (1-12 or name like 'January'):"
            )
            return SET_DOB_MONTH

        context.user_data['dob_month'] = month

        import calendar
        month_name = calendar.month_name[month]
        day = context.user_data.get('dob_day', '?')

        msg = f"✅ Day: **{day}**\n"
        msg += f"✅ Month: **{month_name}**\n\n"
        msg += "Finally, enter your birth **YEAR** (e.g., 1990):"

        await update.message.reply_text(msg, parse_mode='Markdown')
        return SET_DOB_YEAR

    except Exception as e:
        logger.error(f"Error in set_dob_month: {e}")
        await safe_reply(update, "Please enter a valid month:")
        return SET_DOB_MONTH


async def set_dob_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle year input and complete DOB setup with comprehensive validation.

    Args:
        update: Telegram update object
        context: Handler context

    Returns:
        int: ConversationHandler.END
    """
    try:
        if not update.effective_user or not update.message:
            return ConversationHandler.END

        user_id = update.effective_user.id
        year_text = update.message.text.strip()

        # Validate year format
        if not year_text.isdigit() or len(year_text) != 4:
            await update.message.reply_text(
                "❌ Please enter a valid 4-digit year (e.g., 1990):"
            )
            return SET_DOB_YEAR

        year = int(year_text)
        day = context.user_data.get('dob_day')
        month = context.user_data.get('dob_month')

        # Verify session data
        if not day or not month:
            await update.message.reply_text(
                "⚠️ Session expired. Please start over with /setdob",
                reply_markup=bot.get_main_keyboard()
            )
            context.user_data.clear()
            return ConversationHandler.END

        logger.info(f"User {user_id} entered DOB: {day}/{month}/{year}")

        # Validate and create birth date
        try:
            birth_date = bot.astro.validate_birth_date(day, month, year)
            logger.info(f"Birth date validated: {birth_date}")
        except ValueError as e:
            logger.warning(f"Invalid birth date for user {user_id}: {e}")
            await update.message.reply_text(
                f"❌ Error: {e}\n\nPlease enter the year again:"
            )
            return SET_DOB_YEAR

        # Calculate zodiac and life path
        zodiac = bot.astro.get_zodiac_sign(birth_date)
        life_path = bot.astro.calculate_life_path(birth_date)

        logger.info(f"Calculated - Zodiac: {zodiac}, Life Path: {life_path}")

        # Save to database with verification
        logger.info(f"Saving to database for user {user_id}...")
        save_result = bot.db.save_user_dob(user_id, birth_date, zodiac, life_path)

        if save_result:
            # Double-verify the save
            verify_data = bot.db.get_user_data(user_id)

            if verify_data:
                success_msg = "🎉 **Birth date saved successfully!**\n\n"
                success_msg += f"📅 **Date:** {birth_date.strftime('%B %d, %Y')}\n"
                success_msg += f"♈ **Zodiac Sign:** {zodiac}\n"
                success_msg += f"🔢 **Life Path Number:** {life_path}\n\n"
                success_msg += "✨ You can now use all features!\n"
                success_msg += "Try 'Today's Reading' for your daily horoscope."

                await update.message.reply_text(
                    success_msg,
                    reply_markup=bot.get_main_keyboard(),
                    parse_mode='Markdown'
                )
                logger.info(f"✓ Successfully saved and verified DOB for user {user_id}")
            else:
                raise Exception("Data saved but verification failed")
        else:
            error_msg = "❌ **Failed to save your birth date.**\n\n"
            error_msg += "This might be a temporary issue. Please try again later.\n"
            error_msg += "If the problem persists, contact support."

            await update.message.reply_text(
                error_msg,
                reply_markup=bot.get_main_keyboard(),
                parse_mode='Markdown'
            )
            logger.error(f"✗ Failed to save DOB for user {user_id}")

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError as e:
        logger.error(f"Value error in set_dob_year: {e}")
        await update.message.reply_text(
            f"❌ Error: {e}\n\nPlease enter the year again:"
        )
        return SET_DOB_YEAR
    except Exception as e:
        logger.error(f"Unexpected error in set_dob_year: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ An unexpected error occurred.\n\nPlease try /setdob again.",
            reply_markup=bot.get_main_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancel ongoing conversation.

    Args:
        update: Telegram update object
        context: Handler context

    Returns:
        int: ConversationHandler.END
    """
    try:
        context.user_data.clear()
        await update.message.reply_text(
            "❌ Operation cancelled!\n\nYou can start again anytime.",
            reply_markup=bot.get_main_keyboard()
        )
        logger.info(f"User {update.effective_user.id} cancelled conversation")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in cancel_conversation: {e}")
        return ConversationHandler.END


async def today_reading(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Generate and send today's personalized reading.

    Args:
        update: Telegram update object
        context: Handler context
    """
    try:
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id
        bot.metrics.increment_commands()

        user_data = bot.db.get_user_data(user_id)

        if not user_data:
            msg = "⚠️ **Please set your birth date first!**\n\n"
            msg += "Use the 'Set DOB' button below to get started."
            await update.message.reply_text(
                msg,
                reply_markup=bot.get_main_keyboard(),
                parse_mode='Markdown'
            )
            return

        dob_str, zodiac, life_path = user_data

        # Generate reading components
        horoscope = bot.astro.get_horoscope(zodiac)
        lucky_number = bot.astro.generate_lucky_number(life_path, date.today())

        fact_result = bot.db.get_random_fact()
        fact = fact_result[0] if fact_result else "Believe in yourself and trust the journey!"

        reading = f"🔮 **Today's Reading for {zodiac}**\n\n"
        reading += f"📜 **Horoscope:**\n{horoscope}\n\n"
        reading += f"🍀 **Lucky Number:** {lucky_number}\n\n"
        reading += f"💫 **Daily Insight:**\n{fact}"

        await update.message.reply_text(
            reading,
            reply_markup=bot.get_main_keyboard(),
            parse_mode='Markdown'
        )

        logger.info(f"Generated daily reading for user {user_id} ({zodiac})")

    except Exception as e:
        logger.error(f"Error in today_reading: {e}")
        await safe_reply(update, "❌ Couldn't generate your reading. Please try again.")


async def numerology_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Display numerology information and life path analysis.

    Args:
        update: Telegram update object
        context: Handler context
    """
    try:
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id
        bot.metrics.increment_commands()

        user_data = bot.db.get_user_data(user_id)

        if not user_data:
            msg = "⚠️ **Please set your birth date first!**\n\n"
            msg += "Use the 'Set DOB' button to unlock numerology insights."
            await update.message.reply_text(
                msg,
                reply_markup=bot.get_main_keyboard(),
                parse_mode='Markdown'
            )
            return

        dob_str, zodiac, life_path = user_data
        birth_date = datetime.fromisoformat(dob_str).date()

        # Get numerology details
        calculation = bot.astro.get_life_path_calculation_steps(birth_date)
        meaning = bot.astro.get_life_path_meaning(life_path)

        numerology_text = f"🔢 **Your Numerology Profile**\n\n"
        numerology_text += f"**Life Path Number:** {life_path}\n\n"
        numerology_text += f"📊 **Calculation:**\n{calculation}\n\n"
        numerology_text += f"✨ **Meaning:**\n{meaning}"

        await update.message.reply_text(
            numerology_text,
            reply_markup=bot.get_main_keyboard(),
            parse_mode='Markdown'
        )

        logger.info(f"Displayed numerology info for user {user_id} (Life Path {life_path})")

    except Exception as e:
        logger.error(f"Error in numerology_info: {e}")
        await safe_reply(update, "❌ Couldn't retrieve numerology information.")


async def zodiac_secret(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Share a random zodiac secret or interesting fact.

    Args:
        update: Telegram update object
        context: Handler context
    """
    try:
        if not update.effective_user or not update.message:
            return

        bot.metrics.increment_commands()
        fact_result = bot.db.get_random_fact()

        if fact_result:
            fact_text, fact_type = fact_result

            emoji_map = {
                "psychology": "🧠",
                "science": "🔬",
                "numerology": "🔢",
                "astrology": "⭐",
                "general": "💡"
            }
            emoji = emoji_map.get(fact_type, "🎲")

            msg = f"✨ **Zodiac Secret**\n\n{emoji} {fact_text}"
            await update.message.reply_text(
                msg,
                reply_markup=bot.get_main_keyboard(),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "✨ The universe is full of mysteries waiting to be discovered!",
                reply_markup=bot.get_main_keyboard()
            )

    except Exception as e:
        logger.error(f"Error in zodiac_secret: {e}")
        await safe_reply(update, "✨ Here's a secret: You're awesome!")


async def compatibility_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Start compatibility check process.

    Args:
        update: Telegram update object
        context: Handler context
    """
    try:
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id
        bot.metrics.increment_commands()

        user_data = bot.db.get_user_data(user_id)

        if not user_data:
            msg = "⚠️ **Please set your birth date first!**\n\n"
            msg += "You need to set your DOB before checking compatibility."
            await update.message.reply_text(
                msg,
                reply_markup=bot.get_main_keyboard(),
                parse_mode='Markdown'
            )
            return

        dob_str, user_zodiac, user_life_path = user_data

        # Store user data for compatibility calculation
        context.user_data['compatibility_check'] = {
            'user_zodiac': user_zodiac,
            'user_life_path': user_life_path
        }

        check_msg = f"💕 **Compatibility Check**\n\n"
        check_msg += f"**Your Sign:** {user_zodiac}\n"
        check_msg += f"**Your Life Path:** {user_life_path}\n\n"
        check_msg += "📅 Now, send your partner's birth date in this format:\n"
        check_msg += "`DD-MM-YYYY` (e.g., 15-06-1995)"

        await update.message.reply_text(
            check_msg,
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error in compatibility_check: {e}")
        await safe_reply(update, "❌ Couldn't start compatibility check.")


async def process_compatibility_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Process partner's date and calculate compatibility.

    Args:
        update: Telegram update object
        context: Handler context
    """
    try:
        if 'compatibility_check' not in context.user_data:
            return

        date_text = update.message.text.strip()

        try:
            # Parse partner's birth date
            other_date = bot.astro.parse_date_input(date_text)
            other_zodiac = bot.astro.get_zodiac_sign(other_date)
            other_life_path = bot.astro.calculate_life_path(other_date)

            # Get user data
            user_data = context.user_data['compatibility_check']
            user_zodiac = user_data['user_zodiac']
            user_life_path = user_data['user_life_path']

            # Calculate compatibility
            zodiac_score, numerology_score, overall_score, compatibility_level = \
                bot.astro.calculate_compatibility(
                    user_zodiac, user_life_path,
                    other_zodiac, other_life_path
                )

            # Get elements for additional context
            user_element = bot.astro.get_element(user_zodiac)
            other_element = bot.astro.get_element(other_zodiac)

            result = f"💕 **Compatibility Analysis**\n\n"
            result += f"**You:** {user_zodiac} ({user_element}) - Path {user_life_path}\n"
            result += f"**Partner:** {other_zodiac} ({other_element}) - Path {other_life_path}\n\n"
            result += f"⭐ **Zodiac Compatibility:** {zodiac_score}%\n"
            result += f"🔢 **Numerology Harmony:** {numerology_score}%\n\n"
            result += f"💫 **Overall Match:** {overall_score}% - **{compatibility_level}**"

            await update.message.reply_text(
                result,
                reply_markup=bot.get_main_keyboard(),
                parse_mode='Markdown'
            )

            # Clear compatibility data
            context.user_data.pop('compatibility_check', None)

            logger.info(f"Compatibility check: {user_zodiac} + {other_zodiac} = {overall_score}%")

        except ValueError as e:
            await update.message.reply_text(
                f"❌ **Invalid date:** {e}\n\nPlease use DD-MM-YYYY format (e.g., 15-06-1995):"
            )

    except Exception as e:
        logger.error(f"Error processing compatibility: {e}")
        await safe_reply(update, "❌ Couldn't process date. Please use DD-MM-YYYY format.")
        context.user_data.pop('compatibility_check', None)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle general text messages and route to appropriate handlers.

    Args:
        update: Telegram update object
        context: Handler context
    """
    try:
        if not update.effective_user or not update.message:
            return

        text = update.message.text.lower().strip()

        # Route based on message content
        if any(phrase in text for phrase in ["set dob", "birth", "birthday", "date of birth"]):
            return await start_set_dob(update, context)
        elif any(phrase in text for phrase in ["today", "reading", "horoscope", "daily"]):
            return await today_reading(update, context)
        elif "numerology" in text or "life path" in text:
            return await numerology_info(update, context)
        elif any(phrase in text for phrase in ["fact", "secret", "insight"]):
            return await zodiac_secret(update, context)
        elif "compatibility" in text or "match" in text:
            return await compatibility_check(update, context)
        elif "help" in text or "commands" in text:
            return await help_command(update, context)

        # Default response
        default_msg = "👋 Use the menu buttons below to explore features!\n\n"
        default_msg += "Type /help to see all available commands."

        await update.message.reply_text(
            default_msg,
            reply_markup=bot.get_main_keyboard()
        )

    except Exception as e:
        logger.error(f"Error handling text message: {e}")
        await safe_reply(update, "Use the menu buttons to interact with the bot!")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Display bot statistics (admin only).

    Args:
        update: Telegram update object
        context: Handler context
    """
    try:
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id

        if not bot.is_admin(user_id):
            await update.message.reply_text("❌ This command is for admins only.")
            return

        # Get database stats
        db_stats = bot.db.get_database_stats()

        stats_msg = f"📊 **Bot Statistics**\n\n"
        stats_msg += f"⏱️ **Uptime:** {bot.metrics.get_uptime() / 3600:.2f} hours\n"
        stats_msg += f"👥 **Total Users:** {db_stats.get('total_users', 0)}\n"
        stats_msg += f"📝 **Total Facts:** {db_stats.get('total_facts', 0)}\n"
        stats_msg += f"⚡ **Commands Processed:** {bot.metrics.total_commands}\n"
        stats_msg += f"❌ **Errors:** {bot.metrics.total_errors}\n\n"

        if db_stats.get('zodiac_distribution'):
            stats_msg += "♈ **Zodiac Distribution:**\n"
            for sign, count in sorted(db_stats['zodiac_distribution'].items()):
                stats_msg += f"  • {sign}: {count}\n"

        await update.message.reply_text(
            stats_msg,
            reply_markup=bot.get_main_keyboard(),
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error in stats_command: {e}")
        await safe_reply(update, "❌ Couldn't retrieve statistics.")


async def main():
    """Main function with comprehensive error handling and lifecycle management."""
    global bot

    try:
        logger.info("=" * 60)
        logger.info("STARTING ASTROLOGY BOT - ENHANCED VERSION")
        logger.info("=" * 60)

        # Initialize configuration
        config = Config.from_env()
        config.validate()
        setup_logging(config)

        # Initialize bot
        bot = AstrologyBot(config)

        # Test database connection
        if not bot.db.test_connection():
            raise Exception("Database connection test failed - cannot start bot")

        # Setup application
        application = bot.setup_application()

        # Setup DOB conversation handler
        set_dob_conv = ConversationHandler(
            entry_points=[
                CommandHandler('setdob', start_set_dob),
                MessageHandler(
                    filters.TEXT & filters.Regex(r'(?i).*(set|birth|dob).*'),
                    start_set_dob
                )
            ],
            states={
                SET_DOB_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_dob_day)],
                SET_DOB_MONTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_dob_month)],
                SET_DOB_YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_dob_year)],
            },
            fallbacks=[
                CommandHandler('cancel', cancel_conversation),
                MessageHandler(filters.Regex(r'(?i)(cancel|stop|quit)'), cancel_conversation)
            ],
            conversation_timeout=300,
            name="set_dob_conversation"
        )

        # Register all handlers
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('help', help_command))
        application.add_handler(CommandHandler('stats', stats_command))
        application.add_handler(set_dob_conv)
        application.add_handler(CommandHandler('today', today_reading))
        application.add_handler(CommandHandler('numerology', numerology_info))
        application.add_handler(CommandHandler('zodiacsecret', zodiac_secret))
        application.add_handler(CommandHandler('compatibility', compatibility_check))

        # Compatibility date handler (must be before general text handler)
        application.add_handler(
            MessageHandler(filters.TEXT & filters.Regex(r'^\d{2}-\d{2}-\d{4}), process_compatibility_date)
                                                        )

        # General text handler (catch-all)
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
        )

        logger.info(f"✓ Admin IDs configured: {config.admin_ids}")
        logger.info(f"✓ Database: {config.db_path}")
        logger.info("✓ All handlers registered successfully")
        logger.info("🚀 Bot is ready! Press Ctrl+C to stop")
        logger.info("=" * 60)

        # Start bot
        await application.initialize()
        await application.start()
        await application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

        # Setup signal handlers for graceful shutdown
        stop_event = asyncio.Event()

        def signal_handler(sig, frame):
            logger.info(f"📡 Received signal {sig} - initiating shutdown")
            stop_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Wait for shutdown signal
        await stop_event.wait()

    except KeyboardInterrupt:
        logger.info("⌨️  Keyboard interrupt received")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Cleanup
        if bot:
            bot.state = BotState.STOPPING

        if 'application' in locals() and application:
            try:
                logger.info("🛑 Stopping application...")
                await application.updater.stop()
                await application.stop()
                await application.shutdown()
                logger.info("✓ Application stopped cleanly")
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")

        # Force garbage collection
        gc.collect()

        if bot:
            bot.state = BotState.STOPPED

        logger.info("=" * 60)
        logger.info("BOT SHUTDOWN COMPLETE")
        logger.info("=" * 60)


def run_bot():
    """Entry point with platform-specific configuration."""
    try:
        # Configure event loop for Windows
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        # Run the bot
        asyncio.run(main())

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        print("\n✓ Bot stopped gracefully")
    except Exception as e:
        logger.error(f"Fatal error in run_bot: {e}", exc_info=True)
        print(f"\n💥 Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    run_bot()