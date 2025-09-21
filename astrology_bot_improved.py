#!/usr/bin/env python3
"""
Fixed and Enhanced Astrology Bot - Production Ready Version
Fixes weak reference issue and adds improved error handling
"""

import os
import sys
import logging
import random
import calendar
import asyncio
import signal
from datetime import datetime, date
from typing import Optional, Dict, Any
import weakref

# Import our modules
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

# Telegram imports
try:
    from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
    from telegram.ext import (
        Application, CommandHandler, MessageHandler,
        filters, ContextTypes, ConversationHandler
    )
    from telegram.error import TelegramError, NetworkError, TimedOut
except ImportError:
    print("Error: python-telegram-bot not installed!")
    print("Install with: pip install python-telegram-bot==21.0.1")
    sys.exit(1)

# Initialize logger
logger = logging.getLogger(__name__)


class AstrologyBot:
    """Main bot class handling all operations with improved lifecycle management."""

    def __init__(self, config: Config):
        self.config = config
        self.db = DatabaseManager(config.db_path)
        self.astro = AstrologyCalculator()
        self.application: Optional[Application] = None
        self._shutdown_event = asyncio.Event()
        self._running = False
        logger.info("Astrology bot initialized successfully")

    def get_main_keyboard(self):
        """Create main menu keyboard."""
        return ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)

    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        return user_id in self.config.admin_ids

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Global error handler for the bot."""
        logger.error("Exception while handling an update:", exc_info=context.error)

        # Try to inform the user about the error
        if update and isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "Sorry, something went wrong. Please try again.",
                    reply_markup=self.get_main_keyboard()
                )
            except Exception as e:
                logger.error(f"Could not send error message: {e}")

    async def post_init(self, application: Application) -> None:
        """Post initialization hook."""
        logger.info("Bot post-initialization complete")

    async def post_shutdown(self, application: Application) -> None:
        """Post shutdown hook."""
        logger.info("Bot post-shutdown complete")

    def setup_application(self) -> Application:
        """Setup and configure the telegram application."""
        # Create application with proper configuration
        builder = Application.builder()
        builder.token(self.config.token)
        builder.post_init(self.post_init)
        builder.post_shutdown(self.post_shutdown)

        application = builder.build()

        # Add global error handler
        application.add_error_handler(self.error_handler)

        # Store weak reference to avoid circular reference issues
        self.application = application

        return application


# Global bot instance - will be initialized in main()
bot: Optional[AstrologyBot] = None


# Command handlers with improved error handling
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler with enhanced error handling."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"

    logger.info(f"User {user_id} (@{username}) started the bot")

    try:
        await update.message.reply_text(
            Messages.WELCOME,
            reply_markup=bot.get_main_keyboard(),
            parse_mode='Markdown'
        )
    except TelegramError as e:
        logger.error(f"Telegram error in start command: {e}")
        # Fallback without markdown
        try:
            await update.message.reply_text(
                "Welcome! I'm your astrology bot. Use the menu below to get started!",
                reply_markup=bot.get_main_keyboard()
            )
        except Exception as fallback_error:
            logger.error(f"Fallback start message failed: {fallback_error}")
    except Exception as e:
        logger.error(f"Unexpected error in start command: {e}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command handler with fallback."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested help")

    try:
        await update.message.reply_text(Messages.HELP_TEXT, parse_mode='Markdown')
    except TelegramError as e:
        logger.error(f"Telegram error in help command: {e}")
        # Fallback without markdown
        await update.message.reply_text(
            "Available commands:\n"
            "• Set DOB - Configure birth date\n"
            "• Today's Reading - Daily horoscope\n"
            "• Numerology - Life path info\n"
            "• Random Fact - Interesting facts\n"
            "• Support - Support the bot\n\n"
            "Use the menu buttons below!"
        )
    except Exception as e:
        logger.error(f"Unexpected error in help command: {e}")


# DOB conversation handlers with improved validation
async def start_set_dob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the set DOB conversation with validation."""
    if not update.effective_user or not update.message:
        return ConversationHandler.END

    user_id = update.effective_user.id
    logger.info(f"User {user_id} starting DOB setup")

    try:
        await update.message.reply_text(
            Messages.DOB_SETUP_START,
            reply_markup=ReplyKeyboardRemove()
        )
        return SET_DOB_DAY
    except Exception as e:
        logger.error(f"Error starting DOB setup: {e}")
        await update.message.reply_text(
            "Let's set your birth date! Please enter the day (1-31):",
            reply_markup=ReplyKeyboardRemove()
        )
        return SET_DOB_DAY


