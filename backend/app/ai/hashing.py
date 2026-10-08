"""Perceptual hashes, stored as signed 64-bit integers so PostgreSQL BIGINT can hold them.
Two images whose hashes differ in only a few bits are (nearly) the same picture."""
import cv2
import imagehash
from PIL import Image

from .detector import load_bgr


def phash_int(image):
    img = load_bgr(image)
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    value = int(str(imagehash.phash(pil)), 16)          # unsigned 64-bit
    return value - (1 << 64) if value >= (1 << 63) else value


def hamming(a, b):
    return bin((a ^ b) & ((1 << 64) - 1)).count("1")


def is_flat(image, min_std=2.0):
    """A frame with almost no detail (lens covered, black, plain wall or sky). All such frames have
    nearly the same pHash, so they must not take part in the repeat check."""
    gray = cv2.cvtColor(load_bgr(image), cv2.COLOR_BGR2GRAY)
    return float(gray.std()) < min_std
