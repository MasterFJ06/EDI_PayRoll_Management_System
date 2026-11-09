#!/usr/bin/env python3
"""Idempotent RBAC Initialization Script for EPMS.

Initializes all standard permissions, roles, and role-permission mappings in the database.
Safe to run repeatedly without creating duplicates or altering existing users.
"""
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.application.identity.rbac_service import RBACService
from app.infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork


def main() -> int:
    print("=" * 60)
    print(" EPMS Role-Based Access Control (RBAC) Initializer")
    print("=" * 60)

    try:
        with SQLAlchemyUnitOfWork() as uow:
            rbac = RBACService(uow)
            summary = rbac.init_rbac()

            print("\n[SUCCESS] RBAC initialization completed successfully:")
            print(f"  * Roles: {summary['total_roles']} active ({summary['roles_created']} newly created)")
            print(f"  * Permissions: {summary['total_permissions']} active ({summary['permissions_created']} newly created)")
            print(f"  * Role-Permission Mappings: {summary['mappings_created']} newly linked")

            # Print configured roles and their permission counts
            roles = uow.roles.get_all()
            print("\nConfigured System Roles:")
            for r in roles:
                perms = uow.roles.get_role_permissions(r.role_id)
                print(f"  - {r.role_name:<25} ({len(perms)} permissions granted)")

        print("\nDatabase transaction committed cleanly.")
        return 0

    except Exception as exc:
        print(f"\n[ERROR] RBAC initialization failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
