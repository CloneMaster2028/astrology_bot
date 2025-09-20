"""
Constants and message templates for Astrology Bot
"""

# Conversation states
SET_DOB_DAY, SET_DOB_MONTH, SET_DOB_YEAR = range(3)
ADD_FACT_DAY, ADD_FACT_TEXT = range(3, 5)

# Emojis (using Unicode for better compatibility)
class Emoji:
    STAR = "⭐"
    HEART = "❤️"
    BIRTHDAY = "🎂"
    CRYSTAL_BALL = "🔮"
    NUMBERS = "🔢"
    CALENDAR = "📅"
    LOVE = "💕"
    DICE = "🎲"
    MONEY = "💰"
    QUESTION = "❓"
    SPARKLES = "✨"
    FIRE = "🔥"
    WATER = "💧"
    AIR = "💨"
    EARTH = "🌍"
    CHECK = "✅"
    CROSS = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    BRAIN = "🧠"
    SCIENCE = "🔬"
    BULB = "💡"
    BROADCAST = "📢"
    CHART = "📊"
    GREEN_CIRCLE = "🟢"
    RED_CIRCLE = "🔴"

# Message templates
class Messages:
    WELCOME = f"""
{Emoji.STAR} **Welcome to Astrology & Numerology Bot!** {Emoji.STAR}

I can help you with:
• Daily horoscopes and readings
• Numerology life path calculations
• Date-based psychological facts
• Zodiac compatibility checks
• Lucky numbers and insights

Use the menu below to get started, or type /help for more info.
    """
    
    HELP_TEXT = f"""
{Emoji.CRYSTAL_BALL} **Available Commands:**

{Emoji.BIRTHDAY} **Set DOB** - Set your birth date for personalized readings
{Emoji.STAR} **Today's Reading** - Get daily horoscope, lucky number & fact
{Emoji.NUMBERS} **Numerology** - Learn about your life path number
{Emoji.CALENDAR} **Date Facts** - Get facts about specific dates
{Emoji.LOVE} **Compatibility** - Check zodiac compatibility
{Emoji.DICE} **Random Fact** - Get a random interesting fact
{Emoji.MONEY} **Support** - Support the bot development

**Direct Commands:**
/setdob - Set your date of birth
/today - Get today's reading
/numerology - Get your numerology info
/fact <day> - Get fact for specific day
/compatibility - Check compatibility
/randomfact - Random fact

Set your birth date first for personalized readings! {Emoji.SPARKLES}
    """
    
    DOB_SETUP_START = f"Let's set your date of birth! {Emoji.BIRTHDAY}\n\nPlease enter the DAY you were born (1-31):"
    
    DOB_INVALID_DAY = "Please enter a valid day between 1 and 31:"
    DOB_INVALID_MONTH = "Please enter a valid month (1-12 or month name):"
    DOB_INVALID_YEAR = "Please enter a valid year (numbers only):"
    
    DOB_SUCCESS = f"""
{Emoji.SPARKLES} **Birth date saved successfully!** {Emoji.SPARKLES}

{Emoji.CALENDAR} **Date:** {{date}}
{Emoji.STAR} **Zodiac Sign:** {{zodiac}}
{Emoji.NUMBERS} **Life Path Number:** {{life_path}}

You can now use all personalized features! Try "Today's Reading" {Emoji.STAR}
    """
    
    DOB_REQUIRED = f"Please set your birth date first using 'Set DOB' button! {Emoji.BIRTHDAY}"
    
    TODAYS_READING = f"""
{Emoji.STAR} **Today's Reading for {{zodiac}}** {Emoji.STAR}

{Emoji.CRYSTAL_BALL} **Horoscope:**
{{horoscope}}

{Emoji.DICE} **Lucky Number:** {{lucky_number}}

{Emoji.BRAIN} **Daily Insight:**
{{fact}}

{Emoji.SPARKLES} **Note:** This is a templated horoscope. For real-time astrological data, consider integrating with APIs like AstrologyAPI or Horoscope.com
    """
    
    NUMEROLOGY_INFO = f"""
{Emoji.NUMBERS} **Your Numerology Profile** {Emoji.NUMBERS}

**Life Path Number:** {{life_path}}

**Calculation Steps:**
```
{{calculation}}
```

**Meaning:**
{{meaning}}

{Emoji.BULB} **Master Numbers (11, 22, 33) are not reduced further as they carry special spiritual significance.**
    """
    
    DATE_FACTS_PROMPT = f"""
{Emoji.CALENDAR} **Date Facts** {Emoji.CALENDAR}

Choose an option:
• Send a number (1-31) for day-of-month facts
• Type 'my birthday' for your birth date facts
• Type 'today' for today's date facts
    """
    
    COMPATIBILITY_CHECK = f"""
{Emoji.LOVE} **Compatibility Check** {Emoji.LOVE}

Your sign: {{user_zodiac}}
Your life path: {{user_life_path}}

Send me another birth date (DD-MM-YYYY) to check compatibility!
    """
    
    COMPATIBILITY_RESULT = f"""
{Emoji.LOVE} **Compatibility Analysis** {Emoji.LOVE}

**You:** {{user_zodiac}} ({{user_element}}) - Life Path {{user_life_path}}
**Partner:** {{other_zodiac}} ({{other_element}}) - Life Path {{other_life_path}}

**Scores:**
{Emoji.STAR} Zodiac Compatibility: {{zodiac_score}}%
{Emoji.NUMBERS} Numerology Compatibility: {{numerology_score}}%

**Overall: {{overall_score}}% - {{compatibility_level}}**

**Analysis Method:**
• Elements: Fire/Air and Earth/Water are naturally compatible
• Life Path: Similar numbers indicate similar life approaches
• This is a simplified compatibility system for fun!
    """
    
    SUPPORT_INFO = f"""
{Emoji.MONEY} **Support the Bot** {Emoji.MONEY}

This bot is developed and maintained with love! {Emoji.HEART}

If you find it helpful, you can support development:

{Emoji.SPARKLES} **Ways to support:**
• Share with friends who love astrology
• Provide feedback and suggestions
• Consider a small donation via UPI

**UPI ID:** {{upi_id}}

{{support_message}}

Thank you for using Astrology Bot! {Emoji.STAR}
    """
    
    OPERATION_CANCELLED = f"Operation cancelled! {Emoji.CHECK}"
    ADMIN_ONLY = f"{Emoji.CROSS} This command is for admins only."
    SOMETHING_WRONG = "Sorry, something went wrong. Please try again."
    DIDNT_UNDERSTAND = f"I didn't understand that. Use the menu buttons below or type /help for commands! {Emoji.INFO}"
    
    BROADCAST_USAGE = "Usage: /broadcast <message>"
    BROADCAST_COMPLETE = f"{Emoji.BROADCAST} Broadcast completed!\n{Emoji.CHECK} Sent: {{sent}}\n{Emoji.CROSS} Failed: {{failed}}"
    
    HEALTH_CHECK_HEALTHY = f"""
{Emoji.GREEN_CIRCLE} **Bot Status: Healthy**

{Emoji.CHART} **Statistics:**
• Users: {{user_count}}
• Facts: {{fact_count}}
• Uptime: {{uptime}}
    """
    
    HEALTH_CHECK_ERROR = f"{Emoji.RED_CIRCLE} **Bot Status: Error**\n\nError: {{error}}"

