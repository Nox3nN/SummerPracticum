"""
transaction_manager.py
Imprumutare, returnare, calcul amenzi, si raportaj interziere.
"""

from datetime import datetime, timedelta
from database import get_connection
import reservation_manager
 
LOAN_PERIOD_DAYS = 14
FINE_PER_DAY = 0.50
DATE_FORMAT = "%Y-%m-%d"
 
 
def borrow_book(user_id, book_id):
    """Create a borrow transaction if a copy is available."""
    conn = get_connection()
 
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return False, f"No user found with ID {user_id}."
 
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if not book:
        conn.close()
        return False, f"No book found with ID {book_id}."
 
    if book["available_copies"] <= 0:
        conn.close()
        return False, (
            f"No available copies of '{book['title']}' right now. "
            "You can join the waitlist instead (Reserve a book)."
        )
 
    borrow_date = datetime.now()
    due_date = borrow_date + timedelta(days=LOAN_PERIOD_DAYS)
 
    conn.execute(
        """INSERT INTO transactions (book_id, user_id, borrow_date, due_date)
           VALUES (?, ?, ?, ?)""",
        (book_id, user_id, borrow_date.strftime(DATE_FORMAT), due_date.strftime(DATE_FORMAT)),
    )
    conn.execute(
        "UPDATE books SET available_copies = available_copies - 1 WHERE id = ?",
        (book_id,),
    )
    conn.commit()
    conn.close()
    return True, f"'{book['title']}' borrowed by {user['name']}. Due back {due_date.strftime(DATE_FORMAT)}."
 
 
def return_book(transaction_id):
    """Mark a transaction as returned and calculate any overdue fine."""
    conn = get_connection()
    txn = conn.execute(
        "SELECT * FROM transactions WHERE id = ?", (transaction_id,)
    ).fetchone()
 
    if not txn:
        conn.close()
        return False, f"No transaction found with ID {transaction_id}."
    if txn["return_date"] is not None:
        conn.close()
        return False, "This book has already been returned."
 
    return_date = datetime.now()
    due_date = datetime.strptime(txn["due_date"], DATE_FORMAT)
 
    days_late = (return_date.date() - due_date.date()).days
    fine = round(days_late * FINE_PER_DAY, 2) if days_late > 0 else 0.0
 
    conn.execute(
        "UPDATE transactions SET return_date = ?, fine = ? WHERE id = ?",
        (return_date.strftime(DATE_FORMAT), fine, transaction_id),
    )
    conn.execute(
        "UPDATE books SET available_copies = available_copies + 1 WHERE id = ?",
        (txn["book_id"],),
    )
    conn.commit()
    conn.close()
 
    message = f"Book returned. {days_late} day(s) late. Fine due: ${fine:.2f}" if fine > 0 \
        else "Book returned on time. No fine."
 
    # If someone is waiting for this book, the returned copy goes straight
    # to them instead of back into general circulation.
    promoted = reservation_manager.promote_next_reservation(txn["book_id"])
    if promoted:
        message += f" Held for {promoted['user_name']} (next in the reservation queue)."
 
    return True, message
 
 
def get_active_loans(user_id=None):
    """All transactions that have not been returned yet, with book/user info.
    Pass user_id to see only one member's active loans."""
    conn = get_connection()
    query = """
        SELECT t.id AS txn_id, t.book_id, t.user_id, b.title, u.name AS user_name,
               t.borrow_date, t.due_date
        FROM transactions t
        JOIN books b ON t.book_id = b.id
        JOIN users u ON t.user_id = u.id
        WHERE t.return_date IS NULL
    """
    params = []
    if user_id is not None:
        query += " AND t.user_id = ?"
        params.append(user_id)
    query += " ORDER BY t.due_date"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows
 
 
def get_overdue_loans(user_id=None):
    """Active loans whose due date has already passed, with days late and running fine.
    Pass user_id to see only one member's overdue loans."""
    today = datetime.now().date()
    overdue = []
    for row in get_active_loans(user_id=user_id):
        due = datetime.strptime(row["due_date"], DATE_FORMAT).date()
        if today > due:
            days_late = (today - due).days
            overdue.append({
                "txn_id": row["txn_id"],
                "book_id": row["book_id"],
                "user_id": row["user_id"],
                "title": row["title"],
                "user_name": row["user_name"],
                "due_date": row["due_date"],
                "days_late": days_late,
                "current_fine": round(days_late * FINE_PER_DAY, 2),
            })
    return overdue
 
 
def get_all_transactions(user_id=None):
    """Full transaction history, most recent first. Pass user_id for one member's history."""
    conn = get_connection()
    query = """
        SELECT t.id AS txn_id, t.book_id, t.user_id, b.title, u.name AS user_name,
               t.borrow_date, t.due_date, t.return_date, t.fine
        FROM transactions t
        JOIN books b ON t.book_id = b.id
        JOIN users u ON t.user_id = u.id
    """
    params = []
    if user_id is not None:
        query += " WHERE t.user_id = ?"
        params.append(user_id)
    query += " ORDER BY t.id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows