import io
import logging
from pathlib import Path

import requests as req
from PIL import Image

logger = logging.getLogger(__name__)

OG_WIDTH = 1280
OG_HEIGHT = 640

# cover art takes up the left ~72% of the canvas,
# the rest is for the LB overlay branding
GRID_WIDTH = int(OG_WIDTH * 0.72)  # 921px

OVERLAY_PATH = Path(__file__).resolve().parent.parent.parent / "frontend" / "img" / "og-overlay.png"

# Timeout for downloading cover art images (seconds)
DOWNLOAD_TIMEOUT = 5


def _download_image(url):
    """Grab an image from a URL, return as PIL Image or None if anything goes wrong."""
    try:
        resp = req.get(url, timeout=DOWNLOAD_TIMEOUT)
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content)).convert("RGBA")
    except Exception:
        logger.warning("Failed to download cover art from %s", url, exc_info=True)
        return None


def _compose_single(cover):
    """Single cover art filling the left grid region, center-cropped to fit."""
    canvas = Image.new("RGBA", (OG_WIDTH, OG_HEIGHT), (0, 0, 0, 255))

    # aspect ratio math to cover the grid area
    ratio = cover.width / cover.height
    grid_ratio = GRID_WIDTH / OG_HEIGHT

    if ratio > grid_ratio:
        h = OG_HEIGHT
        w = int(OG_HEIGHT * ratio)
    else:
        w = GRID_WIDTH
        h = int(GRID_WIDTH / ratio)

    resized = cover.resize((w, h), Image.LANCZOS)

    # center-crop
    left = (w - GRID_WIDTH) // 2
    top = (h - OG_HEIGHT) // 2
    cropped = resized.crop((left, top, left + GRID_WIDTH, top + OG_HEIGHT))
    canvas.paste(cropped, (0, 0))
    return canvas


def _compose_grid_2x2(covers):
    """2x2 grid on the left ~72% of the canvas. Overlay sits on the right."""
    canvas = Image.new("RGBA", (OG_WIDTH, OG_HEIGHT), (0, 0, 0, 255))

    tile_w = GRID_WIDTH // 2
    tile_h = OG_HEIGHT // 2

    positions = [
        (0, 0),
        (tile_w, 0),
        (0, tile_h),
        (tile_w, tile_h),
    ]

    for img, (x, y) in zip(covers, positions):
        ratio = img.width / img.height
        tile_ratio = tile_w / tile_h

        if ratio > tile_ratio:
            h = tile_h
            w = int(tile_h * ratio)
        else:
            w = tile_w
            h = int(tile_w / ratio)

        resized = img.resize((w, h), Image.LANCZOS)
        left = (w - tile_w) // 2
        top = (h - tile_h) // 2
        cropped = resized.crop((left, top, left + tile_w, top + tile_h))
        canvas.paste(cropped, (x, y))

    return canvas


def generate_playlist_og_image(cover_urls: list[str], overlay_path: str | Path | None = None) -> io.BytesIO | None:
    """Generate a composed OG image for a playlist.

    Args:
        cover_urls: List of cover art image URLs. If 4+, uses a 2x2 grid.
                        If 1-3, uses just the first image. If empty, returns None.
        overlay_path: Path to the LB overlay PNG. Defaults to OVERLAY_PATH.

    Returns a BytesIO with the PNG, or None if something fails.
    """
    if not cover_urls:
        return None

    if overlay_path is None:
        overlay_path = OVERLAY_PATH

    # load the overlay
    try:
        overlay = Image.open(overlay_path).convert("RGBA")
        overlay = overlay.resize((OG_WIDTH, OG_HEIGHT), Image.LANCZOS)
    except Exception:
        logger.error("Failed to load OG overlay from %s", overlay_path, exc_info=True)
        return None

    if len(cover_urls) >= 4:
        # try to get all 4 for the grid
        downloaded = []
        for url in cover_urls[:4]:
            img = _download_image(url)
            if img is not None:
                downloaded.append(img)

        if len(downloaded) == 4:
            canvas = _compose_grid_2x2(downloaded)
        elif downloaded:
            # couldn't get all 4, just use the first one
            canvas = _compose_single(downloaded[0])
        else:
            return None
    else:
        # < 4 urls, just use the first
        img = _download_image(cover_urls[0])
        if img is None:
            return None
        canvas = _compose_single(img)

    # slap the overlay on top
    canvas = Image.alpha_composite(canvas, overlay)
    canvas = canvas.convert("RGB")

    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
