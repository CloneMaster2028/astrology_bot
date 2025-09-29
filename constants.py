"""
Constants and message templates for Astrology Bot
"""

# Conversation states
SET_DOB_DAY = 1
SET_DOB_MONTH = 2
SET_DOB_YEAR = 3

# Main keyboard layout
MAIN_KEYBOARD = [
    ["🎂 Set DOB", "🌟 Today's Reading"],
    ["🔢 Numerology", "💕 Compatibility"],
    ["🎲 Zodiac Secret", "❓ Help"]
]

# Emoji constants
class Emoji:
    STAR = "⭐"
    HEART = "❤️"
    CALENDAR = "📅"
    CRYSTAL = "🔮"
    SPARKLES = "✨"
    CHECK = "✅"
    CROSS = "❌"
    THINKING = "🤔"
    CELEBRATING = "🎉"

# Message templates
class Messages:
    WELCOME = "Welcome! I'm your astrology bot. Set your birth date to get started!"
    DOB_NOT_SET = "Please set your birth date first using 'Set DOB'!"
    ERROR_GENERIC = "Something went wrong. Please try again."
    CANCELLED = "Operation cancelled!"

# Zodiac date ranges (month*100 + day format)
ZODIAC_DATES = {
    "Aries": (321, 419),
    "Taurus": (420, 520),
    "Gemini": (521, 620),
    "Cancer": (621, 722),
    "Leo": (723, 822),
    "Virgo": (823, 922),
    "Libra": (923, 1022),
    "Scorpio": (1023, 1121),
    "Sagittarius": (1122, 1221),
    "Capricorn": [(1222, 1231), (101, 119)],  # Spans year boundary
    "Aquarius": (120, 218),
    "Pisces": (219, 320)
}

# Horoscope templates for each zodiac sign
HOROSCOPE_TEMPLATES = {
    "Aries": [
        "Today brings new opportunities for leadership. Your bold energy attracts success.",
        "Channel your natural courage into creative projects. Others will follow your lead.",
        "A challenge today becomes tomorrow's triumph. Trust your instincts and take action."
    ],
    "Taurus": [
        "Stability and patience bring rewards today. Focus on building lasting foundations.",
        "Your practical nature guides you to wise decisions. Trust the process.",
        "Material and emotional security align favorably. Enjoy the simple pleasures."
    ],
    "Gemini": [
        "Communication flows effortlessly today. Share your ideas with confidence.",
        "Your curiosity opens new doors. Embrace learning and social connections.",
        "Versatility is your strength. Adapt to changes with your characteristic grace."
    ],
    "Cancer": [
        "Emotional intuition guides you true today. Trust your inner voice.",
        "Nurturing relationships brings deep satisfaction. Home and family shine.",
        "Your caring nature creates positive ripples. Others appreciate your support."
    ],
    "Leo": [
        "Your natural charisma draws admiration today. Shine brightly and inspire others.",
        "Creative expression brings joy and recognition. Share your talents generously.",
        "Leadership opportunities arise. Step forward with confidence and warmth."
    ],
    "Virgo": [
        "Attention to detail brings success today. Your analytical skills are valued.",
        "Practical solutions emerge from careful planning. Organization pays off.",
        "Your helpful nature makes a real difference. Service brings satisfaction."
    ],
    "Libra": [
        "Balance and harmony characterize your day. Relationships flourish.",
        "Your diplomatic skills resolve conflicts gracefully. Beauty surrounds you.",
        "Partnership brings mutual benefits. Cooperation leads to success."
    ],
    "Scorpio": [
        "Deep insights emerge today. Your intensity reveals hidden truths.",
        "Transformation is in the air. Embrace positive change with courage.",
        "Your passion and determination overcome obstacles. Trust your power."
    ],
    "Sagittarius": [
        "Adventure calls and you answer enthusiastically. Expand your horizons.",
        "Optimism and wisdom guide your path. Learning brings excitement.",
        "Freedom and exploration energize you. Follow your philosophical nature."
    ],
    "Capricorn": [
        "Disciplined effort brings tangible results. Your ambition is rewarded.",
        "Long-term goals come into focus. Patience and persistence pay off.",
        "Your practical wisdom guides others. Leadership through example."
    ],
    "Aquarius": [
        "Innovation and originality set you apart. Your ideas inspire change.",
        "Social connections bring unexpected opportunities. Community matters.",
        "Your independent spirit finds creative solutions. Think outside the box."
    ],
    "Pisces": [
        "Intuition and compassion guide you today. Trust your spiritual nature.",
        "Creative imagination flows freely. Artistic expression brings fulfillment.",
        "Your empathy creates deep connections. Dreams hold important messages."
    ]
}

