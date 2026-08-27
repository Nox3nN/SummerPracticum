"""
main.py
Interfata de tip Command-line pentru sistem de management al librariei.
Run with: python main.py

Modelul de permisiuni este simplificat, nu contine parole, doar identificare prin email:
- Primul cont creat devine automat admin (bootstrap), deci exista intotdeauna 
cel putin un admin care sa gestioneze sistemul.
- Administratorii pot gestiona cartile, vizualiza rapoarte 
si actiona in numele oricarui membru (ex. imprumut/rezerve la front desk).
- Membrii pot vizualiza cartile, cauta, imprumuta, returna si rezerva 
doar pentru ei insisi.

"""

from database import initialize_database
import book_manager
import user_manager
import transaction_manager
import reservation_manager
import reports_manager
 
CURRENT_USER = None  # set by login() at startup; a sqlite3.Row for the session
 
 
def print_header(text):
    print("\n" + "=" * 50)
    print(text)
    print("=" * 50)
 
 
def print_books(books):
    if not books:
        print("No books found.")
        return
    print(f"\n{'ID':<4}{'Title':<25}{'Author':<20}{'Category':<15}{'Avail/Total':<12}")
    print("-" * 76)
    for b in books:
        print(f"{b['id']:<4}{b['title'][:24]:<25}{b['author'][:19]:<20}"
              f"{(b['category'] or '-')[:14]:<15}{b['available_copies']}/{b['total_copies']:<10}")
 
 
def print_users(users):
    if not users:
        print("No users found.")
        return
    print(f"\n{'ID':<4}{'Name':<20}{'Email':<28}{'Role':<10}")
    print("-" * 62)
    for u in users:
        print(f"{u['id']:<4}{u['name'][:19]:<20}{u['email'][:27]:<28}{u['role']:<10}")
 
 
def prompt(label, required=True):
    while True:
        value = input(f"{label}: ").strip()
        if value or not required:
            return value
        print("This field is required.")
 
 
def prompt_choice(label, choices):
    """choices: dict of {key: description}. Returns the chosen key."""
    for key, desc in choices.items():
        print(f"  {key}. {desc}")
    while True:
        choice = input(f"{label}: ").strip()
        if choice in choices:
            return choice
        print("Invalid option, try again.")
 
 
def is_admin():
    return CURRENT_USER is not None and CURRENT_USER["role"] == "admin"
 
 
def admin_required(func):
    """Decorator: blocks a menu action unless the logged-in user is an admin."""
    def wrapper():
        if not is_admin():
            print("✘ Access denied: this action requires an admin account.")
            return
        return func()
    wrapper.__name__ = func.__name__
    return wrapper
 
 
# ---------------- Login / bootstrap ----------------
 
def login():
    """
    Identify who's using the system this session. No passwords — this is a
    simplified practicum auth model based on email lookup only.
    Returns the user row for the session.
    """
    global CURRENT_USER
    print_header("Welcome to the Library Management System")
 
    if not user_manager.get_all_users():
        print("No accounts exist yet. Let's create the first one — it will be an admin.")
        name = prompt("Name")
        email = prompt("Email")
        ok, msg = user_manager.register_user(name, email, role="admin")
        print(("✔ " if ok else "✘ ") + msg)
        if not ok:
            # Only real failure case here is a blank name/email, prompt loops
            # until register_user succeeds.
            return login()
        CURRENT_USER = user_manager.get_user_by_email(email)
        return CURRENT_USER
 
    while True:
        email = prompt("Enter your email to log in")
        user = user_manager.get_user_by_email(email)
        if user:
            CURRENT_USER = user
            print(f"Welcome back, {user['name']} ({user['role']}).")
            return CURRENT_USER
        print("No account found with that email.")
        choice = prompt_choice("What would you like to do?", {
            "1": "Try a different email",
            "2": "Register a new member account",
        })
        if choice == "2":
            name = prompt("Name")
            new_email = prompt("Email")
            ok, msg = user_manager.register_user(name, new_email, role="member")
            print(("✔ " if ok else "✘ ") + msg)
            if ok:
                CURRENT_USER = user_manager.get_user_by_email(new_email)
                return CURRENT_USER
 
 
# ---------------- Book menu ----------------
 
@admin_required
def menu_add_book():
    print_header("Add a New Book")
    title = prompt("Title")
    author = prompt("Author")
    isbn = prompt("ISBN")
    category = prompt("Category", required=False)
    copies = prompt("Total copies")
    ok, msg = book_manager.add_book(title, author, isbn, category, copies)
    print(("✔ " if ok else "✘ ") + msg)
 
 