# Zodiac and numerology data
ZODIAC_DATES = [
    (321, 419, "Aries"), (420, 520, "Taurus"), (521, 620, "Gemini"),
    (621, 722, "Cancer"), (723, 822, "Leo"), (823, 922, "Virgo"),
    (923, 1022, "Libra"), (1023, 1121, "Scorpio"), (1122, 1221, "Sagittarius"),
    (1222, 1231, "Capricorn"), (101, 119, "Aquarius"), (120, 318, "Pisces")
]

HOROSCOPE_TEMPLATES = {
    "Aries": [
        "Today brings new opportunities for leadership. Trust your instincts.",
        "Your energy is high today. Channel it into creative projects.",
        "A chance encounter could spark interesting conversations.",
        "Bold decisions made today will pay off in the long run.",
        "Your pioneering spirit opens doors to exciting adventures."
    ],
    "Taurus": [
        "Stability and patience will serve you well today.",
        "Focus on practical matters and long-term goals.",
        "Your persistence will pay off in unexpected ways.",
        "Material comfort and security are within reach.",
        "Trust your senses and enjoy life's simple pleasures."
    ],
    "Gemini": [
        "Communication is key today. Express yourself clearly.",
        "Your curiosity leads to interesting discoveries.",
        "Social connections bring new perspectives.",
        "Mental agility helps you solve complex problems.",
        "Versatility is your superpower today."
    ],
    "Cancer": [
        "Trust your intuition in emotional matters today.",
        "Home and family take priority. Nurture your relationships.",
        "Your caring nature attracts positive energy.",
        "Emotional depth leads to meaningful connections.",
        "Create a safe space for yourself and others."
    ],
    "Leo": [
        "Your natural charisma shines bright today.",
        "Creative projects flourish under your attention.",
        "Recognition for your efforts is coming soon.",
        "Leadership opportunities present themselves.",
        "Express your authentic self with confidence."
    ],
    "Virgo": [
        "Attention to detail serves you well today.",
        "Organize your thoughts and priorities for success.",
        "Your analytical skills solve important problems.",
        "Practical solutions emerge from careful planning.",
        "Service to others brings personal satisfaction."
    ],
    "Libra": [
        "Balance and harmony are your themes today.",
        "Diplomatic solutions work better than force.",
        "Beauty and art inspire your best decisions.",
        "Relationships require your gentle touch.",
        "Justice and fairness guide your actions."
    ],
    "Scorpio": [
        "Deep insights emerge from quiet reflection.",
        "Trust your powerful intuition today.",
        "Transformation brings positive changes.",
        "Hidden truths come to light.",
        "Emotional intensity leads to breakthroughs."
    ],
    "Sagittarius": [
        "Adventure and learning expand your horizons.",
        "Your optimism inspires others around you.",
        "New philosophies shape your worldview.",
        "Travel or exploration brings wisdom.",
        "Freedom and truth are your guiding stars."
    ],
    "Capricorn": [
        "Steady progress toward goals brings satisfaction.",
        "Your responsibility and discipline pay dividends.",
        "Professional matters require careful attention.",
        "Long-term planning ensures future success.",
        "Authority and respect come through dedication."
    ],
    "Aquarius": [
        "Innovation and originality set you apart today.",
        "Group activities bring unexpected benefits.",
        "Your unique perspective solves complex problems.",
        "Humanitarian causes call for your support.",
        "Technology and progress align with your vision."
    ],
    "Pisces": [
        "Your empathy and compassion guide important decisions.",
        "Creative inspiration flows freely today.",
        "Spiritual practices bring inner peace.",
        "Dreams and intuition reveal hidden wisdom.",
        "Emotional healing occurs through artistic expression."
    ]
}

