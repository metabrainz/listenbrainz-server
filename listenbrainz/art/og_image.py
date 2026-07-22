import io
import logging
import os.path
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests as req
from PIL import Image

logger = logging.getLogger(__name__)

OPENGRAPH_IMAGE_WIDTH = 1200
OPENGRAPH_IMAGE_HEIGHT = 630

# cover art takes up the left ~77% of the canvas,
# the rest is for the LB overlay branding
GRID_WIDTH = int(OPENGRAPH_IMAGE_WIDTH * 0.77)  # 924px

OVERLAY_PATH = os.path.join("/", "static", "img", "og-overlay.png")

# Timeout for downloading cover art images (seconds)
DOWNLOAD_TIMEOUT = 5

# Shared process-wide thread pool for downloading cover art.
# Caps total download threads regardless of request concurrency.
_OG_EXECUTOR = ThreadPoolExecutor(max_workers=8)

# Content-type allowlist for downloaded images
_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

# Maximum download size for cover art images (10 MB)
_MAX_DOWNLOAD_SIZE = 10 * 1024 * 1024


def _download_image(url, max_retries=1):
    """Grab an image from a URL, return as PIL Image or None if anything goes wrong.

    Uses streaming to avoid buffering large responses in memory, validates
    Content-Type against an allowlist, and enforces a max download size.
    Retries once on failure with a short backoff to handle transient
    archive.org errors (e.g. nginx 502/504).
    """
    for attempt in range(1 + max_retries):
        resp = None
        try:
            resp = req.get(url, timeout=DOWNLOAD_TIMEOUT, stream=True)
            resp.raise_for_status()

            content_type = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if content_type not in _ALLOWED_CONTENT_TYPES:
                logger.warning("Rejected cover art from %s: unexpected Content-Type %s", url, content_type)
                return None

            chunks = []
            bytes_read = 0
            for chunk in resp.iter_content(chunk_size=8192):
                bytes_read += len(chunk)
                if bytes_read > _MAX_DOWNLOAD_SIZE:
                    logger.warning("Cover art from %s exceeds max size (%d bytes), aborting", url, _MAX_DOWNLOAD_SIZE)
                    return None
                chunks.append(chunk)

            return Image.open(io.BytesIO(b"".join(chunks))).convert("RGBA")
        except Exception:
            if attempt < max_retries:
                time.sleep(1)
            else:
                logger.warning("Failed to download cover art from %s after %d attempt(s)", url, attempt + 1, exc_info=True)
        finally:
            if resp is not None:
                resp.close()
    return None


def _compose_single(cover):
    """Single cover art filling the left grid region, center-cropped to fit."""
    canvas = Image.new("RGBA", (OPENGRAPH_IMAGE_WIDTH, OPENGRAPH_IMAGE_HEIGHT), (0, 0, 0, 255))

    # aspect ratio math to cover the grid area
    ratio = cover.width / cover.height
    grid_ratio = GRID_WIDTH / OPENGRAPH_IMAGE_HEIGHT

    if ratio > grid_ratio:
        h = OPENGRAPH_IMAGE_HEIGHT
        w = int(OPENGRAPH_IMAGE_HEIGHT * ratio)
    else:
        w = GRID_WIDTH
        h = int(GRID_WIDTH / ratio)

    resized = cover.resize((w, h), Image.LANCZOS)

    # center-crop
    left = (w - GRID_WIDTH) // 2
    top = (h - OPENGRAPH_IMAGE_HEIGHT) // 2
    cropped = resized.crop((left, top, left + GRID_WIDTH, top + OPENGRAPH_IMAGE_HEIGHT))
    canvas.paste(cropped, (0, 0))
    return canvas


def _compose_grid_2x2(covers):
    """2x2 grid on the left ~77% of the canvas. Overlay sits on the right."""
    canvas = Image.new("RGBA", (OPENGRAPH_IMAGE_WIDTH, OPENGRAPH_IMAGE_HEIGHT), (0, 0, 0, 255))

    tile_w = GRID_WIDTH // 2
    tile_h = OPENGRAPH_IMAGE_HEIGHT // 2

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
        overlay = overlay.resize((OPENGRAPH_IMAGE_WIDTH, OPENGRAPH_IMAGE_HEIGHT), Image.LANCZOS)
    except Exception:
        logger.error("Failed to load OG overlay from %s", overlay_path, exc_info=True)
        return None

    if len(cover_urls) >= 4:
        # download cover art concurrently using the shared executor
        futures = [_OG_EXECUTOR.submit(_download_image, url) for url in cover_urls]
        downloaded = []
        for future in futures:
            try:
                # timeout accounts for _download_image's full retry window:
                # DOWNLOAD_TIMEOUT per attempt × 2 attempts + 1s backoff + 1s margin
                img = future.result(timeout=DOWNLOAD_TIMEOUT * 2 + 2)
            except Exception:
                img = None
            if img is not None:
                downloaded.append(img)

        if len(downloaded) >= 4:
            canvas = _compose_grid_2x2(downloaded[:4])
        elif downloaded:
            # couldn't get 4, just use the first one
            canvas = _compose_single(downloaded[0])
        else:
            return None
    else:
        # < 4 urls — try each URL until one download succeeds
        img = None
        for url in cover_urls:
            img = _download_image(url)
            if img is not None:
                break
        if img is None:
            return None
        canvas = _compose_single(img)

    # slap the overlay on top
    canvas = Image.alpha_composite(canvas, overlay)
    # drop the alpha channel. The overlay is already composited,
    # and PNG-without-alpha is smaller / friendlier to social-media crawlers
    # plus transparent pngs aren't supported by all social media platforms but RGB is
    canvas = canvas.convert("RGB")

    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    # Reset the file pointer to the beginning of the stream so the image data can be read
    buf.seek(0)
    return buf
