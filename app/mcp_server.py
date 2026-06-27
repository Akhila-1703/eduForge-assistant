# ruff: noqa
import logging
from mcp.server.fastmcp import FastMCP

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("eduforge-helper-tools")

@mcp.tool()
def get_study_tips(style: str) -> str:
    """Gets study tips tailored to a student's learning style.

    Args:
        style: The learning style (visual, auditory, kinesthetic, read_write).
    """
    style_clean = style.lower().strip()
    logger.info(f"get_study_tips tool called for style: {style_clean}")
    
    tips = {
        "visual": (
            "💡 Visual Learner Tips:\n"
            "1. Use mind maps and color-coded diagrams to represent connections between ideas.\n"
            "2. Replace words with symbols, icons, or quick sketches where possible.\n"
            "3. Watch instructional videos or animations to visualize abstract processes.\n"
            "4. Use flashcards with drawings or diagrams alongside text."
        ),
        "auditory": (
            "🔊 Auditory Learner Tips:\n"
            "1. Read your notes, textbooks, or summaries aloud to reinforce learning.\n"
            "2. Explain the concepts you are studying to a friend, family member, or even out loud to yourself.\n"
            "3. Record yourself reading key points and listen to them while walking or doing chores.\n"
            "4. Participate in group discussions and ask questions to talk through problems."
        ),
        "read_write": (
            "📝 Reading & Writing Learner Tips:\n"
            "1. Rewrite your notes in your own words to process the information.\n"
            "2. Write summaries of each chapter or study block in bullet points.\n"
            "3. Create lists, Glossaries, and fill-in-the-blank practice sheets.\n"
            "4. Read through handouts and write key definitions repeatedly."
        ),
        "kinesthetic": (
            "🏃 Kinesthetic Learner Tips:\n"
            "1. Take frequent short study breaks (e.g., study 25 mins, walk 5 mins).\n"
            "2. Stand up or pace while reading notes or listening to lecture recordings.\n"
            "3. Use physical objects or index cards that you can shuffle and organize physically.\n"
            "4. Relate concepts to physical actions or real-life activities that require movement."
        )
    }
    
    return tips.get(
        style_clean, 
        f"Unknown style '{style}'. Please choose from: visual, auditory, read_write, or kinesthetic.\nHere is a general tip: Use the Pomodoro Technique (25 minutes of focused work followed by a 5-minute break) to keep your energy high!"
    )

@mcp.tool()
def create_mnemonic(terms_csv: str) -> str:
    """Generates simple, memorable mnemonic phrases for a list of words or terms.

    Args:
        terms_csv: A comma-separated list of terms (e.g., 'Kingdom, Phylum, Class, Order').
    """
    logger.info(f"create_mnemonic tool called for terms: {terms_csv}")
    terms = [t.strip() for t in terms_csv.split(",") if t.strip()]
    if not terms:
        return "Please provide a valid list of terms."

    first_letters = [t[0].upper() for t in terms]
    
    # Pre-coded quality mnemonics for common sequences
    if first_letters == ["K", "P", "C", "O", "F", "G", "S"]:
        return "✨ Mnemonic for Taxonomy Ranks (Kingdom, Phylum, Class, Order, Family, Genus, Species):\n👉 'Kids Prefer Cheese Over Fried Green Spinach'"
    elif first_letters == ["M", "V", "E", "M", "J", "S", "U", "N"]:
        return "✨ Mnemonic for Planets (Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune):\n👉 'My Very Educated Mother Just Served Us Noodles'"

    # Generic generator
    words_dict = {
        "A": "Awesome", "B": "Brilliant", "C": "Clever", "D": "Daring", "E": "Excellent",
        "F": "Friendly", "G": "Great", "H": "Happy", "I": "Interesting", "J": "Jolly",
        "K": "Kind", "L": "Lively", "M": "Merry", "N": "Nice", "O": "Outstanding",
        "P": "Perfect", "Q": "Quick", "R": "Ready", "S": "Super", "T": "Talented",
        "U": "Useful", "V": "Vibrant", "W": "Wonderful", "X": "Xenial", "Y": "Young",
        "Z": "Zealous"
    }
    
    phrase = []
    for letter in first_letters:
        phrase.append(words_dict.get(letter, letter))
        
    generated_phrase = " ".join(phrase)
    return (
        f"✨ Generated Mnemonic for first letters ({', '.join(first_letters)}):\n"
        f"👉 '{generated_phrase}'\n"
        f"💡 Tip: Create your own funny phrase where each word starts with the same letters!"
    )

@mcp.tool()
def simplify_formula(formula: str) -> str:
    """Explains a scientific or mathematical formula, breaking down variables and showing a real-world use.

    Args:
        formula: The formula string (e.g., 'F=ma', 'E=mc^2', 'A=lw').
    """
    f_clean = formula.replace(" ", "").lower()
    logger.info(f"simplify_formula tool called for: {f_clean}")

    formulas = {
        "f=ma": (
            "⚙️ Formula: F = ma (Newton's Second Law of Motion)\n"
            "🔍 Breakdown:\n"
            "  • F = Force (measured in Newtons)\n"
            "  • m = Mass (measured in kilograms)\n"
            "  • a = Acceleration (measured in meters per second squared)\n"
            "🌍 Real-World Example:\n"
            "  If you push a heavy supermarket cart (high mass) versus an empty one (low mass) "
            "  with the same strength (force), the empty cart will speed up (accelerate) much faster."
        ),
        "e=mc^2": (
            "⚛️ Formula: E = mc² (Einstein's Mass-Energy Equivalence)\n"
            "🔍 Breakdown:\n"
            "  • E = Energy (measured in Joules)\n"
            "  • m = Mass (measured in kilograms)\n"
            "  • c = Speed of light in a vacuum (approx. 300,000,000 meters per second)\n"
            "🌍 Real-World Example:\n"
            "  This explains why nuclear power plants can generate massive amounts of energy "
            "  from a very tiny amount of fuel (mass) because the mass is multiplied by the speed of light squared, which is a huge number!"
        ),
        "a=lw": (
            "📐 Formula: A = lw (Area of a Rectangle)\n"
            "🔍 Breakdown:\n"
            "  • A = Area (total surface space)\n"
            "  • l = Length (how long it is)\n"
            "  • w = Width (how wide it is)\n"
            "🌍 Real-World Example:\n"
            "  If you want to buy a rug for a room that is 5 meters long and 4 meters wide, "
            "  you multiply 5 by 4 to get 20 square meters of rug needed."
        )
    }

    return formulas.get(
        f_clean,
        f"Formula '{formula}' is not pre-packaged. Here is a general breakdown:\n"
        f"Remember, formulas represent how different quantities relate. Look up the definition of each letter "
        f"and try to think of what increases or decreases when other parts of the equation change."
    )

if __name__ == "__main__":
    mcp.run()