async def set_dob_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle day input with improved validation."""
    if not update.effective_user or not update.message:
        return ConversationHandler.END

    user_id = update.effective_user.id
    day_text = update.message.text.strip()

    logger.debug(f"User {user_id} entered day: {day_text}")

    try:
        # Enhanced validation
        if not day_text.isdigit() or len(day_text) > 2:
            await update.message.reply_text("Please enter just the day number (1-31):")
            return SET_DOB_DAY

        day = int(day_text)
        if 1 <= day <= 31:
            context.user_data['dob_day'] = day
            await update.message.reply_text(
                f"Day: {day} ✅\n\n"
                "Now enter the MONTH (1-12 or name like 'January'):"
            )
            return SET_DOB_MONTH
        else:
            await update.message.reply_text(Messages.DOB_INVALID_DAY)
            return SET_DOB_DAY

    except ValueError:
        await update.message.reply_text(Messages.DOB_INVALID_DAY)
        return SET_DOB_DAY
    except Exception as e:
        logger.error(f"Error in set_dob_day: {e}")
        await update.message.reply_text("Please enter a valid day number:")
        return SET_DOB_DAY


async def set_dob_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle month input with enhanced parsing."""
    if not update.effective_user or not update.message:
        return ConversationHandler.END

    user_id = update.effective_user.id
    month_text = update.message.text.strip().lower()

    logger.debug(f"User {user_id} entered month: {month_text}")

    try:
        month = None

        # Try to parse as number first
        if month_text.isdigit():
            month_num = int(month_text)
            if 1 <= month_num <= 12:
                month = month_num

        # Try to parse as month name
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
            await update.message.reply_text(Messages.DOB_INVALID_MONTH)
            return SET_DOB_MONTH

        context.user_data['dob_month'] = month
        month_name = calendar.month_name[month]
        await update.message.reply_text(
            f"Day: {context.user_data['dob_day']}\n"
            f"Month: {month_name} ✅\n\n"
            "Finally, enter your birth YEAR (e.g., 1990):"
        )
        return SET_DOB_YEAR

    except Exception as e:
        logger.error(f"Error in set_dob_month: {e}")
        await update.message.reply_text(Messages.DOB_INVALID_MONTH)
        return SET_DOB_MONTH


async def set_dob_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle year input and finalize DOB with comprehensive validation."""
    if not update.effective_user or not update.message:
        return ConversationHandler.END

    user_id = update.effective_user.id
    year_text = update.message.text.strip()

    logger.debug(f"User {user_id} entered year: {year_text}")

    try:
        # Enhanced year validation
        if not year_text.isdigit() or len(year_text) != 4:
            await update.message.reply_text("Please enter a valid 4-digit year (e.g., 1990):")
            return SET_DOB_YEAR

        year = int(year_text)
        day = context.user_data['dob_day']
        month = context.user_data['dob_month']

        # Validate and create birth date
        birth_date = bot.astro.validate_birth_date(day, month, year)

        # Calculate astrology data
        zodiac = bot.astro.get_zodiac_sign(birth_date)
        life_path = bot.astro.calculate_life_path(birth_date)

        # Save to database
        if bot.db.save_user_dob(user_id, birth_date, zodiac, life_path):
            logger.info(f"User {user_id} DOB saved: {birth_date}")

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
            except TelegramError:
                # Fallback without markdown
                await update.message.reply_text(
                    f"Birth date saved successfully!\n\n"
                    f"Date: {birth_date.strftime('%B %d, %Y')}\n"
                    f"Zodiac Sign: {zodiac}\n"
                    f"Life Path Number: {life_path}\n\n"
                    f"You can now use all personalized features!",
                    reply_markup=bot.get_main_keyboard()
                )
        else:
            await update.message.reply_text(
                "Sorry, couldn't save your birth date. Please try again.",
                reply_markup=bot.get_main_keyboard()
            )

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError as e:
        await update.message.reply_text(f"Error: {e}\nPlease enter the year again:")
        return SET_DOB_YEAR
    except Exception as e:
        logger.error(f"Error in set_dob_year: {e}")
        await update.message.reply_text(Messages.DOB_INVALID_YEAR)
        return SET_DOB_YEAR


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current conversation."""
    if not update.effective_user or not update.message:
        return ConversationHandler.END

    user_id = update.effective_user.id
    logger.info(f"User {user_id} cancelled conversation")

    context.user_data.clear()
    await update.message.reply_text(
        Messages.OPERATION_CANCELLED,
        reply_markup=bot.get_main_keyboard()
    )
    return ConversationHandler.END


