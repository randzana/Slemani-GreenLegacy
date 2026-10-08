"""A short plain-Kurdish description of each report photo, for crews and the dashboard.

template_description  always: built from the detector's counts, so it works with no internet.
ClaudeDescriber       optional (DESCRIBE_WITH_CLAUDE=1): a vision model looks at the photo and writes
                      one or two Sorani sentences. It runs in a background thread after the report is
                      saved, so the phone never waits; on any failure the template sentence stays.
"""
import base64
import logging
import threading
import time

import cv2
import psycopg

from ..strings import CLASS_NAMES, LEVEL_WORDS
from .detector import load_bgr

log = logging.getLogger(__name__)

SYSTEM = """You write for the municipality cleaning crews of Slemani (Sulaymaniyah) in the Kurdistan Region.
You get a citizen's photo of a littered spot and what the litter detector counted in it.
Write one or two short sentences in Central Kurdish (Sorani, Arabic script), at most 40 words:
what kind of waste is there, roughly how much, where it lies (roadside, park, beside a bin,
stream bank...), and what the crew should bring (a few bags, gloves, a truck...).
Use plain everyday words. No greeting, no list, no English words, no numbers in Latin digits.
Do not describe or guess anything about people, faces or vehicle plates in the photo.
If you see no litter at all, say that in one sentence."""


def kurdish_digits(value):
    return str(value).translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))


def template_description(classes, count, level):
    """'٨ پارچە پاشماوە دۆزرایەوە (٥ بوتڵ، ٣ کوپ). پلەی پیسی ٣ لە ٥ (زۆر).'"""
    top = sorted(classes.items(), key=lambda kv: (-kv[1], kv[0]))[:4]
    items = "، ".join(f"{kurdish_digits(n)} {CLASS_NAMES.get(name, name)}" for name, n in top)
    text = f"{kurdish_digits(count)} پارچە پاشماوە دۆزرایەوە"
    if items:
        text += f" ({items})"
    text += f". پلەی پیسی {kurdish_digits(level)} لە ٥ ({LEVEL_WORDS.get(level, '')})."
    if level >= 4:
        text += " پێویستی بە پاککردنەوەی خێرایە."
    return text


class ClaudeDescriber:
    """Asks Claude to look at the photo. Credentials come from the environment (ANTHROPIC_API_KEY)."""

    def __init__(self, model, timeout):
        import anthropic   # imported lazily: only needed when the feature is switched on
        self._anthropic = anthropic
        self.model = model
        self.client = anthropic.Anthropic(timeout=timeout, max_retries=1)

    @staticmethod
    def _jpeg_base64(image, max_side=1568):
        img = load_bgr(image)
        h, w = img.shape[:2]
        scale = max_side / max(h, w)
        if scale < 1:
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ok:
            raise ValueError("cannot encode image")
        return base64.standard_b64encode(buf.tobytes()).decode("ascii")

    def describe(self, photo, classes, count, level):
        anthropic = self._anthropic
        counted = ", ".join(f"{n} {name}" for name, n in sorted(classes.items())) or "nothing"
        try:
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=4096,
                # on a safety decline the API retries on Anthropic's recommended fallback model
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                output_config={"effort": "low"},
                system=SYSTEM,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                 "data": self._jpeg_base64(photo)}},
                    {"type": "text", "text": f"Detector: {count} litter items ({counted}); "
                                             f"dirtiness level {level} of 5. Write the description."},
                ]}],
            )
        except anthropic.AuthenticationError:
            log.warning("describe: the Anthropic API key is missing or invalid; keeping the template")
            return None
        except anthropic.RateLimitError:
            log.warning("describe: rate limited; keeping the template")
            return None
        except anthropic.APIStatusError as e:
            log.warning("describe: API error %s; keeping the template", e.status_code)
            return None
        except anthropic.APIConnectionError:
            log.warning("describe: no connection to the API (no internet in the hall?); keeping the template")
            return None
        except ValueError as e:
            log.warning("describe: %s", e)
            return None
        if response.stop_reason == "refusal":
            log.info("describe: declined (%s); keeping the template", response.stop_details)
            return None
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        return text or None


def make_describer(cfg):
    if not cfg.get("DESCRIBE_WITH_CLAUDE"):
        return None
    try:
        return ClaudeDescriber(cfg["DESCRIBE_MODEL"], cfg["DESCRIBE_TIMEOUT"])
    except ImportError:
        log.warning("DESCRIBE_WITH_CLAUDE=1 but the anthropic package is not installed")
        return None


def store(database_url, report_id, text, attempts=10):
    """Write the model's sentence over the template. The report row is committed when the request
    ends, which can be a moment after this thread starts, so try again briefly if it is not there."""
    for _ in range(attempts):
        try:
            with psycopg.connect(database_url) as conn:
                cur = conn.execute(
                    "UPDATE reports SET description = %s, description_source = 'claude' WHERE id = %s",
                    (text, report_id))
                if cur.rowcount:
                    return True
        except psycopg.Error as e:
            log.warning("describe: cannot store the description: %s", e)
            return False
        time.sleep(0.5)
    return False


def describe_later(app, report_id, photo, classes, count, level):
    """Start the model in the background; returns the thread (or None when the feature is off)."""
    describer = app.describer
    if describer is None:
        return None
    url = app.config["DATABASE_URL"]

    def work():
        try:
            text = describer.describe(photo, classes, count, level)
        except Exception:   # e.g. no credentials at all; the template sentence stays
            log.exception("describe: report %s failed; keeping the template", report_id)
            return
        if text:
            store(url, report_id, text)

    thread = threading.Thread(target=work, name=f"describe-{report_id}", daemon=True)
    thread.start()
    return thread
