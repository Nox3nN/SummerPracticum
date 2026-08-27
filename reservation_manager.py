"""
reservation_manager.py
Sistem de tip linie de asteptare (waitlist queue)
pentru carti fara copii valabile in librarie 

Cum functioneaza:
- Un user poate rezerva o carte care nu are copii valabile in prezent.
- Rezervarile se fac dupa metoda first-in-first-out.
- Cand o carte este inapoiata librariei, va avea loc un efect de tip
  "cascada". Cea mai veche rezervare va primi automat dreptul de a
  imprumuta cartea respectiva (`Ready` status in terminal), 
  inloc ca aceasta sa reintre in circulatie.
- O rezervare care intampina statusul de `ready` poate fi indeplinita
  cand persoana respectiva, din waitlist, vine sa imprumute cartea.
  (`fulfill_reservation`). Alftel, rezervarea poate fi stearsa din
  data de baze. Indiferent de metoda, daca o carte devine valabile,
  urmatorul in linie este "promovat", avand dreptul la imprumut.

Acest modul este dependent de `database.py`, nu de `transaction_manager`, pentru 
a ferii un import circular (multumesc geeksforgeeks.org). In schimb, `transaction_manager` importa acest modul.
"""

from datetime import datetime, timedelta
from database import get_connection
 
DATE_FORMAT = "%Y-%m-%d"
LOAN_PERIOD_DAYS = 14  # kept in sync with transaction_manager's loan period
 
 
def reserve_book(user_id, book_id):
    """Place a user on the waitlist for a book. Returns (success, message)."""
    conn = get_connection()
 
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return False, f"No user found with ID {user_id}."
 
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if not book:
        conn.close()
        return False, f"No book found with ID {book_id}."
 
    if book["available_copies"] > 0:
        conn.close()
        return False, f"'{book['title']}' has copies available right now — just borrow it instead."
 
    existing = conn.execute(
        """SELECT id FROM reservations
           WHERE book_id = ? AND user_id = ? AND status IN ('waiting', 'ready')""",
        (book_id, user_id),
    ).fetchone()
    if existing:
        conn.close()
        return False, f"{user['name']} is already on the waitlist for '{book['title']}'."
 
    conn.execute(
        """INSERT INTO reservations (book_id, user_id, reservation_date, status)
           VALUES (?, ?, ?, 'waiting')""",
        (book_id, user_id, datetime.now().strftime(DATE_FORMAT)),
    )
    conn.commit()
 
    position = conn.execute(
        "SELECT COUNT(*) FROM reservations WHERE book_id = ? AND status = 'waiting'",
        (book_id,),
    ).fetchone()[0]
    conn.close()
 
    return True, f"{user['name']} is #{position} in line for '{book['title']}'."
 
 
def _promote_next_in_queue(conn, book_id):
    """
    Internal helper: promote the oldest 'waiting' reservation for a book to
    'ready' and hold a copy for them (decrements available_copies). Expects
    an already-open connection so the caller can keep this atomic with
    whatever triggered it (a return or a cancellation). Does NOT commit —
    the caller is responsible for committing.
 
    Returns a dict with book/user info if someone was promoted, else None.
    """
    next_up = conn.execute(
        """SELECT r.id AS reservation_id, r.user_id, u.name AS user_name, b.title
           FROM reservations r
           JOIN users u ON r.user_id = u.id
           JOIN books b ON r.book_id = b.id
           WHERE r.book_id = ? AND r.status = 'waiting'
           ORDER BY r.reservation_date, r.id
           LIMIT 1""",
        (book_id,),
    ).fetchone()
 
    if not next_up:
        return None
 
    conn.execute(
        "UPDATE reservations SET status = 'ready', ready_date = ? WHERE id = ?",
        (datetime.now().strftime(DATE_FORMAT), next_up["reservation_id"]),
    )
    conn.execute(
        "UPDATE books SET available_copies = available_copies - 1 WHERE id = ?",
        (book_id,),
    )
    return {
        "reservation_id": next_up["reservation_id"],
        "user_name": next_up["user_name"],
        "title": next_up["title"],
    }
 
 
