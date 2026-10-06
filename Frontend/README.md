# EPMS — Employee Payroll Management System (Frontend)

A complete, production-quality **frontend prototype** for an enterprise Employee
Payroll Management System, built to integrate cleanly with a FastAPI + MySQL
backend. This is the frontend only — no backend/API is included.

---

## 1. Tech Stack

- React 19 + TypeScript + Vite 8
- Tailwind CSS v4 (custom design tokens, no component library lock-in)
- React Router v7
- React Hook Form + Zod (validation)
- Recharts (dashboards & analytics)
- Lucide React (icons)

---

## 2. Installation

```bash
npm install
```

## 3. Run (development)

```bash
npm run dev
```

The app runs at `http://localhost:5173` by default.

## 4. Build (production)

```bash
npm run build
npm run preview   # serve the production build locally
```

## 5. Environment Variables

Copy `.env.example` to `.env` and configure the FastAPI server:

```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_USE_MOCKS=false
VITE_AUTH_LOGIN_MODE=json
```

- `VITE_API_BASE_URL` is the only place the backend URL is configured.
- `VITE_USE_MOCKS=false` makes domain services call FastAPI. Set it to `true` for the self-contained demo UI.
- `VITE_AUTH_LOGIN_MODE=json` sends `{ username, password }`. Set it to `form` when the FastAPI login route uses `OAuth2PasswordRequestForm`.
- JWT access tokens are stored only in browser storage for the active session and are attached as `Authorization: Bearer ...`.
- On application startup, an existing token is verified through `GET /auth/me` instead of trusting stale user data in storage.

Every HTTP call goes through `src/services/api.ts`; pages do not construct API URLs directly.

---

## 6. Demo Login

The login page lists six demo accounts (any password of 4+ characters works),
one per role:

| Username | Role |
|---|---|
| radhika.suryatal | Employee |
| amit.kulkarni | Manager |
| priya.sharma | HR |
| payroll.admin | Payroll Administrator |
| sysadmin | System Administrator |
| management | Management |

---

## 7. Folder Structure

```
src/
├── assets/
├── components/
│   ├── layout/       Sidebar, Topbar, Breadcrumb, AppLayout
│   ├── common/        PageHeader, StatusBadge, DashboardCard, ChartCard,
│   │                   EmployeeAvatar, SearchBar, FilterBar, Pagination,
│   │                   Loading/Empty/Error states, NotificationDropdown,
│   │                   ProfileDropdown, GlobalSearch
│   ├── tables/         DataTable (sort, paginate, empty/loading states)
│   ├── forms/          (React Hook Form patterns used inline per module)
│   ├── charts/         (Recharts wrapped via ChartCard)
│   ├── modals/         (Dialog-based patterns used inline per module)
│   └── ui/              Button, Card, Badge, Input, Label, Select, Textarea,
│                         Dialog, ConfirmDialog, Tabs, Checkbox
├── pages/
│   ├── auth/            Login, Forbidden
│   ├── dashboard/       Role-aware dashboards (6 variants)
│   ├── users/            Users, Roles & Permissions
│   ├── organization/    Departments, Designations
│   ├── employees/       Directory, Profile, My Profile
│   ├── attendance/      Attendance
│   ├── leave/            Leave Management
│   ├── payroll/          Salary Structures, Processing, Deductions,
│   │                      Validation, Payslips
│   ├── reports/          Salary Reports, Leave Alerts, Exports
│   ├── audit/            Audit Logs
│   └── infrastructure/  Backup & Restore, System Monitoring
├── services/            api.ts + one service module per domain (API-first,
│                         with an explicit VITE_USE_MOCKS demo mode)
├── context/              AuthContext.tsx
├── config/                permissions.ts (RBAC matrix), navigation.ts
├── routes/                AppRoutes.tsx, ProtectedRoute.tsx
├── types/                 index.ts (Pydantic-mirroring DTOs)
├── data/                  mockData.ts (realistic seed data)
├── hooks/                  useClickOutside
├── utils/                  cn.ts, format.ts
├── App.tsx
└── main.tsx
```

---

## 8. Implemented Pages (28)

1. Login
2. Registration
3. Forbidden (403) / Not Found (404)
4. Dashboard — Employee variant
5. Dashboard — Manager variant
6. Dashboard — HR variant
7. Dashboard — Payroll Administrator variant
8. Dashboard — System Administrator variant
9. Dashboard — Management variant
9. Users (Identity & Access)
10. Roles & Permissions (matrix)
11. Departments
12. Designations
13. Employee Directory
14. Employee Profile (tabbed: Personal, Employment, Attendance, Leave, Salary, Payslips)
15. My Profile (self-service redirect)
16. Attendance
17. Leave Management (apply / approve / reject / cancel)
18. Salary Structures
19. Payroll Processing (14-step workflow visualization)
20. Deductions & Tax Calculation
21. Payroll Validation
22. Payslips (printable payslip document)
23. Salary Reports (filters + charts + export actions)
24. Leave Balance Alerts
25. Export Reports
26. Audit Logs (with WHO/WHAT/WHEN detail modal)
27. Backup & Restore (confirmation-gated restore)
28. System Monitoring

---

## 9. Roles

1. Employee
2. Manager
3. HR
4. Payroll Administrator
5. System Administrator
6. Management

---

## 10. Role–Permission Matrix

Full detail lives in `src/config/permissions.ts` (`ROLE_PERMISSIONS`) and is
also browsable in-app at **Roles & Permissions**. Summary:

| Permission Area | Employee | Manager | HR | Payroll Admin | Sys Admin | Management |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Employee (self) | Y | Y | Y | Y | Y | Y |
| Employee (all) | | Y | Y | Y | Y | Y |
| Employee create/update/delete | | | Y | | | |
| Attendance (self) | Y | Y | Y | | | |
| Attendance (all) / create / update | | Y | Y | Y | | Y |
| Leave apply | Y | Y | | | | |
| Leave approve / reject | | Y | Y | | | |
| Leave view (all) | | Y | Y | Y | | Y |
| Salary (self) | Y | Y | Y | | | |
| Salary (all) / create / update | | | | Y | | Y (view) |
| Payroll view / process / approve / validate | | | | Y | | view only |
| Payslip (self) | Y | Y | Y | Y | | |
| Payslip (all) / generate | | | | Y | | |
| Reports view / export | | Y view | Y | Y | | Y |
| Audit view | | | Y | Y | Y | Y |
| Backup create / restore | | | | | Y | |
| Monitoring view | | | | | Y | |
| Users / Roles / Org manage | | | Y org | | Y | |

Frontend RBAC is a **UI convenience only** — it hides nav items, disables
buttons and blocks routes via `ProtectedRoute`. It is not a security
boundary. The FastAPI backend must independently enforce every permission
using JWT + role/permission checks on each endpoint.

---

## 11. FastAPI Integration Points

Every file in `src/services/` documents the exact endpoint(s) it expects at
the top of the file, e.g.:

```ts
// FastAPI: GET/POST /employees, GET/PUT/DELETE /employees/{id}
```

Full endpoint list expected by the frontend:

```
POST   /auth/login             POST   /auth/register
POST   /auth/refresh           POST   /auth/logout
GET    /auth/me

GET/POST /users                GET/PUT/DELETE /users/{id}
GET/POST /roles                PUT /roles/{id}

GET/POST /departments          GET/PUT/DELETE /departments/{id}
GET/POST /designations         GET/PUT/DELETE /designations/{id}
GET/POST /employees            GET/PUT/DELETE /employees/{id}

GET/POST /attendance           PUT /attendance/{id}
GET/POST /leaves               GET /leaves/{id}
                                PUT /leaves/{id}/approve
                                PUT /leaves/{id}/reject

GET/POST /salary-structures    GET/PUT /salary-structures/{id}

GET /payroll                   POST /payroll/process
POST /payroll/validate         POST /payroll/{id}/approve

GET /deductions                GET /tax-rules
GET /payroll-validation

GET /payslips                  GET /payslips/{id}
GET /payslips/{id}/pdf

GET /reports/salary            GET /reports/leave
GET /reports/payroll

GET/POST /exports

GET /audit-logs

GET/POST /backups              POST /backups/{id}/restore

GET /monitoring
```

---

## 12. FastAPI Integration Status

The frontend now has an API-first service layer. Set `VITE_USE_MOCKS=false` to use FastAPI.
The service modules map the UI operations to the endpoint contract documented above, while
`VITE_USE_MOCKS=true` keeps the complete UI usable without a running backend.

Authentication is real when mocks are disabled: login calls `/auth/login`, the token is attached
to protected requests, and startup validates the session with `/auth/me`. Registration creates
Employee accounts through `/auth/register`; elevated roles are not exposed through public registration.

The frontend remains intentionally independent of backend implementation details. Backend RBAC
must still enforce every permission; frontend permissions only control navigation and UX.

---

## 13. Design System

Colors, spacing and type scale are defined once in `src/index.css` under
`@theme`, matching the required enterprise blue palette:

- Primary `#1E3A8A` · Secondary `#2563EB`
- Background `#F8FAFC` · Card `#FFFFFF`
- Text `#172033` · Muted text `#64748B` · Border `#E2E8F0`
- Success `#16A34A` · Warning `#D97706` · Danger `#DC2626` · Info `#0284C7`

All UI primitives (`src/components/ui/`) consume these tokens via Tailwind
utility classes, so a palette change only requires editing `index.css`.
