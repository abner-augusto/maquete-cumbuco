import { defineConfig, devices } from '@playwright/test';

// Jornadas e2e. O app roda do build de produção.
export default defineConfig({
  testDir: 'e2e',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  // WebGL por software (SwiftShader) ocupa todos os núcleos: um navegador por vez, para a máquina
  // continuar usável. E2E_WORKERS sobe isso quando a máquina estiver livre.
  workers: Number(process.env.E2E_WORKERS ?? 1),
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:4173',
    locale: 'pt-BR',
    timezoneId: 'America/Fortaleza',
    // Sem as ondas do mar: a cena volta a desenhar só sob demanda e o e2e pesa menos.
    reducedMotion: 'reduce',
    launchOptions: { args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] },
  },
  projects: [
    // Densidade 1: com a do Pixel 7 (2,6), o WebGL por software desenha 4× mais pixels e trava no
    // modo entorno. O layout depende do viewport, não da densidade.
    { name: 'celular-retrato', testIgnore: /offline\.spec\.ts/, use: { ...devices['Pixel 7'], viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, browserName: 'chromium' } },
    { name: 'tablet-paisagem', testIgnore: /offline\.spec\.ts/, use: { browserName: 'chromium', viewport: { width: 1180, height: 820 }, hasTouch: true } },
    // O pacote offline, servido pelo próprio servidor PowerShell, com a rede de fora cortada no teste.
    { name: 'offline', testMatch: /offline\.spec\.ts/, use: { browserName: 'chromium', baseURL: 'http://127.0.0.1:8138', viewport: { width: 1180, height: 820 } } },
  ],
  // Os servidores sobem em ordem: o pacote copia o dist/ que o primeiro acabou de gerar.
  webServer: [
    {
      command: 'npm run build && npm run preview',
      url: 'http://127.0.0.1:4173',
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
    },
    {
      command: 'npm run pacote && powershell -NoProfile -ExecutionPolicy Bypass -File pacote/servidor.ps1 -Porta 8138 -SemNavegador',
      url: 'http://127.0.0.1:8138/',
      reuseExistingServer: false,
      timeout: 240_000,
    },
  ],
});