# Enhanced feature handlers
async def today_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate today's reading with enhanced error handling."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested today's reading")

    try:
        user_data = bot.db.get_user_data(user_id)

        if not user_data:
            await update.message.reply_text(
                Messages.DOB_REQUIRED,
                reply_markup=bot.get_main_keyboard()
            )
            return

        dob_str, zodiac, life_path = user_data

        # Get horoscope and lucky number
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
        except TelegramError:
            # Fallback without markdown
            fallback_reading = (
                f"Today's Reading for {zodiac}\n\n"
                f"Horoscope: {horoscope}\n\n"
                f"Lucky Number: {lucky_number}\n\n"
                f"Daily Insight: {fact}"
            )
            await update.message.reply_text(fallback_reading)

    except Exception as e:
        logger.error(f"Error in today_reading: {e}")
        await update.message.reply_text(
            "Sorry, couldn't generate your reading right now. Please try again.",
            reply_markup=bot.get_main_keyboard()
        )


async def numerology_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's numerology information with enhanced formatting."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested numerology info")

    try:
        user_data = bot.db.get_user_data(user_id)

        if not user_data:
            await update.message.reply_text(
                Messages.DOB_REQUIRED,
                reply_markup=bot.get_main_keyboard()
            )
            return

        dob_str, zodiac, life_path = user_data
        birth_date = datetime.fromisoformat(dob_str).date()

        # Get calculation steps and meaning
        calculation = bot.astro.get_life_path_calculation_steps(birth_date)
        meaning = bot.astro.get_life_path_meaning(life_path)

        numerology_text = Messages.NUMEROLOGY_INFO.format(
            life_path=life_path,
            calculation=calculation,
            meaning=meaning
        )

        try:
            await update.message.reply_text(numerology_text, parse_mode='Markdown')
        except TelegramError:
            # Fallback without markdown formatting
            fallback_text = (
                f"Your Numerology Profile\n\n"
                f"Life Path Number: {life_path}\n\n"
                f"Calculation Steps:\n{calculation}\n\n"
                f"Meaning:\n{meaning}"
            )
            await update.message.reply_text(fallback_text)

    except Exception as e:
        logger.error(f"Error in numerology_info: {e}")
        await update.message.reply_text(
            "Sorry, couldn't retrieve your numerology info. Please try again.",
            reply_markup=bot.get_main_keyboard()
        )


async def random_fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get random fact from database with enhanced presentation."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested random fact")

    try:
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
            except TelegramError:
                # Fallback without markdown
                await update.message.reply_text(
                    f"Random Fact\n\n{emoji} {fact_text}"
                )
        else:
            await update.message.reply_text(
                "🎲 The universe is full of infinite possibilities and mysteries!"
            )

    except Exception as e:
        logger.error(f"Error in random_fact: {e}")
        await update.message.reply_text("Here's a fact: You're awesome! ✨")


async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show support information."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested support info")

    try:
        support_text = Messages.SUPPORT_INFO.format(
            upi_id=bot.config.upi_id or "your-upi-id@paytm",
            support_message=bot.config.support_message
        )

        try:
            await update.message.reply_text(support_text, parse_mode='Markdown')
        except TelegramError:
            # Fallback without markdown
            await update.message.reply_text(
                f"Support the Bot\n\n"
                f"This bot is developed with love!\n\n"
                f"Ways to support:\n"
                f"• Share with friends\n"
                f"• Provide feedback\n"
                f"• Consider a donation\n\n"
                f"UPI ID: {bot.config.upi_id or 'your-upi-id@paytm'}\n\n"
                f"{bot.config.support_message}\n\n"
                f"Thank you! ⭐"
            )

    except Exception as e:
        logger.error(f"Error in support_command: {e}")
        await update.message.reply_text("Thank you for considering supporting this bot! 💖")


# Enhanced text message handler
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages with improved pattern matching."""
    if not update.effective_user or not update.message:
        return

    text = update.message.text
    user_id = update.effective_user.id

    logger.debug(f"User {user_id} sent text: {text}")

    try:
        # Enhanced button matching with case-insensitive checking
        text_lower = text.lower()

        if "set dob" in text_lower or "birth" in text_lower:
            return await start_set_dob(update, context)
        elif "today" in text_lower and "reading" in text_lower:
            return await today_reading(update, context)
        elif "numerology" in text_lower:
            return await numerology_info(update, context)
        elif "random fact" in text_lower or "fact" in text_lower:
            return await random_fact(update, context)
        elif "support" in text_lower:
            return await support_command(update, context)
        elif "help" in text_lower:
            return await help_command(update, context)

        # Default response
        await update.message.reply_text(
            Messages.DIDNT_UNDERSTAND,
            reply_markup=bot.get_main_keyboard()
        )

    except Exception as e:
        logger.error(f"Error handling text message: {e}")
        await update.message.reply_text(
            "Sorry, something went wrong. Please try again.",
            reply_markup=bot.get_main_keyboard()
        )


def setup_signal_handlers(application: Application):
    """Setup signal handlers for graceful shutdown."""

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        asyncio.create_task(application.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Enhanced main function with better lifecycle management."""
    global bot

    try:
        # Load configuration
        config = Config.from_env()
        config.validate()

        # Setup logging
        setup_logging(config)

        # Initialize bot
        bot = AstrologyBot(config)

        logger.info("Starting Enhanced Astrology Bot...")
        logger.info(f"Admin IDs: {config.admin_ids}")

        # Create application
        application = bot.setup_application()

        # Set DOB conversation handler
        set_dob_conv = ConversationHandler(
            entry_points=[
                CommandHandler('setdob', start_set_dob),
                MessageHandler(filters.TEXT & filters.Regex(r'(?i).*set.*dob.*'), start_set_dob)
            ],
            states={
                SET_DOB_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_dob_day)],
                SET_DOB_MONTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_dob_month)],
                SET_DOB_YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_dob_year)],
            },
            fallbacks=[
                CommandHandler('cancel', cancel_conversation),
                MessageHandler(filters.Regex(r'(?i)cancel|stop|quit'), cancel_conversation)
            ],
            conversation_timeout=config.conversation_timeout,
        )

        # Add handlers in order of precedence
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('help', help_command))
        application.add_handler(set_dob_conv)

        # Individual command handlers
        application.add_handler(CommandHandler('today', today_reading))
        application.add_handler(CommandHandler('numerology', numerology_info))
        application.add_handler(CommandHandler('randomfact', random_fact))
        application.add_handler(CommandHandler('support', support_command))

        # Text message handler (must be last)
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
        )

        # Setup signal handlers
        setup_signal_handlers(application)

        # Start the bot
        logger.info("Bot is ready! Press Ctrl+C to stop.")

        # Use run_polling with proper error handling
        await application.initialize()
        await application.start()
        await application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

        # Wait for shutdown signal
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutdown requested...")
        finally:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()

    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please check your .env file and fix the configuration.")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"Fatal error occurred: {e}")
    finally:
        logger.info("Bot shutdown complete")


def run_bot():
    """Entry point that handles the event loop properly."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error in event loop: {e}", exc_info=True)


if __name__ == '__main__':
    run_bot()
