"""All user-facing Kurdish (Sorani) text in one place, so it is easy to fix on day two."""

REASONS = {
    # report
    "no_litter": "هیچ پاشماوەیەک لەم وێنەیەدا نەدۆزرایەوە",
    "reused_media": "ئەم وێنە یان ڤیدیۆیە پێشتر نێردراوە",
    "already_reported_by_you": "تۆ پێشتر ئەم شوێنەت ڕاپۆرت کردووە",
    "unreadable_image": "وێنەکە ناخوێندرێتەوە؛ دووبارە وێنە بگرە",
    "daily_cap": "گەیشتیتە سنووری ڕۆژانەی ڕاپۆرتی خاڵدار؛ ڕاپۆرتەکە تۆمار کرا بەڵام خاڵی نییە",
    "confirmed": "سوپاس! ئەم شوێنە پێشتر ڕاپۆرت کرابوو؛ پشتڕاستکردنەوەکەت تۆمار کرا",
    # claim
    "not_open": "ئەم شوێنە ئێستا ئامادە نییە بۆ پاککردنەوە",
    "self_cleanup_blocked": "ناتوانیت لە ماوەی ٢٤ کاتژمێردا شوێنێک پاک بکەیتەوە کە خۆت ڕاپۆرتت کردووە",
    # cleanup chain
    "challenge_invalid": "ڕێنماییەکە دروست نییە؛ دووبارە «من پاکی دەکەمەوە» دابگرە",
    "challenge_expired": "کاتی ڕێنماییەکە تەواو بوو؛ دووبارە هەوڵ بدەرەوە",
    "too_few_frames": "ڤیدیۆکە زۆر کورتە",
    "too_far": "تۆ لە شوێنی ڕاپۆرتەکەوە دووریت",
    "static_frames": "ئەمە ڤیدیۆ نییە؛ هەموو فریمەکان وەک یەکن",
    "instruction_not_followed": "ڕێنماییەکە جێبەجێ نەکرا: کۆدی QR ی زبڵدانەکە لە کاتی داواکراودا نەبینرا",
    "same_place_unsure": "دڵنیا نین هەمان شوێنە؛ بۆ پشکنینی مرۆیی نێردرا",
    "similar_to_earlier": "ئەم وێنانە زۆر لە وێنەیەکی پێشووی هەمان شوێن دەچن؛ بۆ پشکنینی مرۆیی نێردرا",
    "litter_partly_remaining": "هێشتا هەندێک پاشماوە ماوە؛ بۆ پشکنینی مرۆیی نێردرا",
    "litter_still_there": "پاشماوەکە هێشتا لە شوێنەکەدایە",
    "verified": "پاککردنەوەکە سەلمێنرا! سوپاس",
    "approved_by_staff": "پاککردنەوەکە لە لایەن شارەوانییەوە پەسەند کرا",
    "rejected_by_staff": "پاککردنەوەکە لە لایەن شارەوانییەوە ڕەت کرایەوە",
    # auth
    "phone_taken": "ئەم ژمارە مۆبایلە پێشتر تۆمار کراوە",
    "invalid_phone": "ژمارەی مۆبایل دروست نییە",
    "phone_not_allowed": "تەنها ژمارەی مۆبایلی عێراق قبووڵ دەکرێت",
    # email codes
    "invalid_email": "ئیمەیڵەکە دروست نییە",
    "otp_invalid": "کۆدەکە هەڵەیە",
    "otp_expired": "کاتی کۆدەکە بەسەرچووە؛ کۆدێکی نوێ داوا بکە",
    "otp_locked": "هەوڵی زۆر درا؛ کۆدێکی نوێ داوا بکە",
    "otp_too_soon": "تکایە چەند چرکەیەک چاوەڕێ بکە",
    "otp_rate_limited": "داواکاریی زۆر کرا؛ دواتر هەوڵ بدەرەوە",
    "otp_send_failed": "نەتوانرا ئیمەیڵەکە بنێردرێت؛ دواتر هەوڵ بدەرەوە",
    "bad_login": "ئیمەیڵ، ژمارە یان وشەی نهێنی هەڵەیە",
    "email_not_verified": "سەرەتا ئیمەیڵەکەت پشتڕاست بکەرەوە؛ ئەگەر کاتی زۆری برد، کۆدێکی نوێ داوا بکە",
    "email_taken": "ئەم ئیمەیڵە پێشتر تۆمار کراوە",
    "invalid_profile": "هەندێک زانیاری هەڵەیە یان کەمە؛ خانە دیاریکراوەکان بپشکنە",
    # Google
    "google_token_invalid": "چوونەژوورەوە بە Google سەرکەوتوو نەبوو",
    "google_email_unverified": "ئیمەیڵی هەژمارە Google ەکەت پشتڕاست نەکراوەتەوە",
    "google_unavailable": "ناتوانرێت پەیوەندی بە Google بکرێت؛ ئینتەرنێتەکەت بپشکنە",
    "google_disabled": "چوونەژوورەوە بە Google لەم سێرڤەرەدا چالاک نییە",
    "google_signup_expired": "کاتی خۆتۆمارکردنەکە بەسەرچوو؛ دووبارە بە Google بچۆرە ژوورەوە",
    "google_already_linked": "ئەم هەژمارە Google ە پێشتر بە هەژمارێکەوە بەستراوە",
    "missing_fields": "هەموو خانەکان پڕ بکەرەوە",
    "unauthorized": "کاتی چوونەژوورەوەکەت بەسەرچووە؛ دووبارە بچۆرە ژوورەوە",
    "forbidden": "ئەم بەشە تەنها بۆ شارەوانییە",
    "not_found": "ئەم شوێنە نەدۆزرایەوە",
    # points shop + daily tasks
    "unknown_reward": "ئەم خەڵاتە بوونی نییە",
    "not_enough_points": "خاڵی ئازادت بەس نییە بۆ ئەم خەڵاتە",
    "redeemed": "خەڵاتەکە وەرگیرا! کۆدەکە بە شارەوانی یان هاوبەشەکە پیشان بدە",
    "unknown_task": "ئەم ئەرکە بوونی نییە",
    "task_not_done": "ئەم ئەرکە هێشتا تەواو نەبووە",
    "task_already_claimed": "خەڵاتی ئەم ئەرکەت ئەمڕۆ وەرگرتووە",
    "task_claimed": "دەستخۆش! خاڵی ئەرکەکە دوای ٢٤ کاتژمێر ئازاد دەبێت",
    "voucher_used": "ئەم کۆدە پێشتر بەکارهاتووە یان بوونی نییە",
}

