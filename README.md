
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
    routes.py            ڕاپۆرت، claim، cleanup، leaderboard، me (ڕیزبەندی و متمانەش)، /me/places
    auth.py              خۆتۆمارکردن، چوونەژوورەوە (ئیمەیڵ یان ژمارە)، تۆکنەکان، /auth/config
    accounts.py          هەژمار، ماڵ و شوێنی بازرگانی، پارەی مانگانە (بەشی ١٠)
    otp.py, emails.py    کۆدی ئیمەیڵ (console / smtp)، یەک هەژمار بۆ هەر ئیمەیڵێک
    google_auth.py       چوونەژوورەوە بە Google (تۆکنەکە لەسەر سێرڤەر دەپشکنرێت)
    phones.py            ژمارەی مۆبایل بە یەک شێوە (+9647…)
    rewards.py           فرۆشگای خاڵ و ئەرکی ڕۆژانە
    admin.py             کۆتاییەکانی شارەوانی + لاپەڕەی داشبۆرد
    points.py            یاساکانی خاڵ (ledger، ٢٤ کاتژمێر ڕاگرتن، سنووری ڕۆژانە، متمانە، ڕیزبەندی)
    ai/detector.py       YOLOv8 (و ColorBlobDetector تەنها بۆ تاقیکردنەوە)
    ai/verify.py         زنجیرەی سەلماندن: ڤیدیۆی ڕاستەقینە ← QR ← هەمان شوێن ← پاشماوە نەماوە
    ai/describe.py       وەسفی کوردیی وێنەی ڕاپۆرت (قاڵب بێ ئینتەرنێت؛ Claude بە ئارەزوو)
    simulator.py         کامێرای ساختە بۆ سیمولەیتەر (تەنها لەگەڵ colorblob)
    strings.py           هەموو دەقە کوردییەکان
    templates/dashboard.html   داشبۆردی شارەوانی (نەخشە، ئەولەویەت، تۆمار، پشکنین، ماڵ و بازرگانی، پارەی مانگانە، خەڵات، لیگ)
  schema.sql             هەموو خشتەکان (بۆ داتابەیسی نوێ؛ seed.py دەیسڕێتەوە)
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
  lib/screens/registration/  خۆتۆمارکردن: جۆر ← فۆرم و نەخشە ← کۆدی ئیمەیڵ؛ بەستنەوەی Google
  integration_test/      خولی خۆتۆمارکردن و چوونەژوورەوە لەسەر سیمولەیتەر، دژی سێرڤەرێکی تاقیکردنەوە
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
| `OTP_REQUIRED` | `1` | هەژماری نوێ پێویستی بە ئیمەیڵی پشتڕاستکراو هەیە؛ `0` تەنها بۆ ڕاهێنانی بێ ئینتەرنێت (`tools/rehearse.py`) و بیلدی کۆنی ئەپەکە (preflight ئاگادار دەکاتەوە) |
| `HOUSEHOLD_MONTHLY_IQD` / `BUSINESS_MONTHLY_IQD` | `10000` / `25000` | ئەو بڕە پارەیەی داشبۆرد بۆ ماڵ و شوێنی بازرگانیی پەسەندکراو پڕی دەکاتەوە؛ کارمەند دەتوانێت بیگۆڕێت. نرخی نموونەن: لەگەڵ شارەوانی ڕێک بکەون |
| `MAX_MONTHLY_IQD` | `1000000` | زۆرترین بڕی مانگانە بۆ یەک شوێن (هەڵەی سفری زیادە ڕەت دەکرێتەوە) |
| `SERVICE_AREA_BBOX` | `34.3,44.3,36.6,46.4` | ماڵ و شوێنی بازرگانی دەبێت لەناو ئەم چوارگۆشەیەدا بن (`min_lat,min_lon,max_lat,max_lon`، نزیکەی پارێزگای سلێمانی) |
| `GOOGLE_CLIENT_IDS` | بەتاڵ (Google کوژاوەتەوە) | ناسنامەی OAuth ی ئەو ئەپانەی تۆکنەکانیان قبووڵ دەکرێت (Web، Android، iOS)، بە کۆما جیا دەکرێنەوە |
| `GOOGLE_SERVER_CLIENT_ID` | — | ناسنامەی Web؛ ئەپەکە لە `/auth/config` وەریدەگرێت. دەبێت لەناو `GOOGLE_CLIENT_IDS` دا بێت |
| `OTP_SENDER` | `console` | کێ کۆدی ئیمەیڵ دەگەیەنێت: `console` (کۆدەکە لە لۆگی سێرڤەردا دەنووسرێت؛ تەنها بۆ دیمۆ)، `smtp` (ئیمەیڵی ڕاستەقینە)، `fake` (تاقیکردنەوە) |
| `OTP_PEPPER` | — | کلیلی نهێنی بۆ هاشی کۆدەکان؛ ئەگەر دانەنرێت لە `SECRET_KEY` وەردەگیرێت (preflight ئاگادار دەکاتەوە) |
| `OTP_LENGTH` / `OTP_TTL_SECONDS` / `OTP_MAX_ATTEMPTS` | `6` / `300` / `5` | درێژی کۆد، ماوەی کارکردنی، و ژمارەی هەوڵ پێش ئەوەی بمرێت |
| `OTP_RESEND_SECONDS` | 60 | چاوەڕوانی پێش ناردنی کۆدێکی تر بۆ هەمان ئیمەیڵ |
| `OTP_MAX_PER_EMAIL_HOUR` / `OTP_MAX_PER_IP_HOUR` / `OTP_MAX_PER_HOUR` | `5` / `20` / `200` | سنووری کۆد لە کاتژمێرێکدا بۆ هەر ئیمەیڵێک، هەر IP یەک، و هەمووان پێکەوە |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_SECURITY` | — / `587` / `starttls` | سێرڤەری ئیمەیڵ بۆ `OTP_SENDER=smtp`؛ `ssl` بۆ پۆرتی 465 |
| `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` | — | هەژماری ئیمەیڵ (لە `.env` دا، نەک لە کۆدەکەدا)؛ `SMTP_FROM` ی بەتاڵ = `SMTP_USER` |

فەرمانەکانی سەرەوە بەبێ `DATABASE_URL` کار دەکەن، چونکە بنەڕەتەکەی هەمان `localhost:5432/greenlegacy` ە.
ئەگەر PostgreSQL ەکەت لەسەر پۆرتێکی ترە (بۆ نموونە 5433) یان ناوی داتابەیسەکە جیاوازە، پێش هەموو فەرمانێک:
`export DATABASE_URL=postgresql://gl:gl@localhost:5433/greenlegacy` (لە ڕۆژی دیمۆدا لە `.env` دایە، `docs/DEMO.md`).

