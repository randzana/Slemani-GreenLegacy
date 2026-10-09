# Feature: Three account types + Google sign-in + phone OTP — GreenLegacy Slemani

You are a senior full-stack engineer working in the **GreenLegacy Slemani** repository (Flask + PostgreSQL/PostGIS backend, Flutter app, municipality web dashboard). You write production-quality, tested, secure code, and you keep to the conventions the codebase already has instead of adding your own.

Your task is to add **three account types** (individual citizen, business place, household), **Google sign-in**, and **phone OTP verification** for every new registration. Everything you need is below: what the codebase does today, the design decisions already made (with reasons, so you don't reopen them), the data model, the API contract, the security requirements, the tests, and a phased plan.

**Ground rules**
- **If the code disagrees with this prompt, trust the code.** Report the difference and propose a fix. Don't force the prompt's assumption.
- **Work in phases (section 13).** Each phase ends with every test passing (`python -m pytest tests -q`) and `flutter analyze` clean. Stop after each phase and report back in the format in section 17.
- **Don't guess at product decisions.** Section 16 lists the open questions. Ask them before Phase 1 and use the stated default for anything I haven't answered.
- **Protect the uncommitted work.** The working tree has uncommitted changes (pins, bins, notifications, `slemani/`). Never run `git stash`, `git reset`, `git checkout -- .` or `git clean`. Before you start, create a branch `feature/account-types-google-otp` and ask me whether to commit the existing work first.

---

## 1. The codebase today (verified facts; read these files before changing anything)

**Backend (`backend/`)**
- `app/__init__.py`: `create_app(overrides=None, detector=None, describer=None)`. External services are **injected** (that's how tests swap in fakes). Blueprints: `auth`, `routes`, `rewards`, `admin`, `simulator`. The CORS header allows only `GET, POST, OPTIONS`.
- `app/db.py`: raw SQL through psycopg 3 (no ORM). There is one connection per request. `close_db` **commits at teardown when no exception was raised, and rolls back only on an exception**. A JSON 4xx response still commits.
- `app/auth.py`:
  - `make_token` issues HS256 JWTs: `sub`, `role`, `iat`, `exp`, signed with `SECRET_KEY`.
  - `login_required` decodes **any** HS256 JWT signed with `SECRET_KEY`, then does `int(payload["sub"])`. It also rejects tokens issued before the user's `created_at`.
  - Also defines `staff_required`, `public_user`, `POST /auth/signup` (name, phone, password ≥ 6, neighbourhood_id), `POST /auth/login` (phone + password) and `GET /neighbourhoods`.
- `schema.sql`: `users.phone TEXT NOT NULL UNIQUE` (the comment reads *"one account per phone number"*). This is the anti-fraud anchor of the points system. `password_hash NOT NULL`. `role IN ('citizen','staff')`.
- `role = 'citizen'` is the filter in `routes.leaderboard`, `points.ranks` and `admin.py` (stats and neighbourhoods). Every league and count depends on it.
- **Schema workflow.** `schema.sql` plus `seed.py` build a fresh database and wipe it. `migrations/00N_*.sql` upgrade an existing database without data loss. Migrations are idempotent (`IF NOT EXISTS`, `BEGIN/COMMIT`), and `tools/preflight.py` reports which ones are missing. The last one is `005_pin_registrations.sql`.
  - ⚠ `trash_bins`, `bin_disposals` and point kind `'bin_disposal'` exist in `schema.sql` but have **no migration**. Don't fix this silently; tell me about it.
- **Text.** All user-facing Kurdish (Sorani) text lives in `app/strings.py` (`REASONS`, `reason(code)`). Errors are always `{"error": <code>, "message": reason(code)}`, built by `auth.error(code, status)`.
- **Config.** Every setting is an environment variable read in `app/config.py` and documented in the README's settings table (written in Kurdish).
- **Tests.** pytest runs against a real PostGIS test database (`greenlegacy_test`); `conftest.py` re-seeds it for every test, and the `Api` helper drives the phone's flow. `tests/test_races.py` sends truly concurrent requests (threads plus a barrier). Follow that pattern for race tests.

**Mobile (`mobile/`)**
- `lib/api.dart`: a singleton `Api.instance` using `http`. The base URL and token live in `shared_preferences`. `ApiException(message, code)`: **the UI branches on `code`, never on `message`**. `onSignedOut` runs on a 401 `unauthorized`.
- `lib/screens/auth_screen.dart`: a single login/signup screen with a server-URL field, name, phone, password and a neighbourhood dropdown.
- The app is right-to-left everywhere (`main.dart`). Every string is in `lib/strings.dart` (class `S`). Phone and number fields are `TextDirection.ltr`. Colours come from `theme.dart`.
- `mobile/ios/` and `mobile/android/` are **gitignored and generated** by `setup_ios.py` and `setup_android.py`. Any native configuration (Info.plist keys, URL schemes, Gradle settings) must be added **to those scripts**, not to the generated folders.
- App identifiers come from `flutter create --org krd.greenlegacy --project-name slemani_green_legacy`.
- `flutter_map`, `geolocator` (`lib/location.dart`) and `latlong2` are already installed. Reuse them for picking a location.

**Runtime**
- One Flask process runs on a laptop over **plain HTTP**. Phones reach it over a hotspot, and internet access can be weak or missing on demo day.

---

## 2. Goal and user stories

### Account types (`account_type`)
| Code | Kurdish label | What it represents |
|---|---|---|
| `individual` | هاوڵاتی | A person. This is today's account, unchanged. |
| `business` | شوێنی بازرگانی | A shop, restaurant, café or other business with a fixed location. The municipality verifies it. |
| `household` | ماڵ | A home in a neighbourhood. Its exact location is private. |

### Registration methods
1. **Phone + password** (exists today). Now it also needs phone OTP verification.
2. **Google sign-in** (new). It also needs phone OTP verification when the account is created.

### User stories (each one is an acceptance criterion)
- **US-1.** As a new user, I choose one of three account types before entering any details, and the form only asks for what that type needs.
- **US-2.** As a new user, I tap "Continue with Google", choose a type, fill in the profile, verify my phone with a 6-digit SMS code, and land on the home screen signed in.
- **US-3.** As a returning Google user, one tap on "Continue with Google" signs me in. I'm not asked for OTP or profile details again.
- **US-4.** As an existing phone + password user, if I later use Google and verify the same phone, I'm offered **"link Google to your existing account"**. Accepting signs me into my old account with my points intact, and no duplicate account is created.
- **US-5.** As a business, I can use the app right away, but I'm shown as "awaiting municipality approval". I only appear in the business league and on public business listings after staff verify me.
- **US-6.** As a household, my home's location is used only to work out my neighbourhood. Nobody except me and municipality staff can see it.
- **US-7.** As municipality staff, I see a queue of pending businesses on the dashboard and can verify one, or reject it with a reason that the business sees in the app.
- **US-8.** As someone using an old app build, `/auth/login` still works, and so does `/auth/signup` when `OTP_REQUIRED=0`.

---

## 3. Scope

**In scope.** Database migration and schema changes; phone normalisation; OTP service and endpoints; Google ID-token verification; account-type registration through both methods; Google account linking; `/me` and profile editing; separate leagues; the business verification queue on the dashboard; the Flutter registration flow; Kurdish strings; preflight checks; README updates; tests.

**Out of scope** (list these as follow-ups at the end; don't build them):
- Family members inside a household (several logins sharing one home).
- Sign in with Apple. Note: publishing to the App Store with Google login triggers App Store Review Guideline 4.8.
- Passwordless OTP login and email/password accounts.
- Businesses acting as voucher partners.
- Moving the token from `shared_preferences` to `flutter_secure_storage`.
- HTTPS.
- Rate limiting on `/auth/login`.
- An account-deletion screen. The `ON DELETE CASCADE` foreign keys go in now anyway.
- Forcing accounts created before OTP existed to verify their phone. They are grandfathered, with `phone_verified_at` left NULL.

---

## 4. Design decisions (already made; implement them as written)

| # | Decision | Why |
|---|---|---|
| D1 | **`role` and `account_type` are separate columns.** `role` stays authorisation (`citizen` or `staff`). `account_type` is what the account represents. Staff rows get `account_type = 'individual'`. | Mixing "who can do what" with "what kind of account this is" would mean editing every permission check. Today's 9+ `role = 'citizen'` queries keep their meaning. |
| D2 | **Class-table inheritance.** `users` stays the slim core that authentication reads on every request. Type-specific data goes in 1:1 tables, `business_profiles` and `household_profiles`. | Each type gets real `NOT NULL` and `CHECK` constraints (a business *must* have a location) without a wide `users` table full of nullable columns or untyped JSONB. |
| D3 | **Phone is the identity anchor.** Every account, of every type and sign-in method, has exactly one OTP-verified phone. `users.phone` stays `UNIQUE NOT NULL`. So "OTP for Google registration" means **Google proves the email; OTP proves the phone.** | Anyone can create many Google accounts. One account per verified phone is what stops points farming (the trust and ledger design depends on it). |
| D4 | **External logins live in `user_identities(provider, subject)`.** The key is Google's `sub`, never the email. | Emails change and get recycled; `sub` doesn't. This table also takes Apple later without schema churn. |
| D5 | **Google ID tokens are verified on the server** with `google-auth`. The client sends only the raw ID token; email and name are read from the verified claims. | Client-supplied identity data can't be trusted. |
| D6 | **Every JWT carries a `typ` claim.** Access tokens use `typ=access`. Short-lived step tokens use `typ=phone_verified` and `typ=google_signup` (10 minutes, with `aud="gl-step"`). Each endpoint accepts exactly one `typ`. `login_required` rejects anything that isn't an access token (a missing `typ` counts as a legacy access token). | Today `login_required` would accept *any* JWT signed with `SECRET_KEY`, so a step token whose `sub` held a number could pass as a user. Token confusion is a real bug class. |
| D7 | **We generate and verify OTP codes ourselves; the SMS provider only delivers them.** Delivery goes through an `OtpSender` interface injected in `create_app(..., otp_sender=None)`, the same way `detector` is. Implementations: `ConsoleOtpSender` (writes the code to the server log; laptop/demo only), `FakeOtpSender` (tests; stores codes in memory), and one real SMS adapter once I name the provider. | Keeps the security logic testable and the provider replaceable. The console sender makes the demo work with no SMS credit and no internet. |
| D8 | **Phones are normalised to E.164 (`+9647XXXXXXXXX`) at every entry point** (signup, login, OTP, seed) using the `phonenumbers` library with default region `IQ`. The migration converts existing rows. | Without this, `07501234567` and `+9647501234567` would become two "unique" accounts (a fraud hole), and SMS providers need E.164. |
| D9 | **Leagues.** The citizen league is `role='citizen' AND account_type='individual'`, which is the same as today. Businesses (verified only) and households get their own rankings. The neighbourhood league adds up **individual + household** points and **leaves out businesses**. *(Confirm with me; see section 16.)* | One large business shouldn't decide a neighbourhood's rank. |
| D10 | **Business verification.** The status moves from `pending` to `verified` or `rejected`, decided by staff. Pending and rejected businesses can sign in and use every citizen feature, but they're hidden from the business league and public listings. Editing `business_name`, `category` or `location` sets the status back to `pending`. | The app stays useful from the first minute while the public business directory stays trustworthy. |
| D11 | **Household location is private personal data.** It's returned only by the owner's `/me` and by staff endpoints. Public responses are built from an explicit **allow-list serializer**, and a test checks for leaks. | A map of people's homes is sensitive data. |
| D12 | **Backwards compatible.** `/auth/login` doesn't change. `/auth/signup` keeps its fields; `account_type` defaults to `individual`. When `OTP_REQUIRED=1` (the default), signup needs a `phone_verification_token`. When it's `0` (offline rehearsal only), it doesn't, and preflight warns. | Old app builds on teammates' phones keep working. |
| D13 | **No new infrastructure.** OTP state and rate-limit counters live in PostgreSQL; no Redis. | It's a single process on a laptop. Mention Redis or Flask-Limiter as the scaling path in the README. |

---

## 5. Data model: `migrations/006_account_types_google_otp.sql` (and the same changes in `schema.sql`)

Treat this as a starting point; you may adjust names if you explain why. The migration must be **idempotent** (running it twice is safe) and wrapped in `BEGIN/COMMIT`. Also update `schema.sql`, including its `DROP TABLE IF EXISTS` list, so a fresh `seed.py` produces exactly the same schema as old database + migration.

```sql
BEGIN;

-- 1. users: account type, verified contact fields, Google-only accounts have no password
ALTER TABLE users ADD COLUMN IF NOT EXISTS account_type TEXT NOT NULL DEFAULT 'individual';
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_account_type_check;
ALTER TABLE users ADD CONSTRAINT users_account_type_check
    CHECK (account_type IN ('individual', 'business', 'household'));
ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT;                 -- verified Google email; display/contact only
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_verified_at TIMESTAMPTZ;  -- NULL = created before OTP existed
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;            -- Google-only accounts
CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_unique ON users (lower(email)) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS users_account_type_idx ON users (account_type);

-- 2. external identities (Google now, Apple later)
CREATE TABLE IF NOT EXISTS user_identities (
    id            BIGSERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider      TEXT NOT NULL CHECK (provider IN ('google')),
    subject       TEXT NOT NULL,                 -- Google "sub": stable, never the email
    email         TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at TIMESTAMPTZ,
    UNIQUE (provider, subject),
    UNIQUE (user_id, provider)                   -- one Google account per user
);

-- 3. business profile (1:1)
CREATE TABLE IF NOT EXISTS business_profiles (
    user_id             INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    business_name       TEXT NOT NULL CHECK (char_length(btrim(business_name)) BETWEEN 2 AND 120),
    category            TEXT NOT NULL CHECK (category IN
                        ('restaurant','cafe','shop','supermarket','bakery','hotel','workshop','other')),
    license_number      TEXT CHECK (license_number IS NULL OR char_length(license_number) <= 64),
    address             TEXT CHECK (address IS NULL OR char_length(address) <= 300),
    location            GEOGRAPHY(POINT, 4326) NOT NULL,
    verification_status TEXT NOT NULL DEFAULT 'pending'
                        CHECK (verification_status IN ('pending','verified','rejected')),
    verified_by         INTEGER REFERENCES users(id),
    verified_at         TIMESTAMPTZ,
    rejection_reason    TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (verification_status <> 'rejected' OR rejection_reason IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS business_profiles_location_idx ON business_profiles USING GIST (location);
CREATE INDEX IF NOT EXISTS business_profiles_status_idx ON business_profiles (verification_status);

-- 4. household profile (1:1) — location is private (D11)
CREATE TABLE IF NOT EXISTS household_profiles (
    user_id         INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    household_name  TEXT NOT NULL CHECK (char_length(btrim(household_name)) BETWEEN 2 AND 80),
    residents_count SMALLINT NOT NULL CHECK (residents_count BETWEEN 1 AND 30),
    address         TEXT CHECK (address IS NULL OR char_length(address) <= 300),
    location        GEOGRAPHY(POINT, 4326) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5. OTP codes — only a keyed hash is stored, never the code
CREATE TABLE IF NOT EXISTS otp_codes (
    id            BIGSERIAL PRIMARY KEY,
    phone         TEXT NOT NULL,                     -- E.164
    purpose       TEXT NOT NULL CHECK (purpose IN ('verify_phone')),
    code_hash     TEXT NOT NULL,                     -- HMAC-SHA256(OTP_PEPPER, phone|purpose|code)
    attempts      SMALLINT NOT NULL DEFAULT 0,
    expires_at    TIMESTAMPTZ NOT NULL,
    consumed_at   TIMESTAMPTZ,
    superseded_at TIMESTAMPTZ,                       -- a newer code was sent
    request_ip    INET,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS otp_codes_phone_idx ON otp_codes (phone, created_at DESC);
CREATE INDEX IF NOT EXISTS otp_codes_ip_idx ON otp_codes (request_ip, created_at DESC);
-- at most one live code per phone+purpose; a resend supersedes the old one in the same transaction
CREATE UNIQUE INDEX IF NOT EXISTS otp_codes_one_live
    ON otp_codes (phone, purpose) WHERE consumed_at IS NULL AND superseded_at IS NULL;

-- 6. phone normalisation of existing rows (D8) — see below
COMMIT;
```

**Normalising existing phones (step 6).** Convert the deterministic Iraqi formats in SQL:
- `^07\d{9}$` becomes `'+964' || substr(phone, 2)`
- `^9647\d{9}$` becomes `'+' || phone`
- `^\+9647\d{9}$` stays as it is

**Before converting**, run a `DO` block that `RAISE EXCEPTION`s and lists the clashing rows if normalising would create duplicates, so the migration aborts and nothing changes. Leave rows in other formats unchanged and print them with `RAISE NOTICE`.

**Also update:**
- `seed.py`: store the staff phone normalised, with `phone_verified_at = now()`.
- `tools/preflight.py`: make it aware of migration 006.

---

## 6. API contract

**Error shape everywhere:** `{"error": "<code>", "message": reason(code)}`, plus optional fields `retry_after` (seconds), `attempts_left`, or `fields` (field-level validation errors, e.g. `{"business.location": "required"}`). Every new error code gets a Sorani message in `app/strings.py` (drafts in section 9.4).

### Public
| Method & path | Body | Success | Errors |
|---|---|---|---|
| `GET /auth/config` | — | `200 {google: {enabled, server_client_id}, otp: {required, length, ttl_seconds, resend_seconds}, account_types: [...], business_categories: [{code, name}]}`. **No secrets.** The app calls this after the server URL is set. | — |
| `POST /auth/otp/request` | `{phone}` | `200 {sent: true, expires_in, resend_in}`. **Same response whether or not the phone already has an account** (no account enumeration). | `400 invalid_phone`, `400 phone_not_allowed` (country not on the allow-list), `429 otp_too_soon` + `retry_after`, `429 otp_rate_limited` + `retry_after`, `503 otp_send_failed` |
| `POST /auth/otp/verify` | `{phone, code}` | `200 {phone_verification_token, expires_in, phone_has_account}`. Saying whether the phone has an account is fine here because the caller has just proved they own it. | `400 otp_invalid` + `attempts_left`, `400 otp_expired`, `429 otp_locked` |
| `POST /auth/signup` *(extended)* | `{name, password, phone_verification_token, account_type?, neighbourhood_id?, business?, household?}` | `201 {token, user}` | `400 missing_fields`, `400 invalid_account_type`, `400 invalid_profile` + `fields`, `401 phone_not_verified`, `409 phone_taken` |
| `POST /auth/login` | unchanged (phone normalised) | unchanged | unchanged |
| `POST /auth/google` | `{id_token}` | Known identity: `200 {status: "signed_in", token, user}`. New identity: `200 {status: "registration_required", google_signup_token, profile: {name, email}}`. **No row is created yet.** | `401 google_token_invalid`, `403 google_email_unverified`, `503 google_unavailable`, `404 google_disabled` |
| `POST /auth/google/register` | `{google_signup_token, phone_verification_token, account_type, name?, neighbourhood_id?, business?, household?}` | `201 {token, user}`. Creates the user, identity and profile in **one transaction**. | `400 invalid_profile` + `fields`, `401 phone_not_verified` / `google_signup_expired`, `409 phone_has_account` (body includes `can_link: true`), `409 google_already_linked` |
| `POST /auth/google/link` | `{google_signup_token, phone_verification_token}` | `200 {token, user}`. Attaches the Google identity to the existing account that owns the verified phone. | `401 ...`, `404 no_account_for_phone`, `409 google_already_linked` |

**Rules for the signup and register endpoints:**
- The phone is taken **from the verified step token, never from the request body**.
- `neighbourhood_id` for business and household accounts is **derived on the server** with `ST_Covers(n.boundary, location)` when boundaries are loaded. Otherwise the body's value is used. For individuals it works as it does today.
- Locations must fall inside a configurable service area (`SERVICE_AREA_BBOX`, defaulting to roughly the Sulaimani governorate). Otherwise the response is `400 invalid_profile` with `fields: {"<type>.location": "outside_service_area"}`.

### Authenticated
| Method & path | Notes |
|---|---|
| `GET /me` | Adds `account_type`, `email`, `phone_verified` (bool), `auth_methods` (`["password","google"]` as applicable) and `profile`. For a business the profile includes `verification_status` and `rejection_reason`. For a household it includes `location`, since the caller is the owner. `rank` is the rank **within the caller's own league**. |
| `POST /me/profile` | Updates the caller's type-specific profile. Use `POST`, not `PATCH`: the CORS header only allows GET/POST. For businesses, D10 applies (name, category or location changes reset the status to pending). Changing `account_type` is **not** allowed in v1. |
| `GET /leaderboard` | Keeps `neighbourhoods` and `citizens` with today's shape (the old app depends on them). Adds `businesses` (verified only: `business_name`, `category`, `neighbourhood`, `points`) and `households` (`household_name`, `neighbourhood`, `points`; **no location**). Top 10 each. |

### Staff (`staff_required`)
| Method & path | Notes |
|---|---|
| `GET /admin/businesses?status=pending` | Includes phone, license number, location, created_at and owner name. |
| `POST /admin/businesses/<user_id>/review` | `{decision: "verify" or "reject", reason?}`. A reason is required when rejecting. Records `verified_by` and `verified_at`. Reviewing again overwrites the decision (it's not one-way), and every decision is written in an audit-friendly way. |
| `GET /admin/stats` | Adds counts per account type and a pending-business count (used for the dashboard badge). |

---

## 7. Auth flows

```
A) Phone + password (new account)
App: choose type → profile form → phone → POST /auth/otp/request → code → POST /auth/otp/verify
   → POST /auth/signup {…, phone_verification_token} → 201 token → Home

B) Google, first time
App: Google SDK → id_token → POST /auth/google → registration_required + google_signup_token
   → choose type → profile form (name pre-filled from Google) → phone → OTP request/verify
   → POST /auth/google/register → 201 token → Home
   └─ 409 phone_has_account → dialog "Link Google to your existing account?"
        → yes: POST /auth/google/link → 200 token → Home   (no profile created; existing account kept)

C) Google, returning
App: Google SDK → id_token → POST /auth/google → signed_in → Home

D) Old app build
POST /auth/login unchanged; POST /auth/signup works without OTP only when OTP_REQUIRED=0
```

---

## 8. Security requirements (check each one; most have a test in section 12)

### OTP
1. **Generating the code:** `secrets.randbelow(10**OTP_LENGTH)`, zero-padded, 6 digits by default. Never use `random`.
2. **Storing the code:** store only `HMAC-SHA256(OTP_PEPPER, f"{phone}|{purpose}|{code}")`. Compare with `hmac.compare_digest`. The code never appears in the database, in API responses (not even in dev), or in logs. The one exception is `ConsoleOtpSender`, which is how the demo works.
3. **Lifetime:** `OTP_TTL_SECONDS=300`. `OTP_MAX_ATTEMPTS=5` per code; after that the code is dead (`429 otp_locked`) and a new one has to be requested.
4. **Sending limits:**
   - `OTP_RESEND_SECONDS=60` cooldown per phone.
   - `OTP_MAX_PER_PHONE_HOUR=5` and `OTP_MAX_PER_IP_HOUR=20`.
   - A global `OTP_MAX_PER_HOUR` ceiling, which protects the SMS bill.
   - All counted from `otp_codes` in PostgreSQL.
   - A resend marks the previous live code `superseded_at` and inserts the new one **in the same transaction**. If two concurrent requests both try, the `otp_codes_one_live` unique index stops one of them; turn that violation into `429 otp_too_soon`.
5. **Single use, safe under races:** consume the code with one atomic statement: `UPDATE otp_codes SET consumed_at = now() WHERE id = %s AND consumed_at IS NULL AND superseded_at IS NULL AND expires_at > now() AND attempts < %s RETURNING id`. Two simultaneous correct verifications give exactly one success.
6. **⚠ A failed attempt must persist.** `close_db` rolls back on an *exception*. If a wrong code is handled by raising, the `attempts + 1` is rolled back and the code becomes brute-forceable. Increment `attempts` with `UPDATE … RETURNING attempts` and **return** the 400 response; don't raise. Add a test that sends 6 wrong codes and gets `otp_locked` on the 6th.
7. **SMS pumping protection:** `OTP_ALLOWED_COUNTRY_CODES=964` by default. Other countries get `phone_not_allowed`.
8. **No enumeration:** `/auth/otp/request` gives the same response for registered and unregistered phones.
9. **Logs:** mask phones (`+96475*****67`). Never log codes, ID tokens or step tokens.

### Google
10. **Verify the token with `google-auth`** (`google.oauth2.id_token.verify_oauth2_token`):
    - The signature checks out.
    - `iss` is `accounts.google.com` or `https://accounts.google.com`.
    - `aud` is in `GOOGLE_CLIENT_IDS`. Pass the list if the installed version supports it; otherwise check it by hand, but **never skip it**.
    - `exp` hasn't passed, allowing about 10 seconds of clock skew.
    - `email_verified` is `true`.
11. **Cache Google's public certificates**, respecting Cache-Control, so a flaky hotspot doesn't break every sign-in. If the certificates can't be fetched and there's no cache, return `503 google_unavailable` with a clear Kurdish message.
12. **Identity:** key on `sub`. Request only the `openid email profile` scopes. Store no Google access or refresh tokens; we only need to know who the person is.
13. **Transport:** an ID token is a bearer credential for about an hour. Note in the README that anything beyond the laptop demo needs HTTPS.

### JWT and accounts
14. **Token types (D6):**
    - `make_token` adds `typ: "access"`.
    - `login_required` rejects any `typ` other than `access`. A test proves a `phone_verified` step token gets 401 on `/me`.
    - Step tokens carry `typ`, `aud="gl-step"`, `exp` of 10 minutes, and either `phone` or `google_sub`/`email`/`name`. Each endpoint checks `typ` and `aud` explicitly.
15. **One transaction for account creation.** The user row, the identity and the profile are written in a single transaction (the per-request connection already provides one; don't commit midway).
    - If you catch `psycopg.errors.UniqueViolation` and then keep running queries, wrap the risky insert in `with get_db().transaction():` (a savepoint). After an error, the outer transaction is aborted.
    - Map unique violations to `409` with the right code (`phone_taken`, `google_already_linked`, and so on).
16. **Validation:** check input at the API boundary with a small validator per account type. Trim strings; reject unknown keys inside `business` and `household`; reject a profile object that doesn't match the `account_type` (a household body sent with `account_type: "business"` gets 400).
17. **Privacy (D11):** build every public response from explicit allow-list serializers (`public_business(row)`, `public_household(row)`). Never return `SELECT *` rows. A test checks that household coordinates appear in no public response (`/leaderboard`, `/reports`, `/reports/<id>`, `/pins`).
18. **Permissions by type:** if any route needs to be limited to one type, add an `account_type_required(*types)` decorator next to `staff_required`. Don't scatter `if g.user["account_type"] == …` checks across the code.

---

## 9. Mobile (Flutter)

### 9.1 Dependencies and native setup
- Add `google_sign_in`. **Check the current major version's API before writing code.** v7 changed it to `GoogleSignIn.instance.initialize(serverClientId: …)` and `authenticate()`; don't write v6-style code against v7. Pass the **Web client ID** as `serverClientId` so Android gives an ID token whose `aud` the server accepts.
- Client IDs are **not hard-coded**. The app reads `server_client_id` from `GET /auth/config` (the server URL is chosen at runtime, so the server is the source of truth). If Google is disabled or unreachable, hide the Google button.
- **iOS:** extend `setup_ios.py` to add `GIDClientID` and the reversed-client-ID `CFBundleURLTypes` entry to Info.plist, reading the `GOOGLE_IOS_CLIENT_ID` environment variable. If that's unset, skip it with a printed note.
- **Android:** extend `setup_android.py` (or its printed instructions) with what Google needs: an Android OAuth client with package name `krd.greenlegacy.slemani_green_legacy` and the debug keystore's SHA-1. Print the exact `keytool` command. Check whether the current `google_sign_in` needs `google-services.json`; it shouldn't without Firebase.

### 9.2 Screens (new folder `lib/screens/registration/`)
- **`auth_screen.dart`:** add a "Continue with Google" button and an "or" divider. The existing sign-up toggle now opens the registration flow instead of the inline fields. Keep the server-URL field exactly as it works today.
- **`account_type_screen.dart`:** three large cards (icon, title, one-line description) for individual, business and household.
- **`profile_form_screen.dart`:** fields per type.
  - Individual: name and neighbourhood (as today).
  - Business: name, category dropdown (from `/auth/config`), optional license number, address, and a **map pin picker**.
  - Household: name, residents stepper (1–30), address, and a map pin picker with a visible note that the home location stays private.
  - The pin picker reuses `flutter_map` and `location.dart`, starts at the current location or at `MAP_CENTER`, and shows a field error for a pin outside the service area.
- **`phone_otp_screen.dart`:**
  - A phone field (LTR) and a "send" button.
  - Then a 6-digit field with `AutofillHints.oneTimeCode`, a numeric keyboard and LTR digits.
  - A resend countdown driven by the server's `resend_in` / `retry_after`, not a client constant.
  - Shows `attempts_left`. Maps error codes to the UI (for `otp_locked`, clear the field and show "request a new code").
- **Link dialog:** shown on `409 phone_has_account` to offer linking Google to the existing account.

### 9.3 State, API and existing screens
- Keep a `RegistrationDraft` class (type, profile fields, Google signup token, phone verification token) and pass it through the flow, in memory only. **Don't add a state-management package**; the app uses `StatefulWidget`. The draft must survive the user switching to the SMS app and back.
- `api.dart`: add `authConfig()`, `requestOtp()`, `verifyOtp()`, an extended `signup(...)`, `googleSignIn(idToken)`, `googleRegister(...)`, `googleLink(...)` and `updateProfile(...)`. Reuse `_post`, `_guard` and `ApiException.code`. `logout()` also signs out of Google.
- `profile_screen.dart`: show an account-type badge. For businesses, add a verification-status chip (pending, verified, or rejected with its reason) and an edit-profile entry.
- `league_screen.dart`: a segmented control for the three leagues, all from the single `/leaderboard` response.
- Everything stays RTL, works in dark mode, uses `theme.dart` colours, and puts **every** string in `S`. `flutter analyze` must stay clean.

### 9.4 Draft Sorani strings (I will review the Kurdish; keep the tone of the existing strings)
| Key | Draft |
|---|---|
| individual / business / household | هاوڵاتی / شوێنی بازرگانی / ماڵ |
| individual description | بۆ تاکەکەس: ڕاپۆرت بکە، پاکی بکەرەوە، خاڵ کۆبکەرەوە |
| business description | بۆ دوکان، چێشتخانە، کافێ و شوێنە بازرگانییەکان |
| household description | بۆ ماڵێک لە گەڕەکەکەت؛ شوێنی ماڵەکەت نهێنی دەمێنێتەوە |
| categories | چێشتخانە، کافێ، دوکان، سوپەرمارکێت، نانەواخانە، هوتێل، وەرشە، هی تر |
| continueWithGoogle / or | بەردەوامبوون بە Google / یان |
| otpTitle | پشتڕاستکردنەوەی ژمارەی مۆبایل |
| otpSent(phone) | کۆدێکی ٦ ژمارەیی نێردرا بۆ {phone} |
| resend / resendIn(n) | ناردنەوەی کۆد / دەتوانیت دوای {n} چرکە دووبارە بینێریت |
| otp_invalid / otp_expired / otp_locked | کۆدەکە هەڵەیە / کاتی کۆدەکە بەسەرچووە؛ کۆدێکی نوێ داوا بکە / هەوڵی زۆر درا؛ کۆدێکی نوێ داوا بکە |
| otp_too_soon / otp_rate_limited | تکایە چەند چرکەیەک چاوەڕێ بکە / داواکاریی زۆر کرا؛ دواتر هەوڵ بدەرەوە |
| invalid_phone / phone_not_allowed | ژمارەی مۆبایل دروست نییە / تەنها ژمارەی مۆبایلی عێراق قبووڵ دەکرێت |
| google_token_invalid / google_unavailable | چوونەژوورەوە بە Google سەرکەوتوو نەبوو / ناتوانرێت پەیوەندی بە Google بکرێت؛ ئینتەرنێتەکەت بپشکنە |
| phone_has_account | ئەم ژمارەیە پێشتر هەژمارێکی هەیە؛ دەتەوێت Google بەو هەژمارەوە ببەستیتەوە؟ |
| business status | چاوەڕێی پەسەندکردنی شارەوانی / پەسەندکراو / ڕەتکرایەوە |
| householdPrivacyNote | شوێنی ماڵەکەت تەنها بۆ دیاریکردنی گەڕەکەکەت بەکاردێت و بە کەس پیشان نادرێت |

---

## 10. Municipality dashboard (`app/templates/dashboard.html` + `app/admin.py`)
- **New tab** "بازرگانییەکان" with a pending-count badge, built the same way as the existing tabs (`data-tab`, `.table-wrap` tables).
  - Columns: name, category, neighbourhood, phone, license, registered, and a "show on map" link.
  - Buttons: **Verify**, and **Reject** (reason required).
- **Stats cards:** accounts per type and the number of pending businesses.
- **League tab:** a type filter.
- **Homes are not shown on the dashboard map in v1.** Show only the household count per neighbourhood (privacy by default; D11).

---

## 11. Configuration (`app/config.py` plus a row for each in the README settings table)

| Variable | Default | Meaning |
|---|---|---|
| `OTP_REQUIRED` | `1` | `0` lets `/auth/signup` work without OTP (offline rehearsal only; preflight warns) |
| `OTP_SENDER` | `console` | `console` (writes the code to the server log; demo), `fake` (tests), or `<provider>` (real SMS) |
| `OTP_PEPPER` | — | Secret key for the code HMACs. Preflight warns if unset; it falls back to a key derived from `SECRET_KEY` with a fixed label. |
| `OTP_LENGTH` / `OTP_TTL_SECONDS` / `OTP_MAX_ATTEMPTS` | `6` / `300` / `5` | |
| `OTP_RESEND_SECONDS` / `OTP_MAX_PER_PHONE_HOUR` / `OTP_MAX_PER_IP_HOUR` / `OTP_MAX_PER_HOUR` | `60` / `5` / `20` / `200` | |
| `OTP_ALLOWED_COUNTRY_CODES` | `964` | Comma-separated list |
| `GOOGLE_CLIENT_IDS` | empty (Google disabled) | Comma-separated list of allowed `aud` values (Web, Android, iOS client IDs) |
| `GOOGLE_SERVER_CLIENT_ID` | — | The Web client ID sent to the app through `/auth/config` |
| `STEP_TOKEN_MINUTES` | `10` | Lifetime of `phone_verified` and `google_signup` tokens |
| `SERVICE_AREA_BBOX` | Sulaimani governorate (roughly) | `min_lat,min_lon,max_lat,max_lon` |

**`tools/preflight.py` additions** (same ✓ / ⚠ / ✗ style as the existing checks):
- ⚠ `OTP_SENDER=console`, with the message "codes appear in the server log; fine for the demo, never for a pilot".
- ⚠ `OTP_REQUIRED=0`.
- ⚠ `OTP_PEPPER` is unset.
- ℹ Google is disabled.
- ✗ Migration 006 is missing.

**`requirements.txt`:** add `google-auth` and `phonenumbers`, with lower bounds in the file's existing style.

---

## 12. Tests (pytest, real PostGIS, following `conftest.py`)

**Fakes come in through `create_app`.**
- `FakeOtpSender` records `(phone, code)` and has a `last_code(phone)` helper.
- `FakeGoogleVerifier` maps test token strings to claim sets. It can also simulate an invalid token, `email_verified=false`, a wrong `aud`, and "Google unreachable".

**Update the `Api.signup` helper in `conftest.py`** so it goes through the real OTP flow using the fake sender. Its signature doesn't change, so every existing test keeps passing unmodified.

**New test files:**

`tests/test_otp.py`
- Request then verify returns a step token, and `phone_has_account` is correct.
- The database row holds no plaintext code; the response holds no code.
- A wrong code decrements `attempts_left`; the 6th attempt gives `otp_locked`; the attempts **persist** (D6 / requirement 6).
- An expired code gives `otp_expired` (move `expires_at` back in SQL rather than sleeping).
- A used code can't be used again. A superseded code fails after a resend.
- Resending within 60 seconds gives `429 otp_too_soon` with `retry_after`. The hourly per-phone and per-IP caps are enforced.
- A non-Iraqi number gives `phone_not_allowed`; a garbage number gives `invalid_phone`. `07501234567` and `+9647501234567` count as the same phone.
- `/auth/otp/request` gives the same response for registered and unregistered phones.
- **Race:** two threads verify the same correct code at the same instant, and exactly one succeeds (use `at_once` from `test_races.py`). Two concurrent requests for the same phone leave exactly one live code.

`tests/test_account_types.py`
- Signup works for each of the three types. Missing or invalid profile fields return `fields` errors. A profile that doesn't match its type gives 400. A location outside the service area gives 400.
- A business or household neighbourhood is derived from boundaries when they're loaded.
- `/me` returns the type and profile. `POST /me/profile` works, and editing a business sets it back to `pending`.
- Leagues: the citizen list contains only individuals. Businesses appear only once verified. The neighbourhood total counts individuals and households but not businesses (D9). The old `/leaderboard` keys are unchanged.
- **Privacy:** after creating a household, no public endpoint's JSON contains its latitude or longitude.
- Staff: list pending businesses, verify, reject with a required reason; a non-staff user gets 403.

`tests/test_google_auth.py`
- An invalid token gives 401. `email_verified=false` gives 403. Unreachable Google gives 503. Google disabled gives 404.
- A new `sub` gives `registration_required`, and no user row is created.
- A full register works for each type. A returning user gets `signed_in` and `last_login_at` is updated.
- A phone that already belongs to a password account gives `409 phone_has_account`. Linking then signs into the **same** user id, with points intact.
- A `sub` that's already linked gives `409 google_already_linked`. An expired `google_signup_token` gives 401.

`tests/test_tokens.py`
- A `phone_verified` or `google_signup` step token is rejected by `/me` with 401.
- An access token is rejected where a step token is expected.
- A legacy token without `typ` still works.

**Migration test**
- Build the database from the *previous* schema (keep a copy as a fixture, or build it from the migrations in order) with sample users in mixed phone formats.
- Run 006 twice; the data is intact and the phones are normalised.
- A planted duplicate (`0750…` and `+964750…`) makes the migration abort with nothing changed.

**Mobile**
- `flutter analyze` is clean.
- Add widget tests for `AccountTypeScreen` (three cards, selection) and `PhoneOtpScreen` (the countdown disables resend; error codes map to the right messages).

---

## 13. Implementation plan (one phase at a time; each ends green and is committed separately)

Commit messages follow the repo's style, e.g. `Auth: OTP request/verify with rate limits and race-safe consume`.

| Phase | Work | Done when |
|---|---|---|
| **0. Read & plan** | Read every file named in section 1. Confirm or correct the facts. Ask the section 16 questions. Propose any changes to sections 5 and 6. | I've replied |
| **1. Schema** | Migration 006, `schema.sql`, `seed.py`, phone normalisation helper (`app/phones.py`), preflight awareness | Existing tests pass on a fresh seed **and** on an old database plus the migration; the migration tests pass |
| **2. Token hardening** | `typ` claims, step-token helpers, the `login_required` fix | `test_tokens.py` passes; nothing else breaks |
| **3. OTP** | `app/otp.py` (service, `OtpSender` interface, console/fake senders), the endpoints, strings, config | `test_otp.py` passes, including the races |
| **4. Account types** | `app/accounts.py` (validators, `create_account()` shared by both sign-up methods, serializers), extended `/auth/signup`, `/me`, `/me/profile`, leagues, `points.ranks` per league | `test_account_types.py` passes; the conftest helper goes through OTP |
| **5. Google** | `app/google_auth.py` (verifier with cert caching, injected), `/auth/google`, `/register`, `/link`, `/auth/config` | `test_google_auth.py` passes |
| **6. Dashboard** | Admin endpoints, the businesses tab, stats, the league filter | Staff tests pass; tab checked by hand in a browser |
| **7. Mobile** | `api.dart`, the registration screens, the OTP screen, the Google button, profile and league updates, strings, setup scripts | `flutter analyze` is clean; widget tests pass; flows A–D from section 7 run against the local server with `OTP_SENDER=console` |
| **8. Docs** | README sections (Kurdish, matching the existing style): the new settings, the new endpoints, how to create Google OAuth clients, how to read console OTP codes on demo day; `docs/DEMO.md` notes | I've reviewed it |

**If time is short (hackathon mode),** the smallest slice worth demoing is Phases 1 → 2 → 3 → 4 → 7 (without the Google parts): three account types with console OTP. Then add 5 (Google) as the next slice. Leave linking (US-4), profile editing and the dashboard tab for last.

---

## 14. Conventions to keep
- Raw SQL with `query()`; no ORM. Use parameterised queries only, never string-formatted SQL with user input.
- New modules follow the existing layout and comment style (short docstrings explaining *why*, as in `points.py` and `db.py`).
- Every user-facing string goes in `strings.py` / `strings.dart`; error codes are stable `snake_case`.
- Settings come from environment variables in `config.py` with safe defaults; no secrets in code. Any new secret goes in `.env`, which is already gitignored.
- External services are injected through `create_app(...)`. Tests never touch the network.
- Native mobile configuration goes through `setup_ios.py` / `setup_android.py`.
- Don't reformat unrelated code. Keep each diff focused on its phase.

---

## 15. Definition of done
- [ ] US-1 to US-8 work end to end, checked by hand against the local server using flows A–D.
- [ ] `python -m pytest tests -q` is green, including all new tests and the race tests. `flutter analyze` is clean.
- [ ] Migration 006 is idempotent, preserves data, and aborts safely on phone duplicates. `schema.sql` matches old database + migration.
- [ ] Each of security requirements 1–18 is implemented, and the ones marked testable have a test.
- [ ] No OTP code, ID token or step token appears in any response, log line (except the console sender) or database column.
- [ ] Household coordinates appear in no public response (there's a test).
- [ ] The old app build still logs in. `/leaderboard` and `/me` are backwards compatible.
- [ ] README and preflight are updated. Out-of-scope follow-ups are listed.

---

## 16. Questions to ask me before Phase 1 (use the default if I don't answer)
1. **SMS provider for Iraqi numbers** (Twilio, a local Iraqi gateway, or WhatsApp)? *Default: build only `console` and `fake` now, with the provider adapter behind the interface later.*
2. **Neighbourhood league:** count households, and leave businesses out? *Default: yes, as in D9.*
3. **Points for businesses and households:** the same point tables and daily caps as individuals? *Default: the same.*
4. **Google Cloud project:** who creates the OAuth clients (Web, Android, iOS)? *Default: I'll create them; the tests use the fake verifier, so this only blocks manual testing of the Google flow.*
5. **Uncommitted work in the tree:** commit it to `main` first, or carry it onto the feature branch as it is? *Default: ask, and don't touch it until I answer.*

---

## 17. How to report back after each phase
1. **Done:** what changed, with file paths.
2. **Decisions:** anything you decided that this prompt didn't cover, and why.
3. **Deviations:** anything in this prompt that turned out wrong against the code, and what you did instead.
4. **Tests:** the commands you ran and the pass/fail counts (paste the summary line).
5. **Risks and follow-ups:** anything I should know before the next phase.
6. **Next:** the next phase, and any question that blocks it.

Before you report a phase as done, review your own diff against sections 8 and 14 the way a strict reviewer would: missed rollback traps, unvalidated input, leaked personal data, untested branches, strings outside `strings.py`/`strings.dart`.
