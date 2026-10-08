# GreenLegacy Slemani — وەشانی ڕاهێنان

> **⚠️ ئەم ڕیپۆیە تەنها بۆ ڕاهێنانە، نەک بۆ هاکاسۆنەکە.**
> یاسای هاکاسۆنەکە دەڵێت هەر شتێک پێشکەش دەکرێت دەبێت لە ٨ و ٩ی تشرینی یەکەم دروست کرابێت.
> بەیانیی ٨ی تشرین ڕیپۆیەکی **نوێ و بەتاڵ** دروست بکەن و **هیچ** فایلێک لێرەوە کۆپی مەکەن.
> ئەم کۆدە بۆ ئەوەیە پێشوەختە فێری ئامرازەکان و ئەو هەڵانە ببن کە ڕوو دەدەن، و کاتی هەر بەشێک بپێون.

خولەکە: هاوڵاتی وێنەی شوێنێکی پیس دەگرێت ← YOLOv8 پاشماوەکە دەژمێرێت و پلەی پیسی ١ بۆ ٥ دادەنێت ←
شوێنەکە لەسەر نەخشەی شارەوانی دەردەکەوێت ← کەسێکی تر پاکی دەکاتەوە و بە ڕێنماییەکی هەڕەمەکی ڤیدیۆی «دوا» تۆمار دەکات ←
AI دەیسەلمێنێت ← شوێنەکە سەوز دەبێت و خاڵ دەدرێت.

## ناوەڕۆک

```
backend/                 Flask API + YOLOv8 + PostgreSQL/PostGIS (یەک پرۆسە، لەسەر لاپتۆپ)
  app/
    routes.py            ڕاپۆرت، claim، cleanup، leaderboard، me
    admin.py             کۆتاییەکانی شارەوانی + لاپەڕەی داشبۆرد
    points.py            یاساکانی خاڵ (ledger، ٢٤ کاتژمێر ڕاگرتن، سنووری ڕۆژانە)
    ai/detector.py       YOLOv8 (و ColorBlobDetector تەنها بۆ تاقیکردنەوە)
    ai/verify.py         زنجیرەی سەلماندن: ڤیدیۆی ڕاستەقینە ← QR ← هەمان شوێن ← پاشماوە نەماوە
    simulator.py         کامێرای ساختە بۆ سیمولەیتەر (تەنها لەگەڵ colorblob)
    strings.py           هەموو دەقە کوردییەکان
    templates/dashboard.html   داشبۆردی شارەوانی (نەخشە، ئەولەویەت، تۆمار، پشکنین)
  schema.sql             شەش خشتە
  tests/                 ٢٣ تاقیکردنەوە بەسەر PostGIS ی ڕاستەقینەدا
  tools/rehearse.py      هەموو خولەکە لەسەر سێرڤەرێکی کاراوە تاقی دەکاتەوە
  tools/make_qr_stickers.py  ستیکەری QR بۆ زبڵدانەکان چاپ دەکات
mobile/                  ئەپی Flutter ی هاوڵاتی (کوردی، ڕاست بۆ چەپ)
```

## ١. سێرڤەر (لاپتۆپ)

پێویستییەکان: Python 3.11، PostgreSQL لەگەڵ PostGIS.

```bash
# داتابەیس (یەک جار)
psql -U postgres -c "CREATE ROLE gl LOGIN PASSWORD 'gl';"
psql -U postgres -c "CREATE DATABASE greenlegacy OWNER gl;"
psql -U postgres -c "CREATE DATABASE greenlegacy_test OWNER gl;"
psql -U postgres -d greenlegacy -c "CREATE EXTENSION postgis;"
psql -U postgres -d greenlegacy_test -c "CREATE EXTENSION postgis;"

cd backend
pip install -r requirements.txt
python tools/download_model.py        # yolov8n.pt
python seed.py                        # خشتەکان + گەڕەکەکان + هەژماری شارەوانی
python run.py                         # http://0.0.0.0:5000
```

داشبۆرد: `http://localhost:5000/dashboard` — هەژماری شارەوانی: `07500000000` / `staff1234`

ڕێکخستنەکان هەموویان لە environment variables دێن (`app/config.py`). گرنگترینەکان:

| گۆڕاو | بنەڕەت | واتا |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql://gl:gl@localhost:5432/greenlegacy` | داتابەیس |
| `MODEL_PATH` | `models/yolov8n.pt` | مۆدێلی YOLOv8 |
| `LITTER_CLASSES` | bottle,cup,... | کام پۆلەکان پاشماوەن؛ `*` بۆ مۆدێلی پاشماوە |
| `DETECTOR_KIND` | `yolo` | `colorblob` بۆ ڕاهێنان بە کاغەزی سوور |
| `CLEANUP_RADIUS_M` | 50 | دووری ڕێگەپێدراو لە ڕاپۆرتەکە |
| `SAME_PLACE_MIN_INLIERS` | 20 | خاڵی ORB بۆ «هەمان شوێن» |
| `HASH_MAX_DISTANCE` | 6 | بیتی pHash بۆ «وێنەی دووبارە» |

## ٢. تاقیکردنەوەکان

```bash
cd backend
python -m pytest tests -q
```

