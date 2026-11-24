import type { Config } from 'jest';

const config: Config = {
  rootDir: '..',
  testMatch: ['<rootDir>/tests/**/*.test.ts'],
  transform: {
    '^.+\\.tsx?$': [
      'ts-jest',
      {
        tsconfig: {
          module: 'commonjs',
          target: 'ES2022',
          lib: ['ES2022'],
          esModuleInterop: true,
          allowJs: true,
          resolveJsonModule: true,
          moduleResolution: 'node',
          strict: true,
          skipLibCheck: true,
          outDir: './dist-types',
          rootDir: '.',
        },
      },
    ],
  },
  testEnvironment: 'node',
  setupFiles: ['<rootDir>/tests/setup.ts'],
  reporters: [
    'default',
    [
      'jest-html-reporter',
      {
        pageTitle: 'GenForge Test Report',
        outputPath: '<rootDir>/tests/reports/test-report.html',
        includeFailureMsg: true,
        includeConsoleLog: true,
        theme: 'darkTheme',
      },
    ],
  ],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
  verbose: true,
  testTimeout: 60000,
};

export default config;
