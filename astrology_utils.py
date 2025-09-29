"""
Astrology and numerology calculation utilities
"""
import random
import calendar
from datetime import date
from typing import Tuple
from constants import (
    HOROSCOPE_TEMPLATES, LIFE_PATH_MEANINGS,
    ZODIAC_ELEMENTS, ELEMENT_COMPATIBILITY
)


class AstrologyCalculator:
    """Handles all astrology and numerology calculations."""

    @staticmethod
    def get_zodiac_sign(birth_date: date) -> str:
        """Calculate zodiac sign from birth date with proper Capricorn handling."""
        month = birth_date.month
        day = birth_date.day

        # Zodiac date ranges with proper handling
        zodiac_ranges = [
            ((3, 21), (4, 19), "Aries"),
            ((4, 20), (5, 20), "Taurus"),
            ((5, 21), (6, 20), "Gemini"),
            ((6, 21), (7, 22), "Cancer"),
            ((7, 23), (8, 22), "Leo"),
            ((8, 23), (9, 22), "Virgo"),
            ((9, 23), (10, 22), "Libra"),
            ((10, 23), (11, 21), "Scorpio"),
            ((11, 22), (12, 21), "Sagittarius"),
            ((12, 22), (12, 31), "Capricorn"),
            ((1, 1), (1, 19), "Capricorn"),
            ((1, 20), (2, 18), "Aquarius"),
            ((2, 19), (3, 20), "Pisces"),
        ]

        for (start_month, start_day), (end_month, end_day), sign in zodiac_ranges:
            if (month == start_month and day >= start_day) or \
               (month == end_month and day <= end_day):
                return sign

        return "Capricorn"  # Fallback

    @staticmethod
    def calculate_life_path(birth_date: date) -> int:
        """Calculate life path number with proper reduction and master number preservation."""
        # Get full birth date as string of digits
        date_str = birth_date.strftime("%d%m%Y")

        # Sum all digits
        digit_sum = sum(int(digit) for digit in date_str)

        # Reduce while preserving master numbers (11, 22, 33)
        while digit_sum > 9 and digit_sum not in [11, 22, 33]:
            digit_sum = sum(int(digit) for digit in str(digit_sum))

        return digit_sum

    @staticmethod
    def get_life_path_calculation_steps(birth_date: date) -> str:
        """Get step-by-step calculation for life path number."""
        date_digits = birth_date.strftime("%d%m%Y")
        digit_sum = sum(int(d) for d in date_digits)

        calculation_steps = f"Birth date: {birth_date.strftime('%d/%m/%Y')}\n"
        calculation_steps += f"Add all digits: {' + '.join(date_digits)} = {digit_sum}\n"

        # Show reduction steps
        temp_sum = digit_sum
        while temp_sum > 9 and temp_sum not in [11, 22, 33]:
            temp_digits = [int(d) for d in str(temp_sum)]
            new_sum = sum(temp_digits)
            calculation_steps += f"Reduce: {' + '.join(map(str, temp_digits))} = {new_sum}\n"
            temp_sum = new_sum

        if temp_sum in [11, 22, 33]:
            calculation_steps += f"\nMaster Number: {temp_sum} (not reduced further)"
        else:
            calculation_steps += f"\nLife Path Number: {temp_sum}"

        return calculation_steps

    @staticmethod
    def get_horoscope(zodiac: str) -> str:
        """Get a random horoscope for the given zodiac sign."""
        templates = HOROSCOPE_TEMPLATES.get(
            zodiac,
            ["The stars are aligned in your favor today."]
        )
        return random.choice(templates)

    @staticmethod
    def generate_lucky_number(life_path: int, seed_date: date) -> int:
        """Generate a lucky number based on life path and date."""
        # Create a seed based on life path and date
        lucky_seed = life_path + seed_date.day + seed_date.month + (seed_date.year % 100)

        # Use modulo to keep in range 1-50
        lucky_number = ((lucky_seed * 7) % 50) + 1

        return lucky_number

    @staticmethod
    def get_life_path_meaning(life_path: int) -> str:
        """Get the meaning for a life path number."""
        return LIFE_PATH_MEANINGS.get(
            life_path,
            "Your path is unique and special, combining multiple influences."
        )

    @staticmethod
    def calculate_compatibility(user_zodiac: str, user_life_path: int,
                              other_zodiac: str, other_life_path: int) -> Tuple[int, int, int, str]:
        """
        Calculate compatibility between two people.
        Returns: (zodiac_score, numerology_score, overall_score, compatibility_level)
        """
        # Get elements
        user_element = ZODIAC_ELEMENTS.get(user_zodiac, 'Unknown')
        other_element = ZODIAC_ELEMENTS.get(other_zodiac, 'Unknown')

        # Element compatibility scoring
        compatible_elements = ELEMENT_COMPATIBILITY.get(user_element, [])

        # Zodiac score based on elements and same sign
        if user_zodiac == other_zodiac:
            zodiac_score = 90  # Same sign bonus
        elif other_element in compatible_elements:
            zodiac_score = 80  # Compatible elements
        else:
            zodiac_score = 60  # Different elements

        # Life path compatibility (similar numbers are more compatible)
        life_path_diff = abs(user_life_path - other_life_path)
        if life_path_diff == 0:
            numerology_score = 100  # Same life path
        elif life_path_diff <= 2:
            numerology_score = 85  # Very similar
        elif life_path_diff <= 4:
            numerology_score = 70  # Moderately similar
        else:
            numerology_score = 55  # Different paths

        # Overall compatibility (average of both scores)
        overall_score = (zodiac_score + numerology_score) // 2

        # Determine compatibility level with emoji
        if overall_score >= 85:
            compatibility_level = "Excellent ❤️"
        elif overall_score >= 70:
            compatibility_level = "Very Good 💖"
        elif overall_score >= 60:
            compatibility_level = "Good 💕"
        else:
            compatibility_level = "Challenging 💙"

        return zodiac_score, numerology_score, overall_score, compatibility_level

    @staticmethod
    def get_element(zodiac: str) -> str:
        """Get the element for a zodiac sign."""
        return ZODIAC_ELEMENTS.get(zodiac, 'Unknown')

    @staticmethod
    def is_compatible_element(element1: str, element2: str) -> bool:
        """Check if two elements are compatible."""
        compatible = ELEMENT_COMPATIBILITY.get(element1, [])
        return element2 in compatible

    @staticmethod
    def parse_date_input(date_text: str) -> date:
        """Parse date input in DD-MM-YYYY format."""
        try:
            parts = date_text.strip().split('-')
            if len(parts) != 3:
                raise ValueError("Invalid format. Use DD-MM-YYYY")

            day, month, year = map(int, parts)

            # Validate ranges
            if not (1 <= day <= 31):
                raise ValueError("Day must be between 1-31")
            if not (1 <= month <= 12):
                raise ValueError("Month must be between 1-12")
            if not (1900 <= year <= date.today().year):
                raise ValueError(f"Year must be between 1900-{date.today().year}")

            return date(year, month, day)

        except ValueError as e:
            raise ValueError(f"Invalid date: {e}")
    
    @staticmethod
    def validate_birth_date(day: int, month: int, year: int) -> date:
        """Validate and create birth date."""
        try:
            birth_date = date(year, month, day)
            
            # Check if date is not in the future
            if birth_date > date.today():
                raise ValueError("Birth date cannot be in the future")
            
            # Check reasonable age limits
            current_year = date.today().year
            if year < 1900:
                raise ValueError("Please enter a year after 1900")
            if current_year - year > 120:
                raise ValueError("Please enter a more recent birth year")
            
            return birth_date
            
        except ValueError as e:
            if "day is out of range for month" in str(e):
                month_name = calendar.month_name[month]
                max_day = calendar.monthrange(year, month)[1]
                raise ValueError(f"{month_name} {year} only has {max_day} days")
            raise
    
    @staticmethod
    def get_zodiac_info(zodiac: str) -> dict:
        """Get comprehensive information about a zodiac sign."""
        element = ZODIAC_ELEMENTS.get(zodiac, 'Unknown')
        compatible_elements = ELEMENT_COMPATIBILITY.get(element, [])
        
        # Find compatible zodiac signs
        compatible_signs = [
            sign for sign, elem in ZODIAC_ELEMENTS.items()
            if elem in compatible_elements and sign != zodiac
        ]
        
        return {
            'sign': zodiac,
            'element': element,
            'compatible_elements': compatible_elements,
            'compatible_signs': compatible_signs,
            'templates': HOROSCOPE_TEMPLATES.get(zodiac, [])
        }
    
    @staticmethod
    def get_numerology_info(life_path: int) -> dict:
        """Get comprehensive numerology information."""
        is_master = life_path in [11, 22, 33]
        
        return {
            'number': life_path,
            'is_master': is_master,
            'meaning': LIFE_PATH_MEANINGS.get(life_path, "Unique path"),
            'type': 'Master Number' if is_master else 'Life Path Number'
        }