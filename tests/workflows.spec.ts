import { test, expect } from "@playwright/test";
test("onboarding, expense, audited edit and deletion update account balances", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Set up your first account" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Account nickname").fill("My daily wallet");
  await dialog.getByLabel("Opening balance").fill("1000.00");
  await dialog.getByRole("button", { name: "Save account" }).click();
  await expect(dialog).toHaveCount(0);
  await page.getByRole("button", { name: "Add transaction" }).click();
  await dialog.getByLabel("Description").fill("Lunch with friends");
  await dialog.getByLabel("Amount (PHP)", { exact: true }).fill("125.50");
  await dialog.getByRole("button", { name: "Save transaction" }).click();
  await expect(dialog).toHaveCount(0);
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Accounts", exact: true })
    .click();
  await expect(page.locator(".account-card .stat-value")).toHaveText("₱874.50");
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Transactions", exact: true })
    .click();
  await page.getByRole("button", { name: "Edit Lunch with friends" }).click();
  await dialog.getByLabel("Amount (PHP)", { exact: true }).fill("100.00");
  await dialog.getByRole("button", { name: "Save transaction" }).click();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Accounts", exact: true })
    .click();
  await expect(page.locator(".account-card .stat-value")).toHaveText("₱900.00");
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Transactions", exact: true })
    .click();
  await page.getByRole("button", { name: "Edit Lunch with friends" }).click();
  page.once("dialog", (d) => d.accept());
  await dialog.getByRole("button", { name: "Delete entry" }).click();
  await expect(dialog).toHaveCount(0);
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Accounts", exact: true })
    .click();
  await expect(page.locator(".account-card .stat-value")).toHaveText(
    "₱1,000.00",
  );
});
test("sample navigation, privacy, CSV idempotency, and theme", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Load example data" }).click();
  await expect(page.locator(".stat.featured .stat-value")).not.toHaveText(
    "₱0.00",
  );
  await page.getByRole("button", { name: "Toggle privacy" }).click();
  await expect(page.locator(".stat.featured .stat-value")).toContainText(
    "••••••",
  );
  await page.getByRole("button", { name: "Toggle privacy" }).click();
  for (const name of [
    "Budgets",
    "Savings",
    "Investments",
    "Analytics",
    "Settings",
    "Transactions",
  ]) {
    await page
      .getByRole("navigation")
      .getByRole("button", { name, exact: true })
      .click();
    await expect(page.locator("h1")).toHaveText(name);
  }
  await page.getByRole("button", { name: "Import CSV" }).click();
  const d = page.getByRole("dialog");
  const now = await d.locator("input[type=file]").evaluate(() =>
    new Intl.DateTimeFormat("en-CA", {
      timeZone: "Asia/Manila",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date()),
  );
  const csv = `date,description,kind,amount,category\n${now},Imported lunch,expense,100.00,Food`;
  await d.locator("input[type=file]").setInputFiles({
    name: "test.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(csv),
  });
  await expect(d.getByRole("button", { name: "Confirm 1 rows" })).toBeEnabled();
  await d.getByRole("button", { name: "Confirm 1 rows" }).click();
  await page.getByRole("button", { name: "Edit Imported lunch" }).click();
  await d.getByLabel("Amount (PHP)", { exact: true }).fill("90.00");
  await d.getByRole("button", { name: "Save transaction" }).click();
  await page.getByRole("button", { name: "Import CSV" }).click();
  await d.locator("input[type=file]").setInputFiles({
    name: "test.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(csv),
  });
  await expect(
    d.getByRole("button", { name: "Confirm 0 rows" }),
  ).toBeDisabled();
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Toggle theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.screenshot({
    path: "test-results/saldo-light.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Toggle theme" }).click();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Overview", exact: true })
    .click();
  await page.screenshot({
    path: "test-results/saldo-dashboard.png",
    fullPage: true,
  });
});

