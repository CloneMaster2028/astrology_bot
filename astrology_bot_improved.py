#!/usr/bin/env python3
"""
Enhanced Astrology Bot - Production Ready Version
All issues fixed with improved reliability and error handling
"""

import os
import sys
import logging
import asyncio
import signal
import gc
from datetime import datetime, date
from typing import Optional

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


class AstrologyBot:
    """Main bot class with improved lifecycle management."""

    def __init__(self, config: Config):
        self.config = config
        self.db = DatabaseManager(config.db_path)
        self.astro = AstrologyCalculator()
        self.application = None
        self._shutdown_event = asyncio.Event()
        self._running = False
        self._startup_time = datetime.now()
        logger.info("Bot components initialized")

    def get_main_keyboard(self):
        """Create main menu keyboard."""
        try:
            return ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)
        except Exception as e:
            logger.error(f"Keyboard creation failed: {e}")
            return ReplyKeyboardMarkup([["Help"]], resize_keyboard=True)

    def is_admin(self, user_id: int) -> bool:
        """Check admin status."""
        return user_id in self.config.admin_ids

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Global error handler with detailed logging."""
        logger.error("Exception while handling update:", exc_info=context.error)

        error_message = "Sorry, something went wrong. Please try again."

        if isinstance(context.error, NetworkError):
            error_message = "Network error. Please try again shortly."
        elif isinstance(context.error, TimedOut):
            error_message = "Request timed out. Please try again."
        elif isinstance(context.error, BadRequest):
            error_message = "Invalid request. Please check your input."

        try:
            if update and isinstance(update, Update) and update.effective_message:
                await update.effective_message.reply_text(
                    error_message,
                    reply_markup=self.get_main_keyboard()
                )
        except Exception as e:
            logger.error(f"Could not send error message: {e}")

    def setup_application(self) -> Application:
        """Setup Telegram application."""
        try:
            builder = Application.builder()
            builder.token(self.config.token)
            builder.connection_pool_size(self.config.connection_pool_size)
            builder.read_timeout(self.config.request_timeout)
            builder.write_timeout(self.config.request_timeout)

            application = builder.build()
            application.add_error_handler(self.error_handler)

            self.application = application
            self._running = True

            logger.info("Application setup completed")
            return application

        except Exception as e:
            logger.error(f"Application setup failed: {e}")
            raise


# Global bot instance
bot: Optional[AstrologyBot] = None


async def safe_reply(update: Update, message: str, keyboard=None):
    """Safe reply with fallback."""
    try:
        if update and update.effective_message:
            reply_markup = keyboard if keyboard is not None else bot.get_main_keyboard()
            await update.effective_message.reply_text(message, reply_markup=reply_markup)
            return True
    except Exception as e:
        logger.error(f"Failed to send reply: {e}")
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler."""
    try:
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id
        first_name = update.effective_user.first_name or "User"

        logger.info(f"User {user_id} started the bot")

        welcome_msg = f"Welcome {first_name}! I'm your astrology bot.\n\n"
        welcome_msg += "I can help you with:\n"
        welcome_msg += "• Daily horoscopes and readings\n"
        welcome_msg += "• Numerology life path calculations\n"
        welcome_msg += "• Zodiac compatibility checks\n"
        welcome_msg += "• Lucky numbers and insights\n\n"
        welcome_msg += "Use the menu below to get started!"

        await update.message.reply_text(
            welcome_msg,
            reply_markup=bot.get_main_keyboard()
        )

    except Exception as e:
        logger.error(f"Error in start: {e}")
        await safe_reply(update, "Welcome! Use the menu to explore features.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command handler."""
    try:
        if not update.effective_user or not update.message:
            return

        help_text = "Available Features:\n\n"
        help_text += "• Set DOB - Configure your birth date\n"
        help_text += "• Today's Reading - Daily horoscope\n"
        help_text += "• Numerology - Life path analysis\n"
        help_text += "• Compatibility - Relationship analysis\n"
        help_text += "• Zodiac Secret - Random insights\n\n"
        help_text += "Commands:\n"
        help_text += "/setdob - Set birth date\n"
        help_text += "/today - Daily reading\n"
        help_text += "/numerology - Numerology info\n"
        help_text += "/compatibility - Check compatibility\n"
        help_text += "/help - Show this help"

        await update.message.reply_text(help_text, reply_markup=bot.get_main_keyboard())

    except Exception as e:
        logger.error(f"Error in help: {e}")
        await safe_reply(update, "Help is available via the menu buttons.")


async def start_set_dob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start DOB conversation."""
    try:
        if not update.effective_user or not update.message:
            return ConversationHandler.END

        context.user_data.clear()

        await update.message.reply_text(
            "Let's set your birth date!\n\nEnter the DAY (1-31):",
            reply_markup=ReplyKeyboardRemove()
        )
        return SET_DOB_DAY

    except Exception as e:
        logger.error(f"Error starting DOB: {e}")
        await safe_reply(update, "Please enter the day (1-31):")
        return SET_DOB_DAY


async def set_dob_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle day input."""
    try:
        if not update.effective_user or not update.message:
            return ConversationHandler.END

        day_text = update.message.text.strip()

        if not day_text.isdigit() or len(day_text) > 2:
            await update.message.reply_text("Enter a valid day (1-31):")
            return SET_DOB_DAY

        day = int(day_text)
        if not (1 <= day <= 31):
            await update.message.reply_text("Day must be between 1 and 31:")
            return SET_DOB_DAY

        context.user_data['dob_day'] = day

        await update.message.reply_text(
            f"Day: {day} ✓\n\nNow enter the MONTH (1-12 or name):"
        )
        return SET_DOB_MONTH

    except Exception as e:
        logger.error(f"Error in set_dob_day: {e}")
        await safe_reply(update, "Please enter a valid day (1-31):")
        return SET_DOB_DAY


async def set_dob_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle month input."""
    try:
        if not update.effective_user or not update.message:
            return ConversationHandler.END

        month_text = update.message.text.strip().lower()
        month = None

        if month_text.isdigit():
            month_num = int(month_text)
            if 1 <= month_num <= 12:
                month = month_num

        if month is None:
            month_names = {
                'january': 1, 'jan': 1, 'february': 2, 'feb': 2,
                'march': 3, 'mar': 3, 'april': 4, 'apr': 4,
                'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
                'august': 8, 'aug': 8, 'september': 9, 'sep': 9,
                'october': 10, 'oct': 10, 'november': 11, 'nov': 11,
                'december': 12, 'dec': 12
            }
            month = month_names.get(month_text)

        if month is None:
            await update.message.reply_text(
                "Enter valid month (1-12 or name like 'January'):"
            )
            return SET_DOB_MONTH

        context.user_data['dob_month'] = month

        import calendar
        month_name = calendar.month_name[month]

        await update.message.reply_text(
            f"Day: {context.user_data['dob_day']}\n"
            f"Month: {month_name} ✓\n\n"
            f"Finally, enter your birth YEAR (e.g., 1990):"
        )
        return SET_DOB_YEAR

    except Exception as e:
        logger.error(f"Error in set_dob_month: {e}")
        await safe_reply(update, "Please enter valid month:")
        return SET_DOB_MONTH


async def set_dob_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle year input with comprehensive error handling."""
    try:
        if not update.effective_user or not update.message:
            return ConversationHandler.END

        user_id = update.effective_user.id
        year_text = update.message.text.strip()

        # Validate year format
        if not year_text.isdigit() or len(year_text) != 4:
            await update.message.reply_text("Enter valid 4-digit year (e.g., 1990):")
            return SET_DOB_YEAR

        year = int(year_text)
        day = context.user_data.get('dob_day')
        month = context.user_data.get('dob_month')

        # Check if day and month are in user_data
        if not day or not month:
            await update.message.reply_text(
                "Session expired. Please start over with /setdob",
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
            await update.message.reply_text(f"Error: {e}\nEnter year again:")
            return SET_DOB_YEAR

        # Calculate zodiac and life path
        zodiac = bot.astro.get_zodiac_sign(birth_date)
        life_path = bot.astro.calculate_life_path(birth_date)

        logger.info(f"Calculated zodiac: {zodiac}, life path: {life_path}")

        # Save to database
        logger.info(f"Attempting to save to database for user {user_id}...")
        save_result = bot.db.save_user_dob(user_id, birth_date, zodiac, life_path)

        logger.info(f"Save result: {save_result}")

        if save_result:
            # Verify the save
            verify_data = bot.db.get_user_data(user_id)
            logger.info(f"Verification: {verify_data}")

            if verify_data:
                success_msg = f"✅ Birth date saved successfully!\n\n"
                success_msg += f"📅 Date: {birth_date.strftime('%B %d, %Y')}\n"
                success_msg += f"♈ Zodiac: {zodiac}\n"
                success_msg += f"🔢 Life Path: {life_path}\n\n"
                success_msg += "You can now use all features!"

                await update.message.reply_text(
                    success_msg,
                    reply_markup=bot.get_main_keyboard()
                )
                logger.info(f"Successfully saved and verified DOB for user {user_id}")
            else:
                raise Exception("Data saved but verification failed")
        else:
            error_msg = "❌ Failed to save your birth date.\n\n"
            error_msg += "Please try again later or contact support."

            await update.message.reply_text(
                error_msg,
                reply_markup=bot.get_main_keyboard()
            )
            logger.error(f"Failed to save DOB for user {user_id}")

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError as e:
        logger.error(f"Value error in set_dob_year: {e}")
        await update.message.reply_text(f"Error: {e}\nEnter year again:")
        return SET_DOB_YEAR
    except Exception as e:
        logger.error(f"Unexpected error in set_dob_year: {e}", exc_info=True)
        await update.message.reply_text(
            "An unexpected error occurred. Please try /setdob again.",
            reply_markup=bot.get_main_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel conversation."""
    try:
        context.user_data.clear()
        await update.message.reply_text(
            "Operation cancelled!",
            reply_markup=bot.get_main_keyboard()
        )
        return ConversationHandler.END
    except Exception:
        return ConversationHandler.END


async def today_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Today's reading handler."""
    try:
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id
        user_data = bot.db.get_user_data(user_id)

        if not user_data:
            await update.message.reply_text(
                "Please set your birth date first using 'Set DOB'!",
                reply_markup=bot.get_main_keyboard()
            )
            return

        dob_str, zodiac, life_path = user_data
        horoscope = bot.astro.get_horoscope(zodiac)
        lucky_number = bot.astro.generate_lucky_number(life_path, date.today())

        fact_result = bot.db.get_random_fact()
        fact = fact_result[0] if fact_result else "Believe in yourself!"

        reading = f"Today's Reading for {zodiac}\n\n"
        reading += f"Horoscope:\n{horoscope}\n\n"
        reading += f"Lucky Number: {lucky_number}\n\n"
        reading += f"Daily Insight:\n{fact}"

        await update.message.reply_text(reading, reply_markup=bot.get_main_keyboard())

    except Exception as e:
        logger.error(f"Error in today_reading: {e}")
        await safe_reply(update, "Couldn't generate reading. Try again.")


async def numerology_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Numerology handler."""
    try:
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id
        user_data = bot.db.get_user_data(user_id)

        if not user_data:
            await update.message.reply_text(
                "Please set your birth date first!",
                reply_markup=bot.get_main_keyboard()
            )
            return

        dob_str, zodiac, life_path = user_data
        birth_date = datetime.fromisoformat(dob_str).date()

        calculation = bot.astro.get_life_path_calculation_steps(birth_date)
        meaning = bot.astro.get_life_path_meaning(life_path)

        numerology_text = f"Your Numerology Profile\n\n"
        numerology_text += f"Life Path Number: {life_path}\n\n"
        numerology_text += f"Calculation:\n{calculation}\n\n"
        numerology_text += f"Meaning:\n{meaning}"

        await update.message.reply_text(numerology_text, reply_markup=bot.get_main_keyboard())

    except Exception as e:
        logger.error(f"Error in numerology: {e}")
        await safe_reply(update, "Couldn't retrieve numerology info.")


async def zodiac_secret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zodiac secret handler."""
    try:
        if not update.effective_user or not update.message:
            return

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

            await update.message.reply_text(
                f"Zodiac Secret\n\n{emoji} {fact_text}",
                reply_markup=bot.get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                "The universe is full of mysteries!",
                reply_markup=bot.get_main_keyboard()
            )

    except Exception as e:
        logger.error(f"Error in zodiac_secret: {e}")
        await safe_reply(update, "Here's a fact: You're awesome!")


async def compatibility_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Compatibility check handler."""
    try:
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id
        user_data = bot.db.get_user_data(user_id)

        if not user_data:
            await update.message.reply_text(
                "Please set your birth date first!",
                reply_markup=bot.get_main_keyboard()
            )
            return

        dob_str, user_zodiac, user_life_path = user_data

        context.user_data['compatibility_check'] = {
            'user_zodiac': user_zodiac,
            'user_life_path': user_life_path
        }

        check_msg = f"Compatibility Check\n\n"
        check_msg += f"Your sign: {user_zodiac}\n"
        check_msg += f"Your life path: {user_life_path}\n\n"
        check_msg += "Send partner's birth date (DD-MM-YYYY):"

        await update.message.reply_text(
            check_msg,
            reply_markup=ReplyKeyboardRemove()
        )

    except Exception as e:
        logger.error(f"Error in compatibility_check: {e}")
        await safe_reply(update, "Couldn't start compatibility check.")


async def process_compatibility_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process compatibility date input."""
    try:
        if 'compatibility_check' not in context.user_data:
            return

        date_text = update.message.text.strip()

        try:
            other_date = bot.astro.parse_date_input(date_text)
            other_zodiac = bot.astro.get_zodiac_sign(other_date)
            other_life_path = bot.astro.calculate_life_path(other_date)

            user_data = context.user_data['compatibility_check']
            user_zodiac = user_data['user_zodiac']
            user_life_path = user_data['user_life_path']

            zodiac_score, numerology_score, overall_score, compatibility_level = \
                bot.astro.calculate_compatibility(
                    user_zodiac, user_life_path,
                    other_zodiac, other_life_path
                )

            user_element = bot.astro.get_element(user_zodiac)
            other_element = bot.astro.get_element(other_zodiac)

            result = f"Compatibility Analysis\n\n"
            result += f"You: {user_zodiac} ({user_element}) - Path {user_life_path}\n"
            result += f"Partner: {other_zodiac} ({other_element}) - Path {other_life_path}\n\n"
            result += f"Zodiac: {zodiac_score}%\n"
            result += f"Numerology: {numerology_score}%\n\n"
            result += f"Overall: {overall_score}% - {compatibility_level}"

            await update.message.reply_text(
                result,
                reply_markup=bot.get_main_keyboard()
            )

            context.user_data.pop('compatibility_check', None)

        except ValueError as e:
            await update.message.reply_text(
                f"Invalid date: {e}\nUse DD-MM-YYYY format:"
            )

    except Exception as e:
        logger.error(f"Error processing compatibility: {e}")
        await safe_reply(update, "Couldn't process date. Try DD-MM-YYYY format.")
        context.user_data.pop('compatibility_check', None)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """General text handler."""
    try:
        if not update.effective_user or not update.message:
            return

        text = update.message.text.lower().strip()

        if any(phrase in text for phrase in ["set dob", "birth", "birthday"]):
            return await start_set_dob(update, context)
        elif any(phrase in text for phrase in ["today", "reading", "horoscope"]):
            return await today_reading(update, context)
        elif "numerology" in text or "life path" in text:
            return await numerology_info(update, context)
        elif any(phrase in text for phrase in ["fact", "secret"]):
            return await zodiac_secret(update, context)
        elif "compatibility" in text:
            return await compatibility_check(update, context)
        elif "help" in text or "commands" in text:
            return await help_command(update, context)

        default_msg = "Use the menu buttons below to explore features!"
        await update.message.reply_text(
            default_msg,
            reply_markup=bot.get_main_keyboard()
        )

    except Exception as e:
        logger.error(f"Error handling text: {e}")
        await safe_reply(update, "Use the menu buttons!")


async def main():
    """Main function with comprehensive error handling."""
    global bot

    try:
        logger.info("=" * 50)
        logger.info("STARTING ASTROLOGY BOT")
        logger.info("=" * 50)

        config = Config.from_env()
        config.validate()
        setup_logging(config)

        bot = AstrologyBot(config)

        # Test database connection
        if not bot.db.test_connection():
            raise Exception("Database connection test failed")

        application = bot.setup_application()

        # Setup conversation handler
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
        )

        # Register handlers
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('help', help_command))
        application.add_handler(set_dob_conv)
        application.add_handler(CommandHandler('today', today_reading))
        application.add_handler(CommandHandler('numerology', numerology_info))
        application.add_handler(CommandHandler('zodiacsecret', zodiac_secret))
        application.add_handler(CommandHandler('compatibility', compatibility_check))

        application.add_handler(
            MessageHandler(filters.TEXT & filters.Regex(r'^\d{2}-\d{2}-\d{4}$'), process_compatibility_date)
        )
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
        )

        logger.info(f"Admin IDs: {config.admin_ids}")
        logger.info("Bot ready! Press Ctrl+C to stop")

        await application.initialize()
        await application.start()
        await application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

        # Keep running until shutdown
        stop_event = asyncio.Event()

        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}")
            stop_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        await stop_event.wait()

    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if bot:
            bot._running = False
        if 'application' in locals():
            try:
                await application.updater.stop()
                await application.stop()
                await application.shutdown()
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")
        gc.collect()
        logger.info("Bot shutdown complete")


def run_bot():
    """Entry point with platform-specific configuration."""
    try:
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        print("\nBot stopped gracefully")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    run_bot()