# The email with the sign-up code (app/otp.py); {code} and {minutes} are filled in
EMAIL_CODE_SUBJECT = "کۆدی پشتڕاستکردنەوەی GreenLegacy"
EMAIL_CODE_BODY = """سڵاو،

کۆدی پشتڕاستکردنەوەی ئیمەیڵەکەت: {code}

ئەم کۆدە بۆ {minutes} خولەک کار دەکات. ئەگەر تۆ داوات نەکردووە، ئەم ئیمەیڵە پشتگوێ بخە.

GreenLegacy سلێمانی
"""

# Kinds of business a person can register (codes in accounts.CATEGORIES)
CATEGORY_NAMES = {
    "restaurant": "چێشتخانە", "cafe": "کافێ", "shop": "دوکان", "supermarket": "سوپەرمارکێت",
    "bakery": "نانەواخانە", "hotel": "هوتێل", "workshop": "وەرشە", "other": "هی تر",
}

# Points shop: names and one-line descriptions (costs are in config.REWARDS)
REWARDS = {
    "cloth_bag": ("جانتای قوماش", "جانتایەکی قوماشی بۆ بازاڕکردن، لە جیاتی نایلۆن"),
    "bus_ticket": ("بلیتی پاس", "سەفەرێکی بێبەرامبەر بە پاسی ناو شار"),
    "park_coffee": ("قاوە لە پارک", "قاوەیەک لە کافێی پارکی ئازادی"),
    "tree": ("دارێک بە ناوی تۆ", "شارەوانی دارێک بە ناوی تۆ دەڕوێنێت"),
}

# Daily tasks: title shown in the app (targets and bonus are in config.DAILY_TASKS)
TASKS = {
    "report": "ڕاپۆرتی شوێنێکی پیس بکە",
    "confirm": "ڕاپۆرتی کەسێکی تر پشتڕاست بکەرەوە",
    "cleanup": "شوێنێک پاک بکەرەوە و بیسەلمێنە",
}

# Litter class names (YOLO / TACO / COCO) for the offline Kurdish description
CLASS_NAMES = {
    "bottle": "بوتڵ", "plastic bottle": "بوتڵی پلاستیک", "glass bottle": "بوتڵی شووشە",
    "cup": "کوپ", "paper cup": "کوپی کاغەز", "can": "قوتوو", "drink can": "قوتووی خواردنەوە",
    "plastic bag": "نایلۆن", "plastic bag & wrapper": "نایلۆن و بەرگ", "bag": "نایلۆن",
    "carton": "کارتۆن", "cardboard": "کارتۆن", "paper": "کاغەز", "plastic": "پلاستیک",
    "metal": "کانزا", "glass": "شووشە", "trash": "زبڵ", "cigarette": "جگەرە",
    "lid": "سەرقاپ", "bottle cap": "سەرقاپ", "straw": "قامیش", "styrofoam piece": "فلین",
    "wrapper": "بەرگ", "food": "پاشماوەی خواردن", "banana": "توێکڵی مۆز", "apple": "سێو",
    "orange": "پرتەقاڵ", "wine glass": "پەرداخ", "bowl": "قاپ", "fork": "چەتاڵ", "knife": "چەقۆ",
    "spoon": "کەوچک", "sandwich": "ساندویچ", "pizza": "پیتزا", "donut": "دۆنات",
    "red_item": "پارچەی سوور",
}

LEVEL_WORDS = {1: "کەم", 2: "مامناوەند", 3: "زۆر", 4: "زۆر زۆر", 5: "یەکجار پیس"}

INSTRUCTIONS = {
    "qr_first": "سەرەتا کۆدی QR ی زبڵدانەکە نیشان بدە، پاشان شوێنە پاککراوەکە",
    "qr_last": "سەرەتا شوێنە پاککراوەکە نیشان بدە، پاشان کۆدی QR ی زبڵدانەکە",
}


def reason(code):
    return REASONS.get(code, code)
