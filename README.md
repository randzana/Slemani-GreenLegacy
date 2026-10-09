
docs/
├── README.md
├── architecture/
│   ├── overview.md
│   ├── system-context.md
│   ├── component-diagram.md
│   ├── data-flow.md
│   ├── security-architecture.md
│   └── deployment-architecture.md
├── requirements/
│   ├── business-requirements.md
│   ├── functional-requirements.md
│   ├── non-functional-requirements.md
│   └── user-stories.md
├── setup/
│   ├── local-development.md
│   ├── environment-variables.md
│   ├── prerequisites.md
│   └── onboarding.md
├── backend/
│   ├── python-architecture.md
│   ├── api-design.md
│   ├── services.md
│   ├── database-model.md
│   └── jobs-and-scheduled-tasks.md
├── frontend/
│   ├── dart-app-architecture.md
│   ├── ui-structure.md
│   ├── state-management.md
│   ├── navigation.md
│   └── design-system.md
├── web/
│   ├── html-css-structure.md
│   ├── static-assets-guide.md
│   └── frontend-integration.md
├── data/
│   ├── schema.md
│   ├── migrations.md
│   ├── seed-data.md
│   └── data-pipelines.md
├── api/
│   ├── overview.md
│   ├── authentication.md
│   ├── endpoints.md
│   ├── request-response-examples.md
│   └── error-handling.md
├── testing/
│   ├── testing-strategy.md
│   ├── unit-tests.md
│   ├── integration-tests.md
│   ├── e2e-tests.md
│   └── bug-reporting.md
├── security/
│   ├── overview.md
│   ├── auth-and-authorization.md
│   ├── secrets-management.md
│   ├── vulnerability-management.md
│   └── compliance.md
├── operations/
│   ├── deployment.md
│   ├── monitoring.md
│   ├── logging.md
│   ├── backups.md
│   └── troubleshooting.md
├── contribution/
│   ├── contributing.md
│   ├── coding-standards.md
│   ├── branching-strategy.md
│   ├── pull-request-template.md
│   └── release-process.md
├── roadmap/
│   ├── roadmap.md
│   ├── milestones.md
│   └── changelog.md
├── templates/
│   ├── issue-template.md
│   ├── feature-request.md
│   └── bug-report.md
└── glossary.md






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
    routes.py            ڕاپۆرت، claim، cleanup، leaderboard، me (ڕیزبەندی و متمانەش)
    rewards.py           فرۆشگای خاڵ و ئەرکی ڕۆژانە
    admin.py             کۆتاییەکانی شارەوانی + لاپەڕەی داشبۆرد
    points.py            یاساکانی خاڵ (ledger، ٢٤ کاتژمێر ڕاگرتن، سنووری ڕۆژانە، متمانە، ڕیزبەندی)
    ai/detector.py       YOLOv8 (و ColorBlobDetector تەنها بۆ تاقیکردنەوە)
    ai/verify.py         زنجیرەی سەلماندن: ڤیدیۆی ڕاستەقینە ← QR ← هەمان شوێن ← پاشماوە نەماوە
    ai/describe.py       وەسفی کوردیی وێنەی ڕاپۆرت (قاڵب بێ ئینتەرنێت؛ Claude بە ئارەزوو)
    simulator.py         کامێرای ساختە بۆ سیمولەیتەر (تەنها لەگەڵ colorblob)
    strings.py           هەموو دەقە کوردییەکان
    templates/dashboard.html   داشبۆردی شارەوانی (نەخشە، ئەولەویەت، تۆمار، پشکنین، خەڵات، لیگ)
  schema.sql             شەش خشتە
  migrations/            بۆ داتابەیسێکی کۆن بێ سڕینەوەی داتا
  tests/                 تاقیکردنەوەکان بەسەر PostGIS ی ڕاستەقینەدا (python -m pytest tests -q)
  tools/rehearse.py      هەموو خولەکە لەسەر سێرڤەرێکی کاراوە تاقی دەکاتەوە
  tools/make_qr_stickers.py  ستیکەری QR بۆ زبڵدانەکان چاپ دەکات
  tools/download_model.py    yolov8n یان مۆدێلی گشتیی پاشماوە (--trash) دادەبەزێنێت
  tools/train.py         دابەشکردنی وێنەکان و ڕاهێنانی مۆدێل لەسەر وێنەی سلێمانی (Colab/Kaggle)
  tools/evaluate.py      هەڵسەنگاندنی مۆدێل لەسەر ٥٠ وێنەی تاقیکردنەوە + پێشنیاری پلەکانی پیسی
  tools/fraud_bench.py   ٢٠ هەوڵی ڕاستەقینە و فێڵ بە زنجیرەی سەلماندندا؛ خشتە بۆ سلایدەکان
  tools/import_boundaries.py  سنووری گەڕەکەکان لە GeoJSON ەوە بار دەکات
  tools/preflight.py     پشکنینی پێش شانۆ (✓/⚠/✗)
  notebooks/finetune_colab.ipynb  ڕاهێنانی مۆدێل لەسەر Colab
mobile/                  ئەپی Flutter ی هاوڵاتی (کوردی، ڕاست بۆ چەپ؛ هەموو دەقەکان لە lib/strings.dart)
docs/DEMO.md             ڕێنمایی ڕۆژی دیمۆ: ئامادەکاری، سیناریۆی سەر شانۆ، چارەسەری کێشەکان
docs/VERIFICATION.md     زنجیرەی سەلماندن، ئەنجامی تاقیکردنەوەی فێڵ و سنوورەکانی
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
(تەنها بۆ ڕاهێنان: ئەم وشە نهێنییە لێرە نووسراوە. بۆ دیمۆ `STAFF_PASSWORD=... python seed.py`؛ `seed.py` و preflight ئاگادارت دەکەنەوە.)

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
| `LEVEL_COUNT_BANDS` | `2,5,10,20` | سنووری ژمارەی پاشماوە بۆ پلەی ١، ٢، ٣، ٤ (زیاتر = ٥) |
| `DESCRIBE_WITH_CLAUDE` | `0` | `1` = Claude وێنەکە دەبینێت و وەسفی کوردی دەنووسێت (پێویستی بە `ANTHROPIC_API_KEY` و ئینتەرنێتە) |
| `DESCRIBE_MODEL` | `claude-opus-5-5` | مۆدێلی وەسفکردن |
| `PHONE_REGION` | `IQ` | ژمارەیەک بێ کۆدی وڵات (`0750…`) وەک ژمارەی ئەم وڵاتە دەخوێندرێتەوە؛ هەموو ژمارەکان بە شێوەی `+9647…` هەڵدەگیرێن |
| `PHONE_ALLOWED_COUNTRY_CODES` | `964` | کۆدی ئەو وڵاتانەی ژمارەکانیان قبووڵ دەکرێت، بە کۆما جیا دەکرێنەوە |
| `STEP_TOKEN_MINUTES` | 10 | ماوەی تۆکنی هەنگاوێکی خۆتۆمارکردن (ئیمەیڵی پشتڕاستکراو، یان چوونەژوورەوەی یەکەمجاری Google)؛ هەرگیز وەک چوونەژوورەوە قبووڵ ناکرێت |

فەرمانەکانی سەرەوە بەبێ `DATABASE_URL` کار دەکەن، چونکە بنەڕەتەکەی هەمان `localhost:5432/greenlegacy` ە.
ئەگەر PostgreSQL ەکەت لەسەر پۆرتێکی ترە (بۆ نموونە 5433) یان ناوی داتابەیسەکە جیاوازە، پێش هەموو فەرمانێک:
`export DATABASE_URL=postgresql://gl:gl@localhost:5433/greenlegacy` (لە ڕۆژی دیمۆدا لە `.env` دایە، `docs/DEMO.md`).

داتابەیسێکی کۆنت هەیە و ناتەوێت بیسڕیتەوە؟ لە جیاتی `seed.py`، بە ڕیز:
```bash
psql "$DATABASE_URL" -f migrations/001_shop_tasks_description.sql
psql "$DATABASE_URL" -f migrations/002_neighbourhood_boundaries.sql
psql "$DATABASE_URL" -f migrations/003_voucher_honoured.sql
psql "$DATABASE_URL" -f migrations/004_custom_pins_and_notifications.sql
psql "$DATABASE_URL" -f migrations/005_pin_registrations.sql
psql "$DATABASE_URL" -f migrations/006_trash_bins.sql
psql "$DATABASE_URL" -f migrations/007_accounts_email_google.sql
```
`python tools/preflight.py` پێت دەڵێت کامیان ماوە.