test("transfers, fees and reviewable reconciliation preserve accounting", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Load example data" }).click();
  await expect(page.locator(".stat.featured .stat-value")).toHaveText(
    "₱304,990.25",
  );
  await page.getByRole("button", { name: "Add transaction" }).click();
  const d = page.getByRole("dialog");
  await d.getByLabel("Description").fill("Move to savings");
  await d.getByLabel("Type", { exact: true }).selectOption("transfer");
  await d.getByLabel("Account", { exact: true }).selectOption("a0");
  await d.getByLabel("Transfer destination").selectOption("a1");
  await d.getByLabel("Amount (PHP)", { exact: true }).fill("1000.00");
  await d.getByLabel("Separate fee").fill("10.00");
  await d.getByRole("button", { name: "Save transaction" }).click();
  await expect(d).toHaveCount(0);
  await expect(page.locator(".stat.featured .stat-value")).toHaveText(
    "₱304,980.25",
  );
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Accounts", exact: true })
    .click();
  await page.getByRole("button", { name: "Verify a balance" }).click();
  await d.getByLabel("Account", { exact: true }).selectOption("a0");
  await d.getByLabel("Actual verified balance").fill("4500.00");
  await d.getByRole("button", { name: "Save reconcile" }).click();
  await expect(d).toHaveCount(0);
  await expect(
    page
      .locator(".account-card")
      .filter({
        has: page.getByRole("heading", { name: "GCash", exact: true }),
      })
      .locator(".stat-value"),
  ).toHaveText("₱4,330.25");
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Review & post adjustment" }).click();
  await expect(
    page
      .locator(".account-card")
      .filter({
        has: page.getByRole("heading", { name: "GCash", exact: true }),
      })
      .locator(".stat-value"),
  ).toHaveText("₱4,500.00");
  await expect(
    page.getByRole("button", { name: "Review & post adjustment" }),
  ).toHaveCount(0);
});

test("informational ETF prices, exact PHP valuation and bank shortcuts", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Load example data" }).click();
  const initial = await page
    .locator(".stat.featured .stat-value")
    .textContent();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Investments", exact: true })
    .click();
  await page.getByRole("button", { name: "Add ticker" }).click();
  await page.getByLabel("US ticker").fill("SPY");
  await page.getByLabel("Display name").fill("S&P 500 ETF");
  await page.getByLabel("Units (0 for watchlist only)").fill("0.5");
  await page.getByLabel("Optional total cost basis").fill("50.00");
  await page.getByRole("button", { name: "Save ticker" }).click();
  let dialogs = 0;
  page.on("dialog", async (d) => {
    if (d.type() === "prompt")
      await d.accept(dialogs++ === 0 ? "123.45" : "2026-01-01");
    else await d.accept();
  });
  await page.getByRole("button", { name: "Manual price", exact: true }).click();
  await expect(page.locator("tbody")).toContainText("$61.73");
  await expect(page.locator("tbody")).toContainText("$11.73 unrealized");
  await expect(page.locator("tbody")).toContainText("Manual valuation");
  await page.getByLabel("PHP per 1 USD").fill("56.123456");
  await page.getByLabel("Rate date").fill("2026-01-01");
  await page.getByRole("button", { name: "Save exchange rate" }).click();
  await expect(page.locator(".stats")).toContainText("₱3,464.50");
  await expect(
    page.getByRole("button", { name: "Refresh prices" }),
  ).toBeDisabled();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Overview", exact: true })
    .click();
  await expect(page.locator(".stat.featured .stat-value")).toHaveText(initial!);
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Connections", exact: true })
    .click();
  await expect(page.getByText("Sync unavailable", { exact: true })).toHaveCount(
    5,
  );
  await expect(page.locator("input[type=password]")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Sign in on the official BPI website" }),
  ).toBeEnabled();
  await expect(
    page.getByRole("button", { name: "Official app sign-in guidance" }),
  ).toBeEnabled();
});