def promote_next_reservation(book_id):
    """Public wrapper around _promote_next_in_queue that manages its own connection."""
    conn = get_connection()
    result = _promote_next_in_queue(conn, book_id)
    conn.commit()
    conn.close()
    return result
 
 
def fulfill_reservation(reservation_id):
    """
    Convert a 'ready' reservation into an actual loan (the person showing
    up to pick up their held book). Does NOT touch available_copies since
    the copy was already set aside when the reservation became 'ready'.
    """
    conn = get_connection()
    res = conn.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone()
 
    if not res:
        conn.close()
        return False, f"No reservation found with ID {reservation_id}."
    if res["status"] != "ready":
        status = res["status"]
        conn.close()
        return False, f"This reservation isn't ready for pickup yet (status: {status})."
 
    borrow_date = datetime.now()
    due_date = borrow_date + timedelta(days=LOAN_PERIOD_DAYS)
 
    conn.execute(
        """INSERT INTO transactions (book_id, user_id, borrow_date, due_date)
           VALUES (?, ?, ?, ?)""",
        (res["book_id"], res["user_id"], borrow_date.strftime(DATE_FORMAT), due_date.strftime(DATE_FORMAT)),
    )
    conn.execute(
        "UPDATE reservations SET status = 'fulfilled', fulfilled_date = ? WHERE id = ?",
        (borrow_date.strftime(DATE_FORMAT), reservation_id),
    )
    conn.commit()
    conn.close()
    return True, f"Reservation picked up. Due back {due_date.strftime(DATE_FORMAT)}."
 
 
def cancel_reservation(reservation_id):
    """
    Cancel a waiting or ready reservation. If a copy was being held for it
    (status was 'ready'), release that copy and cascade the hold to the
    next person waiting in line for the same book.
    """
    conn = get_connection()
    res = conn.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone()
 
    if not res:
        conn.close()
        return False, f"No reservation found with ID {reservation_id}."
    if res["status"] not in ("waiting", "ready"):
        conn.close()
        return False, f"This reservation is already {res['status']} and can't be cancelled."
 
    was_ready = res["status"] == "ready"
    conn.execute("UPDATE reservations SET status = 'cancelled' WHERE id = ?", (reservation_id,))
 
    message = "Reservation cancelled."
    if was_ready:
        conn.execute(
            "UPDATE books SET available_copies = available_copies + 1 WHERE id = ?",
            (res["book_id"],),
        )
        promoted = _promote_next_in_queue(conn, res["book_id"])
        if promoted:
            message += f" Held copy passed to {promoted['user_name']} (next in line)."
 
    conn.commit()
    conn.close()
    return True, message
 
 
def get_queue_for_book(book_id):
    """Waiting + ready reservations for one book, in queue order."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT r.id AS reservation_id, u.name AS user_name, r.status, r.reservation_date
           FROM reservations r
           JOIN users u ON r.user_id = u.id
           WHERE r.book_id = ? AND r.status IN ('waiting', 'ready')
           ORDER BY r.reservation_date, r.id""",
        (book_id,),
    ).fetchall()
    conn.close()
    return rows
 
 
def get_all_active_reservations():
    """All waiting/ready reservations across every book, for the admin view."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT r.id AS reservation_id, b.title, u.name AS user_name,
                  r.status, r.reservation_date, r.ready_date
           FROM reservations r
           JOIN books b ON r.book_id = b.id
           JOIN users u ON r.user_id = u.id
           WHERE r.status IN ('waiting', 'ready')
           ORDER BY b.title, r.reservation_date, r.id""",
    ).fetchall()
    conn.close()
    return rows
 
 
def get_reservations_for_user(user_id, active_only=True):
    """A single member's reservations, most recent first. Used for 'My reservations'."""
    conn = get_connection()
    query = """
        SELECT r.id AS reservation_id, r.book_id, b.title, r.status,
               r.reservation_date, r.ready_date, r.fulfilled_date
        FROM reservations r
        JOIN books b ON r.book_id = b.id
        WHERE r.user_id = ?
    """
    params = [user_id]
    if active_only:
        query += " AND r.status IN ('waiting', 'ready')"
    query += " ORDER BY r.id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows