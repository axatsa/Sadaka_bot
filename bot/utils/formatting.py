
def format_number(number: int | float) -> str:
    """Format number with spaces as thousand separators"""
    if number is None:
        return "0"
    return f"{int(number):,}".replace(",", " ")

def parse_amount(text: str) -> int:
    """Parse amount from text, handling spaces and commas"""
    if not text:
        raise ValueError("Empty text")
    
    # Remove spaces
    clean_text = text.replace(" ", "")
    # Replace comma with dot
    clean_text = clean_text.replace(",", ".")
    
    # Convert to float first to handle decimals, then int
    try:
        val = float(clean_text)
        return int(val)
    except ValueError:
        raise ValueError("Invalid number format")
