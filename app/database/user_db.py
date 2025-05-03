import psycopg2
import bcrypt
from app.database.url_db import get_db


# Initialize user table when the app starts
def init_user_db():
    # Connect to database
    conn = get_db()
    cursor = conn.cursor()

    # Create user table if it doesn't exist
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS users
                   (
                       id SERIAL PRIMARY KEY,
                       username TEXT UNIQUE NOT NULL,
                       email TEXT UNIQUE NOT NULL,
                       password_hash TEXT NOT NULL,
                       created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                   )
                   """)

    # Add indexes for faster lookups
    cursor.execute("""
                   CREATE INDEX IF NOT EXISTS idx_username ON users (username)
                   """)

    cursor.execute("""
                   CREATE INDEX IF NOT EXISTS idx_email ON users (email)
                   """)

    # Save changes and close connection
    conn.commit()
    cursor.close()
    conn.close()


# Check if a username already exists
def username_exists(username):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM users WHERE username = %s", (username,))
    result = cursor.fetchone() is not None

    cursor.close()
    conn.close()
    return result


# Check if an email already exists
def email_exists(email):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM users WHERE email = %s", (email,))
    result = cursor.fetchone() is not None

    cursor.close()
    conn.close()
    return result


# Create a new user in the database
def create_user(username, email, password):
    conn = get_db()
    cursor = conn.cursor()

    # Hash the password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        cursor.execute(
            """
            INSERT INTO users (username, email, password_hash)
            VALUES (%s, %s, %s) RETURNING id, created_at
            """,
            (username, email, password_hash)
        )

        user_id, created_at = cursor.fetchone()
        conn.commit()

        return {
            "id": user_id,
            "username": username,
            "email": email,
            "created_at": created_at.isoformat()
        }
    except psycopg2.Error as e:
        conn.rollback()
        if e.pgcode == '23505':  # Unique violation
            if 'users_username_key' in str(e):
                raise ValueError("Username already exists")
            elif 'users_email_key' in str(e):
                raise ValueError("Email already exists")
        raise e
    finally:
        cursor.close()
        conn.close()