LIFE_PATH_MEANINGS = {
    1: "The Leader - Independent, pioneering, and ambitious. You're meant to lead and innovate.",
    2: "The Cooperator - Diplomatic, sensitive, and peace-loving. You excel at partnerships.",
    3: "The Communicator - Creative, expressive, and optimistic. You inspire others with words.",
    4: "The Builder - Practical, disciplined, and hardworking. You create lasting foundations.",
    5: "The Adventurer - Freedom-loving, curious, and versatile. You thrive on variety.",
    6: "The Nurturer - Caring, responsible, and protective. You're drawn to help others.",
    7: "The Seeker - Analytical, spiritual, and introspective. You seek deeper truths.",
    8: "The Achiever - Ambitious, material-focused, and powerful. You're meant for success.",
    9: "The Humanitarian - Compassionate, generous, and wise. You serve humanity.",
    11: "The Intuitive - Master number. Highly sensitive and spiritually aware.",
    22: "The Master Builder - Master number. Capable of turning dreams into reality.",
    33: "The Master Teacher - Master number. Born to uplift and inspire humanity."
}

# Compatibility data
ELEMENT_COMPATIBILITY = {
    'Fire': ['Air', 'Fire'],
    'Earth': ['Water', 'Earth'], 
    'Air': ['Fire', 'Air'],
    'Water': ['Earth', 'Water']
}

ZODIAC_ELEMENTS = {
    'Aries': 'Fire', 'Leo': 'Fire', 'Sagittarius': 'Fire',
    'Taurus': 'Earth', 'Virgo': 'Earth', 'Capricorn': 'Earth',
    'Gemini': 'Air', 'Libra': 'Air', 'Aquarius': 'Air',
    'Cancer': 'Water', 'Scorpio': 'Water', 'Pisces': 'Water'
}

# Keyboard layouts
MAIN_KEYBOARD = [
    [f"{Emoji.BIRTHDAY} Set DOB", f"{Emoji.STAR} Today's Reading"],
    [f"{Emoji.NUMBERS} Numerology", f"{Emoji.CALENDAR} Date Facts"],
    [f"{Emoji.LOVE} Compatibility", f"{Emoji.DICE} Random Fact"],
    [f"{Emoji.MONEY} Support", f"{Emoji.QUESTION} Help"]
]

# Sample facts for database initialization
SAMPLE_FACTS = [
    (14, None, 'psychology',
     'People born on the 14th are often natural mediators with strong communication skills.'),
    (7, None, 'science',
     'The number 7 appears frequently in nature: 7 colors in rainbow, 7 notes in music scale.'),
    (21, None, 'psychology',
     'Those born on the 21st often possess leadership qualities and creative problem-solving abilities.'),
    (3, None, 'science',
     'The number 3 is fundamental in geometry - the minimum points needed to define a plane.'),
    (9, None, 'psychology',
     'People born on the 9th are often empathetic and drawn to humanitarian causes.'),
    (15, None, 'science',
     'The 15th day marks the middle of most months, representing balance and harmony.'),
    (1, 1, 'general',
     'January 1st: New Year\'s Day represents fresh starts and new possibilities worldwide.'),
    (25, 12, 'general',
     'December 25th: Christmas Day celebrates hope, giving, and family connections globally.'),
    (14, 2, 'general',
     'February 14th: Valentine\'s Day emphasizes love, relationships, and emotional connections.'),
    (31, 10, 'general',
     'October 31st: Halloween celebrates creativity, imagination, and facing our fears.'),
    (4, 7, 'general',
     'July 4th: Independence Day represents freedom, self-determination, and national pride.'),
    (22, None, 'numerology',
     'Master number 22 appears in birth dates of many architects and master builders throughout history.')
]