/**
 * Routes Configuration Tests
 *
 * Validates that the App.tsx file contains the expected route definitions
 * and that the ScaffolderPage has the correct 4 template groups configured.
 * These tests parse the source file as text to verify structure without
 * requiring a full React rendering environment.
 */

import * as fs from 'fs';
import * as path from 'path';

const APP_TSX_PATH = path.resolve(
  __dirname,
  '../../packages/app/src/App.tsx',
);

describe('Routes Configuration', () => {
  let appTsxContent: string;

  beforeAll(() => {
    appTsxContent = fs.readFileSync(APP_TSX_PATH, 'utf-8');
  });

  describe('App.tsx exists and is valid', () => {
    test('App.tsx file exists', () => {
      expect(fs.existsSync(APP_TSX_PATH)).toBe(true);
    });

    test('App.tsx is not empty', () => {
      expect(appTsxContent.length).toBeGreaterThan(0);
    });

    test('App.tsx exports default', () => {
      expect(appTsxContent).toMatch(/export default/);
    });
  });

  describe('route definitions', () => {
    test('has /catalog route', () => {
      expect(appTsxContent).toMatch(/path=["']\/catalog["']/);
    });

    test('has /create route (scaffolder)', () => {
      expect(appTsxContent).toMatch(/path=["']\/create["']/);
    });

    test('has /docs route (techdocs)', () => {
      expect(appTsxContent).toMatch(/path=["']\/docs["']/);
    });

    test('has /search route', () => {
      expect(appTsxContent).toMatch(/path=["']\/search["']/);
    });

    test('has /settings route', () => {
      expect(appTsxContent).toMatch(/path=["']\/settings["']/);
    });

    test('has /api-docs route', () => {
      expect(appTsxContent).toMatch(/path=["']\/api-docs["']/);
    });

    test('has /notifications route', () => {
      expect(appTsxContent).toMatch(/path=["']\/notifications["']/);
    });

    test('root path redirects to catalog', () => {
      expect(appTsxContent).toMatch(/path=["']\/["']/);
      expect(appTsxContent).toMatch(/Navigate to=["']catalog["']/);
    });
  });

  describe('ScaffolderPage template groups', () => {
    test('uses ScaffolderPage component', () => {
      expect(appTsxContent).toMatch(/ScaffolderPage/);
    });

    test('ScaffolderPage has groups prop', () => {
      expect(appTsxContent).toMatch(/groups=\{?\[/);
    });

    test('has Foundation group', () => {
      expect(appTsxContent).toMatch(/title:\s*['"]Foundation['"]/);
    });

    test('has Generative AI & FMOps group', () => {
      expect(appTsxContent).toMatch(
        /title:\s*['"]Generative AI & FMOps['"]/,
      );
    });

    test('has AI Agents group', () => {
      expect(appTsxContent).toMatch(/title:\s*['"]AI Agents['"]/);
    });

    test('has MLflow group', () => {
      expect(appTsxContent).toMatch(/title:\s*['"]MLflow['"]/);
    });

    test('has exactly 4 template groups', () => {
      // Count occurrences of group title definitions in the groups array
      const groupTitleMatches = appTsxContent.match(
        /title:\s*['"](Foundation|Generative AI & FMOps|AI Agents|MLflow)['"]/g,
      );
      expect(groupTitleMatches).toHaveLength(4);
    });

    test('Foundation group filters by foundation type', () => {
      expect(appTsxContent).toMatch(/type\s*===\s*['"]foundation['"]/);
    });

    test('FMOps group filters by fmops type', () => {
      expect(appTsxContent).toMatch(/type\s*===\s*['"]fmops['"]/);
    });

    test('Agents group filters by agents type', () => {
      expect(appTsxContent).toMatch(/type\s*===\s*['"]agents['"]/);
    });

    test('MLflow group filters by mlflow type', () => {
      expect(appTsxContent).toMatch(/type\s*===\s*['"]mlflow['"]/);
    });
  });

  describe('required imports', () => {
    test('imports ScaffolderPage from scaffolder plugin', () => {
      expect(appTsxContent).toMatch(
        /import\s*\{[^}]*ScaffolderPage[^}]*\}\s*from\s*['"]@backstage\/plugin-scaffolder['"]/,
      );
    });

    test('imports CatalogIndexPage from catalog plugin', () => {
      expect(appTsxContent).toMatch(
        /import\s*\{[^}]*CatalogIndexPage[^}]*\}\s*from\s*['"]@backstage\/plugin-catalog['"]/,
      );
    });

    test('imports SearchPage from search plugin', () => {
      expect(appTsxContent).toMatch(
        /import\s*\{[^}]*SearchPage[^}]*\}\s*from\s*['"]@backstage\/plugin-search['"]/,
      );
    });

    test('imports TechDocsIndexPage from techdocs plugin', () => {
      expect(appTsxContent).toMatch(
        /import\s*\{[^}]*TechDocsIndexPage[^}]*\}\s*from\s*['"]@backstage\/plugin-techdocs['"]/,
      );
    });

    test('imports UserSettingsPage from user-settings plugin', () => {
      expect(appTsxContent).toMatch(
        /import\s*\{[^}]*UserSettingsPage[^}]*\}\s*from\s*['"]@backstage\/plugin-user-settings['"]/,
      );
    });

    test('imports NotificationsPage from notifications plugin', () => {
      expect(appTsxContent).toMatch(
        /import\s*\{[^}]*NotificationsPage[^}]*\}\s*from\s*['"]@backstage\/plugin-notifications['"]/,
      );
    });
  });

  describe('route binding', () => {
    test('binds catalog external routes', () => {
      expect(appTsxContent).toMatch(/bind\(catalogPlugin\.externalRoutes/);
    });

    test('binds scaffolder external routes', () => {
      expect(appTsxContent).toMatch(
        /bind\(scaffolderPlugin\.externalRoutes/,
      );
    });

    test('uses FlatRoutes', () => {
      expect(appTsxContent).toMatch(/FlatRoutes/);
    });
  });

  describe('auth configuration', () => {
    test('has SignInPage component', () => {
      expect(appTsxContent).toMatch(/SignInPage/);
    });

    test('uses guest provider', () => {
      expect(appTsxContent).toMatch(/providers=\{\[['"]guest['"]\]\}/);
    });
  });
});
