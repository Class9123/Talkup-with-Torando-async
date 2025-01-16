import cloudinary
import cloudinary.uploader
import cloudinary.api
import base64
from io import BytesIO
from PIL import Image
from values import CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_SECRET_KEY

# Cloudinary configuration
cloudinary.config(
    cloud_name=CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_SECRET_KEY
)

def upload_image(image_data):

    if image_data.startswith('data:image'):
        image_data = image_data.split(',')[1]

    image_bytes = base64.b64decode(image_data)
    response = cloudinary.uploader.upload(
        BytesIO(image_bytes),
        resource_type="auto"  # auto determines if it's an image or video
    )
    print("Uploaded Image URL:", response.get("secure_url"))
    return str(response.get("secure_url"))
