"""
user_manager.py
Inregistrare/Listare useri ai librariei (members/admins).
"""

from database import get_connection
 
 
def register_user(name, email, role="member"):
    """Register a new user. Returns (success: bool, message: str)."""
    if not name.strip() or not email.strip():
        return False, "Name and email cannot be empty."
 
    role = role.strip().lower() if role.strip() else "member"
    if role not in ("member", "admin"):
        return False, "Role must be 'member' or 'admin'."
 
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (name, email, role) VALUES (?, ?, ?)",
            (name.strip(), email.strip().lower(), role),
        )
        conn.commit()
        return True, f"User '{name}' registered as {role}."
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            return False, f"A user with email '{email}' already exists."
        return False, f"Error registering user: {e}"
    finally:
        conn.close()
 
 
VALID_SORT_FIELDS = {"id", "name", "email", "role"}
 
 
def get_all_users(sort_by="name", descending=False):
    """List all users. sort_by one of: id, name, email, role."""
    if sort_by not in VALID_SORT_FIELDS:
        sort_by = "name"
    direction = "DESC" if descending else "ASC"
    conn = get_connection()
    users = conn.execute(f"SELECT * FROM users ORDER BY {sort_by} {direction}").fetchall()
    conn.close()
    return users
 
 
def get_user_by_id(user_id):
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user
 
 
def get_user_by_email(email):
    conn = get_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email.strip(),)
    ).fetchone()
    conn.close()
    return user
 
 
def update_user_role(user_id, new_role):
    """Promote/demote an existing user between 'member' and 'admin'.
    Returns (success: bool, message: str)."""
    new_role = new_role.strip().lower()
    if new_role not in ("member", "admin"):
        return False, "Role must be 'member' or 'admin'."
 
    user = get_user_by_id(user_id)
    if not user:
        return False, f"No user found with ID {user_id}."
 
    if user["role"] == new_role:
        return False, f"{user['name']} is already {new_role}."
 
    if user["role"] == "admin" and new_role == "member":
        conn = get_connection()
        admin_count = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0]
        conn.close()
        if admin_count <= 1:
            return False, "Can't demote the last remaining admin — promote someone else first."
 
    conn = get_connection()
    conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    conn.commit()
    conn.close()
    return True, f"{user['name']} is now {new_role}."
 
 
def delete_user(user_id):
    """Delete a user, unless they have any borrowing/reservation history
    (active or past), or are the last remaining admin.
 
    Past transactions and reservations still reference the user via a
    foreign key (same reasoning as book_manager.delete_book), so this
    protects both data integrity and the audit trail — a member who ever
    borrowed something can't just vanish from the transaction history.
    Returns (success: bool, message: str).
    """
    user = get_user_by_id(user_id)
    if not user:
        return False, f"No user found with ID {user_id}."
 
    conn = get_connection()
 
    active_loans = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE user_id = ? AND return_date IS NULL",
        (user_id,),
    ).fetchone()[0]
    if active_loans > 0:
        conn.close()
        return False, f"Cannot delete: {user['name']} has {active_loans} book(s) currently on loan."
 
    total_transactions = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    if total_transactions > 0:
        conn.close()
        return False, f"Cannot delete: {user['name']} has past borrowing history on record."
 
    active_reservations = conn.execute(
        "SELECT COUNT(*) FROM reservations WHERE user_id = ? AND status IN ('waiting', 'ready')",
        (user_id,),
    ).fetchone()[0]
    if active_reservations > 0:
        conn.close()
        return False, f"Cannot delete: {user['name']} has active reservation(s) on the waitlist."
 
    total_reservations = conn.execute(
        "SELECT COUNT(*) FROM reservations WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    if total_reservations > 0:
        conn.close()
        return False, f"Cannot delete: {user['name']} has past reservation history on record."
 
    if user["role"] == "admin":
        admin_count = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0]
        if admin_count <= 1:
            conn.close()
            return False, "Can't delete the last remaining admin — promote someone else first."
 
    cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
 
    if cursor.rowcount == 0:
        return False, f"No user found with ID {user_id}."
    return True, f"User '{user['name']}' deleted successfully."