داتابەیسێکی کۆنت هەیە و ناتەوێت بیسڕیتەوە؟ لە جیاتی `seed.py`، بە ڕیز (`-v ON_ERROR_STOP=1` لە یەکەم هەڵەدا دەوەستێت):
```bash
psql -v ON_ERROR_STOP=1 "$DATABASE_URL" -f migrations/001_shop_tasks_description.sql
psql -v ON_ERROR_STOP=1 "$DATABASE_URL" -f migrations/002_neighbourhood_boundaries.sql
psql -v ON_ERROR_STOP=1 "$DATABASE_URL" -f migrations/003_voucher_honoured.sql
psql -v ON_ERROR_STOP=1 "$DATABASE_URL" -f migrations/004_custom_pins_and_notifications.sql
psql -v ON_ERROR_STOP=1 "$DATABASE_URL" -f migrations/005_pin_registrations.sql
psql -v ON_ERROR_STOP=1 "$DATABASE_URL" -f migrations/006_trash_bins.sql
psql -v ON_ERROR_STOP=1 "$DATABASE_URL" -f migrations/007_accounts_email_google.sql
```
`python tools/preflight.py` پێت دەڵێت کامیان ماوە. هەر فایلێک دووبارە کارپێکردنی بێمەترسییە.
`007` ژمارەی مۆبایلە کۆنەکان دەکات بە `+9647…`؛ ئەگەر دوو هەژمار هەمان ژمارە بن بە دوو شێوەی نووسین (`0750…` و `+964750…`)،
دەوەستێت، ناویان دەبات و هیچ ناگۆڕێت: یەکێکیان بە دەست چاک بکە و دووبارە کاری پێبکە. ژمارەیەک کە مۆبایلی عێراقی نییە
وەک خۆی دەمێنێتەوە و ئەو کەسە بە هەمان نووسین دەچێتە ژوورەوە.

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

