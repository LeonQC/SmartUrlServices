import os
import psycopg2


# Get database connection settings from environment variables(.env)
def get_db_params():
    return {
        "dbname": os.environ.get("DB_NAME", "url_shortener"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", "postgres"),
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": os.environ.get("DB_PORT", "5432")
    }


# Connect to the database
def get_db():
    return psycopg2.connect(**get_db_params())


# Create our table when the app starts
def init_db():
    # Connect to database
    conn = get_db()
    cursor = conn.cursor()

    # Create URLs table if it doesn't exist
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS urls (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            original_url TEXT NOT NULL,
            short_code TEXT UNIQUE NOT NULL,
            title TEXT,
            clicks INTEGER DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
                   """)

    # Add index for faster lookups
    cursor.execute("""
                   CREATE INDEX IF NOT EXISTS idx_short_code ON urls (short_code)
                   """)

    cursor.execute("""
                   CREATE INDEX IF NOT EXISTS idx_urls_user ON urls (user_id)
                   """)

    # Create QR codes table if it doesn't exist
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS qrcodes (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            original_url TEXT NOT NULL,
            qr_code_id TEXT UNIQUE NOT NULL,
            title TEXT,
            scans INTEGER DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
                   """)

    cursor.execute("""
                   CREATE INDEX IF NOT EXISTS idx_qr_code_id ON qrcodes (qr_code_id)
                   """)

    cursor.execute("""
                   CREATE INDEX IF NOT EXISTS idx_qrcodes_user ON qrcodes (user_id)
                   """)

    # Create barcodes table if it doesn't exist
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS barcodes (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            original_url TEXT NOT NULL,
            barcode_id TEXT UNIQUE NOT NULL,
            title TEXT,
            scans INTEGER DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
                   """)

    cursor.execute("""
                   CREATE INDEX IF NOT EXISTS idx_barcode_id ON barcodes (barcode_id)
                   """)

    cursor.execute("""
                   CREATE INDEX IF NOT EXISTS idx_barcodes_user ON barcodes (user_id)
                   """)

    # Save changes and close connection
    conn.commit()
    cursor.close()
    conn.close()


# Check if a short code already exists
def code_exists(short_code):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM urls WHERE short_code = %s", (short_code,))
    result = cursor.fetchone() is not None

    cursor.close()
    conn.close()
    return result


# Check if a QR code ID already exists
def qr_code_exists(qr_code_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM qrcodes WHERE qr_code_id = %s", (qr_code_id,))
    result = cursor.fetchone() is not None

    cursor.close()
    conn.close()
    return result


def barcode_exists(barcode_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM barcodes WHERE barcode_id = %s", (barcode_id,))
    result = cursor.fetchone() is not None

    cursor.close()
    conn.close()
    return result


# Find a URL by its short code
def find_by_code(short_code):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT original_url, clicks, title, user_id, created_at FROM urls WHERE short_code = %s",
        (short_code,)
    )
    result = cursor.fetchone()

    cursor.close()
    conn.close()
    return result


# Find a QR code by its ID
def find_qr_code_by_id(qr_code_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT original_url, scans, title, user_id, created_at FROM qrcodes WHERE qr_code_id = %s",
        (qr_code_id,)
    )
    result = cursor.fetchone()

    cursor.close()
    conn.close()
    return result


def find_barcode_by_id(barcode_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT original_url, scans, title, user_id, created_at FROM barcodes WHERE barcode_id = %s",
        (barcode_id,)
    )
    result = cursor.fetchone()

    cursor.close()
    conn.close()
    return result


# Save a new URL in the database
def save_url(original_url, short_code, title=None, user_id=None):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO urls (original_url, short_code, title, user_id) VALUES (%s, %s, %s, %s)",
        (original_url, short_code, title, user_id)
    )

    conn.commit()
    cursor.close()
    conn.close()


# Save a new QR code in the database
def save_qr_code(original_url, qr_code_id, title=None, user_id=None):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO qrcodes (original_url, qr_code_id, title, user_id) VALUES (%s, %s, %s, %s)",
        (original_url, qr_code_id, title, user_id)
    )

    conn.commit()
    cursor.close()
    conn.close()


def save_barcode(original_url, barcode_id, title=None, user_id=None):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO barcodes (original_url, barcode_id, title, user_id) VALUES (%s, %s, %s, %s)",
        (original_url, barcode_id, title, user_id)
    )

    conn.commit()
    cursor.close()
    conn.close()


# Increase the click counter when someone uses a short URL
def increment_clicks(short_code):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE urls SET clicks = clicks + 1 WHERE short_code = %s",
        (short_code,)
    )

    conn.commit()
    cursor.close()
    conn.close()


# Increase the scan counter when someone uses a QR code
def increment_qr_scans(qr_code_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE qrcodes SET scans = scans + 1 WHERE qr_code_id = %s",
        (qr_code_id,)
    )

    conn.commit()
    cursor.close()
    conn.close()


def increment_barcode_scans(barcode_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE barcodes SET scans = scans + 1 WHERE barcode_id = %s",
        (barcode_id,)
    )

    conn.commit()
    cursor.close()
    conn.close()


def update_click_count(short_code, count):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE urls SET clicks = %s WHERE short_code = %s",
        (count, short_code)
    )

    conn.commit()
    cursor.close()
    conn.close()


def update_qr_scan_count(qr_code_id, count):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE qrcodes SET scans = %s WHERE qr_code_id = %s",
        (count, qr_code_id)
    )

    conn.commit()
    cursor.close()
    conn.close()


def update_barcode_scan_count(barcode_id, count):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE barcodes SET scans = %s WHERE barcode_id = %s",
        (count, barcode_id)
    )

    conn.commit()
    cursor.close()
    conn.close()


def get_url_created_at(short_code):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT created_at FROM urls WHERE short_code = %s",
        (short_code,)
    )
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result[0] if result else None


def get_qr_code_created_at(qr_code_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT created_at FROM qrcodes WHERE qr_code_id = %s",
        (qr_code_id,)
    )
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result[0] if result else None


def get_barcode_created_at(barcode_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT created_at FROM barcodes WHERE barcode_id = %s",
        (barcode_id,)
    )
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result[0] if result else None