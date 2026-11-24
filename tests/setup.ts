/**
 * GenForge Test Setup
 *
 * Configures Jest environment for template validation and CDK synthesis tests.
 * CDK synthesis tests may take longer due to Python virtualenv creation and
 * pip dependency installation, so a higher default timeout is set.
 */

// Increase default timeout to 60 seconds for CDK synthesis tests
jest.setTimeout(60000);
