# EPMS Role-Based Access Control (RBAC) Setup & Administration Guide

## 1. Overview and Architecture

The Employee Payroll Management System (EPMS) implements a database-backed Role-Based Access Control (RBAC) architecture enforcing the principle of least privilege across both the FastAPI backend and React frontend.

### Database Design
- **`roles`**: Stores defined roles (`role_id`, `role_name`, `description`, `is_active`, `created_at`).
- **`permissions`**: Stores granular system permissions (`permission_id`, `permission_code`, `description`, `created_at`).
- **`role_permissions`**: Many-to-many junction table mapping roles to authorized permission codes (`role_id`, `permission_id`).
- **`user_roles`**: Many-to-many junction table assigning roles to users (`user_id`, `role_id`, `assigned_by_user_id`, `assigned_at`).
  - *Constraint*: `assigned_by_user_id` is a required foreign key pointing to `users(user_id)`. During initial admin bootstrap, self-assignment (`assigned_by_user_id = user.user_id`) is used. For subsequent user role updates, the active admin's `user_id` is recorded.
- **`users`**: Contains identity and authentication credentials (`user_id`, `username`, `email`, `password_hash`, `status`). It contains no raw role column; roles and permissions are resolved dynamically via `user_roles`.

---

## 2. Roles and Permission Mappings

EPMS provides 6 canonical system roles mapped to 34 granular permissions:

| Role Name | Description | Key Permissions Granted |
| :--- | :--- | :--- |
| **System Administrator** | Full administrative access across the platform | All 34 system permissions, including `users.manage`, `users.view`, `roles.manage`, `audit.view`, configuration, employee management, payroll processing, and report exports. |
| **HR** | Human resources management and employee lifecycle | `employee.view.all`, `employee.create`, `employee.update`, `attendance.view.all`, `attendance.update`, `leave.view.all`, `leave.approve`, `leave.reject`, `salary.view.all`, `reports.view`, `reports.export`, `audit.view` |
| **Payroll Administrator** | Salary and payroll management | `employee.view.all`, `attendance.view.all`, `leave.view.all`, `salary.view.all`, `salary.create`, `salary.update`, `payroll.view`, `payroll.process`, `payroll.approve`, `payroll.validate`, `payslip.view.all`, `payslip.generate`, `reports.view`, `reports.export`, `audit.view` |
| **Manager** | Departmental management and approvals | `employee.view.all`, `attendance.view.all`, `attendance.update`, `leave.view.all`, `leave.approve`, `leave.reject`, `salary.view.self`, `payslip.view.self`, `reports.view`, `reports.export`, `audit.view` |
| **Employee** *(Default)* | Standard employee / member self-service | `employee.view.self`, `attendance.view.self`, `attendance.record`, `leave.view.self`, `leave.apply`, `leave.cancel`, `salary.view.self`, `payslip.view.self` |
| **Management** | Executive oversight and reporting | `employee.view.all`, `attendance.view.all`, `leave.view.all`, `salary.view.all`, `payroll.view`, `reports.view`, `reports.export`, `audit.view` |

### Granular Permission List (34 Total)
- **Users & Roles**: `users.view`, `users.manage`, `roles.view`, `roles.manage`
- **Employees**: `employee.view.all`, `employee.view.self`, `employee.create`, `employee.update`, `employee.delete`
- **Attendance**: `attendance.view.all`, `attendance.view.self`, `attendance.record`, `attendance.update`
- **Leave**: `leave.view.all`, `leave.view.self`, `leave.apply`, `leave.approve`, `leave.reject`, `leave.cancel`
- **Salary**: `salary.view.all`, `salary.view.self`, `salary.create`, `salary.update`
- **Payroll**: `payroll.view`, `payroll.process`, `payroll.approve`, `payroll.validate`
- **Payslip**: `payslip.view.all`, `payslip.view.self`, `payslip.generate`, `payslip.download`
- **Reports & Auditing**: `reports.view`, `reports.export`, `audit.view`

---

## 3. Files Changed and Rationale

