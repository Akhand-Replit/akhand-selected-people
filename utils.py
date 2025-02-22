import base64
from PIL import Image
import io
import requests
import os
from pdf2image import convert_from_bytes
from typing import List, Optional, Dict

def upload_to_imgbb(image_data: bytes, name: str = "image") -> Optional[str]:
    """Upload an image to ImgBB and return the URL"""
    try:
        api_key = os.environ.get('IMGBB_API_KEY')
        if not api_key:
            raise ValueError("ImgBB API key not found")

        url = "https://api.imgbb.com/1/upload"
        payload = {
            "key": api_key,
            "image": base64.b64encode(image_data).decode('utf-8'),
            "name": name
        }

        response = requests.post(url, payload)
        response.raise_for_status()

        return response.json()['data']['url']
    except Exception as e:
        print(f"Error uploading image to ImgBB: {str(e)}")
        return None

def load_image(image_file) -> Optional[Dict]:
    """Process uploaded image file"""
    if image_file is None:
        return None

    try:
        img = Image.open(image_file)
        # Resize image to a reasonable size
        max_size = (800, 800)
        img.thumbnail(max_size, Image.LANCZOS)

        # Convert to bytes
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        image_bytes = buffered.getvalue()

        # Upload to ImgBB
        image_url = upload_to_imgbb(image_bytes, image_file.name)

        return {
            'url': image_url,
            'preview_data': base64.b64encode(image_bytes).decode()
        } if image_url else None

    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return None

def process_pdf(pdf_file) -> List[str]:
    """Convert PDF to images and upload to ImgBB"""
    try:
        # Read PDF file
        pdf_bytes = pdf_file.read()

        # Convert PDF pages to images
        images = convert_from_bytes(pdf_bytes)

        # Upload each page
        image_urls = []
        for i, image in enumerate(images):
            # Convert PIL Image to bytes
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            image_bytes = buffered.getvalue()

            # Upload to ImgBB
            image_url = upload_to_imgbb(image_bytes, f"{pdf_file.name}_page_{i+1}")
            if image_url:
                image_urls.append(image_url)

        return image_urls

    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        return []

def display_image(image_data: str) -> str:
    """Display base64 image in Streamlit"""
    if image_data:
        return f'<img src="data:image/png;base64,{image_data}" style="max-width: 200px;">'
    return None