## ٢. تاقیکردنەوەکان

```bash
cd backend
python -m pytest tests -q
```

هەموو ڕێگاکانی ڕەتکردنەوە تاقی دەکرێنەوە: وێنەی پاک، وێنەی دووبارە، ڕاپۆرتی دووەم (پشتڕاستکردنەوە)،
پاککردنەوەی شوێنی خۆت، ڕیزبەندیی هەڵەی ڕێنمایی، دووری، فریمی وەستاو، ڕێنمایی بەسەرچوو،
پاشماوە ماوە، شوێنی جیاواز ← پشکنین، پەسەند/ڕەتکردنەوەی شارەوانی، سنووری ڕۆژانە.
`tests/test_races.py` داواکاریی هاوکات بە thread ی ڕاستەقینە دەنێرێت: هەمان پاککردنەوە کە سێ جار پێکەوە دەنێردرێت
(ئەپ دووبارەی دەکاتەوە کاتێک یەکەمیان هێشتا شی دەکرێتەوە) تەنها یەک جار خاڵ دەدات، دوو «من پاکی دەکەمەوە»ی هاوکات
یەک ڕێنمایی دەدەن، و کۆدی خەڵات تەنها یەک جار ڕادەست دەکرێت.

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

هەموو دەقە کوردییەکانی ئەپ لە `mobile/lib/strings.dart` (کلاسی `S`) دان، بە پێی شاشە ڕیزکراون؛ بۆ چاککردنی کوردییەکە تەنها
ئەو فایلە بگۆڕە. ئاگاداری: `S.plantHealthy`، `S.plantThirsty` و `S.plantLevel1`–`3` لەسەر مۆبایل هەڵدەگیرێن و بەراورد دەکرێن؛
گۆڕینیان ڕووەکە هەڵگیراوەکان تێکدەدات. خاڵەکانی باخچەی دیجیتاڵی تەنها نووسینن لەسەر شاشە و ناچنە ledger ی سێرڤەر.

⚠️ `flutter analyze` بێ هەڵە تێدەپەڕێت، و شاشە نوێکان (ئەرکی ڕۆژانە، فرۆشگا، ڕیزبەندی، وەسف) لە build ی web دا
بینراون، بەڵام ئەپەکە هێشتا لەسەر مۆبایلی ڕاستەقینە تاقی نەکراوەتەوە.

## ٥. شتەکانی پێویستە بە وێنەی ڕاستەقینە ڕێکبخرێن

- **مۆدێل:** yolov8n ی ئاسایی تەنها بوتڵ، کوپ و هەندێک شتی تر دەناسێتەوە. مۆدێلی پاشماوەی Hugging Face دابەزێنن و
  `MODEL_PATH=models/<file>.pt LITTER_CLASSES=*` بەکاربهێنن.
- **پلەی پیسی:** `app/ai/scoring.py` — بە ٥٠ وێنەی سلێمانی تاقی بکەنەوە.
- **هەمان شوێن:** `SAME_PLACE_MIN_INLIERS=20` لەسەر وێنەی دروستکراو تاقی کراوەتەوە، نەک لەسەر شەقامی ڕاستەقینە.
- **QR:** ستیکەرەکان بە `python tools/make_qr_stickers.py 12` چاپ بکەن (~٩ سم) و لە ~٣٠ سم تاقی بکەنەوە.

## ٦. مۆدێل: دابەزاندن، ڕاهێنان، هەڵسەنگاندن

