from os import getenv
from dotenv import load_dotenv
load_dotenv()

DEV_MONGO_URI = getenv("DEV_MONGO_URI")
DB_NAME = getenv("DB_NAME")
CLOUD_NAME = getenv("CLOUD_NAME")
CLOUDINARY_API_KEY = getenv("CLOUDINARY_API_KEY")
CLOUDINARY_SECRET_KEY = getenv("CLOUDINARY_SECRET_KEY")

