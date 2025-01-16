import re
from bson import ObjectId
from datetime import datetime

def validate_email_password(email, password, confirm_password):
    # Validate Email
    email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(email_pattern, email):
        return "Invalid email format."
    
    # Validate Passwords
    if password != confirm_password:
        return "The passwords aren't matching!"
    
    # Check if the password is at least 8 characters long
    elif len(password) < 8:
        return "The password must be at least 8 characters long."
    
    # Check if the password contains at least one uppercase letter
    elif not re.search(r'[A-Z]', password):
        return "The password must contain at least one uppercase letter."
    
    # Check if the password contains at least one lowercase letter
    elif not re.search(r'[a-z]', password):
        return "The password must contain at least one lowercase letter."
    
    # Check if the password contains at least one number
    elif not re.search(r'[0-9]', password):
        return "The password must contain at least one number."
    
    # Check if the password contains at least one special character
    elif not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return "The password must contain at least one special character."
    
    # If everything is valid
    return True
    
def extract_username(email):
    # Define a regular expression for validating an email
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    
    # Validate the email
    if re.match(email_regex, email):
        # Extract the username part before the '@'
        return email.split('@')[0]
    
    # Return None if the email is invalid
    return None

def serialize_dict(data: dict) -> dict:
    """
    Serializes a dictionary that may contain ObjectId and datetime instances, converting them to strings.

    Args:
        data (dict): The dictionary to serialize.

    Returns:
        dict: The serialized dictionary with ObjectId and datetime instances converted to strings.
    """
    def convert_objectid_and_datetime(value):
        if isinstance(value, ObjectId):
            return str(value)
        elif isinstance(value, datetime):
            return value.isoformat()  # Convert datetime to ISO 8601 string
        elif isinstance(value, list):
            return [str(x) if isinstance(x, ObjectId) else x for x in value]
        return value

    return {key: convert_objectid_and_datetime(value) for key, value in data.items()}

def deserialize_dict(data: dict) -> dict:
    """
    Deserializes a dictionary, converting ObjectId strings back to ObjectId instances
    and ISO 8601 strings back to datetime instances.

    Args:
        data (dict): The dictionary to deserialize.

    Returns:
        dict: The deserialized dictionary with ObjectId strings and ISO 8601 datetime strings converted back.
    """
    def convert_to_objectid_and_datetime(key, value):
        # Convert strings ending with '_id' back to ObjectId
        if key.endswith("id") and isinstance(value, str):
            return ObjectId(value)
        elif key.endswith("_id") and isinstance(value, str):
            return ObjectId(value)
        elif key.endswith("friends") and isinstance(value, list):
            return [ObjectId(v) for v in value]
        # Convert ISO 8601 strings back to datetime
        elif isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                pass
        return value

    return {key: convert_to_objectid_and_datetime(key, value) for key, value in data.items()}

def key_from_value(Data , value):
  key = next((k for k, v in Data.items() if v == value), None)
  return key 
