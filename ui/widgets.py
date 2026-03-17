from io import BytesIO
from urllib.request import urlopen

import customtkinter as ctk
from PIL import Image, ImageDraw

from core.constants import APP_VERSION


def make_placeholder_thumbnail(size=(220, 124)) -> Image.Image:
    """Placeholder Nexus — fondo negro, borde rojo, sin texto."""
    img = Image.new("RGB", size, color=(10, 10, 10))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, size[0] - 1, size[1] - 1), outline=(230, 51, 51), width=1)
    return img


def make_splash_image(size=(360, 180)) -> Image.Image:
    """Splash screen Nexus — fondo negro, acento rojo."""
    img = Image.new("RGB", size, color=(8, 8, 8))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        (12, 12, size[0] - 12, size[1] - 12),
        radius=4, outline=(230, 51, 51), width=2
    )
    # Triángulo play estilo Nexus
    draw.polygon([(52, 56), (52, 120), (106, 88)], fill=(230, 51, 51))
    draw.text((122, 56), "NovaDL", fill=(255, 255, 255))
    draw.text((122, 94), f"v{APP_VERSION}", fill=(85, 85, 85))
    return img


def load_thumbnail_from_url(image_url: str, size=(220, 124)) -> Image.Image | None:
    """
    Descarga y retorna una imagen PIL desde una URL.
    Retorna None si falla (la UI mostrará el placeholder).
    """
    if not image_url:
        return None
    try:
        with urlopen(image_url, timeout=10) as response:
            data = response.read()
        return Image.open(BytesIO(data)).convert("RGB")
    except Exception:
        return None


def make_ctk_thumbnail(img: Image.Image | None, size=(220, 124)) -> ctk.CTkImage:
    """Convierte una imagen PIL en CTkImage, usando el placeholder Nexus si img es None."""
    source = img if img is not None else make_placeholder_thumbnail(size)
    return ctk.CTkImage(light_image=source, dark_image=source, size=size)
