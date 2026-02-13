import type { Page } from "@playwright/test";

/** Wait for page to be fully ready: networkidle + no skeleton animations */
export async function waitForPageReady(page: Page) {
  await page.waitForLoadState("networkidle");
  await page
    .waitForFunction(() => document.querySelectorAll('[class*="animate-pulse"]').length === 0, {
      timeout: 5000,
    })
    .catch(() => {});
}

/** Inject CSS to disable all animations/transitions for deterministic screenshots */
export async function hideAnimations(page: Page) {
  await page.addStyleTag({
    content: `*, *::before, *::after {
      animation-duration: 0s !important;
      animation-delay: 0s !important;
      transition-duration: 0s !important;
      transition-delay: 0s !important;
    }`,
  });
}

/** Clear Zustand persisted localStorage to start from clean state */
export async function clearLocalStorage(page: Page) {
  await page.addInitScript(() => {
    window.localStorage.clear();
  });
}
