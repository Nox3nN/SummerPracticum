"""
database.py
Se ocupa de conexiunea SQLite si creaza toate tabelele folosite 
de sistemul de management al librariei. Orice alt modul importa
get_connection() de aici, inloc sa isi deschida propria conexiune.
"""

import sqlite3
import os
 
DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "library.db")
 
 
def get_connection():
    """Return a connection to the SQLite database with foreign keys enabled."""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn
 
 
def initialize_database():
    """Create all tables if they do not already exist. Safe to call every run."""
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            isbn TEXT UNIQUE NOT NULL,
            category TEXT,
            total_copies INTEGER NOT NULL DEFAULT 1,
            available_copies INTEGER NOT NULL DEFAULT 1
        )
    """)
 
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL DEFAULT 'member'
        )
    """)
 
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            borrow_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            return_date TEXT,
            fine REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (book_id) REFERENCES books (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
 
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            reservation_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'waiting',
            ready_date TEXT,
            fulfilled_date TEXT,
            FOREIGN KEY (book_id) REFERENCES books (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
 
    conn.commit()
    conn.close()
 
 
if __name__ == "__main__":
    initialize_database()
    print(f"Database initialized at {DB_NAME}")