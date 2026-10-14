import { readFileSync } from "node:fs";
import { test, expect, type Page } from "@playwright/test";

type SmokeUser = { user_id: number; username: string; password: string };
type SmokeFixture = {
  api_base_url: string;
  users: { setup: SmokeUser; hr: SmokeUser; payroll: SmokeUser; employee: SmokeUser };
  department_id: number;
  designation_id: number;
  employee_id: number;
  other_employee_id: number;
  leave_type_id: number;
  leave_dates: [string, string, string, string];
};

const fixturePath = process.env.EPMS_SMOKE_FIXTURE_FILE;
if (!fixturePath) throw new Error("EPMS_SMOKE_FIXTURE_FILE must point to the private CI fixture file.");
const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as SmokeFixture;

async function signIn(page: Page, user: SmokeUser) {
  await page.goto("/login");
  await page.getByLabel("Username").fill(user.username);
  await page.getByLabel("Password").fill(user.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
}

test("browser login refreshes the session and logout revokes the rotated credential", async ({ page, request }) => {
  test.setTimeout(120_000);
  await page.goto("/login");
  await page.getByLabel("Username").fill(fixture.users.hr.username);
  await page.getByLabel("Password").fill(fixture.users.hr.password);
  const loginResponsePromise = page.waitForResponse((response) => response.url().endsWith("/auth/login"));
  await page.getByRole("button", { name: "Sign in" }).click();
  expect((await loginResponsePromise).status()).toBe(200);
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

  const persistedTokenKeys = await page.evaluate(() => [
    ...Object.keys(localStorage), ...Object.keys(sessionStorage),
  ].filter((key) => /token|auth|session/i.test(key)));
  expect(persistedTokenKeys).toEqual([]);

  // CI config uses a one-minute access JWT. A protected request must trigger the
  // frontend's real refresh path and retry using the returned pair.
  await page.waitForTimeout(65_000);
  const refreshResponsePromise = page.waitForResponse((response) => response.url().endsWith("/auth/refresh"));
  await page.getByRole("link", { name: "Employees" }).click();
  const refreshResponse = await refreshResponsePromise;
  expect(refreshResponse.status()).toBe(200);
  const rotated = await refreshResponse.json() as { refresh_token: string };
  await expect(page.getByRole("heading", { name: "Employee directory" })).toBeVisible();

  const logoutResponsePromise = page.waitForResponse((response) => response.url().endsWith("/auth/logout"));
  await page.getByRole("button", { name: /sign out/i }).click();
  expect((await logoutResponsePromise).status()).toBe(204);
  await expect(page.getByRole("heading", { name: "Sign in to EPMS" })).toBeVisible();

  const revokedRefresh = await request.post(`${fixture.api_base_url}/auth/refresh`, {
    data: { refresh_token: rotated.refresh_token },
  });
  expect(revokedRefresh.status()).toBe(401);
});

test("invalid credentials, missing authentication, and persisted permission denial keep API statuses", async ({ request }) => {
  const invalidLogin = await request.post(`${fixture.api_base_url}/auth/login`, {
    data: { username: fixture.users.employee.username, password: "invalid-smoke-password" },
  });
  expect(invalidLogin.status()).toBe(401);

  const anonymous = await request.get(`${fixture.api_base_url}/reports/employees`);
  expect(anonymous.status()).toBe(401);

  const login = await request.post(`${fixture.api_base_url}/auth/login`, {
    data: { username: fixture.users.employee.username, password: fixture.users.employee.password },
  });
  expect(login.status()).toBe(200);
  const employeeToken = (await login.json()).access_token as string;
  const denied = await request.get(`${fixture.api_base_url}/reports/employees`, {
    headers: { Authorization: `Bearer ${employeeToken}` },
  });
  expect(denied.status()).toBe(403);

  const payrollLogin = await request.post(`${fixture.api_base_url}/auth/login`, {
    data: { username: fixture.users.payroll.username, password: fixture.users.payroll.password },
  });
  expect(payrollLogin.status()).toBe(200);
  const payrollToken = (await payrollLogin.json()).access_token as string;
  const payrollDenied = await request.get(`${fixture.api_base_url}/reports/employees`, {
    headers: { Authorization: `Bearer ${payrollToken}` },
  });
  expect(payrollDenied.status()).toBe(403);

  const invalidRefresh = await request.post(`${fixture.api_base_url}/auth/refresh`, {
    data: { refresh_token: "not-a-real-refresh-credential" },
  });
  expect(invalidRefresh.status()).toBe(401);
});

test("refresh replay is rejected and revokes the rotated family", async ({ request }) => {
  const login = await request.post(`${fixture.api_base_url}/auth/login`, {
    data: { username: fixture.users.employee.username, password: fixture.users.employee.password },
  });
  expect(login.status()).toBe(200);
  const original = (await login.json()).refresh_token as string;
  const rotatedResponse = await request.post(`${fixture.api_base_url}/auth/refresh`, {
    data: { refresh_token: original },
  });
  expect(rotatedResponse.status()).toBe(200);
  const rotated = (await rotatedResponse.json()).refresh_token as string;

  const replay = await request.post(`${fixture.api_base_url}/auth/refresh`, {
    data: { refresh_token: original },
  });
  expect(replay.status()).toBe(401);
  const familyRevoked = await request.post(`${fixture.api_base_url}/auth/refresh`, {
    data: { refresh_token: rotated },
  });
  expect(familyRevoked.status()).toBe(401);
});

test("HR user creates an employee with persisted organization references", async ({ page }) => {
  await signIn(page, fixture.users.hr);
  await page.getByRole("link", { name: "Employees" }).click();
  await expect(page.getByRole("heading", { name: "Employee directory" })).toBeVisible();
  await page.getByRole("link", { name: "Add employee" }).click();
  const employeeCode = `SMK-${Date.now().toString(36).toUpperCase()}`;
  await page.getByLabel("Employee code").fill(employeeCode);
  await page.getByLabel("First name").fill("Browser");
  await page.getByLabel("Last name").fill("Smoke");
  await page.getByLabel("Department ID").fill(String(fixture.department_id));
  await page.getByLabel("Designation ID").fill(String(fixture.designation_id));
  await page.getByLabel("Joining date").fill(new Date().toISOString().slice(0, 10));
  const createResponse = page.waitForResponse((response) => response.url().endsWith("/employees") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Create employee" }).click();
  expect((await createResponse).status()).toBe(201);
  await expect(page.getByText(employeeCode)).toBeVisible();
});

test("employee can request own leave, cannot request another employee, and HR can", async ({ page }) => {
  await signIn(page, fixture.users.employee);

  async function submitLeave(employeeId: number, day: string) {
    await page.getByLabel("Employee ID").fill(String(employeeId));
    await page.getByLabel("Leave type ID").fill(String(fixture.leave_type_id));
    await page.getByLabel("Start date").fill(day);
    await page.getByLabel("End date").fill(day);
    await page.getByLabel("Requested days").fill("1.00");
    await page.getByLabel("Allocation date").fill(day);
    const responsePromise = page.waitForResponse((response) => response.url().endsWith("/leave-requests") && response.request().method() === "POST");
    await page.getByRole("button", { name: "Submit request" }).click();
    return responsePromise;
  }

  await page.getByRole("link", { name: "Leave" }).click();
  await page.getByRole("link", { name: "New request" }).click();
  expect((await submitLeave(fixture.employee_id, fixture.leave_dates[0])).status()).toBe(201);
  await expect(page.getByRole("heading", { name: "Request submitted" })).toBeVisible();

  await page.getByRole("link", { name: "Leave allocations" }).click();
  await expect(page.getByRole("heading", { name: "Leave report unavailable" })).toBeVisible();
  await page.getByRole("link", { name: "New request" }).click();
  expect((await submitLeave(fixture.other_employee_id, fixture.leave_dates[1])).status()).toBe(403);
  await expect(page.getByRole("alert")).toContainText("permission");

  await signIn(page, fixture.users.hr);
  await page.getByRole("link", { name: "Leave" }).click();
  await page.getByRole("link", { name: "New request" }).click();
  expect((await submitLeave(fixture.other_employee_id, fixture.leave_dates[2])).status()).toBe(201);
  await expect(page.getByRole("heading", { name: "Request submitted" })).toBeVisible();
  await page.getByRole("link", { name: "Leave allocations" }).click();
  await expect(page.getByText("Synthetic Colleague")).toBeVisible();
});

test("Payroll Administrator can create compensation while an unprivileged user is denied", async ({ page }) => {
  await signIn(page, fixture.users.payroll);
  await page.getByRole("link", { name: "Compensation" }).click();
  await page.getByRole("button", { name: "Create", exact: true }).first().click();
  await page.getByLabel("Structure code").fill(`SMK-${Date.now().toString(36).toUpperCase()}`);
  await page.getByLabel("Structure name").fill("Browser Smoke Structure");
  const successResponse = page.waitForResponse((response) => response.url().endsWith("/salary-structures") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Create", exact: true }).last().click();
  expect((await successResponse).status()).toBe(201);
  await expect(page.getByRole("heading", { name: "Created successfully" })).toBeVisible();

  await signIn(page, fixture.users.employee);
  await page.getByRole("link", { name: "Compensation" }).click();
  await page.getByRole("button", { name: "Create", exact: true }).first().click();
  await page.getByLabel("Structure code").fill(`DEN-${Date.now().toString(36).toUpperCase()}`);
  await page.getByLabel("Structure name").fill("Denied Smoke Structure");
  const deniedResponse = page.waitForResponse((response) => response.url().endsWith("/salary-structures") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Create", exact: true }).last().click();
  expect((await deniedResponse).status()).toBe(403);
  await expect(page.getByRole("alert")).toContainText("compensation.write");
});
