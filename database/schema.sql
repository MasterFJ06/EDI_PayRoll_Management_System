-- =====================================================================
-- EMPLOYEE PAYROLL MANAGEMENT SYSTEM
-- PHYSICAL DATABASE DESIGN — PART 7
-- FINAL EXECUTABLE MYSQL SCHEMA
--
-- Target DBMS : MySQL 8.x
-- Engine      : InnoDB
-- Normal Form : 3NF
-- Tables      : 27
-- =====================================================================


-- =====================================================================
-- 0. DATABASE CREATION
-- =====================================================================

CREATE DATABASE IF NOT EXISTS employee_payroll_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE employee_payroll_db;


-- =====================================================================
-- DOMAIN A — IDENTITY & ACCESS MANAGEMENT
-- =====================================================================


-- =====================================================================
-- 1. USERS
-- =====================================================================

CREATE TABLE users (
    user_id BIGINT UNSIGNED AUTO_INCREMENT,

    username VARCHAR(50) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,

    status VARCHAR(20) NOT NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    last_login_at DATETIME NULL,

    CONSTRAINT pk_users
        PRIMARY KEY (user_id),

    CONSTRAINT uq_users_username
        UNIQUE (username),

    CONSTRAINT uq_users_email
        UNIQUE (email),

    CONSTRAINT chk_users_status
        CHECK (
            status IN (
                'ACTIVE',
                'DISABLED',
                'LOCKED'
            )
        )
) ENGINE = InnoDB;


-- =====================================================================
-- 2. ROLES
-- =====================================================================

CREATE TABLE roles (
    role_id BIGINT UNSIGNED AUTO_INCREMENT,

    role_name VARCHAR(100) NOT NULL,
    description VARCHAR(500) NULL,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_roles
        PRIMARY KEY (role_id),

    CONSTRAINT uq_roles_role_name
        UNIQUE (role_name)
) ENGINE = InnoDB;


-- =====================================================================
-- 3. PERMISSIONS
-- =====================================================================

CREATE TABLE permissions (
    permission_id BIGINT UNSIGNED AUTO_INCREMENT,

    permission_code VARCHAR(100) NOT NULL,
    description VARCHAR(500) NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_permissions
        PRIMARY KEY (permission_id),

    CONSTRAINT uq_permissions_permission_code
        UNIQUE (permission_code)
) ENGINE = InnoDB;


-- =====================================================================
-- 4. USER_ROLES
-- =====================================================================

