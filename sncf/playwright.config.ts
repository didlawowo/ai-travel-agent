
import type { PlaywrightTestConfig } from '@playwright/test';

const config: PlaywrightTestConfig = {
    // Nous utilisons Chromium par défaut car c'est le navigateur le plus stable pour le scraping
    use: {
        // Utilisation de Chromium headless par défaut
        browserName: 'chromium',
        headless: true,

        // Configuration de la viewport
        viewport: { width: 1920, height: 1080 },

        // Timeout pour les actions
        actionTimeout: 30000,

        // Configuration des screenshots
        screenshot: 'only-on-failure',

        // Ignorer les erreurs HTTPS
        ignoreHTTPSErrors: true,
    },

    // Configuration des timeouts globaux
    timeout: 60000,
    expect: {
        timeout: 10000,
    },

    // Un seul worker pour éviter d'être bloqué par SNCF
    workers: 1,

    // Dossier de sortie des reports
    outputDir: 'test-results',

    // Reporter pour avoir de beaux logs
    reporter: [
        ['list'],
        ['html', { open: 'never' }]
    ],
};

export default config;