هەژمار و کۆد: `test_otp.py` (هاش لە جیاتی کۆد، ٥ هەوڵ تەنانەت ئەگەر ٢٠ پێکەوە بنێردرێن، سنوورەکان، ناردنی SMTP بە سێرڤەرێکی ساختە)،
`test_tokens.py` (تۆکنی هەنگاو هەرگیز وەک چوونەژوورەوە قبووڵ ناکرێت)، `test_accounts.py` و `test_places_admin.py` (ماڵ و بازرگانی،
پشکنینی شارەوانی، پارەی مانگانە، و هیچ لاپەڕەیەکی گشتی شوێنی ماڵ پیشان نادات)، `test_google_auth.py` (تۆکنی Google بە کلیلێکی
دروستکراو و endpoint ێکی ساختە؛ هیچ تاقیکردنەوەیەک قسە لەگەڵ Google ناکات)، `test_migrations.py` (داتابەیسی کۆن + `007` = هەمان
schema ی `seed.py`).

ئەپ:

```bash
cd mobile && flutter analyze && flutter test       # تاقیکردنەوەی ویجێت
```

خولی تەواو لەسەر سیمولەیتەر، دژی سێرڤەرێکی تاقیکردنەوە (کۆدی ئیمەیڵ لە لۆگی سێرڤەرەکە دەخوێنرێتەوە، وەک ڕۆژی دیمۆ):

```bash
# پەنجەرەی یەکەم، لە backend/ (داتابەیسی test: هەر جارێک هەژمارێکی نوێ دروست دەکات)
DATABASE_URL=postgresql://gl:gl@localhost:5432/greenlegacy_test OTP_SENDER=console DETECTOR_KIND=colorblob \
    PORT=5055 python run.py 2> /tmp/gl_server.log
# پەنجەرەی دووەم، لە mobile/
flutter test integration_test/flows_test.dart -d <سیمولەیتەر> \
    --dart-define=SERVER_URL=http://localhost:5055 --dart-define=SERVER_LOG=/tmp/gl_server.log
```

`flows_test.dart` هەژمارێکی نوێ بە ماڵەوە دروست دەکات، شارەوانی ڕەتی دەکاتەوە و کەسەکە چاکی دەکات، پاشان بە ئیمەیڵ و بە ژمارە
دەچێتە ژوورەوە. `google_not_set_up_test.dart` (سێرڤەرێک بە `GOOGLE_CLIENT_IDS` و `GOOGLE_SERVER_CLIENT_ID`، و تەنها `SERVER_URL`) دڵنیا
دەبێتەوە کە بیلدێک بێ ڕێکخستنی Google ی iOS ڕوونی دەکاتەوە، نەک دابخرێت.

## ٣. ڕاهێنانی هەموو خولەکە بێ مۆبایل