| File Path | Change Rationale |
| :--- | :--- |
| [role_repository.py](file:///d:/FJ/Coding%20work/Python/EDI_PayRoll_Management_System/app/infrastructure/persistence/repositories/role_repository.py) | Added helper methods for permissions and role assignments (`get_permission_by_code`, `add_permission`, `get_role_permission`, `add_role_permission`, `remove_user_roles`, `get_user_permissions`). |
| [rbac_service.py](file:///d:/FJ/Coding%20work/Python/EDI_PayRoll_Management_System/app/application/identity/rbac_service.py) | **(New)** Implemented `RBACService` encapsulating standard roles, permissions, idempotent initialization (`init_rbac`), role assignments, and permission verification. |
| [permissions.py](file:///d:/FJ/Coding%20work/Python/EDI_PayRoll_Management_System/app/api/dependencies/permissions.py) | **(New)** Created FastAPI dependencies `require_permission(code)` and `require_role(role)` returning HTTP 403 Forbidden for unauthorized requests. |
| [schemas.py](file:///d:/FJ/Coding%20work/Python/EDI_PayRoll_Management_System/app/application/identity/schemas.py) | Added dynamic `permissions: list[str]` field to `UserMeResponse` and `UserResponse`. |
| [user_service.py](file:///d:/FJ/Coding%20work/Python/EDI_PayRoll_Management_System/app/application/identity/user_service.py) | Enforced default `Employee` role assignment upon public registration; prevented role tampering; dynamically attached permissions in `to_user_me`; audited user and role changes. |
| [users.py](file:///d:/FJ/Coding%20work/Python/EDI_PayRoll_Management_System/app/api/v1/endpoints/users.py) | Guarded `GET /users`, `POST /users`, `PUT /users/{id}`, and `DELETE /users/{id}` with `require_permission("users.manage")`; permitted self-inspection on `GET /users/{id}`; blocked admin self-deletion. |
| [roles.py](file:///d:/FJ/Coding%20work/Python/EDI_PayRoll_Management_System/app/api/v1/endpoints/roles.py) | Guarded `POST /roles` and `PUT /roles/{id}` with `require_permission("roles.manage")`. |
| [scripts/init_rbac.py](file:///d:/FJ/Coding%20work/Python/EDI_PayRoll_Management_System/scripts/init_rbac.py) | **(New)** Idempotent CLI script to populate system roles, permissions, and mappings without modifying user accounts. |
| [scripts/bootstrap_admin.py](file:///d:/FJ/Coding%20work/Python/EDI_PayRoll_Management_System/scripts/bootstrap_admin.py) | **(New)** Secure interactive first-Admin bootstrap CLI using `getpass` (masked input) with input validation, password hashing, and audit logging. |
| [AuthContext.tsx](file:///d:/FJ/Coding%20work/Python/EDI_PayRoll_Management_System/Frontend/src/context/AuthContext.tsx) | Updated frontend authorization context so `can(permission)` checks dynamic backend permissions returned from `/auth/me`. |
| [UsersList.tsx](file:///d:/FJ/Coding%20work/Python/EDI_PayRoll_Management_System/Frontend/src/pages/users/UsersList.tsx) | Added visual 403 Forbidden alerts and enhanced user management error states. |
| [UserFormDialog.tsx](file:///d:/FJ/Coding%20work/Python/EDI_PayRoll_Management_System/Frontend/src/pages/users/UserFormDialog.tsx) | Added password fields for user creation and improved role selection UI. |
| [test_rbac.py](file:///d:/FJ/Coding%20work/Python/EDI_PayRoll_Management_System/tests/api/test_rbac.py) | **(New)** Automated test suite containing 13 tests covering RBAC initialization, authorization guards, privilege escalation defense, and admin operations. |

---

## 4. RBAC Initialization (PowerShell)

To initialize or verify all roles, permissions, and role-permission mappings in the database, execute:

```powershell
.\.venv\Scripts\python.exe scripts/init_rbac.py
```

### Idempotency Guarantee
Running this command repeatedly is 100% safe. It checks for existing records before inserting:
- If a permission or role exists, it is reused.
- If a mapping exists, it is skipped.
- Existing user accounts and passwords are not touched.

---

## 5. First-Admin Bootstrap (PowerShell)

There is no default hardcoded admin account. You must bootstrap the initial administrator using the secure interactive script:

### Interactive Mode (Recommended)
```powershell
.\.venv\Scripts\python.exe scripts/bootstrap_admin.py
```

You will be prompted interactively:
1. **Enter Admin Username**: e.g. `admin` or `system.admin`
2. **Enter Admin Email**: e.g. `admin@company.in`
3. **Enter Admin Password (min 8 chars)**: Masked input using `getpass` (characters are not printed or echoed to terminal)
4. **Confirm Admin Password**: Masked confirmation

### Promoting an Existing User to Admin
If the username entered belongs to an existing user (e.g. `farhan.member`), the CLI will ask:
```
Promote existing user 'farhan.member' to System Administrator? [y/N]:
```
Entering `y` assigns the `System Administrator` role without altering the existing password or account details.

### Non-Interactive / Scripted Mode
For CI/CD or automated staging environments, credentials can be supplied via environment variables without hardcoding secrets in files:

```powershell
$env:ADMIN_PASSWORD="YourSecurePassword123!"
.\.venv\Scripts\python.exe scripts/bootstrap_admin.py --username sysadmin --email sysadmin@company.in --non-interactive
Remove-Item Env:ADMIN_PASSWORD
```

---

## 6. How to Log In as the Admin

1. Start or verify the backend server:
   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
   ```
2. Start the frontend development server:
   ```powershell
   cd Frontend
   npm run dev
   ```
3. Open `http://localhost:5173/login` in your web browser.
4. Log in with the credentials supplied during the bootstrap process:
   - **Username**: `<admin_username>`
   - **Password**: `<admin_password>`
5. Upon login:
   - The `/auth/me` endpoint returns role `System Administrator` and all 34 granted permissions.
   - The navigation sidebar unlocks administrative routes: **User Management** (`/users`), **Roles & Permissions**, **Audit Logs**, and **Reports**.

---

## 7. How an Admin Assigns Roles to Other Users

1. In the sidebar, navigate to **User Management** (`/users`).
2. To create a new user with a specific role:
   - Click **Add User**.
   - Enter Username, Email, First Name, Last Name, Password, and select the desired **Role** (e.g. `HR`, `Payroll Administrator`, `Manager`, or `Employee`).
   - Click **Create User**.
3. To edit or change the role of an existing user:
   - Find the user in the list and click the **Edit** icon.
   - In the dropdown, change the **Role**.
   - Click **Save Changes**.
4. The backend validates:
   - The calling user holds the `users.manage` permission.
   - The target role name is normalized and valid.
   - `assigned_by_user_id` records the calling admin's `user_id`.
   - Security audit event `USER_ROLE_ASSIGNED` is saved to the audit log.

---

## 8. Safe Recovery Procedures if Bootstrap Fails

- **If the password is forgotten for the initial admin**:
  Run the bootstrap script targeting an alternate username or execute the bootstrap CLI in non-interactive mode with a new password.
- **If database transaction fails or is interrupted**:
  `scripts/bootstrap_admin.py` and `scripts/init_rbac.py` wrap changes in an explicit database transaction with automatic rollback on exception. No partial or corrupted state is saved.
- **Pre-existing test account `testuser01`**:
  If the development password for `testuser01` is unknown, it can be promoted or its password reset via the Admin User Management UI once logged in as the initial Admin.

---

## 9. Automated Verification & Test Results

### Backend Test Suite
Executed all unit, integration, and security tests:
```powershell
.\.venv\Scripts\pytest.exe -q
```
**Result**: `151 passed, 1 warning in 3.81s`

Key test cases verified:
- `test_rbac_init_is_idempotent`: RBAC init can be run multiple times with 0 duplicate records.
- `test_register_defaults_to_member_role`: Public registration always assigns `Employee` role.
- `test_register_ignores_client_provided_admin_role`: Privilege escalation via registration payload is rejected.
- `test_unauthenticated_request_rejected`: 401 Unauthorized for missing tokens.
- `test_member_cannot_access_user_list`: 403 Forbidden when a Member requests `GET /api/v1/users`.
- `test_admin_can_access_user_list`: 200 OK with full user list for System Administrator.
- `test_member_cannot_create_user`: 403 Forbidden when a Member tries to create accounts.
- `test_admin_can_create_user_with_role`: 201 Created and correct role assignment in DB.
- `test_admin_cannot_delete_own_account`: 400 Bad Request to protect against accidental admin lockout.
- `test_member_cannot_modify_roles`: 403 Forbidden for role modification endpoints.
- `test_role_assignment_persists_assigned_by_user_id`: Database constraint validated.
- `test_bootstrap_admin_validators`: Input validation rules enforced.

### Frontend Production Build
```powershell
cd Frontend
npm run build
```
**Result**: `tsc -b && vite build` built clean in `1.20s` with **0 TypeScript errors**.

---

## 10. Remaining Limitations & Notes

- **Multi-tenant / Fine-grained Branching**: Role assignments are currently system-wide. Department-scoped manager restrictions (e.g. manager only approving leaves for their own department) are handled at the business logic layer via employee department IDs.
- **Token Invalidation on Role Change**: When an admin updates another user's role, the target user's existing JWT token remains valid until expiry (default 60 minutes), after which refreshing or re-logging fetches the updated role and permissions.
