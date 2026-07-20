import re
from rest_framework.exceptions import ValidationError

# Regex compile for common contact patterns
PHONE_REGEX = re.compile(
    r'(?:'
    r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}' # Standard phone numbers
    r'|'
    r'(?:\d[-.\s]?){9,11}\d'                                   # Spaces/hyphens between digits (e.g. 9 8 7 6 5 4 3 2 1 0)
    r')'
)

EMAIL_REGEX = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
)

UPI_REGEX = re.compile(
    r'[a-zA-Z0-9.\-_]{2,256}@(axl|ybl|okaxis|okhdfcbank|okicici|paytm|barodampay|upi|yapi)'
)

# Detect social links or keywords implying contact bypass
SOCIAL_URLS_REGEX = re.compile(
    r'(wa\.me|t\.me|instagram\.com|facebook\.com|fb\.me|twitter\.com|linkedin\.com)',
    re.IGNORECASE
)

# Textual representations of numbers to bypass digit checks (e.g. "nine double-eight seven...")
SPELLED_NUMBERS = [
    'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
    'double', 'triple', 'contact', 'call me', 'whatsapp', 'number is', 'ph no', 'phone no'
]


def check_anti_bypass_text(text: str) -> bool:
    """
    Checks if a string contains contact details (Phone, Email, UPI, Social links).
    Returns True if contact details are found, False otherwise.
    """
    if not text:
        return False
    
    # 1. Regex checks
    if PHONE_REGEX.search(text):
        return True
    if EMAIL_REGEX.search(text):
        return True
    if UPI_REGEX.search(text):
        return True
    if SOCIAL_URLS_REGEX.search(text):
        return True
        
    # 2. Text clean check for spelled out numbers
    cleaned_text = text.lower().replace(" ", "").replace("-", "").replace(".", "")
    
    # Check for consecutive spelling matches (e.g., 'nineseeveneight...')
    spelled_digit_mapping = {
        'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
        'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9'
    }
    
    # Extract digit words
    words = re.findall(r'[a-zA-Z]+', text.lower())
    numeric_sequence = ""
    for w in words:
        if w in spelled_digit_mapping:
            numeric_sequence += spelled_digit_mapping[w]
            
    if len(numeric_sequence) >= 8:  # Likely a spelled phone number
        return True
        
    return False


def validate_clean_message(text: str, field_name: str = "description"):
    """
    Validation utility for Django Rest Framework serializers.
    """
    if check_anti_bypass_text(text):
        raise ValidationError({
            field_name: "Sharing contact details (phone numbers, email, UPI IDs, or links) before a confirmed booking is prohibited to protect platform safety."
        })
    return text