# Life path number meanings
LIFE_PATH_MEANINGS = {
    1: "The Leader - Independent, ambitious, and pioneering. You're born to lead and innovate.",
    2: "The Peacemaker - Diplomatic, cooperative, and intuitive. You excel at bringing harmony.",
    3: "The Creative - Expressive, optimistic, and artistic. You inspire joy and creativity.",
    4: "The Builder - Practical, stable, and hardworking. You create lasting foundations.",
    5: "The Explorer - Adventurous, freedom-loving, and versatile. Change is your constant.",
    6: "The Nurturer - Responsible, caring, and family-oriented. You heal and protect others.",
    7: "The Seeker - Analytical, spiritual, and introspective. You seek deeper truths.",
    8: "The Powerhouse - Ambitious, authoritative, and materially successful. You manifest abundance.",
    9: "The Humanitarian - Compassionate, idealistic, and selfless. You serve the greater good.",
    11: "The Illuminator (Master Number) - Highly intuitive, inspiring, and spiritually aware. You bring enlightenment.",
    22: "The Master Builder (Master Number) - Visionary, practical genius, and manifesting great things. You build dreams into reality.",
    33: "The Master Teacher (Master Number) - Compassionate guide, healer, and uplifter. You teach through love and example."
}

# Zodiac elements
ZODIAC_ELEMENTS = {
    "Aries": "Fire",
    "Taurus": "Earth",
    "Gemini": "Air",
    "Cancer": "Water",
    "Leo": "Fire",
    "Virgo": "Earth",
    "Libra": "Air",
    "Scorpio": "Water",
    "Sagittarius": "Fire",
    "Capricorn": "Earth",
    "Aquarius": "Air",
    "Pisces": "Water"
}

# Element compatibility
ELEMENT_COMPATIBILITY = {
    "Fire": ["Fire", "Air"],      # Fire + Air = energy
    "Earth": ["Earth", "Water"],  # Earth + Water = growth
    "Air": ["Air", "Fire"],       # Air + Fire = energy
    "Water": ["Water", "Earth"]   # Water + Earth = growth
}

# Sample facts for the database (used during initialization)
SAMPLE_FACTS = [
    (1, None, "psychology", "People born on the 1st of any month tend to be natural leaders with strong independence."),
    (7, None, "psychology", "The 7th is associated with deep thinkers and those drawn to spirituality and analysis."),
    (15, None, "science", "The 15th day of the month is exactly halfway through most lunar cycles."),
    (21, None, "numerology", "21 reduces to 3 (2+1), the number of creativity and self-expression."),
    (None, None, "general", "Your birth date holds unique patterns that influence your personality traits."),
    (None, None, "numerology", "Master numbers 11, 22, and 33 are not reduced in numerology calculations."),
    (None, None, "psychology", "Birth order and date can create interesting correlations with personality development."),
    (None, None, "science", "Statistical studies show slight personality variations based on birth seasons."),
    (11, None, "numerology", "11 is a master number representing intuition and spiritual enlightenment."),
    (22, None, "numerology", "22 is the master builder number, representing the manifestation of dreams."),
    (3, None, "psychology", "Those born on the 3rd often possess strong communication skills and creativity."),
    (9, None, "numerology", "9 is the number of completion and humanitarian service in numerology.")
]