def menu_view_books():
    print_header("All Books")
    sort_choice = prompt_choice("Sort by", {
        "1": "Title (A-Z)", "2": "Author (A-Z)", "3": "Category (A-Z)", "4": "Most copies available",
    })
    sort_map = {"1": "title", "2": "author", "3": "category", "4": "available_copies"}
    descending = sort_choice == "4"
    print_books(book_manager.get_all_books(sort_by=sort_map[sort_choice], descending=descending))
 
 
def menu_filter_books():
    print_header("Filter Books")
    categories = book_manager.get_all_categories()
    category = None
    if categories:
        print("Categories in use:", ", ".join(categories))
        category = prompt("Filter by category (blank for all)", required=False) or None
    only_available = prompt("Show only available copies? (y/n)", required=False).lower() == "y"
    print_books(book_manager.filter_books(category=category, available_only=only_available))
 
 
def menu_search_books():
    print_header("Search Books")
    keyword = prompt("Search term (title/author/category)")
    print_books(book_manager.search_books(keyword))
 
 
@admin_required
def menu_update_book():
    print_header("Update a Book")
    menu_view_books()
    book_id = prompt("Book ID to update")
    if not book_id.isdigit():
        print("✘ Invalid ID.")
        return
    print("Leave a field blank to keep its current value.")
    title = prompt("New title", required=False)
    author = prompt("New author", required=False)
    category = prompt("New category", required=False)
    total_copies = prompt("New total copies", required=False)
    ok, msg = book_manager.update_book(int(book_id), title, author, category, total_copies)
    print(("✔ " if ok else "✘ ") + msg)
 
 
@admin_required
def menu_delete_book():
    print_header("Delete a Book")
    menu_view_books()
    book_id = prompt("Book ID to delete")
    if not book_id.isdigit():
        print("✘ Invalid ID.")
        return
    ok, msg = book_manager.delete_book(int(book_id))
    print(("✔ " if ok else "✘ ") + msg)
 
 
# ---------------- User menu ----------------
 
@admin_required
def menu_register_user():
    print_header("Register a New User")
    name = prompt("Name")
    email = prompt("Email")
    role = prompt("Role (member/admin) [default: member]", required=False)
    ok, msg = user_manager.register_user(name, email, role or "member")
    print(("✔ " if ok else "✘ ") + msg)
 
 
@admin_required
def menu_view_users():
    print_header("All Users")
    sort_choice = prompt_choice("Sort by", {"1": "ID", "2": "Name (A-Z)", "3": "Role"})
    sort_map = {"1": "id", "2": "name", "3": "role"}
    print_users(user_manager.get_all_users(sort_by=sort_map[sort_choice]))
 
 
@admin_required
def menu_change_user_role():
    print_header("Change a User's Role")
    print_users(user_manager.get_all_users(sort_by="id"))
    user_id = prompt("User ID to promote/demote")
    if not user_id.isdigit():
        print("✘ Invalid ID.")
        return
    user_id = int(user_id)
 
    if CURRENT_USER["id"] == user_id:
        print("✘ You can't change your own role — ask another admin.")
        return
 
    new_role = prompt_choice("New role", {"1": "member", "2": "admin"})
    role_value = "member" if new_role == "1" else "admin"
    ok, msg = user_manager.update_user_role(user_id, role_value)
    print(("✔ " if ok else "✘ ") + msg)
 
 
@admin_required
def menu_delete_user():
    print_header("Delete a User")
    print_users(user_manager.get_all_users(sort_by="id"))
    user_id = prompt("User ID to delete")
    if not user_id.isdigit():
        print("✘ Invalid ID.")
        return
    user_id = int(user_id)
 
    if CURRENT_USER["id"] == user_id:
        print("✘ You can't delete your own account — ask another admin.")
        return
 
    target = user_manager.get_user_by_id(user_id)
    if not target:
        print(f"✘ No user found with ID {user_id}.")
        return
 
    confirm = prompt(f"Type '{target['name']}' to confirm deletion", required=False)
    if confirm.strip().lower() != target["name"].strip().lower():
        print("✘ Confirmation didn't match. Deletion cancelled.")
        return
 
    ok, msg = user_manager.delete_user(user_id)
    print(("✔ " if ok else "✘ ") + msg)
 
 
# ---------------- Transaction menu ----------------
 
def _resolve_acting_user_id(action_label):
    """Admins can act on behalf of any member; members can only act as themselves."""
    if is_admin():
        print_header(f"{action_label} — Admin: choose the member")
        print_users(user_manager.get_all_users())
        user_id = prompt("Member's User ID")
        if not user_id.isdigit():
            print("✘ Invalid ID.")
            return None
        return int(user_id)
    return CURRENT_USER["id"]
 
 
def menu_borrow_book():
    print_header("Borrow a Book")
    user_id = _resolve_acting_user_id("Borrow")
    if user_id is None:
        return
    print_books(book_manager.get_all_books())
    book_id = prompt("Book ID to borrow")
    if not book_id.isdigit():
        print("✘ Invalid ID.")
        return
    ok, msg = transaction_manager.borrow_book(user_id, int(book_id))
    print(("✔ " if ok else "✘ ") + msg)
 
 
def menu_return_book():
    print_header("Return a Book")
    user_id = None if is_admin() else CURRENT_USER["id"]
    loans = transaction_manager.get_active_loans(user_id=user_id)
    if not loans:
        print("No active loans right now." if is_admin() else "You have no active loans.")
        return
    print(f"\n{'TxnID':<7}{'Title':<25}{'User':<18}{'Due':<12}")
    print("-" * 62)
    for l in loans:
        print(f"{l['txn_id']:<7}{l['title'][:24]:<25}{l['user_name'][:17]:<18}{l['due_date']:<12}")
    txn_id = prompt("Transaction ID to return")
    if not txn_id.isdigit():
        print("✘ Invalid ID.")
        return
    txn_id = int(txn_id)
    if not is_admin() and txn_id not in [l["txn_id"] for l in loans]:
        print("✘ That loan doesn't belong to you.")
        return
    ok, msg = transaction_manager.return_book(txn_id)
    print(("✔ " if ok else "✘ ") + msg)
 
 
def menu_view_overdue():
    print_header("Overdue Books")
    user_id = None if is_admin() else CURRENT_USER["id"]
    overdue = transaction_manager.get_overdue_loans(user_id=user_id)
    if not overdue:
        print("Nothing overdue. Nice.")
        return
    print(f"\n{'TxnID':<7}{'Title':<25}{'User':<18}{'Days Late':<10}{'Fine':<8}")
    print("-" * 70)
    for o in overdue:
        print(f"{o['txn_id']:<7}{o['title'][:24]:<25}{o['user_name'][:17]:<18}"
              f"{o['days_late']:<10}${o['current_fine']:.2f}")
 
 
def menu_view_transactions():
    print_header("Transaction History")
    user_id = None if is_admin() else CURRENT_USER["id"]
    txns = transaction_manager.get_all_transactions(user_id=user_id)
    if not txns:
        print("No transactions yet.")
        return
    print(f"\n{'ID':<4}{'Title':<22}{'User':<15}{'Borrowed':<12}{'Due':<12}{'Returned':<12}{'Fine':<6}")
    print("-" * 85)
    for t in txns:
        returned = t["return_date"] or "-"
        print(f"{t['txn_id']:<4}{t['title'][:21]:<22}{t['user_name'][:14]:<15}"
              f"{t['borrow_date']:<12}{t['due_date']:<12}{returned:<12}${t['fine']:.2f}")
 
 
# ---------------- Reservation menu ----------------
 
def menu_reserve_book():
    print_header("Reserve a Book (Waitlist)")
    fully_booked = [b for b in book_manager.get_all_books() if b["available_copies"] == 0]
    if not fully_booked:
        print("Nothing is fully checked out right now — everything can be borrowed directly.")
        return
    print_books(fully_booked)
    user_id = _resolve_acting_user_id("Reserve")
    if user_id is None:
        return
    book_id = prompt("Book ID to reserve")
    if not book_id.isdigit():
        print("✘ Invalid ID.")
        return
    ok, msg = reservation_manager.reserve_book(user_id, int(book_id))
    print(("✔ " if ok else "✘ ") + msg)
 
 
def menu_view_reservation_queue():
    print_header("Reservation Queue")
    if is_admin():
        reservations = reservation_manager.get_all_active_reservations()
    else:
        reservations = reservation_manager.get_reservations_for_user(CURRENT_USER["id"])
    if not reservations:
        print("No active reservations.")
        return
    print(f"\n{'ID':<5}{'Title':<25}{'Status':<10}{'Since':<12}")
    print("-" * 55)
    for r in reservations:
        print(f"{r['reservation_id']:<5}{r['title'][:24]:<25}{r['status']:<10}{r['reservation_date']:<12}")
    print("\n'ready' = a copy is being held and can be picked up.")
 
 
