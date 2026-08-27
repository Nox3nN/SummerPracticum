"""
make_admin.py
Standalone utility to promote an existing user to admin, or create a brand
new admin account, without going through the interactive main.py menu.

Useful for bootstrapping access when you already have data in library.db
and don't want to wipe it just to get a fresh admin account.

Run with: python make_admin.py
"""

from database import initialize_database
import user_manager


def main():
    initialize_database()
    print("=" * 50)
    print("Grant Admin Access")
    print("=" * 50)

    email = input("Email of the user to make admin: ").strip()
    if not email:
        print("✘ Email cannot be empty.")
        return

    user = user_manager.get_user_by_email(email)

    if user:
        if user["role"] == "admin":
            print(f"✔ {user['name']} ({email}) is already an admin. Nothing to do.")
            return
        ok, msg = user_manager.update_user_role(user["id"], "admin")
        print(("✔ " if ok else "✘ ") + msg)
        return

    print(f"No existing user found with email '{email}'.")
    choice = input("Create a brand new admin account with this email? (y/n): ").strip().lower()
    if choice != "y":
        print("No changes made.")
        return

    name = input("Name: ").strip()
    if not name:
        print("✘ Name cannot be empty. No changes made.")
        return

    ok, msg = user_manager.register_user(name, email, role="admin")
    print(("✔ " if ok else "✘ ") + msg)


if __name__ == "__main__":
    main()