```bash
OTP_REQUIRED=0 DETECTOR_KIND=colorblob python run.py     # پەنجەرەی یەکەم (خەڵکەکەی بێ کۆدی ئیمەیڵ تۆمار دەبن)
python tools/rehearse.py                                  # پەنجەرەی دووەم
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

هەژماری نوێ: «هەژماری نوێ» ← هاوڵاتی، و ئەگەر هەیە ماڵ و/یان شوێنی بازرگانی ← فۆرم (شوێن لەسەر نەخشە) ← کۆدی ئیمەیڵ.
چوونەژوورەوە بە ئیمەیڵ یان ژمارە. دوگمەی Google تەنها کاتێک دەردەکەوێت کە سێرڤەرەکە Google ی چالاک کردبێت (بەشی ١٠).
بیلدی کۆنی ئەپ (پێش ئیمەیڵ) دەتوانێت بچێتە ژوورەوە، بەڵام تەنها بە `OTP_REQUIRED=0` هەژماری نوێ دروست دەکات.

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

## ١٠. هەژمار: ئیمەیڵ، Google، ماڵ و شوێنی بازرگانی

هەر هەژمارێک یەک کەسە و ناسنامەکەی **ئیمەیڵێکی پشتڕاستکراوە**: یەک هەژمار بۆ هەر ئیمەیڵێک (لە Gmail خاڵ و `+tag` هەمان
سندوقن). ژمارەی مۆبایل پێویستە و تاکە (`+9647…`)، بەڵام پشتڕاست ناکرێتەوە؛ هەژمارە کۆنەکان (پێش ئیمەیڵ) هێشتا بە ژمارە دەچنە
ژوورەوە. هەر کەسێک دەتوانێت **ماڵ** و/یان **شوێنی بازرگانی** زیاد بکات؛ شارەوانی هەردووکیان دەپشکنێت (چاوەڕێ ← پەسەندکراو،
یان ڕەتکراوە بە هۆکارێک کە کەسەکە لە ئەپدا دەیبینێت). خاڵ تەنها بۆ کاری خودی کەسەکەیە (ڕاپۆرت، پاککردنەوەی سەلمێنراو)، بۆیە لیگ
وەک پێشووە. ماڵ و بازرگانیی پەسەندکراو **پارەی مانگانە** وەردەگرن کە کارمەند لە داشبۆرد تۆماری دەکات: ئێستا تەنها ژمارەیەکە لە
پرۆفایلدا، دواتر بانکی دیجیتاڵی دەیدات. شوێنی ماڵ نهێنییە: تەنها خاوەنەکەی و شارەوانی دەیبینن، و لەسەر نەخشەی داشبۆرد نییە
(تەنها ژمارەی ماڵ لە هەر گەڕەکێکدا).

| Endpoint | کێ | چی دەکات |
| --- | --- | --- |
| `GET /auth/config` | ئەپ | ئایا Google چالاکە، ڕێکخستنی کۆد، جۆرەکانی بازرگانی، سنووری خزمەتگوزاری؛ هیچ نهێنییەک تێدا نییە |
| `POST /auth/otp/request` | ئەپ | `{email}`: کۆدێکی ٦ ژمارەیی؛ وەڵامەکە یەکسانە چ ئیمەیڵەکە هەژماری هەبێت چ نا. ٦٠ چرکە چاوەڕوانی (`retry_after`) |
| `POST /auth/otp/verify` | ئەپ | `{email, code}`: تۆکنی هەنگاو (١٠ خولەک)؛ ٥ هەوڵ (`attempts_left`)، پاشان `429 otp_locked` |
| `POST /auth/signup` | ئەپ | ناو، ژمارە، وشەی نهێنی، تۆکنی ئیمەیڵ، گەڕەک، و `household` / `business` (ئارەزوومەندانە). ئیمەیڵ تەنها لە تۆکنەکەوە دێت؛ هەڵەی خانەکان لە `fields` دا |
| `POST /auth/login` | ئەپ، داشبۆرد | `{login, password}`: ئیمەیڵ یان ژمارە بە هەر شێوەیەک (بیلدی کۆن `{phone}` دەنێرێت) |
| `POST /auth/google` | ئەپ | ID token ی Google: هەژماری ناسراو دەچێتە ژوورەوە؛ نوێ تۆکنی `google_signup` وەردەگرێت و هێشتا هیچ ڕیزێک دروست نابێت |
| `POST /auth/google/register` | ئەپ | هەژماری نوێ بە ئیمەیڵی Google (بێ کۆد و بێ وشەی نهێنی)؛ ژمارە یان ئیمەیڵێکی گیراو ← `409` لەگەڵ `can_link` |
| `POST /auth/google/link` | ئەپ | Google بە هەژمارێکی هەبووەوە دەبەستێتەوە؛ وشەی نهێنیی ئەو هەژمارە پێویستە. هەژماری شارەوانی نابەسترێتەوە |
| `GET /me` | ئەپ | ئێستا `email`، `auth_methods`، `places` (لەگەڵ شوێن، تەنها بۆ خاوەنەکەی) و `money` یشی تێدایە |
| `POST /me/places` | ئەپ | ماڵ یان بازرگانی زیاد یان دەستکاری دەکات؛ گۆڕینی ئەوەی شارەوانی پشکنیویەتی (ناو، شوێن، دانیشتووان، جۆر، مۆڵەت) دەیگەڕێنێتەوە بۆ چاوەڕێ |
| `GET /admin/places` | داشبۆرد | ڕیزی پشکنین: `?status=pending` (بنەڕەت)، `verified`، `rejected`، `all` |
| `POST /admin/places/<id>/review` | داشبۆرد | `verify` یان `reject` + هۆکار؛ ئەگەر خاوەنەکەی دوای بینینت گۆڕیبێتی ← `409 place_changed`. هەموو بڕیارێک لە `place_reviews` دا دەمێنێتەوە |
| `GET /admin/payments` | داشبۆرد | پارەی مانگێک (`?month=YYYY-MM`) بۆ هەموو شوێنە پەسەندکراوەکان و کۆی گشتی |
| `POST /admin/places/<id>/payments` | داشبۆرد | پارەی یەک مانگ بۆ یەک شوێنی پەسەندکراو، یەک جار |
| `POST /admin/payments` | داشبۆرد | پارەی مانگێک بۆ هەموو ئەوانەی هێشتا وەریان نەگرتووە؛ دووجار داگرتن کەس دووجار پارە نادات |

### کۆدی ئیمەیڵ

- **دیمۆ:** `OTP_SENDER=console` (بنەڕەت). کۆدەکە لە پەنجەرەی سێرڤەردا دەردەکەوێت، بۆ نموونە
  `EMAIL CODE for ra***@gmail.com: 123456`؛ ئینتەرنێت و هەژماری ئیمەیڵ پێویست نین (`docs/DEMO.md`).
- **ئیمەیڵی ڕاستەقینە:** هەر هەژمارێکی SMTP. بۆ Gmail، «App Password» دروست بکە (نەک وشەی نهێنیی هەژمارەکە). لە `.env`:

  ```bash
  export OTP_SENDER=smtp SMTP_HOST=smtp.gmail.com SMTP_PORT=587 SMTP_USER=<هەژمار>@gmail.com
  export SMTP_PASSWORD='<App Password>'
  export OTP_PEPPER=$(python -c 'import secrets; print(secrets.token_hex(32))')   # یەک جار، و مەیگۆڕە
  ```

### چوونەژوورەوە بە Google

١. Google Cloud Console ← پرۆجێکتێک ← OAuth consent screen: تەنها `openid`، `email`، `profile`. تا کاتێک لە «Testing» دایە،
   تەنها ئەو هەژمارانەی وەک test user زیاد کراون دەتوانن بچنە ژوورەوە: هەژماری تیمەکە زیاد بکەن.
٢. Credentials ← Create OAuth client ID، سێ دانە:
   - **Web application**: ناسنامەکەی `GOOGLE_SERVER_CLIENT_ID` ە.
   - **Android**: package `krd.greenlegacy.slemani_green_legacy` و SHA-1 ی کلیلی واژووکردن؛ `python setup_android.py` فەرمانی
     `keytool` ەکەی چاپ دەکات. `google-services.json` پێویست نییە.
   - **iOS**: bundle ID `krd.greenlegacy.slemaniGreenLegacy`، پاشان
     `GOOGLE_IOS_CLIENT_ID=<ناسنامەی iOS> python3 setup_ios.py` (GIDClientID و URL scheme لە Info.plist زیاد دەکات).
٣. لە `.env` ی سێرڤەر (تۆکنی iOS بۆ ناسنامەی iOS دەردەچێت، بۆیە هەر سێکیان):

   ```bash
   export GOOGLE_CLIENT_IDS=<web>,<android>,<ios>
   export GOOGLE_SERVER_CLIENT_ID=<web>
   ```

٤. `python tools/preflight.py`: «Google ✓» و «کلیلەکانی Google ✓». Google پێویستی بە ئینتەرنێتە لەسەر مۆبایل و لاپتۆپ؛
   ئەگەر نەبوو، ئیمەیڵ و وشەی نهێنی هەر کار دەکەن. سێرڤەر خۆی تۆکنەکە دەپشکنێت (واژوو، `aud`، `iss`، کات، `email_verified`)
   و تەنها `sub` ی Google هەڵدەگرێت، نەک هیچ access token ێک.

### ئاسایش و سنوورەکان

- **HTTPS:** سێرڤەری لاپتۆپ `http://` ی سادەیە؛ وشەی نهێنی، تۆکنەکان و ID token ی Google بێ شفرە دەڕۆن. بۆ دیمۆ لەسەر هۆتسپۆتی
  خۆتان باشە؛ پێش هەر pilot ێک HTTPS پێویستە.