```bash
cd backend
python tools/download_model.py --trash          # turhancan97/yolov8-segment-trash-detection (MIT)
MODEL_PATH=models/yolov8m-seg.pt LITTER_CLASSES=* python run.py
python tools/download_model.py --stock yolov8s.pt   # بنەمای ڕاهێنان ئەگەر لەیبڵەکان چوارگۆشە (box) بن

# ئێوارەی ڕۆژی یەکەم: وێنەکانی سلێمانی بە YOLO format هەناردە بکە (Label Studio / CVAT / Roboflow)
python tools/train.py split --images export/images --labels export/labels \
    --classes export/classes.txt --out datasets/slemani --test 50
# لەسەر Colab/Kaggle (GPU):  pip install ultralytics
python tools/train.py train --data datasets/slemani/data.yaml --base models/yolov8m-seg.pt

# بەراوردکردن: ئەگەر مۆدێلی ڕاهێنراو باشتر نەبوو، گشتییەکە بەکاربهێنە
python tools/evaluate.py datasets/slemani/test --model models/yolov8m-seg.pt --model models/slemani.pt
# پلەکانی پیسی: ستوونی level لە datasets/slemani/test/labels.csv بە دەست پڕ بکەرەوە
python tools/evaluate.py datasets/slemani/test --model models/slemani.pt --suggest-bands
```

لەسەر Colab: `backend/notebooks/finetune_colab.ipynb` بکەرەوە (Runtime ← Change runtime type ← T4 GPU) و خانەکان بە ڕیز
کار پێبکە: zip ی هەناردەی YOLO لە Drive وەردەگرێت، دابەشی دەکات (٥٠ وێنەی تاقیکردنەوە هەرگیز بۆ ڕاهێنان بەکارناهێنرێن)،
ڕادەهێنێت، بەراوردی دەکات و `slemani.pt` دادەبەزێنێت.

- `--base` دەبێت لەگەڵ جۆری لەیبڵەکان بگونجێت: box ← `yolov8s.pt`؛ polygon ← مۆدێلی پاشماوە (`-seg`). `train.py` جۆری مۆدێلەکە
  دەخوێنێتەوە و ئەگەر نەگونجا بە ڕوونی دەوەستێت.
- سێرڤەر دەستپێناکات ئەگەر فایلی `MODEL_PATH` بوونی نەبێت (پێشتر ultralytics بە بێدەنگی مۆدێلی COCO ی هاوناوی دادەبەزاند و
  مرۆڤی وەک پاشماوە دەژمارد)، یان ئەگەر هیچ ناوێکی `LITTER_CLASSES` لە پۆلەکانی مۆدێلەکەدا نەبێت.
- `LITTER_CLASSES=*` تەنها لەگەڵ مۆدێلی پاشماوە؛ لەگەڵ `yolov8n.pt` ی ئاسایی مرۆڤ و پاسیش دەژمێرێت.
- تەنها mAP سەیر مەکە: خشتەی `evaluate.py` (دۆزینەوە لە وێنەی پیس، پاشماوەی ناڕاست لە وێنەی پاک، هەڵەی ژماردن) ڕاستییەکە دەڵێت.
- YOLOv8n لەسەر CPU ی ٤ هەستەیی: نزیکەی ٠٫٠٤–٠٫١٦ چرکە بۆ هەر وێنەیەک (پێوانە لەسەر وێنەی نموونە، نەک سلێمانی).

ناوی مۆدێلەکە و TACO (CC BY 4.0) لە سلایدەکاندا بهێنن.

## ٧. تاقیکردنەوەی فێڵ (fraud bench)

```bash
python tools/fraud_bench.py                     # ٢٠ هەوڵ لەسەر داتابەیسی test (دەیسڕێتەوە)
python tools/fraud_bench.py --from-db           # هەوڵە ڕاستەقینەکان لەسەر سێرڤەری کاراوە (تەنها خوێندنەوە)
SAME_PLACE_MIN_INLIERS=15 python tools/fraud_bench.py --from-db --rerun   # ڕێکخستنی نوێ لەسەر هەمان فریمەکان
```

ئەنجامی ئێستا (وێنەی دروستکراو): ٤/٤ پاککردنەوەی ڕاستەقینە سەلمێنران؛ ٠/١٦ فێڵ خاڵی وەرگرت
(١٤ ڕەتکرانەوە، ٢ چوونە پشکنینی مرۆیی). بۆ «٢٠ ڤیدیۆی ساختە»ی ڕۆژی دووەم، هەوڵەکان بە ئەپی ڕاستەقینە بکەن و
پاشان `--from-db` خشتەکە دەدات.

## ٨. فرۆشگای خاڵ، ئەرکی ڕۆژانە، وەسفی کوردی، متمانە

