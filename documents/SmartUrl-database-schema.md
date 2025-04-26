# SmartUrl Database Schema

This document outlines the database schema for the SmartUrl service, which includes tables for user management, URL shortening, QR code generation, barcode generation, and analytics tracking.

## Database Tables

### Table: users

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier for each user |
| username | TEXT | UNIQUE, NOT NULL | User's chosen username |
| email | TEXT | UNIQUE, NOT NULL | User's email address |
| password_hash | TEXT | | Hashed password (NULL for OAuth users) |
| auth_provider | TEXT | | Authentication provider (NULL for local auth, "google" for Google) |
| auth_provider_id | TEXT | | Provider-specific user ID |
| created_at | TIMESTAMP | NOT NULL | When the user was created |
| updated_at | TIMESTAMP | NOT NULL | When the user was last updated |

**Indexes:**
- PRIMARY KEY on `id` (automatically created)
- UNIQUE INDEX on `username` (automatically created by UNIQUE constraint)
- UNIQUE INDEX on `email` (automatically created by UNIQUE constraint)
- INDEX on `auth_provider` and `auth_provider_id` for OAuth lookups

**SQL for creating the table:**

```sql
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    auth_provider TEXT,
    auth_provider_id TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_auth_provider ON users (auth_provider, auth_provider_id);
```

### Table: urls

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier for each URL entry |
| user_id | INTEGER | FOREIGN KEY, NULL | ID of user who created this URL (NULL if user was deleted) |
| original_url | TEXT | NOT NULL | The original long URL |
| short_code | TEXT | UNIQUE, NOT NULL | The randomly generated code (e.g., "abc123") |
| title | TEXT | | Title of the website (extracted from HTML) |
| clicks | INTEGER | DEFAULT 0 | Number of times the short URL has been accessed |
| created_at | TIMESTAMP | NOT NULL | When the short URL was created |

**Indexes:**
- PRIMARY KEY on `id` (automatically created)
- UNIQUE INDEX on `short_code` (automatically created by UNIQUE constraint)
- INDEX on `user_id` for user's URLs lookup
- INDEX on `short_code` for faster lookups

**SQL for creating the table:**

```sql
CREATE TABLE IF NOT EXISTS urls (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    original_url TEXT NOT NULL,
    short_code TEXT UNIQUE NOT NULL,
    title TEXT,
    clicks INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_urls_user ON urls (user_id);
CREATE INDEX IF NOT EXISTS idx_short_code ON urls (short_code);
```

### Table: qrcodes

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier for each QR code entry |
| user_id | INTEGER | FOREIGN KEY, NULL | ID of user who created this QR code (NULL if user was deleted) |
| original_url | TEXT | NOT NULL | The original URL encoded in the QR code |
| qr_code_id | TEXT | UNIQUE, NOT NULL | The unique identifier for the QR code |
| title | TEXT | | Title of the website (extracted from HTML) |
| scans | INTEGER | DEFAULT 0 | Number of times the QR code has been scanned |
| created_at | TIMESTAMP | NOT NULL | When the QR code was created |

**Indexes:**
- PRIMARY KEY on `id` (automatically created)
- UNIQUE INDEX on `qr_code_id` (automatically created by UNIQUE constraint)
- INDEX on `user_id` for user's QR codes lookup
- INDEX on `qr_code_id` for faster lookups

**SQL for creating the table:**

```sql
CREATE TABLE IF NOT EXISTS qrcodes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    original_url TEXT NOT NULL,
    qr_code_id TEXT UNIQUE NOT NULL,
    title TEXT,
    scans INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_qrcodes_user ON qrcodes (user_id);
CREATE INDEX IF NOT EXISTS idx_qr_code_id ON qrcodes (qr_code_id);
```

### Table: barcodes

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier for each barcode entry |
| user_id | INTEGER | FOREIGN KEY, NULL | ID of user who created this barcode (NULL if user was deleted) |
| original_url | TEXT | NOT NULL | The original URL encoded in the barcode |
| barcode_id | TEXT | UNIQUE, NOT NULL | The unique identifier for the barcode |
| title | TEXT | | Title of the website (extracted from HTML) |
| scans | INTEGER | DEFAULT 0 | Number of times the barcode has been scanned |
| created_at | TIMESTAMP | NOT NULL | When the barcode was created |

