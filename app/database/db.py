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

    # Create table if it doesn't exist
    cursor.execute("""CREATE TABLE IF NOT EXISTS urls (
            id SERIAL PRIMARY KEY,
            original_url TEXT NOT NULL,
            short_code TEXT UNIQUE NOT NULL,
            title TEXT,
            clicks INTEGER DEFAULT 0
        )""")

    # Add index for faster lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_short_code ON urls (short_code)
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

# Find a URL by its short code
def find_by_code(short_code):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT original_url, clicks, title FROM urls WHERE short_code = %s",
        (short_code,)
    )
    result = cursor.fetchone()

    cursor.close()
    conn.close()
    return result

# Save a new URL in the database
def save_url(original_url, short_code, title=None):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO urls (original_url, short_code, title) VALUES (%s, %s, %s)",
        (original_url, short_code, title)
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