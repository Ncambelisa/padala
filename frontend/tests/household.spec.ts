import { test, expect, type Page } from '@playwright/test';
import { resolve } from 'node:path';

const password = 'FictionalTestPass!2026';
const sampleReceipt = resolve(__dirname, '../../samples/SAMPLE-groceries.png');

async function acknowledgePrivacyIfRequired(page: Page) {
  const acknowledgement = page.getByRole('checkbox', { name: /I acknowledge that I read the Privacy Notice/i });
  if (await acknowledgement.count()) await acknowledgement.check();
}

test('a household can allocate a padala, submit a declaration, and accept it', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Create a household', exact: true }).click();
  await page.getByLabel('Your name').fill('Test OFW');
  await page.getByLabel('Household name').fill('Automated test household');
  await page.getByLabel('Email address').fill(`e2e-${Date.now()}-${Math.random().toString(16).slice(2)}@example.test`);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await acknowledgePrivacyIfRequired(page);
  await page.getByRole('button', { name: 'Create household', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Hello, Test.' })).toBeVisible();
  await page.getByRole('button', { name: 'New padala', exact: true }).click();
  await page.getByLabel('Padala title').fill('E2E monthly support');
  await page.getByLabel('Amount received (PHP)').fill('3000');
  for (const input of await page.locator('.plan-line input[inputmode="decimal"]').all()) await input.fill('1000');
  await page.getByRole('button', { name: 'Create padala', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'E2E monthly support', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Add evidence', exact: true }).click();
  await page.getByLabel('Merchant / payee').fill('Fictional corner store');
  await page.getByLabel('Total amount (PHP)', { exact: true }).fill('500');
  await page.getByLabel('Explanation (required without a receipt)').fill('Fictional test purchase; no payment actually occurred.');
  await page.getByRole('button', { name: 'Submit evidence', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeHidden();
  await page.getByRole('button').filter({ hasText: 'Fictional corner store' }).first().click();
  await expect(page.getByText('Provider: not connected', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Accept record', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeHidden();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
});

test('a wrong password shows a clear error', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Email address').fill('nonexistent@example.test');
  await page.getByLabel('Password', { exact: true }).fill('NotThePassword!2026');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.locator('.error[role="alert"]')).toContainText('Email or password is incorrect');
});

test('the privacy notice page is available before sign-in', async ({ page }) => {
  await page.goto('/privacy');
  await expect(page.getByRole('heading', { name: /How Padala handles household information|Privacy notice not yet published/ })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Back to Padala' })).toBeVisible();
});

test('the signed-in interface remains usable at required viewport widths', async ({ browser }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop-chromium', 'The viewport matrix creates its own desktop and mobile contexts.');
  const viewportEmail = `viewport-${Date.now()}-${Math.random().toString(16).slice(2)}@example.test`;
  for (const [index, width] of [360, 390, 768, 1440].entries()) {
    const context = await browser.newContext({ viewport: { width, height: 900 } });
    const page = await context.newPage();
    try {
      await page.goto('/');
      if (index === 0) {
        await page.getByRole('button', { name: 'Create a household', exact: true }).click();
        await page.getByLabel('Your name').fill('Viewport OFW');
        await page.getByLabel('Household name').fill('Viewport test household');
        await page.getByLabel('Email address').fill(viewportEmail);
        await page.getByLabel('Password', { exact: true }).fill(password);
        await acknowledgePrivacyIfRequired(page);
        await page.getByRole('button', { name: 'Create household', exact: true }).click();
      } else {
        await page.getByLabel('Email address').fill(viewportEmail);
        await page.getByLabel('Password', { exact: true }).fill(password);
        await page.getByRole('button', { name: 'Sign in', exact: true }).click();
      }
      await expect(page.getByRole('heading', { name: 'Hello, Viewport.' })).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBeTruthy();

      await page.getByRole('button', { name: 'New padala', exact: true }).press('Enter');
      const dialog = page.getByRole('dialog');
      await expect(dialog).toBeVisible();
      await expect(dialog).toBeFocused();
      await page.keyboard.press('Escape');
      await expect(dialog).toBeHidden();
    } finally {
      await context.close();
    }
  }
});

test('two household members can complete a fictional remittance review workflow', async ({ browser }) => {
  const senderContext = await browser.newContext();
  const sender = await senderContext.newPage();
  const memberContext = await browser.newContext();
  const member = await memberContext.newPage();
  const replayContext = await browser.newContext();
  const replay = await replayContext.newPage();
  const suffix = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const memberEmail = `member-${suffix}@example.test`;

  try {
    await sender.goto('/');
    await sender.getByRole('button', { name: 'Create a household', exact: true }).click();
    await sender.getByLabel('Your name').fill('Fictional Sender');
    await sender.getByLabel('Household name').fill('Two-account test household');
    await sender.getByLabel('Email address').fill(`sender-${suffix}@example.test`);
    await sender.getByLabel('Password', { exact: true }).fill(password);
    await acknowledgePrivacyIfRequired(sender);
    await sender.getByRole('button', { name: 'Create household', exact: true }).click();
    await expect(sender.getByRole('heading', { name: 'Hello, Fictional.' })).toBeVisible();

    await sender.getByRole('button', { name: 'My family', exact: true }).click();
    await sender.getByRole('button', { name: 'Invite family', exact: true }).click();
    await sender.getByLabel('Their name').fill('Fictional Member');
    await sender.getByLabel('Their email').fill(memberEmail);
    await sender.getByRole('button', { name: 'Create invitation', exact: true }).click();
    const invitation = sender.getByLabel('Private invitation link');
    await expect(invitation).toHaveValue(/invite=/);
    const invitationUrl = await invitation.inputValue();

    await member.goto(invitationUrl);
    await member.getByLabel('Your name').fill('Fictional Member');
    await member.getByLabel('Password', { exact: true }).fill(password);
    await acknowledgePrivacyIfRequired(member);
    await member.getByRole('button', { name: 'Join household', exact: true }).click();
    await expect(member.getByRole('heading', { name: 'Hello, Fictional.' })).toBeVisible();

    await replay.goto(invitationUrl);
    await expect(replay.locator('.error[role="alert"]')).toContainText('Invitation expired or unavailable');

    await sender.reload();
    await sender.getByRole('button', { name: 'New padala', exact: true }).click();
    await sender.getByLabel('Padala title').fill('E2E two-account workflow');
    await sender.getByLabel('Amount received (PHP)').fill('30000');
    await sender.getByRole('button', { name: 'Add allocation', exact: true }).click();
    await sender.getByRole('button', { name: 'Add allocation', exact: true }).click();

    const plans = sender.locator('.plan-line');
    await expect(plans).toHaveCount(5);
    const allocations = [
      ['Rent', 'expense', '10000'],
      ['Groceries', 'expense', '7000'],
      ['School', 'expense', '5000'],
      ['Utilities', 'expense', '3000'],
      ['Savings', 'savings', '5000'],
    ] as const;
    for (const [name, kind, amount] of allocations) {
      const index = allocations.findIndex((allocation) => allocation[0] === name);
      const row = plans.nth(index);
      await row.locator('input').first().fill(name);
      await row.locator('select').first().selectOption(kind);
      await row.locator('input[inputmode="decimal"]').fill(amount);
    }
    await sender.getByRole('button', { name: 'Create padala', exact: true }).click();
    await expect(sender.getByRole('heading', { name: 'E2E two-account workflow', exact: true })).toBeVisible();

    await member.reload();
    await member.locator('.latest-card').filter({ hasText: 'E2E two-account workflow' }).getByRole('button', { name: 'View padala', exact: true }).click();
    await member.getByRole('button', { name: 'Confirm received', exact: true }).click();
    await expect(member.locator('.page-heading p').filter({ hasText: 'Recipient confirmed receiving the money.' })).toBeVisible();

    await member.getByRole('button', { name: 'Add evidence', exact: true }).click();
    await member.getByLabel('Receipt file').setInputFiles(sampleReceipt);
    await expect(member.getByText('SAMPLE-groceries.png', { exact: true })).toBeVisible();
    await member.getByLabel('Merchant / payee').fill('Fictional grocery receipt');
    await member.getByLabel('Total amount (PHP)', { exact: true }).fill('2000');
    await member.getByLabel('Allocation').selectOption({ label: 'Groceries' });
    await member.getByRole('button', { name: 'Submit evidence', exact: true }).click();
    await expect(member.getByRole('dialog')).toBeHidden();

    await sender.reload();
    await sender.getByRole('button', { name: 'Notifications', exact: true }).click();
    await expect(sender.getByRole('button', { name: /New evidence to review/ })).toBeVisible();
    await sender.getByRole('button', { name: /New evidence to review/ }).click();
    await sender.getByRole('button').filter({ hasText: 'Fictional grocery receipt' }).first().click();
    await expect(sender.getByText('Provider: not connected', { exact: true })).toBeVisible();
    await sender.locator('#review-note').fill('Please explain how this grocery purchase supports the weekly plan.');
    await sender.getByRole('button', { name: 'Ask for clarification', exact: true }).click();
    await expect(sender.getByRole('dialog')).toBeHidden();

    await member.reload();
    await member.getByRole('button', { name: /^Receipts/ }).click();
    await member.getByRole('button').filter({ hasText: 'Fictional grocery receipt' }).first().click();
    await member.locator('#review-note').fill('This covers the household grocery list for the week.');
    await member.getByRole('button', { name: 'Send explanation', exact: true }).click();
    await expect(member.getByRole('dialog')).toBeHidden();

    await sender.reload();
    await sender.getByRole('button', { name: /^Receipts/ }).click();
    await sender.getByRole('button').filter({ hasText: 'Fictional grocery receipt' }).first().click();
    await sender.getByRole('button', { name: 'Accept record', exact: true }).click();
    await expect(sender.getByRole('dialog')).toBeHidden();
    await sender.reload();
    await expect(sender.getByText('E2E two-account workflow', { exact: true })).toBeVisible();
  } finally {
    await Promise.all([senderContext.close(), memberContext.close(), replayContext.close()]);
  }
});

test('a sender can revoke and restore a family member without erasing the household', async ({ browser }) => {
  const senderContext = await browser.newContext();
  const sender = await senderContext.newPage();
  const memberContext = await browser.newContext();
  const member = await memberContext.newPage();
  const suffix = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const memberEmail = `access-member-${suffix}@example.test`;

  try {
    await sender.goto('/');
    await sender.getByRole('button', { name: 'Create a household', exact: true }).click();
    await sender.getByLabel('Your name').fill('Access Sender');
    await sender.getByLabel('Household name').fill('Access lifecycle test household');
    await sender.getByLabel('Email address').fill(`access-sender-${suffix}@example.test`);
    await sender.getByLabel('Password', { exact: true }).fill(password);
    await acknowledgePrivacyIfRequired(sender);
    await sender.getByRole('button', { name: 'Create household', exact: true }).click();

    await sender.getByRole('button', { name: 'My family', exact: true }).click();
    await sender.getByRole('button', { name: 'Invite family', exact: true }).click();
    await sender.getByLabel('Their name').fill('Access Member');
    await sender.getByLabel('Their email').fill(memberEmail);
    await sender.getByRole('button', { name: 'Create invitation', exact: true }).click();
    const invitationUrl = await sender.getByLabel('Private invitation link').inputValue();
    await sender.getByRole('button', { name: 'Close dialog', exact: true }).click();

    await member.goto(invitationUrl);
    await member.getByLabel('Your name').fill('Access Member');
    await member.getByLabel('Password', { exact: true }).fill(password);
    await acknowledgePrivacyIfRequired(member);
    await member.getByRole('button', { name: 'Join household', exact: true }).click();
    await expect(member.getByRole('heading', { name: 'Hello, Access.' })).toBeVisible();

    sender.on('dialog', dialog => dialog.accept());
    await sender.getByRole('button', { name: 'Remove access', exact: true }).click();
    await expect(sender.getByText('Access removed', { exact: true })).toBeVisible();
    await expect(sender.getByRole('status')).toContainText('Existing shared records remain in the household history.');

    await member.reload();
    await expect(member.getByRole('button', { name: 'Sign in', exact: true })).toBeVisible();

    await sender.getByRole('button', { name: 'Restore access', exact: true }).click();
    await expect(sender.getByText('Family member', { exact: true })).toBeVisible();

    await member.getByLabel('Email address').fill(memberEmail);
    await member.getByLabel('Password', { exact: true }).fill(password);
    await member.getByRole('button', { name: 'Sign in', exact: true }).click();
    await expect(member.getByRole('heading', { name: 'Hello, Access.' })).toBeVisible();
  } finally {
    await Promise.all([senderContext.close(), memberContext.close()]);
  }
});