def menu_fulfill_reservation():
    print_header("Pick Up a Reserved Book")
    if is_admin():
        ready = [r for r in reservation_manager.get_all_active_reservations() if r["status"] == "ready"]
    else:
        ready = [r for r in reservation_manager.get_reservations_for_user(CURRENT_USER["id"])
                 if r["status"] == "ready"]
    if not ready:
        print("No reservations are ready for pickup yet.")
        return
    print(f"\n{'ID':<5}{'Title':<25}")
    print("-" * 32)
    for r in ready:
        print(f"{r['reservation_id']:<5}{r['title'][:24]:<25}")
    res_id = prompt("Reservation ID to pick up")
    if not res_id.isdigit():
        print("✘ Invalid ID.")
        return
    ok, msg = reservation_manager.fulfill_reservation(int(res_id))
    print(("✔ " if ok else "✘ ") + msg)
 
 
def menu_cancel_reservation():
    print_header("Cancel a Reservation")
    menu_view_reservation_queue()
    res_id = prompt("Reservation ID to cancel")
    if not res_id.isdigit():
        print("✘ Invalid ID.")
        return
    ok, msg = reservation_manager.cancel_reservation(int(res_id))
    print(("✔ " if ok else "✘ ") + msg)
 
 
# ---------------- Reports (admin only) ----------------
 
@admin_required
def menu_reports():
    print_header("Library Reports")
    s = reports_manager.library_summary()
    print(f"Books: {s['total_books']} titles, {s['available_copies']}/{s['total_copies']} copies available")
    print(f"Members: {s['total_users']}")
    print(f"Active loans: {s['active_loans']}   |   Active reservations: {s['active_reservations']}")
    print(f"Total transactions ever: {s['total_transactions']}")
    print(f"Total fine revenue collected: ${reports_manager.total_fine_revenue():.2f}")
 
    print("\n-- Most borrowed books --")
    rows = reports_manager.most_borrowed_books()
    if not rows:
        print("No loans yet.")
    for r in rows:
        print(f"  {r['borrow_count']:>3}x  {r['title']} ({r['author']})")
 
    print("\n-- Most active members --")
    rows = reports_manager.most_active_members()
    if not rows:
        print("No loans yet.")
    for r in rows:
        print(f"  {r['loan_count']:>3}x  {r['name']}")
 
    print("\n-- Top fine payers --")
    rows = reports_manager.top_fine_payers()
    if not rows:
        print("No fines charged yet.")
    for r in rows:
        print(f"  ${r['total_fines']:>6.2f}  {r['name']} ({r['late_returns']} late return(s))")
 
    print("\n-- Books by category --")
    for r in reports_manager.category_breakdown():
        print(f"  {r['category']:<20} {r['book_count']} title(s), {r['copy_count']} copies")
 
 
# ---------------- Main loop ----------------
 
def build_menu():
    """Menu text and action map differ depending on whether CURRENT_USER is an admin."""
    lines = [
        "",
        f"LIBRARY MANAGEMENT SYSTEM — logged in as {CURRENT_USER['name']} ({CURRENT_USER['role']})",
        "-" * 65,
        " 1. View books",
        " 2. Filter books",
        " 3. Search books",
        " 4. Borrow a book",
        " 5. Return a book",
        " 6. My/overdue books" if not is_admin() else " 6. View overdue books",
        " 7. Transaction history",
        " 8. Reserve a book (waitlist)",
        " 9. View reservation queue",
        "10. Pick up a reserved book",
        "11. Cancel a reservation",
    ]
    actions = {
        "1": menu_view_books,
        "2": menu_filter_books,
        "3": menu_search_books,
        "4": menu_borrow_book,
        "5": menu_return_book,
        "6": menu_view_overdue,
        "7": menu_view_transactions,
        "8": menu_reserve_book,
        "9": menu_view_reservation_queue,
        "10": menu_fulfill_reservation,
        "11": menu_cancel_reservation,
    }
    if is_admin():
        lines += [
            "12. Add a book",
            "13. Update a book",
            "14. Delete a book",
            "15. Register a user",
            "16. View all users",
            "17. Reports & statistics",
            "18. Change a user's role (promote/demote admin)",
            "19. Delete a user",
        ]
        actions.update({
            "12": menu_add_book,
            "13": menu_update_book,
            "14": menu_delete_book,
            "15": menu_register_user,
            "16": menu_view_users,
            "17": menu_reports,
            "18": menu_change_user_role,
            "19": menu_delete_user,
        })
    lines.append(" 0. Exit")
    return "\n".join(lines), actions
 
 
def main():
    initialize_database()
    login()
    while True:
        menu_text, actions = build_menu()
        print(menu_text)
        choice = input("Choose an option: ").strip()
        if choice == "0":
            print("Goodbye!")
            break
        action = actions.get(choice)
        if action:
            try:
                action()
            except Exception as e:
                print(f"✘ Unexpected error: {e}")
        else:
            print("Invalid option. Please choose a number from the menu.")
 
 
if __name__ == "__main__":
    main()