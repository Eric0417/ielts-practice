"""
Create an admin user from the command line.

Usage:
    python scripts/create_admin.py --email admin@example.com --password yourpassword

This script is meant for one-time admin account creation.
It hashes the password with bcrypt and inserts directly into the database.
"""
import argparse
import sys
import os

# Add backend to path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.database import SessionLocal
from app.models import User
from app.auth import hash_password


def main():
    parser = argparse.ArgumentParser(
        description="Create an admin user for the IELTS practice platform"
    )
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument("--password", required=True, help="Admin password (min 6 chars)")
    args = parser.parse_args()

    if len(args.password) < 6:
        print("ERROR: Password must be at least 6 characters.")
        sys.exit(1)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == args.email).first()
        if existing:
            if existing.is_admin:
                print(f"User {args.email} is already an admin.")
            else:
                existing.is_admin = True
                db.commit()
                print(f"Upgraded {args.email} to admin.")
            return

        user = User(
            email=args.email,
            password_hash=hash_password(args.password),
            is_admin=True,
        )
        db.add(user)
        db.commit()
        print(f"Admin user created: {args.email}")

    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