- سنوورەکانی کۆد (هەر ئیمەیڵێک، هەر IP یەک، هەمووان) لە PostgreSQL دان، چونکە یەک پرۆسەیە. بۆ چەند سێرڤەرێک: Redis یان Flask-Limiter.
- ژمارەی مۆبایل پشتڕاست ناکرێتەوە بەڵام تاکەیە: کەسێک دەتوانێت ژمارەی کەسێکی تر بگرێت و ئەو کەسە `phone_taken` وەردەگرێت.
  شارەوانی بە دەست چاکی دەکات.
- ئیمەیڵ لە ژمارەی مۆبایل لاوازترە دژی چەند هەژمارێکی یەک کەس (Gmail ی نوێ ئاسانە)؛ سنووری ڕۆژانە و سەلماندنی AI ی خاڵەکان
  هێشتا سنوورداری دەکەن.

### دواتر (لەم بەشەدا نەکراون)

- خێزان: چەند هەژمار بۆ یەک ماڵ.
- Sign in with Apple (App Store ئەگەر Google هەبێت داوای دەکات؛ Guideline 4.8).
- چوونەژوورەوە تەنها بە کۆدی ئیمەیڵ، و گۆڕینی وشەی نهێنیی لەبیرچوو بە کۆدی ئیمەیڵ.
- بانکی دیجیتاڵی بۆ پارەی مانگانە، و چاککردنەوەی پارەیەکی هەڵە لە داشبۆرد.
- لیستی گشتیی بازرگانییە پەسەندکراوەکان.
- `flutter_secure_storage` بۆ تۆکن، HTTPS، سنووری هەوڵی چوونەژوورەوە.
- شاشەی سڕینەوەی هەژمار (FK ەکان پێشتر `ON DELETE CASCADE` ن).
- پشتڕاستکردنەوەی ئیمەیڵ بۆ هەژمارە کۆنەکان (ئێستا بە ژمارە دەچنە ژوورەوە).
- endpoint ە کۆنەکان (pins، bins...) هێشتا بۆ JSON ی نا-object `500` دەدەن، و هەندێک پەیامی کوردییان لە `strings.py` دا نییە.

