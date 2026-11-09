#!/usr/bin/env python3
"""Secure First-Admin Bootstrap CLI for EPMS.

Prompts securely for admin credentials without echoing passwords.
Idempotently assigns the System Administrator role and respects all database constraints.
"""
import argparse
import getpass
import os
import re
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.application.identity.rbac_service import RBACService
from app.infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork
from app.infrastructure.persistence.models.user import User
from app.infrastructure.security.password import hash_password


EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_username(username: str) -> None:
    if len(username.strip()) < 3:
        raise ValueError("Username must be at least 3 characters long.")
    if not re.match(r"^[a-zA-Z0-9._-]+$", username.strip()):
        raise ValueError("Username may only contain letters, numbers, dots, dashes, and underscores.")


def validate_email(email: str) -> None:
    if not EMAIL_REGEX.match(email.strip()):
        raise ValueError("Please enter a valid email address.")


def validate_password(password: str) -> None:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")


def get_existing_admins(uow: SQLAlchemyUnitOfWork) -> list[User]:
    """Find all users currently assigned the System Administrator role."""
    admin_role = uow.roles.get_by_name("System Administrator")
    if not admin_role:
        return []
    statement = (
        uow.session.query(User)
        .join(
            uow.roles.session.query(uow.roles.__class__).subquery()
            if False else User
        )
    )
    # Use user_roles query
    from app.infrastructure.persistence.models.role import UserRole
    admin_user_ids = [
        ur.user_id for ur in
        uow.session.query(UserRole).filter(UserRole.role_id == admin_role.role_id).all()
    ]
    if not admin_user_ids:
        return []
    return uow.session.query(User).filter(User.user_id.in_(admin_user_ids)).all()


def bootstrap_admin(
    username: str,
    email: str,
    password: str | None = None,
    force: bool = False,
) -> bool:
    validate_username(username)
    validate_email(email)
    if password is not None:
        validate_password(password)

    with SQLAlchemyUnitOfWork() as uow:
        rbac = RBACService(uow)
        # 1. Ensure roles and permissions are initialized
        rbac.init_rbac()

        admin_role = uow.roles.get_by_name("System Administrator")
        if not admin_role:
            print("[ERROR] System Administrator role could not be resolved.", file=sys.stderr)
            return False

        existing_admins = get_existing_admins(uow)
        if existing_admins and not force:
            print("\n[NOTE] One or more Administrator accounts already exist in the system:")
            for adm in existing_admins:
                print(f"  - {adm.username} ({adm.email})")

        # 2. Check if the target user already exists
        user = uow.users.get_by_username(username.strip())

        if user is not None:
            # Check if this user is already an admin
            user_roles = uow.roles.get_user_roles(user.user_id)
            if any(r.role_id == admin_role.role_id for r in user_roles):
                print(f"\n[INFO] User '{user.username}' is already a System Administrator. No changes required.")
                return True

            print(f"\n[PROMOTION] Found existing user '{user.username}' ({user.email}).")
            if not force:
                confirm = input(f"Promote existing user '{user.username}' to System Administrator? [y/N]: ").strip().lower()
                if confirm not in ("y", "yes"):
                    print("[ABORTED] Promotion cancelled.")
                    return False

            # Assign admin role preserving user's existing credentials and details
            rbac.assign_user_role(
                user_id=user.user_id,
                role_name="System Administrator",
                assigned_by_user_id=user.user_id,
            )
            print(f"[SUCCESS] Successfully promoted '{user.username}' to System Administrator.")

        else:
            # Need password for creating a new user
            if not password:
                raise ValueError("Password is required to create a new Administrator user.")

            # Check email uniqueness
            existing_email_user = uow.users.get_by_email(email.strip())
            if existing_email_user is not None:
                raise ValueError(f"Email '{email}' is already registered to user '{existing_email_user.username}'.")

            # Create new admin user with hashed password
            hashed = hash_password(password)
            user = User(
                username=username.strip(),
                email=email.strip(),
                password_hash=hashed,
                status="ACTIVE",
            )
            uow.users.add(user)
            uow.session.flush()

            # Assign System Administrator role with self-assignment for bootstrap
            rbac.assign_user_role(
                user_id=user.user_id,
                role_name="System Administrator",
                assigned_by_user_id=user.user_id,
            )

            # Record audit event
            if getattr(uow, "audits", None) is not None:
                from app.application.audit.audit_service import AuditService
                AuditService(uow).record_event(
                    actor_user_id=user.user_id,
                    action="First Admin Bootstrap",
                    resource_type="User",
                    resource_id=user.user_id,
                )

            uow.commit()
            print(f"\n[SUCCESS] New System Administrator account created successfully:")
            print(f"  * User ID:  {user.user_id}")
            print(f"  * Username: {user.username}")
            print(f"  * Email:    {user.email}")
            print(f"  * Role:     System Administrator")

        return True


def main() -> int:
    parser = argparse.ArgumentParser(description="EPMS First-Admin Bootstrap CLI")
    parser.add_argument("--username", "-u", help="Admin username (optional, prompts if omitted)")
    parser.add_argument("--email", "-e", help="Admin email (optional, prompts if omitted)")
    parser.add_argument("--non-interactive", action="store_true", help="Run without interactive prompts (reads ADMIN_PASSWORD from env)")
    parser.add_argument("--force", "-f", action="store_true", help="Bypass existing admin confirmation prompts")
    args = parser.parse_args()

    print("=" * 60)
    print(" EPMS Secure First-Admin Bootstrap CLI")
    print("=" * 60)

    # 1. Username
    username = args.username or os.getenv("ADMIN_USERNAME")
    if not username:
        if args.non_interactive:
            print("[ERROR] --username or ADMIN_USERNAME required in non-interactive mode.", file=sys.stderr)
            return 1
        username = input("Enter Admin Username: ").strip()

    try:
        validate_username(username)
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    # 2. Email
    email = args.email or os.getenv("ADMIN_EMAIL")
    if not email:
        if args.non_interactive:
            print("[ERROR] --email or ADMIN_EMAIL required in non-interactive mode.", file=sys.stderr)
            return 1
        email = input("Enter Admin Email: ").strip()

    try:
        validate_email(email)
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    # 3. Password (masked prompt, never echoed)
    password = os.getenv("ADMIN_PASSWORD")
    if not password:
        if args.non_interactive:
            print("[ERROR] ADMIN_PASSWORD environment variable required in non-interactive mode.", file=sys.stderr)
            return 1

        password = getpass.getpass("Enter Admin Password (min 8 chars): ")
        confirm = getpass.getpass("Confirm Admin Password: ")
        if password != confirm:
            print("[ERROR] Passwords do not match.", file=sys.stderr)
            return 1

    try:
        validate_password(password)
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    try:
        success = bootstrap_admin(username=username, email=email, password=password, force=args.force)
        return 0 if success else 1
    except Exception as exc:
        print(f"\n[ERROR] Bootstrap failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
