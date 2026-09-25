# Checagens de frontend para o `.dev-workflows.toml`

Estas checagens precisam do app de pé ou de configuração do projeto, por isso entram como
`[[check]]`. O gate só roda as do nível pedido ou abaixo.

```toml
[[check]]
name = "lighthouse"
cmd = "npx lhci autorun"
tier = 2

[[check]]
name = "a11y"
cmd = "npx playwright test e2e/a11y.spec.ts"
tier = 2

[[check]]
name = "bundle"
cmd = "npx size-limit"
tier = 2

[[check]]
name = "visual"
cmd = "npx playwright test e2e/visual.spec.ts"
tier = 3
```

## Lighthouse CI com orçamento (`lighthouserc.json`)

```json
{
  "ci": {
    "collect": { "startServerCommand": "npm run start", "url": ["http://localhost:3000/"], "numberOfRuns": 3 },
    "assert": {
      "assertions": {
        "largest-contentful-paint": ["error", { "maxNumericValue": 2500 }],
        "total-blocking-time": ["error", { "maxNumericValue": 200 }],
        "cumulative-layout-shift": ["error", { "maxNumericValue": 0.1 }],
        "categories:accessibility": ["error", { "minScore": 0.9 }]
      }
    }
  }
}
```

INP só existe com usuário real; em laboratório, TBT é o proxy.

## Acessibilidade com Playwright + axe (`e2e/a11y.spec.ts`)

```ts
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

for (const path of ["/", "/login"]) {
  test(`a11y ${path}`, async ({ page }) => {
    await page.goto(path);
    const { violations } = await new AxeBuilder({ page }).analyze();
    const graves = violations.filter(v => v.impact === "serious" || v.impact === "critical");
    expect(graves).toEqual([]);
  });
}
```

## Regressão visual (`e2e/visual.spec.ts`)

```ts
import { test, expect } from "@playwright/test";

for (const width of [375, 1280]) {
  test(`home ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await expect(page).toHaveScreenshot(`home-${width}.png`, { fullPage: true });
  });
}
```

A primeira execução grava a referência (`--update-snapshots`); as seguintes comparam.

## Bundle (`size-limit` no `package.json`)

```json
"size-limit": [{ "path": "dist/**/*.js", "limit": "200 KB" }]
```

## Screenshot rápida para o `ui-critic`

```bash
npx playwright screenshot --viewport-size=375,812 http://localhost:3000 /tmp/ui-375.png
npx playwright screenshot --viewport-size=1280,800 http://localhost:3000 /tmp/ui-1280.png
```