ئەمانە یەکەم شتن کە کاتی کەم بوو لادەبرێن (پلانی دروستکردن)، بۆیە لە `rewards.py` ی جیادان و هیچ شتێکی تر پشتیان پێ نابەستێت.

| Endpoint | کێ | چی دەکات |
| --- | --- | --- |
| `GET /rewards` | ئەپ | خەڵاتەکان، خاڵی ئازاد و کۆدەکانی پێشووت |
| `POST /rewards/<code>/redeem` | ئەپ | خاڵی ئازاد دەگۆڕێتەوە بە کۆدێک (`GL-XXXXXX`)؛ دوو داواکاریی هاوکات هەمان خاڵ دووجار خەرج ناکەن |
| `GET /tasks` | ئەپ | سێ ئەرکی ئەمڕۆ: ڕاپۆرت، پشتڕاستکردنەوە، پاککردنەوەی سەلمێنراو |
| `POST /tasks/<code>/claim` | ئەپ | خاڵی ئەرکێکی تەواوبوو، ڕۆژی یەک جار، دوای ٢٤ کاتژمێر ئازاد دەبێت |
| `GET /admin/redemptions` | داشبۆرد | کۆدەکان بۆ ئەوەی شارەوانی بیانپشکنێت، و کەی ڕادەست کراون (`honoured_at`) |
| `POST /admin/redemptions/<id>/honour` | داشبۆرد | دوگمەی «ڕادەستکردن» لە تابی «خەڵاتەکان»: خەڵاتەکە درا. هەر کۆدێک تەنها یەک جار (جاری دووەم `409 voucher_used`)، بۆیە سکرینشۆتی کۆدێک دووبارە کار ناکات |

- `GET /me` ئێستا `rank`، `neighbourhood_rank` و `trust_level` یش دەگەڕێنێتەوە، و `earned` (هەموو خاڵی ئازادکراو، بۆ پلە و
  نیشانەکان؛ خەرجکردن کەمی ناکاتەوە) لە تەنیشت `released` (ئەوەی دەتوانرێت خەرج بکرێت). `GET /rewards` بۆ هەر کۆدێک `honoured` دەدات.
- خەرجکردنی خاڵ ڕیزی لیگ کەم ناکاتەوە (لیگ خاڵی بەدەستهاتوو دەژمێرێت).
- خەڵاتەکان (`config.REWARDS`) نموونەن؛ خەڵاتی ڕاستەقینە و کێ کۆدەکان قبووڵ دەکات لەگەڵ شارەوانی ڕێکبخەن.
- متمانە: پاککردنەوەی سەلمێنراو +١، ڕاپۆرتی پشتڕاستکراو +١، ڤیدیۆی دووبارە −٢، ڕەتکردنەوەی شارەوانی −٢ (`TRUST_DELTAS`).
  لە کارتی پشکنینی داشبۆرددا دەردەکەوێت.
- وەسفی کوردی: هەمیشە ڕستەیەکی قاڵب لە ژمارەکانی YOLO؛ بە `DESCRIBE_WITH_CLAUDE=1` Claude لە پشتەوە وێنەکە دەبینێت و
  ڕستەکە دەگۆڕێت (ئەپ چاوەڕێ ناکات؛ ئەگەر ئینتەرنێت نەبوو قاڵبەکە دەمێنێتەوە). وێنەکان دەچنە دەرەوەی لاپتۆپ،
  بۆیە تەنها کاتێک بیکەنەوە کە ئەمە ڕێککەوتراوە.

## ٩. سنووری گەڕەکەکان و لیگ

سنووری ڕاستەقینەی گەڕەکەکانی سلێمانی لەم ڕیپۆیەدا نییە و نابێت لە خۆمانەوە دروستیان بکەین. لەسەر لاپتۆپێک کە ئینتەرنێتی هەیە
فایلێکی GeoJSON ئامادە بکەن: لە overpass-turbo.eu (نموونەی query لە سەرەتای `tools/import_boundaries.py` دایە) ← Export ← GeoJSON،
یان لە geojson.io ناوچەکان بکێشن و بۆ هەر یەکێکیان `name` بنووسن، ڕێک وەک ناوی گەڕەکەکە لە `seed.py`. زۆر گەڕەک لە OSM
تەنها خاڵێکە و دەبێت بە دەست بکێشرێت.