## ١١. پێش چوونە سەر شانۆ

```bash
cd backend
python tools/preflight.py --model --server http://localhost:5000          # ڕۆژی دیمۆ: دەبێت 0 ✗ بێت
DETECTOR_KIND=colorblob python tools/preflight.py --rehearsal --server http://localhost:5000   # ڕاهێنان
```

هەر پشکنینێک یەک هێڵە: ✓ باشە، ⚠ سەیری بکە، ✗ پێش دیمۆ چاکی بکە (exit code 1): داتابەیس و migration ەکان، هەژماری شارەوانی
(و ئایا هێشتا `staff1234` ە)، گەڕەکەکان، فۆڵدەری وێنە، ناسەر و مۆدێل (`--model` باری دەکات و کاتەکەی دەپێوێت)، Leaflet، ستیکەری QR،
`SECRET_KEY`، `SIM_CAMERA`، وەسفی Claude، کۆدی ئیمەیڵ (`console` ⚠ دەدات: لە دیمۆدا ئاساییە، بۆ pilot نا)، `OTP_PEPPER`،
`OTP_REQUIRED`، Google (ڕێکخستن و ئایا کلیلەکانی Google دەگەنە لاپتۆپ)، IP ی لاپتۆپ و ئەو ناونیشانەی لە مۆبایل دەنووسرێت؛ بە `--server` سێرڤەری کاراوەش: ئایا
داتابەیسەکەی دەخوێنێتەوە (`/neighbourhoods`)، کام ناسەر بەکاردێنێت، ئایا هەمان مۆدێلی ئەم پەنجەرەیە بەکاردێنێت (نەک فایلێکی تر)،
و ئایا `/sim` کراوەیە. هەموو هەنگاوەکانی ڕۆژی دیمۆ و سیناریۆی سەر شانۆ: `docs/DEMO.md`.

## ١٢. چی فێربوون (لەم ڕاهێنانەدا دۆزرانەوە)

- وێنەی «دوا»ی هەمان شوێن زۆر لە وێنەی «پێش» دەچێت؛ پشکنینی دووبارە دەبێت وێنەکانی هەمان ڕاپۆرت لاببات.
- ستیکەری QR ی هەمان زبڵدان لە هەموو پاککردنەوەیەکدا یەکسانە؛ تەنها فریمەکانی شوێنەکە بۆ دووبارە بپشکنن.
- ئەگەر Leaflet لە CDN بێت و ئینتەرنێت نەبێت، هەموو داشبۆردەکە دەوەستێت؛ Leaflet لە ناو ئەپەکەدایە.
- مۆبایلی ئەندرۆید بێ `usesCleartextTraffic` ناتوانێت بگاتە `http://` ی لاپتۆپ.

## مۆڵەت

Ultralytics YOLOv8 بە AGPL-3.0 یە. پێش فرۆشتنی بەرهەمێکی داخراو بە شارەوانی، ئەمە یەکلا بکەنەوە.
داتاسێتی TACO بە CC BY 4.0 یە؛ لە سلایدەکاندا ناوی بهێنن. Leaflet بە BSD-2 یە (`backend/app/static/leaflet/LICENSE`).