CREATE TABLE user_roles (
    user_id BIGINT UNSIGNED NOT NULL,
    role_id BIGINT UNSIGNED NOT NULL,

    assigned_by_user_id BIGINT UNSIGNED NOT NULL,
    assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_user_roles
        PRIMARY KEY (
            user_id,
            role_id
        ),

    CONSTRAINT fk_user_roles_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,

    CONSTRAINT fk_user_roles_role
        FOREIGN KEY (role_id)
        REFERENCES roles(role_id)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,

    CONSTRAINT fk_user_roles_assigned_by
        FOREIGN KEY (assigned_by_user_id)
        REFERENCES users(user_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    INDEX idx_user_roles_role (role_id)
) ENGINE = InnoDB;


-- =====================================================================
-- 5. ROLE_PERMISSIONS
-- =====================================================================

CREATE TABLE role_permissions (
    role_id BIGINT UNSIGNED NOT NULL,
    permission_id BIGINT UNSIGNED NOT NULL,

    CONSTRAINT pk_role_permissions
        PRIMARY KEY (
            role_id,
            permission_id
        ),

    CONSTRAINT fk_role_permissions_role
        FOREIGN KEY (role_id)
        REFERENCES roles(role_id)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,

    CONSTRAINT fk_role_permissions_permission
        FOREIGN KEY (permission_id)
        REFERENCES permissions(permission_id)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,

    INDEX idx_role_permissions_permission (permission_id)
) ENGINE = InnoDB;



-- =====================================================================
-- DOMAIN B — ORGANIZATION MANAGEMENT
-- =====================================================================


-- =====================================================================
-- 6. DEPARTMENTS
-- =====================================================================

CREATE TABLE departments (
    department_id BIGINT UNSIGNED AUTO_INCREMENT,

    department_code VARCHAR(30) NOT NULL,
    department_name VARCHAR(100) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_departments
        PRIMARY KEY (department_id),

    CONSTRAINT uq_departments_code
        UNIQUE (department_code),

    CONSTRAINT uq_departments_name
        UNIQUE (department_name),

    CONSTRAINT chk_departments_status
        CHECK (
            status IN (
                'ACTIVE',
                'INACTIVE'
            )
        )
) ENGINE = InnoDB;


-- =====================================================================
-- 7. DESIGNATIONS
-- =====================================================================

CREATE TABLE designations (
    designation_id BIGINT UNSIGNED AUTO_INCREMENT,

    designation_code VARCHAR(30) NOT NULL,
    designation_name VARCHAR(100) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_designations
        PRIMARY KEY (designation_id),

    CONSTRAINT uq_designations_code
        UNIQUE (designation_code),

    CONSTRAINT uq_designations_name
        UNIQUE (designation_name),

    CONSTRAINT chk_designations_status
        CHECK (
            status IN (
                'ACTIVE',
                'INACTIVE'
            )
        )
) ENGINE = InnoDB;


-- =====================================================================
-- 8. EMPLOYEES
-- =====================================================================

CREATE TABLE employees (
    employee_id BIGINT UNSIGNED AUTO_INCREMENT,

    employee_code VARCHAR(30) NOT NULL,

    user_id BIGINT UNSIGNED NULL,

    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,

    department_id BIGINT UNSIGNED NOT NULL,
    designation_id BIGINT UNSIGNED NOT NULL,

    manager_employee_id BIGINT UNSIGNED NULL,

    joining_date DATE NOT NULL,

    employment_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_employees
        PRIMARY KEY (employee_id),

    CONSTRAINT uq_employees_employee_code
        UNIQUE (employee_code),

    CONSTRAINT uq_employees_user
        UNIQUE (user_id),

    CONSTRAINT chk_employees_status
        CHECK (
            employment_status IN (
                'ACTIVE',
                'INACTIVE',
                'TERMINATED'
            )
        ),

    CONSTRAINT fk_employees_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT fk_employees_department
        FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT fk_employees_designation
        FOREIGN KEY (designation_id)
        REFERENCES designations(designation_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT fk_employees_manager
        FOREIGN KEY (manager_employee_id)
        REFERENCES employees(employee_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    INDEX idx_employees_department_status (
        department_id,
        employment_status
    ),

    INDEX idx_employees_designation (
        designation_id
    ),

    INDEX idx_employees_manager (
        manager_employee_id
    )
) ENGINE = InnoDB;


-- =====================================================================
-- 9. EMPLOYMENT_HISTORY
-- =====================================================================

CREATE TABLE employment_history (
    employment_history_id BIGINT UNSIGNED AUTO_INCREMENT,

    employee_id BIGINT UNSIGNED NOT NULL,
    department_id BIGINT UNSIGNED NOT NULL,
    designation_id BIGINT UNSIGNED NOT NULL,

    manager_employee_id BIGINT UNSIGNED NULL,

    effective_from DATE NOT NULL,
    effective_to DATE NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_employment_history
        PRIMARY KEY (employment_history_id),

    CONSTRAINT chk_employment_history_dates
        CHECK (
            effective_to IS NULL
            OR effective_to >= effective_from
        ),

    CONSTRAINT fk_employment_history_employee
        FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT fk_employment_history_department
        FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT fk_employment_history_designation
        FOREIGN KEY (designation_id)
        REFERENCES designations(designation_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT fk_employment_history_manager
        FOREIGN KEY (manager_employee_id)
        REFERENCES employees(employee_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    INDEX idx_employment_history_employee_date (
        employee_id,
        effective_from
    ),

    INDEX idx_employment_history_department (
        department_id
    ),

    INDEX idx_employment_history_designation (
        designation_id
    ),

    INDEX idx_employment_history_manager (
        manager_employee_id
    )
) ENGINE = InnoDB;



-- =====================================================================
-- DOMAIN C — ATTENDANCE & LEAVE MANAGEMENT
-- =====================================================================


-- =====================================================================
-- 10. ATTENDANCE_RECORDS
-- =====================================================================

CREATE TABLE attendance_records (
    attendance_id BIGINT UNSIGNED AUTO_INCREMENT,

    employee_id BIGINT UNSIGNED NOT NULL,

    attendance_date DATE NOT NULL,

    check_in_time DATETIME NULL,
    check_out_time DATETIME NULL,

    attendance_status VARCHAR(20) NOT NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_attendance_records
        PRIMARY KEY (attendance_id),

    CONSTRAINT uq_attendance_employee_date
        UNIQUE (
            employee_id,
            attendance_date
        ),

    CONSTRAINT chk_attendance_status
        CHECK (
            attendance_status IN (
                'PRESENT',
                'ABSENT',
                'HALF_DAY',
                'ON_LEAVE',
                'HOLIDAY'
            )
        ),

    CONSTRAINT chk_attendance_time_order
        CHECK (
            check_out_time IS NULL
            OR check_in_time IS NULL
            OR check_out_time >= check_in_time
        ),

    CONSTRAINT fk_attendance_employee
        FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    INDEX idx_attendance_date (
        attendance_date
    )
) ENGINE = InnoDB;


-- =====================================================================
-- 11. LEAVE_TYPES
-- =====================================================================

CREATE TABLE leave_types (
    leave_type_id BIGINT UNSIGNED AUTO_INCREMENT,

    leave_type_code VARCHAR(30) NOT NULL,
    leave_type_name VARCHAR(100) NOT NULL,

    description VARCHAR(500) NULL,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_leave_types
        PRIMARY KEY (leave_type_id),

    CONSTRAINT uq_leave_types_code
        UNIQUE (leave_type_code),

    CONSTRAINT uq_leave_types_name
        UNIQUE (leave_type_name)
) ENGINE = InnoDB;


-- =====================================================================
-- 12. LEAVE_BALANCES
-- =====================================================================

CREATE TABLE leave_balances (
    leave_balance_id BIGINT UNSIGNED AUTO_INCREMENT,

    employee_id BIGINT UNSIGNED NOT NULL,
    leave_type_id BIGINT UNSIGNED NOT NULL,

    balance_year SMALLINT UNSIGNED NOT NULL,

    allocated_days DECIMAL(6,2) NOT NULL DEFAULT 0.00,
    used_days DECIMAL(6,2) NOT NULL DEFAULT 0.00,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_leave_balances
        PRIMARY KEY (leave_balance_id),

    CONSTRAINT uq_leave_balance
        UNIQUE (
            employee_id,
            leave_type_id,
            balance_year
        ),

    CONSTRAINT chk_leave_balance_allocated
        CHECK (
            allocated_days >= 0
        ),

    CONSTRAINT chk_leave_balance_used
        CHECK (
            used_days >= 0
        ),

    CONSTRAINT chk_leave_balance_limit
        CHECK (
            used_days <= allocated_days
        ),

    CONSTRAINT fk_leave_balance_employee
        FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT fk_leave_balance_type
        FOREIGN KEY (leave_type_id)
        REFERENCES leave_types(leave_type_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    INDEX idx_leave_balances_type (
        leave_type_id
    )
) ENGINE = InnoDB;


-- =====================================================================
-- 13. LEAVE_REQUESTS
-- =====================================================================

CREATE TABLE leave_requests (
    leave_request_id BIGINT UNSIGNED AUTO_INCREMENT,

    employee_id BIGINT UNSIGNED NOT NULL,
    leave_type_id BIGINT UNSIGNED NOT NULL,

    start_date DATE NOT NULL,
    end_date DATE NOT NULL,

    requested_days DECIMAL(6,2) NOT NULL,

    reason VARCHAR(1000) NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',

    reviewed_by_employee_id BIGINT UNSIGNED NULL,
    reviewed_at DATETIME NULL,
    review_comment VARCHAR(1000) NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_leave_requests
        PRIMARY KEY (leave_request_id),

    CONSTRAINT chk_leave_request_dates
        CHECK (
            end_date >= start_date
        ),

    CONSTRAINT chk_leave_requested_days
        CHECK (
            requested_days > 0
        ),

    CONSTRAINT chk_leave_request_status
        CHECK (
            status IN (
                'PENDING',
                'APPROVED',
                'REJECTED',
                'CANCELLED'
            )
        ),

    CONSTRAINT chk_leave_review_consistency
        CHECK (
            (
                status = 'PENDING'
                AND reviewed_by_employee_id IS NULL
                AND reviewed_at IS NULL
            )
            OR
            (
                status IN ('APPROVED', 'REJECTED')
                AND reviewed_by_employee_id IS NOT NULL
                AND reviewed_at IS NOT NULL
            )
            OR
            (
                status = 'CANCELLED'
            )
        ),

    CONSTRAINT fk_leave_request_employee
        FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT fk_leave_request_type
        FOREIGN KEY (leave_type_id)
        REFERENCES leave_types(leave_type_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT fk_leave_request_reviewer
        FOREIGN KEY (reviewed_by_employee_id)
        REFERENCES employees(employee_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    INDEX idx_leave_requests_employee_date (
        employee_id,
        start_date
    ),

    INDEX idx_leave_requests_status_created (
        status,
        created_at
    ),

    INDEX idx_leave_requests_type (
        leave_type_id
    ),

    INDEX idx_leave_requests_reviewer (
        reviewed_by_employee_id
    )
) ENGINE = InnoDB;



-- =====================================================================
-- DOMAIN D — COMPENSATION MANAGEMENT
-- =====================================================================


-- =====================================================================
-- 14. SALARY_STRUCTURES
-- =====================================================================

CREATE TABLE salary_structures (
    salary_structure_id BIGINT UNSIGNED AUTO_INCREMENT,

    structure_code VARCHAR(30) NOT NULL,
    structure_name VARCHAR(100) NOT NULL,

    description VARCHAR(500) NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_salary_structures
        PRIMARY KEY (salary_structure_id),

    CONSTRAINT uq_salary_structures_code
        UNIQUE (structure_code),

    CONSTRAINT chk_salary_structures_status
        CHECK (
            status IN (
                'ACTIVE',
                'INACTIVE'
            )
        )
) ENGINE = InnoDB;


-- =====================================================================
-- 15. SALARY_COMPONENTS
-- =====================================================================

CREATE TABLE salary_components (
    salary_component_id BIGINT UNSIGNED AUTO_INCREMENT,

    component_code VARCHAR(30) NOT NULL,
    component_name VARCHAR(100) NOT NULL,

    component_type VARCHAR(20) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_salary_components
        PRIMARY KEY (salary_component_id),

    CONSTRAINT uq_salary_components_code
        UNIQUE (component_code),

    CONSTRAINT chk_salary_component_type
        CHECK (
            component_type IN (
                'EARNING',
                'DEDUCTION'
            )
        ),

    CONSTRAINT chk_salary_component_status
        CHECK (
            status IN (
                'ACTIVE',
                'INACTIVE'
            )
        )
) ENGINE = InnoDB;


-- =====================================================================
-- 16. SALARY_REVISIONS
-- =====================================================================

CREATE TABLE salary_revisions (
    salary_revision_id BIGINT UNSIGNED AUTO_INCREMENT,

    salary_structure_id BIGINT UNSIGNED NOT NULL,

    revision_number INT UNSIGNED NOT NULL,

    effective_from DATE NOT NULL,
    effective_to DATE NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_salary_revisions
        PRIMARY KEY (salary_revision_id),

    CONSTRAINT uq_salary_revision_number
        UNIQUE (
            salary_structure_id,
            revision_number
        ),

    CONSTRAINT chk_salary_revision_dates
        CHECK (
            effective_to IS NULL
            OR effective_to >= effective_from
        ),

    CONSTRAINT fk_salary_revision_structure
        FOREIGN KEY (salary_structure_id)
        REFERENCES salary_structures(salary_structure_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    INDEX idx_salary_revisions_structure_effective (
        salary_structure_id,
        effective_from,
        effective_to
    )
) ENGINE = InnoDB;


-- =====================================================================
-- 17. SALARY_REVISION_COMPONENTS
-- =====================================================================

CREATE TABLE salary_revision_components (
    salary_revision_id BIGINT UNSIGNED NOT NULL,
    salary_component_id BIGINT UNSIGNED NOT NULL,

    calculation_type VARCHAR(20) NOT NULL,

    fixed_amount DECIMAL(15,2) NULL,
    percentage_value DECIMAL(8,4) NULL,

    base_component_id BIGINT UNSIGNED NULL,

    CONSTRAINT pk_salary_revision_components
        PRIMARY KEY (
            salary_revision_id,
            salary_component_id
        ),

    CONSTRAINT chk_salary_calculation_type
        CHECK (
            calculation_type IN (
                'FIXED',
                'PERCENTAGE'
            )
        ),

    CONSTRAINT chk_salary_component_calculation
        CHECK (
            (
                calculation_type = 'FIXED'
                AND fixed_amount IS NOT NULL
                AND fixed_amount >= 0
                AND percentage_value IS NULL
                AND base_component_id IS NULL
            )
            OR
            (
                calculation_type = 'PERCENTAGE'
                AND fixed_amount IS NULL
                AND percentage_value IS NOT NULL
                AND percentage_value >= 0
                AND base_component_id IS NOT NULL
            )
        ),

    CONSTRAINT chk_salary_component_not_self_base
        CHECK (
            base_component_id IS NULL
            OR base_component_id <> salary_component_id
        ),

    CONSTRAINT fk_revision_component_revision
        FOREIGN KEY (salary_revision_id)
        REFERENCES salary_revisions(salary_revision_id)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,

    CONSTRAINT fk_revision_component_component
        FOREIGN KEY (salary_component_id)
        REFERENCES salary_components(salary_component_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT fk_revision_component_base
        FOREIGN KEY (base_component_id)
        REFERENCES salary_components(salary_component_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    INDEX idx_revision_components_component (
        salary_component_id
    ),

    INDEX idx_revision_components_base (
        base_component_id
    )
) ENGINE = InnoDB;


-- =====================================================================
-- 18. EMPLOYEE_SALARY_ASSIGNMENTS
-- =====================================================================

CREATE TABLE employee_salary_assignments (
    salary_assignment_id BIGINT UNSIGNED AUTO_INCREMENT,

    employee_id BIGINT UNSIGNED NOT NULL,
    salary_revision_id BIGINT UNSIGNED NOT NULL,

    effective_from DATE NOT NULL,
    effective_to DATE NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_employee_salary_assignments
        PRIMARY KEY (salary_assignment_id),

    CONSTRAINT chk_salary_assignment_dates
        CHECK (
            effective_to IS NULL
            OR effective_to >= effective_from
        ),

    CONSTRAINT fk_salary_assignment_employee
        FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT fk_salary_assignment_revision
        FOREIGN KEY (salary_revision_id)
        REFERENCES salary_revisions(salary_revision_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    INDEX idx_salary_assignments_employee_effective (
        employee_id,
        effective_from,
        effective_to
    ),

    INDEX idx_salary_assignments_revision (
        salary_revision_id
    )
) ENGINE = InnoDB;



-- =====================================================================
-- DOMAIN E — PAYROLL PROCESSING
-- =====================================================================


-- =====================================================================
-- 19. PAYROLL_RUNS
-- =====================================================================

CREATE TABLE payroll_runs (
    payroll_run_id BIGINT UNSIGNED AUTO_INCREMENT,

    payroll_year SMALLINT UNSIGNED NOT NULL,
    payroll_month TINYINT UNSIGNED NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'CREATED',

    initiated_by_user_id BIGINT UNSIGNED NOT NULL,

    started_at DATETIME NULL,
    completed_at DATETIME NULL,
    finalized_at DATETIME NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_payroll_runs
        PRIMARY KEY (payroll_run_id),

    CONSTRAINT uq_payroll_period
        UNIQUE (
            payroll_year,
            payroll_month
        ),

    CONSTRAINT chk_payroll_month
        CHECK (
            payroll_month BETWEEN 1 AND 12
        ),

    CONSTRAINT chk_payroll_run_status
        CHECK (
            status IN (
                'CREATED',
                'PROCESSING',
                'FAILED',
                'PROCESSED',
                'FINALIZED'
            )
        ),

    CONSTRAINT fk_payroll_run_initiator
        FOREIGN KEY (initiated_by_user_id)
        REFERENCES users(user_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT
) ENGINE = InnoDB;


-- =====================================================================
-- 20. PAYROLL_RESULTS
-- =====================================================================

CREATE TABLE payroll_results (
    payroll_result_id BIGINT UNSIGNED AUTO_INCREMENT,

    payroll_run_id BIGINT UNSIGNED NOT NULL,
    employee_id BIGINT UNSIGNED NOT NULL,
    salary_assignment_id BIGINT UNSIGNED NOT NULL,

    gross_earnings DECIMAL(15,2) NOT NULL,
    total_deductions DECIMAL(15,2) NOT NULL,
    net_salary DECIMAL(15,2) NOT NULL,

    processed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_payroll_results
        PRIMARY KEY (payroll_result_id),

    CONSTRAINT uq_payroll_result_employee
        UNIQUE (
            payroll_run_id,
            employee_id
        ),

    CONSTRAINT chk_payroll_gross_earnings
        CHECK (
            gross_earnings >= 0
        ),

    CONSTRAINT chk_payroll_total_deductions
        CHECK (
            total_deductions >= 0
        ),

    CONSTRAINT chk_payroll_net_salary
        CHECK (
            net_salary = gross_earnings - total_deductions
        ),

    CONSTRAINT fk_payroll_result_run
        FOREIGN KEY (payroll_run_id)
        REFERENCES payroll_runs(payroll_run_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT fk_payroll_result_employee
        FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT fk_payroll_result_assignment
        FOREIGN KEY (salary_assignment_id)
        REFERENCES employee_salary_assignments(salary_assignment_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    INDEX idx_payroll_results_employee (
        employee_id
    ),

    INDEX idx_payroll_results_assignment (
        salary_assignment_id
    )
) ENGINE = InnoDB;


-- =====================================================================
-- 21. PAYROLL_RESULT_COMPONENTS
-- =====================================================================

CREATE TABLE payroll_result_components (
    payroll_result_component_id BIGINT UNSIGNED AUTO_INCREMENT,

    payroll_result_id BIGINT UNSIGNED NOT NULL,
    salary_component_id BIGINT UNSIGNED NOT NULL,

    component_type VARCHAR(20) NOT NULL,

    amount DECIMAL(15,2) NOT NULL,

    calculation_order INT UNSIGNED NOT NULL,

    CONSTRAINT pk_payroll_result_components
        PRIMARY KEY (payroll_result_component_id),

    CONSTRAINT uq_payroll_result_component
        UNIQUE (
            payroll_result_id,
            salary_component_id
        ),

    CONSTRAINT chk_payroll_result_component_type
        CHECK (
            component_type IN (
                'EARNING',
                'DEDUCTION'
            )
        ),

    CONSTRAINT chk_payroll_component_amount
        CHECK (
            amount >= 0
        ),

    CONSTRAINT fk_payroll_component_result
        FOREIGN KEY (payroll_result_id)
        REFERENCES payroll_results(payroll_result_id)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,

    CONSTRAINT fk_payroll_component_definition
        FOREIGN KEY (salary_component_id)
        REFERENCES salary_components(salary_component_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    INDEX idx_payroll_result_components_component (
        salary_component_id
    )
) ENGINE = InnoDB;


-- =====================================================================
-- 22. PAYROLL_PROCESSING_ISSUES
-- =====================================================================

CREATE TABLE payroll_processing_issues (
    payroll_issue_id BIGINT UNSIGNED AUTO_INCREMENT,

    payroll_run_id BIGINT UNSIGNED NOT NULL,
    employee_id BIGINT UNSIGNED NULL,

    issue_code VARCHAR(100) NOT NULL,
    issue_message VARCHAR(1000) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',

    detected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME NULL,

    CONSTRAINT pk_payroll_processing_issues
        PRIMARY KEY (payroll_issue_id),

    CONSTRAINT chk_payroll_issue_status
        CHECK (
            status IN (
                'OPEN',
                'RESOLVED'
            )
        ),

    CONSTRAINT chk_payroll_issue_resolution
        CHECK (
            (
                status = 'OPEN'
                AND resolved_at IS NULL
            )
            OR
            (
                status = 'RESOLVED'
                AND resolved_at IS NOT NULL
            )
        ),

    CONSTRAINT fk_payroll_issue_run
        FOREIGN KEY (payroll_run_id)
        REFERENCES payroll_runs(payroll_run_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT fk_payroll_issue_employee
        FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    INDEX idx_payroll_issues_run_status (
        payroll_run_id,
        status
    ),

    INDEX idx_payroll_issues_employee (
        employee_id
    )
) ENGINE = InnoDB;


-- =====================================================================
-- 23. PAYSLIPS
-- =====================================================================

CREATE TABLE payslips (
    payslip_id BIGINT UNSIGNED AUTO_INCREMENT,

    payroll_result_id BIGINT UNSIGNED NOT NULL,

    payslip_number VARCHAR(50) NOT NULL,

    generated_by_user_id BIGINT UNSIGNED NOT NULL,
    generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    document_path VARCHAR(500) NOT NULL,

    CONSTRAINT pk_payslips
        PRIMARY KEY (payslip_id),

    CONSTRAINT uq_payslip_result
        UNIQUE (payroll_result_id),

    CONSTRAINT uq_payslip_number
        UNIQUE (payslip_number),

    CONSTRAINT fk_payslip_result
        FOREIGN KEY (payroll_result_id)
        REFERENCES payroll_results(payroll_result_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT fk_payslip_generator
        FOREIGN KEY (generated_by_user_id)
        REFERENCES users(user_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT
) ENGINE = InnoDB;



-- =====================================================================
-- DOMAIN F — AUDIT
-- =====================================================================


-- =====================================================================
-- 24. AUDIT_EVENTS
-- =====================================================================

CREATE TABLE audit_events (
    audit_event_id BIGINT UNSIGNED AUTO_INCREMENT,

    actor_user_id BIGINT UNSIGNED NULL,

    action_type VARCHAR(100) NOT NULL,

    resource_type VARCHAR(100) NOT NULL,
    resource_id BIGINT UNSIGNED NULL,

    correlation_id VARCHAR(100) NULL,

    source_ip VARCHAR(45) NULL,
    user_agent VARCHAR(500) NULL,

    occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_audit_events
        PRIMARY KEY (audit_event_id),

    CONSTRAINT fk_audit_actor
        FOREIGN KEY (actor_user_id)
        REFERENCES users(user_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    INDEX idx_audit_resource_time (
        resource_type,
        resource_id,
        occurred_at
    ),

    INDEX idx_audit_actor_time (
        actor_user_id,
        occurred_at
    ),

    INDEX idx_audit_occurred (
        occurred_at
    ),

    INDEX idx_audit_correlation (
        correlation_id
    )
) ENGINE = InnoDB;


-- =====================================================================
-- 25. AUDIT_EVENT_CHANGES
-- =====================================================================

CREATE TABLE audit_event_changes (
    audit_event_change_id BIGINT UNSIGNED AUTO_INCREMENT,

    audit_event_id BIGINT UNSIGNED NOT NULL,

    field_name VARCHAR(100) NOT NULL,

    old_value TEXT NULL,
    new_value TEXT NULL,

    CONSTRAINT pk_audit_event_changes
        PRIMARY KEY (audit_event_change_id),

    CONSTRAINT fk_audit_change_event
        FOREIGN KEY (audit_event_id)
        REFERENCES audit_events(audit_event_id)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,

    INDEX idx_audit_changes_event (
        audit_event_id
    )
) ENGINE = InnoDB;



-- =====================================================================
-- DOMAIN G — SECURITY
-- =====================================================================


-- =====================================================================
-- 26. SECURITY_EVENTS
-- =====================================================================

CREATE TABLE security_events (
    security_event_id BIGINT UNSIGNED AUTO_INCREMENT,

    user_id BIGINT UNSIGNED NULL,

    event_type VARCHAR(100) NOT NULL,

    severity VARCHAR(20) NOT NULL,

    description VARCHAR(1000) NOT NULL,

    source_ip VARCHAR(45) NULL,
    correlation_id VARCHAR(100) NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',

    occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    resolved_at DATETIME NULL,
    resolved_by_user_id BIGINT UNSIGNED NULL,

    CONSTRAINT pk_security_events
        PRIMARY KEY (security_event_id),

    CONSTRAINT chk_security_severity
        CHECK (
            severity IN (
                'LOW',
                'MEDIUM',
                'HIGH',
                'CRITICAL'
            )
        ),

    CONSTRAINT chk_security_status
        CHECK (
            status IN (
                'OPEN',
                'RESOLVED'
            )
        ),

    CONSTRAINT chk_security_resolution
        CHECK (
            (
                status = 'OPEN'
                AND resolved_at IS NULL
                AND resolved_by_user_id IS NULL
            )
            OR
            (
                status = 'RESOLVED'
                AND resolved_at IS NOT NULL
                AND resolved_by_user_id IS NOT NULL
            )
        ),

    CONSTRAINT fk_security_event_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT fk_security_event_resolver
        FOREIGN KEY (resolved_by_user_id)
        REFERENCES users(user_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    INDEX idx_security_status_time (
        status,
        occurred_at
    ),

    INDEX idx_security_user_time (
        user_id,
        occurred_at
    ),

    INDEX idx_security_resolver (
        resolved_by_user_id
    )
) ENGINE = InnoDB;



-- =====================================================================
-- DOMAIN H — SYSTEM CONFIGURATION
-- =====================================================================


-- =====================================================================
-- 27. SYSTEM_SETTINGS
-- =====================================================================

CREATE TABLE system_settings (
    system_setting_id BIGINT UNSIGNED AUTO_INCREMENT,

    setting_key VARCHAR(100) NOT NULL,

    setting_value TEXT NOT NULL,

    value_type VARCHAR(20) NOT NULL,

    description VARCHAR(500) NULL,

    updated_by_user_id BIGINT UNSIGNED NOT NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_system_settings
        PRIMARY KEY (system_setting_id),

    CONSTRAINT uq_system_settings_key
        UNIQUE (setting_key),

    CONSTRAINT chk_system_setting_type
        CHECK (
            value_type IN (
                'STRING',
                'INTEGER',
                'DECIMAL',
                'BOOLEAN',
                'JSON'
            )
        ),

    CONSTRAINT fk_system_setting_updater
        FOREIGN KEY (updated_by_user_id)
        REFERENCES users(user_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT
) ENGINE = InnoDB;


-- =====================================================================
-- END OF EMPLOYEE PAYROLL MANAGEMENT SYSTEM SCHEMA
-- =====================================================================