import { chromium } from "@playwright/test";

const FRONTEND = process.env.FRONTEND_URL || "http://127.0.0.1:3000";

function must(cond, msg) {
  if (!cond) throw new Error(msg);
}

const orgId = `org_ui_smoke_${Math.random().toString(16).slice(2, 10)}`;

const browser = await chromium.launch();
const context = await browser.newContext();
await context.addInitScript(([key, value]) => {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // ignore
  }
}, ["creddypens_org_id", orgId]);

const page = await context.newPage();
const logs = [];
page.on("console", (msg) => {
  const text = msg.text();
  if (msg.type() === "error" || text.toLowerCase().includes("error")) logs.push(`console.${msg.type()}: ${text}`);
});
page.on("pageerror", (err) => {
  logs.push(`pageerror: ${err?.message || err}`);
});

async function step(name, fn) {
  process.stdout.write(`\n==> ${name}\n`);
  await fn();
  process.stdout.write(`PASS: ${name}\n`);
}

try {
  await step("1) Landing loads", async () => {
    await page.goto(`${FRONTEND}/`, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(300);
    const title = await page.getByText("THE CREDDYPENS DIRECTORATE").first().isVisible();
    must(title, "Landing title not visible");
  });

  await step("2) View Author dossier", async () => {
    await page.goto(`${FRONTEND}/agents/Author-01`, { waitUntil: "domcontentloaded" });
    await page.getByText("Author-01").first().waitFor({ timeout: 15000 });
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);
  });

  await step("3) Hire (mock checkout) and redirect to My Agents", async () => {
    await page.getByRole("button", { name: /^Hire$/ }).first().waitFor({ timeout: 15000 });
    await page.waitForTimeout(300);
    await page.getByRole("button", { name: /^Hire$/ }).first().click();
    await page.waitForTimeout(250);
    const modalCount = await page.locator("text=DEPLOYMENT AUTHORIZATION").count();
    if (modalCount === 0) {
      const buttons = await page.locator("button").allTextContents();
      throw new Error(`Checkout modal did not open. Buttons on page: ${buttons.slice(0, 12).join(" | ")}`);
    }
    await page.locator("button", { hasText: "AUTHORIZE" }).first().click();
    await page.waitForURL("**/dashboard/my-agents", { timeout: 20000 });
    await page.getByText("MY AGENTS").first().waitFor({ timeout: 15000 });
  });

  await step("4) Open chat and receive response", async () => {
    await page.getByRole("button", { name: /OPEN CHAT/i }).first().click();
    await page.getByPlaceholder("Give this agent a task...").waitFor({ timeout: 15000 });
    await page.getByPlaceholder("Give this agent a task...").fill("Write a 2-sentence intro for a coffee shop called Brewed Awakening.");
    await page.getByRole("button", { name: /SEND/i }).click();
    // Wait for agent response bubble that isn't the initial greeting.
    await page.waitForTimeout(500);
    const responses = page.locator("text=Response Time •");
    await responses.first().waitFor({ timeout: 60000 });
  });

  process.stdout.write("\nUI SMOKE: PASS\n");
  await browser.close();
  process.exit(0);
} catch (err) {
  if (logs.length) {
    process.stdout.write("\n--- Browser errors ---\n");
    for (const line of logs.slice(-12)) process.stdout.write(line + "\n");
  }
  process.stdout.write(`\nUI SMOKE: FAIL: ${err?.message || err}\n`);
  await browser.close();
  process.exit(1);
}
