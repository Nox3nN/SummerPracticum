"""
book_manager.py
Toate operatiile relevante cartilor: add, view, update, delete, search.
"""

from database import get_connection
 
 
def add_book(title, author, isbn, category, total_copies):
    """Insert a new book. Returns (success: bool, message: str)."""
    if not title.strip() or not author.strip() or not isbn.strip():
        return False, "Title, author, and ISBN cannot be empty."
 
    try:
        total_copies = int(total_copies)
        if total_copies < 1:
            return False, "Total copies must be at least 1."
    except ValueError:
        return False, "Total copies must be a whole number."
 
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO books (title, author, isbn, category, total_copies, available_copies)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (title.strip(), author.strip(), isbn.strip(), category.strip(), total_copies, total_copies),
        )
        conn.commit()
        return True, f"Book '{title}' added successfully."
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            return False, f"A book with ISBN '{isbn}' already exists."
        return False, f"Error adding book: {e}"
    finally:
        conn.close()
 
 
VALID_BOOK_SORT_FIELDS = {"id", "title", "author", "category", "available_copies", "total_copies"}
 
 
def get_all_books(sort_by="title", descending=False):
    """List all books. sort_by one of: id, title, author, category, available_copies, total_copies."""
    if sort_by not in VALID_BOOK_SORT_FIELDS:
        sort_by = "title"
    direction = "DESC" if descending else "ASC"
    conn = get_connection()
    books = conn.execute(f"SELECT * FROM books ORDER BY {sort_by} {direction}").fetchall()
    conn.close()
    return books
 
 
def get_all_categories():
    """Distinct, non-empty categories currently in use — for building a filter menu."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT category FROM books WHERE category IS NOT NULL AND category != '' ORDER BY category"
    ).fetchall()
    conn.close()
    return [r["category"] for r in rows]
 
 
def filter_books(category=None, available_only=False, sort_by="title", descending=False):
    """Filter books by category and/or availability, with the same sort options as get_all_books."""
    if sort_by not in VALID_BOOK_SORT_FIELDS:
        sort_by = "title"
    direction = "DESC" if descending else "ASC"
 
    clauses = []
    params = []
    if category:
        clauses.append("category = ? COLLATE NOCASE")
        params.append(category)
    if available_only:
        clauses.append("available_copies > 0")
 
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    conn = get_connection()
    books = conn.execute(f"SELECT * FROM books {where} ORDER BY {sort_by} {direction}", params).fetchall()
    conn.close()
    return books
 
 
def get_book_by_id(book_id):
    conn = get_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    return book
 
 
def search_books(keyword):
    """Search by title, author, or category (case-insensitive, partial match)."""
    conn = get_connection()
    like_term = f"%{keyword.strip()}%"
    books = conn.execute(
        """SELECT * FROM books
           WHERE title LIKE ? COLLATE NOCASE
              OR author LIKE ? COLLATE NOCASE
              OR category LIKE ? COLLATE NOCASE
           ORDER BY title""",
        (like_term, like_term, like_term),
    ).fetchall()
    conn.close()
    return books
 
 
def update_book(book_id, title=None, author=None, category=None, total_copies=None):
    """Update only the fields provided. Returns (success: bool, message: str)."""
    book = get_book_by_id(book_id)
    if not book:
        return False, f"No book found with ID {book_id}."
 
    new_title = title.strip() if title else book["title"]
    new_author = author.strip() if author else book["author"]
    new_category = category.strip() if category else book["category"]
 
    if total_copies is not None and str(total_copies).strip() != "":
        try:
            new_total = int(total_copies)
            if new_total < 0:
                return False, "Total copies cannot be negative."
        except ValueError:
            return False, "Total copies must be a whole number."
        # Adjust available_copies by the same delta so currently-borrowed
        # books stay consistent.
        borrowed = book["total_copies"] - book["available_copies"]
        new_available = max(new_total - borrowed, 0)
    else:
        new_total = book["total_copies"]
        new_available = book["available_copies"]
 
    conn = get_connection()
    conn.execute(
        """UPDATE books SET title = ?, author = ?, category = ?,
           total_copies = ?, available_copies = ? WHERE id = ?""",
        (new_title, new_author, new_category, new_total, new_available, book_id),
    )
    conn.commit()
    conn.close()
    return True, f"Book ID {book_id} updated successfully."
 
 
def delete_book(book_id):
    """Delete a book, unless it has any transaction history (active or past).
 
    Past transactions still reference the book via a foreign key, so deleting
    a book that was ever borrowed would either break history or violate the
    foreign key constraint. We block deletion and explain why.
    """
    conn = get_connection()
    active_loans = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE book_id = ? AND return_date IS NULL",
        (book_id,),
    ).fetchone()[0]
 
    if active_loans > 0:
        conn.close()
        return False, "Cannot delete: this book has copies currently on loan."
 
    total_history = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE book_id = ?",
        (book_id,),
    ).fetchone()[0]
 
    if total_history > 0:
        conn.close()
        return False, "Cannot delete: this book has past borrow history on record."
 
    cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
 
    if cursor.rowcount == 0:
        return False, f"No book found with ID {book_id}."
    return True, f"Book ID {book_id} deleted successfully."

