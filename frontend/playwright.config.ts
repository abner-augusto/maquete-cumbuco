import { defineConfig, devices } from '@playwright/test';

// Jornadas e2e. O app roda do build de produção.
export default defineConfig({
  testDir: 'e2e',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  // WebGL por software (SwiftShader) derruba o navegador com muitas instâncias simultâneas.
  workers: 2,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:4173',
    locale: 'pt-BR',
    timezoneId: 'America/Fortaleza',
    launchOptions: { args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] },
  },
  projects: [
    // Densidade 1: com a do Pixel 7 (2,6), o WebGL por software desenha 4× mais pixels e trava no
    // modo entorno. O layout depende do viewport, não da densidade.
    { name: 'celular-retrato', use: { ...devices['Pixel 7'], viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, browserName: 'chromium' } },
    { name: 'tablet-paisagem', use: { browserName: 'chromium', viewport: { width: 1180, height: 820 }, hasTouch: true } },
  ],
  webServer: {
    command: 'npm run build && npm run preview',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
});