```bash
python tools/import_boundaries.py slemani.geojson --dry-run           # سەرەتا تەنها پوختەکە ببینە
python tools/import_boundaries.py slemani.geojson                     # پاشان پاشەکەوتی بکە
python tools/import_boundaries.py slemani.geojson --add-missing       # گەڕەکی نوێش زیاد بکە
```

ناو بەم ڕیزبەندییە دەخوێنرێتەوە: `name:ckb`، `name:ku`، `name` (`--name-prop`). خاڵ و هێڵ ڕەت دەکرێنەوە، ناوە نەدۆزراوەکان
چاپ دەکرێن و چەند پارچەیەک بە هەمان ناو یەک دەخرێن.

- `GET /neighbourhoods?geo=1` سنوورەکان بە GeoJSON دەگەڕێنێتەوە؛ بێ `geo` وەک پێشوو تەنها `id` و `name`.
- `GET /admin/neighbourhoods` (تەنها شارەوانی): خاڵ، ژمارەی هاوڵاتی، شوێنی کراوە و پاککراوە لەناو هەر سنوورێکدا.
- داشبۆرد: سنوورەکان لەژێر شوێنەکان بە شین (شوێنی کراوەی زیاتر = تۆختر)؛ تابی «لیگ» گەڕەکەکان و باشترین هاوڵاتییان.

## ١٠. پێش چوونە سەر شانۆ

```bash
cd backend
python tools/preflight.py --model --server http://localhost:5000          # ڕۆژی دیمۆ: دەبێت 0 ✗ بێت
DETECTOR_KIND=colorblob python tools/preflight.py --rehearsal --server http://localhost:5000   # ڕاهێنان
```

هەر پشکنینێک یەک هێڵە: ✓ باشە، ⚠ سەیری بکە، ✗ پێش دیمۆ چاکی بکە (exit code 1): داتابەیس و migration ەکان، هەژماری شارەوانی
(و ئایا هێشتا `staff1234` ە)، گەڕەکەکان، فۆڵدەری وێنە، ناسەر و مۆدێل (`--model` باری دەکات و کاتەکەی دەپێوێت)، Leaflet، ستیکەری QR،
`SECRET_KEY`، `SIM_CAMERA`، وەسفی Claude، IP ی لاپتۆپ و ئەو ناونیشانەی لە مۆبایل دەنووسرێت؛ بە `--server` سێرڤەری کاراوەش: ئایا
داتابەیسەکەی دەخوێنێتەوە (`/neighbourhoods`)، کام ناسەر بەکاردێنێت، ئایا هەمان مۆدێلی ئەم پەنجەرەیە بەکاردێنێت (نەک فایلێکی تر)،
و ئایا `/sim` کراوەیە. هەموو هەنگاوەکانی ڕۆژی دیمۆ و سیناریۆی سەر شانۆ: `docs/DEMO.md`.

## ١١. چی فێربوون (لەم ڕاهێنانەدا دۆزرانەوە)

- وێنەی «دوا»ی هەمان شوێن زۆر لە وێنەی «پێش» دەچێت؛ پشکنینی دووبارە دەبێت وێنەکانی هەمان ڕاپۆرت لاببات.
- ستیکەری QR ی هەمان زبڵدان لە هەموو پاککردنەوەیەکدا یەکسانە؛ تەنها فریمەکانی شوێنەکە بۆ دووبارە بپشکنن.
- ئەگەر Leaflet لە CDN بێت و ئینتەرنێت نەبێت، هەموو داشبۆردەکە دەوەستێت؛ Leaflet لە ناو ئەپەکەدایە.
- مۆبایلی ئەندرۆید بێ `usesCleartextTraffic` ناتوانێت بگاتە `http://` ی لاپتۆپ.

## مۆڵەت

Ultralytics YOLOv8 بە AGPL-3.0 یە. پێش فرۆشتنی بەرهەمێکی داخراو بە شارەوانی، ئەمە یەکلا بکەنەوە.
داتاسێتی TACO بە CC BY 4.0 یە؛ لە سلایدەکاندا ناوی بهێنن. Leaflet بە BSD-2 یە (`backend/app/static/leaflet/LICENSE`).