**Indexes:**
- PRIMARY KEY on `id` (automatically created)
- UNIQUE INDEX on `barcode_id` (automatically created by UNIQUE constraint)
- INDEX on `user_id` for user's barcodes lookup
- INDEX on `barcode_id` for faster lookups

**SQL for creating the table:**

```sql
CREATE TABLE IF NOT EXISTS barcodes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    original_url TEXT NOT NULL,
    barcode_id TEXT UNIQUE NOT NULL,
    title TEXT,
    scans INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_barcodes_user ON barcodes (user_id);
CREATE INDEX IF NOT EXISTS idx_barcode_id ON barcodes (barcode_id);
```

### Table: analytics

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier for each analytics entry |
| resource_type | TEXT | NOT NULL | Type of resource ("url", "qrcode", or "barcode") |
| resource_id | TEXT | NOT NULL | ID of the resource (short_code, qr_code_id, or barcode_id) |
| event_type | TEXT | NOT NULL | Type of event ("click" or "scan") |
| event_date | TIMESTAMP | NOT NULL | Date and time of the event |
| referrer | TEXT | | Source of the visit (for URLs) |
| browser | TEXT | | Browser used (Chrome, Firefox, etc.) |
| os | TEXT | | Operating system (Windows, macOS, iOS, Android, etc.) |
| device_type | TEXT | | Device type (desktop, mobile, tablet) |
| country | TEXT | | Country of the visitor |
| region | TEXT | | Region or state of the visitor |
| city | TEXT | | City of the visitor |
| language | TEXT | | Language setting of the visitor's browser |

**Indexes:**
- PRIMARY KEY on `id` (automatically created)
- INDEX on `resource_type` and `resource_id` for faster lookups
- INDEX on `event_date` for date-based queries
- INDEX on `device_type` for device-based queries
- INDEX on `country` for location-based queries

**SQL for creating the table:**

```sql
CREATE TABLE IF NOT EXISTS analytics (
    id SERIAL PRIMARY KEY,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    referrer TEXT,
    browser TEXT,
    os TEXT,
    device_type TEXT,
    country TEXT,
    region TEXT,
    city TEXT,
    language TEXT
);

CREATE INDEX IF NOT EXISTS idx_resource ON analytics (resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_event_date ON analytics (event_date);
CREATE INDEX IF NOT EXISTS idx_device_type ON analytics (device_type);
CREATE INDEX IF NOT EXISTS idx_country ON analytics (country);
```

## Key Relationships

**Relationship 1: User-to-Resource**
* Type: One-to-Many relationship
* Description: A single user can create multiple resources (URLs, QR codes, barcodes)
* Implementation: Through `user_id` foreign key in resource tables
* Creation requirement: All resources must be created by authenticated users (enforced at application level)
* Deletion behavior: When a user is deleted, resources remain but user association is removed (SET NULL)
* Resource persistence: All URLs, QR codes, and barcodes continue to function normally even after the creating user is deleted

**Relationship 2: Resource-to-Analytics**
* Type: One-to-Many relationship
* Description: Each resource (URL, QR code, barcode) can have multiple analytics entries
* Implementation: Through `resource_type` and `resource_id` fields in the analytics table
* Event tracking: Each row in the analytics table represents a single interaction event (one click or scan)
* Data captured: The analytics table stores detailed information about each interaction with a resource

## Notes on Implementation

1. **QR Codes and Barcodes Generation**
   - The actual QR code and barcode images are generated on-demand
   - No image data is stored in the database, only the metadata
   - Images are created when requested through the image endpoints

2. **Authentication**
   - Supports both local authentication (username/password) and OAuth (Google)
   - Passwords are stored as secure bcrypt hashes, never as plaintext
   - JWT authentication is used instead of sessions

3. **Resource Persistence**
   - All resources require user authentication to create
   - Resources persist even if the creating user's account is deleted
   - This ensures that shared links and codes remain functional

4. **Website Title Extraction**
   - When a resource is created, the system attempts to extract the title from the target website's HTML
   - If extraction fails (due to network issues, invalid URL, or missing title tag), the title field may be NULL
   - Titles provide context about the destination without requiring manual entry

5. **Database Indexing**
   - Indexes are used to improve query performance, especially for lookups and analytics
   - Compound indexes like `idx_resource` optimize common query patterns
   - Each analytics event (click or scan) is stored as a separate row for detailed analysis
