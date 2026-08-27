"""
reports_manager.py
Aggregate statistics and reports for admins: most-borrowed books, most
active members, fine revenue, and a library-wide summary.
"""

from database import get_connection


def library_summary():
    """High-level counts for a dashboard-style overview."""
    conn = get_connection()
    total_books = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    total_copies = conn.execute("SELECT COALESCE(SUM(total_copies), 0) FROM books").fetchone()[0]
    available_copies = conn.execute("SELECT COALESCE(SUM(available_copies), 0) FROM books").fetchone()[0]
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    active_loans = conn.execute("SELECT COUNT(*) FROM transactions WHERE return_date IS NULL").fetchone()[0]
    total_transactions = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    active_reservations = conn.execute(
        "SELECT COUNT(*) FROM reservations WHERE status IN ('waiting', 'ready')"
    ).fetchone()[0]
    conn.close()
    return {
        "total_books": total_books,
        "total_copies": total_copies,
        "available_copies": available_copies,
        "total_users": total_users,
        "active_loans": active_loans,
        "total_transactions": total_transactions,
        "active_reservations": active_reservations,
    }


def most_borrowed_books(limit=5):
    """Books ranked by total number of times borrowed (active + returned)."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT b.id, b.title, b.author, COUNT(t.id) AS borrow_count
           FROM transactions t
           JOIN books b ON t.book_id = b.id
           GROUP BY t.book_id
           ORDER BY borrow_count DESC, b.title
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def most_active_members(limit=5):
    """Members ranked by total number of loans they've taken out."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT u.id, u.name, COUNT(t.id) AS loan_count
           FROM transactions t
           JOIN users u ON t.user_id = u.id
           GROUP BY t.user_id
           ORDER BY loan_count DESC, u.name
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def top_fine_payers(limit=5):
    """Members ranked by total fines accrued from late returns."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT u.id, u.name, SUM(t.fine) AS total_fines,
                  COUNT(CASE WHEN t.fine > 0 THEN 1 END) AS late_returns
           FROM transactions t
           JOIN users u ON t.user_id = u.id
           WHERE t.fine > 0
           GROUP BY t.user_id
           ORDER BY total_fines DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def total_fine_revenue():
    """Sum of all fines ever charged on returned books."""
    conn = get_connection()
    total = conn.execute(
        "SELECT COALESCE(SUM(fine), 0) FROM transactions WHERE return_date IS NOT NULL"
    ).fetchone()[0]
    conn.close()
    return round(total, 2)


def category_breakdown():
    """How many titles (and copies) exist in each category."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT COALESCE(NULLIF(category, ''), 'Uncategorized') AS category,
                  COUNT(*) AS book_count,
                  COALESCE(SUM(total_copies), 0) AS copy_count
           FROM books
           GROUP BY category
           ORDER BY book_count DESC"""
    ).fetchall()
    conn.close()
    return rows