هەموو ڕێگاکانی ڕەتکردنەوە تاقی دەکرێنەوە: وێنەی پاک، وێنەی دووبارە، ڕاپۆرتی دووەم (پشتڕاستکردنەوە)،
پاککردنەوەی شوێنی خۆت، ڕیزبەندیی هەڵەی ڕێنمایی، دووری، فریمی وەستاو، ڕێنمایی بەسەرچوو،
پاشماوە ماوە، شوێنی جیاواز ← پشکنین، پەسەند/ڕەتکردنەوەی شارەوانی، سنووری ڕۆژانە.

## ٣. ڕاهێنانی هەموو خولەکە بێ مۆبایل

```bash
DETECTOR_KIND=colorblob python run.py     # پەنجەرەی یەکەم
python tools/rehearse.py                  # پەنجەرەی دووەم
```

ئەنجام: ڕاپۆرت ← خۆت پاکی ناکەیتەوە (٤٠٣) ← ڕیزبەندیی هەڵە ڕەت دەکرێتەوە ← ڤیدیۆی دروست دەسەلمێنرێت ←
هەمان ڤیدیۆ بۆ شوێنێکی تر ڕەت دەکرێتەوە ← شوێنی جیاواز دەچێتە پشکنین. داشبۆردەکە لە کاتی کارکردندا ببینە.

## ٤. ئەپی مۆبایل (Flutter)

```bash
cd mobile
python setup_android.py      # flutter create + مۆڵەتەکانی کامێرا، GPS، ئینتەرنێت و http
flutter pub get
flutter run                  # مۆبایلی ئەندرۆید بە USB
```

لە شاشەی چوونەژوورەوەدا ناونیشانی سێرڤەر بنووسە: `http://<IP ی لاپتۆپ>:5000` (لاپتۆپ و مۆبایل لەسەر هەمان هۆتسپۆت).

### سیمولەیتەری iOS (Mac)

سیمولەیتەری iOS کامێرای نییە. کاتێک ئەپەکە کامێرا نادۆزێتەوە، وێنەی دروستکراو لە سێرڤەرەوە وەردەگرێت
(`backend/app/simulator.py`)، بۆیە سێرڤەر دەبێت بە `colorblob` کار بکات:

```bash
cd backend && DETECTOR_KIND=colorblob python run.py              # پەنجەرەی یەکەم
xcrun simctl location booted set 35.5613,45.4373                  # شوێنی سیمولەیتەر: سلێمانی
cd mobile && python3 setup_ios.py && flutter pub get && flutter run   # پەنجەرەی دووەم
```

`setup_ios.py` مۆڵەتی کامێرا و شوێن و `http://` لە `Info.plist` زیاد دەکات؛ بەبێ ئەوانە iOS ئەپەکە دادەخات
یان ڕێگە نادات بگاتە سێرڤەر. لە شاشەی چوونەژوورەوە: `http://localhost:5000` (ئیمولەیتەری ئەندرۆید: `http://10.0.2.2:5000`).
ڕاپۆرت بکە، پاشان بە هەژمارێکی تر پاکی بکەرەوە: فریمەکان هەمان شوێنن بێ پاشماوە و بە ڕێنماییەکە، بۆیە دەسەلمێنرێت.

⚠️ `flutter analyze` بێ هەڵە تێدەپەڕێت، بەڵام ئەپەکە هێشتا لەسەر مۆبایل یان سیمولەیتەر تاقی نەکراوەتەوە.

## ٥. شتەکانی پێویستە بە وێنەی ڕاستەقینە ڕێکبخرێن

- **مۆدێل:** yolov8n ی ئاسایی تەنها بوتڵ، کوپ و هەندێک شتی تر دەناسێتەوە. مۆدێلی پاشماوەی Hugging Face دابەزێنن و
  `MODEL_PATH=models/<file>.pt LITTER_CLASSES=*` بەکاربهێنن.
- **پلەی پیسی:** `app/ai/scoring.py` — بە ٥٠ وێنەی سلێمانی تاقی بکەنەوە.
- **هەمان شوێن:** `SAME_PLACE_MIN_INLIERS=20` لەسەر وێنەی دروستکراو تاقی کراوەتەوە، نەک لەسەر شەقامی ڕاستەقینە.
- **QR:** ستیکەرەکان بە `python tools/make_qr_stickers.py 12` چاپ بکەن و لە ٣٠–٥٠ سم تاقی بکەنەوە.

## ٦. چی فێربوون (لەم ڕاهێنانەدا دۆزرانەوە)

- وێنەی «دوا»ی هەمان شوێن زۆر لە وێنەی «پێش» دەچێت؛ پشکنینی دووبارە دەبێت وێنەکانی هەمان ڕاپۆرت لاببات.
- ستیکەری QR ی هەمان زبڵدان لە هەموو پاککردنەوەیەکدا یەکسانە؛ تەنها فریمەکانی شوێنەکە بۆ دووبارە بپشکنن.
- ئەگەر Leaflet لە CDN بێت و ئینتەرنێت نەبێت، هەموو داشبۆردەکە دەوەستێت؛ Leaflet لە ناو ئەپەکەدایە.
- مۆبایلی ئەندرۆید بێ `usesCleartextTraffic` ناتوانێت بگاتە `http://` ی لاپتۆپ.

## مۆڵەت

Ultralytics YOLOv8 بە AGPL-3.0 یە. پێش فرۆشتنی بەرهەمێکی داخراو بە شارەوانی، ئەمە یەکلا بکەنەوە.
داتاسێتی TACO بە CC BY 4.0 یە؛ لە سلایدەکاندا ناوی بهێنن. Leaflet بە BSD-2 یە (`backend/app/static/leaflet/LICENSE`).
