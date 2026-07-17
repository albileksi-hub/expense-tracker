"""Receipt scanning: turn a photo of a receipt into expense fields using Claude.

The web app calls extract_receipt() with an uploaded image. If an Anthropic API
key is configured, Claude reads the receipt and returns the amount, date, a
guessed category, and the merchant. If it isn't configured (or the call fails),
we raise ReceiptError so the caller can fall back to a manual review form —
the feature still works, you just type the fields in yourself.
"""

import base64
import io
import json
import os

import anthropic
from PIL import Image

# The skill's guidance: default to Claude Opus 4.8 unless the user picks another
# model. Swap this for "claude-haiku-4-5" if you want cheaper, faster scans.
MODEL = "claude-opus-4-8"

MAX_IMAGE_EDGE = 2000  # px on the long side — plenty for reading receipt text

_PROMPT = (
    "This is a photo of a purchase receipt. Extract the expense details. "
    "For the total, use the final amount paid (after tax and tip), not a subtotal. "
    "Infer a short lowercase spending category from the merchant (e.g. groceries, "
    "food, transport, shopping). Use an empty string for anything you can't read."
)

# All fields are required strings; the model returns "" when a value is unreadable.
# Strings (rather than nullable numbers) keep the JSON schema simple and robust.
_SCHEMA = {
    "type": "object",
    "properties": {
        "amount": {"type": "string", "description": "final total as a plain number, e.g. 24.50"},
        "date": {"type": "string", "description": "purchase date as YYYY-MM-DD"},
        "category": {"type": "string", "description": "short lowercase spending category"},
        "merchant": {"type": "string", "description": "the store or merchant name"},
    },
    "required": ["amount", "date", "category", "merchant"],
    "additionalProperties": False,
}


class ReceiptError(Exception):
    """Raised when a receipt can't be scanned automatically."""


def is_configured() -> bool:
    """True when an Anthropic API key is available for auto-extraction."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def prepare_image(file_stream) -> tuple[str, str]:
    """Read an uploaded image, downscale it, and return (base64, media_type)."""
    try:
        image = Image.open(file_stream)
        image = image.convert("RGB")
    except Exception:
        raise ReceiptError("That doesn't look like a readable image — try a JPG or PNG.")

    longest = max(image.size)
    if longest > MAX_IMAGE_EDGE:
        scale = MAX_IMAGE_EDGE / longest
        image = image.resize((round(image.width * scale), round(image.height * scale)))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return base64.standard_b64encode(buffer.getvalue()).decode(), "image/jpeg"


def extract_receipt(image_b64: str, media_type: str) -> dict:
    """Ask Claude to read the receipt. Returns {amount, date, category, note}."""
    if not is_configured():
        raise ReceiptError(
            "Automatic scanning isn't turned on — set the ANTHROPIC_API_KEY "
            "environment variable to enable it.")

    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": image_b64},
                    },
                    {"type": "text", "text": _PROMPT},
                ],
            }],
        )
    except anthropic.APIError as err:
        raise ReceiptError(f"Couldn't reach the receipt reader: {err}")

    if response.stop_reason == "refusal":
        raise ReceiptError("The receipt couldn't be processed. Enter the details manually.")

    text = next((block.text for block in response.content if block.type == "text"), "")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise ReceiptError("Couldn't read the receipt clearly. Enter the details manually.")

    return {
        "amount": data.get("amount", ""),
        "date": data.get("date", ""),
        "category": data.get("category", ""),
        "note": data.get("merchant", ""),
    }
