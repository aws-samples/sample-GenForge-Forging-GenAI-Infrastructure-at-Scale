/**
 * CDK Synthesis Runner Helper
 *
 * Utility for running CDK synthesis tests against template skeletons.
 * Copies a skeleton to a temp directory, substitutes Backstage template
 * variables (${{ values.xxx }}) with provided values, creates a Python
 * virtualenv, installs CDK dependencies, and runs `cdk synth`.
 */

import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import { execSync } from 'child_process';

export interface CdkSynthResult {
  exitCode: number;
  stdout: string;
  stderr: string;
  cfnTemplate: any | null;
}

/**
 * Recursively copy a directory.
 */
function copyDirRecursive(src: string, dest: string): void {
  if (!fs.existsSync(dest)) {
    fs.mkdirSync(dest, { recursive: true });
  }

  const entries = fs.readdirSync(src, { withFileTypes: true });
  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    if (entry.isDirectory()) {
      copyDirRecursive(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

/**
 * Recursively find all files in a directory.
 */
function getAllFiles(dir: string): string[] {
  const results: string[] = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...getAllFiles(fullPath));
    } else {
      results.push(fullPath);
    }
  }

  return results;
}

/**
 * Substitute Backstage template variables in file content.
 *
 * Handles two patterns:
 * 1. ${{ values.xxx }} - standard Backstage template interpolation
 * 2. {% raw %}...{% endraw %} blocks - strips the raw/endraw tags and preserves
 *    the inner content as-is (these protect GitHub Actions expressions)
 *
 * @param content - File content with template variables
 * @param values - Map of variable names to replacement values
 * @returns Content with variables substituted
 */
function substituteTemplateVariables(
  content: string,
  values: Record<string, string>,
): string {
  let result = content;

  // First, handle {% raw %}...{% endraw %} blocks.
  // These wrap GitHub Actions expressions that should be preserved literally.
  // Strip the raw/endraw tags but keep the inner content.
  result = result.replace(
    /\{%\s*raw\s*%\}([\s\S]*?)\{%\s*endraw\s*%\}/g,
    (_match, inner) => inner,
  );

  // Now substitute ${{ values.xxx }} patterns with provided values
  result = result.replace(
    /\$\{\{\s*values\.(\w+)\s*\}\}/g,
    (_match, key) => {
      if (key in values) {
        return values[key];
      }
      // Return empty string for unmatched variables to avoid breaking Python syntax
      return '';
    },
  );

  // Also handle ${{ parameters.xxx | parseEntityRef | pick('name') }} patterns
  // that may appear in some templates - replace with the accountId value
  result = result.replace(
    /\$\{\{\s*parameters\.\w+\s*\|\s*parseEntityRef\s*\|\s*pick\('name'\)\s*\}\}/g,
    values['accountId'] || '111111111111',
  );

  // Handle remaining ${{ parameters.xxx }} patterns
  result = result.replace(
    /\$\{\{\s*parameters\.(\w+)\s*\}\}/g,
    (_match, key) => {
      if (key in values) {
        return values[key];
      }
      return '';
    },
  );

  // Handle ${{ steps[...] }} patterns (output references) - keep them as placeholders
  result = result.replace(
    /\$\{\{\s*steps\[.*?\]\.output\.\w+\s*\}\}/g,
    'https://example.com/placeholder',
  );

  return result;
}

/**
 * Prepare a skeleton directory for CDK synthesis testing.
 *
 * 1. Copies the skeleton/ directory from the template to a temp location
 * 2. Substitutes all ${{ values.xxx }} patterns with provided values
 * 3. Handles {% raw %}...{% endraw %} blocks
 *
 * @param templateDir - Root directory of the template (containing skeleton/)
 * @param values - Map of template variable names to values for substitution
 * @returns Path to the prepared temp directory (containing cdk/ at top level)
 */
export async function prepareSkeleton(
  templateDir: string,
  values: Record<string, string>,
): Promise<string> {
  const skeletonDir = path.join(templateDir, 'skeleton');
  if (!fs.existsSync(skeletonDir)) {
    throw new Error(`Skeleton directory not found: ${skeletonDir}`);
  }

  // Create a temp directory
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'genforge-cdk-test-'));

  // Copy skeleton to temp directory
  copyDirRecursive(skeletonDir, tmpDir);

  // Substitute template variables in all text files
  const allFiles = getAllFiles(tmpDir);
  const textExtensions = [
    '.py',
    '.txt',
    '.json',
    '.yml',
    '.yaml',
    '.md',
    '.cfg',
    '.ini',
    '.toml',
    '.sh',
    '.env',
  ];

  for (const filePath of allFiles) {
    const ext = path.extname(filePath).toLowerCase();
    // Process text files and files without extensions (like Dockerfile)
    if (
      textExtensions.includes(ext) ||
      path.basename(filePath) === 'Dockerfile'
    ) {
      try {
        const content = fs.readFileSync(filePath, 'utf-8');
        const substituted = substituteTemplateVariables(content, values);
        fs.writeFileSync(filePath, substituted, 'utf-8');
      } catch {
        // Skip files that cannot be read as text
      }
    }
  }

  return tmpDir;
}

/**
 * Run CDK synthesis in a prepared working directory.
 *
 * 1. Creates a Python virtual environment
 * 2. Installs pip dependencies from requirements.txt
 * 3. Runs `cdk synth` using the local CDK installation
 * 4. Parses the synthesized CloudFormation template
 *
 * @param workDir - Prepared working directory (output of prepareSkeleton)
 * @returns CdkSynthResult with exit code, output, and parsed template
 */
export async function runCdkSynth(workDir: string): Promise<CdkSynthResult> {
  const cdkDir = path.join(workDir, 'cdk');

  if (!fs.existsSync(cdkDir)) {
    return {
      exitCode: 1,
      stdout: '',
      stderr: `CDK directory not found: ${cdkDir}`,
      cfnTemplate: null,
    };
  }

  try {
    // Determine python command (macOS uses python3)
    const pythonCmd = process.platform === 'darwin' ? 'python3' : 'python3';

    // Create virtual environment
    execSync(`${pythonCmd} -m venv ${path.join(cdkDir, '.venv')}`, {
      cwd: cdkDir,
      stdio: 'pipe',
      timeout: 30000,
    });

    // Determine venv bin directory
    const venvBin = path.join(cdkDir, '.venv', 'bin');
    const pipPath = path.join(venvBin, 'pip');
    const pythonPath = path.join(venvBin, 'python');

    // Install requirements
    execSync(`${pipPath} install --upgrade pip`, {
      cwd: cdkDir,
      stdio: 'pipe',
      timeout: 60000,
    });

    const requirementsPath = path.join(cdkDir, 'requirements.txt');
    if (fs.existsSync(requirementsPath)) {
      execSync(`${pipPath} install -r requirements.txt`, {
        cwd: cdkDir,
        stdio: 'pipe',
        timeout: 120000,
      });
    }

    // Run CDK synth
    // Use npx cdk to use the local CDK or global CDK
    const synthResult = execSync(
      `npx cdk synth --app "${pythonPath} app.py" --no-staging 2>&1`,
      {
        cwd: cdkDir,
        stdio: 'pipe',
        timeout: 120000,
        env: {
          ...process.env,
          VIRTUAL_ENV: path.join(cdkDir, '.venv'),
          PATH: `${venvBin}:${process.env.PATH}`,
        },
      },
    );

    const stdout = synthResult.toString('utf-8');

    // Try to read the CloudFormation template from cdk.out
    let cfnTemplate: any = null;
    const cdkOutDir = path.join(cdkDir, 'cdk.out');
    if (fs.existsSync(cdkOutDir)) {
      const templateFiles = fs
        .readdirSync(cdkOutDir)
        .filter(f => f.endsWith('.template.json'));
      if (templateFiles.length > 0) {
        const templateContent = fs.readFileSync(
          path.join(cdkOutDir, templateFiles[0]),
          'utf-8',
        );
        cfnTemplate = JSON.parse(templateContent);
      }
    }

    return {
      exitCode: 0,
      stdout,
      stderr: '',
      cfnTemplate,
    };
  } catch (error: any) {
    return {
      exitCode: error.status || 1,
      stdout: error.stdout ? error.stdout.toString('utf-8') : '',
      stderr: error.stderr
        ? error.stderr.toString('utf-8')
        : error.message || 'Unknown error',
      cfnTemplate: null,
    };
  }
}

/**
 * Clean up a temporary working directory created by prepareSkeleton.
 * @param workDir - Path to the temp directory to remove
 */
export async function cleanup(workDir: string): Promise<void> {
  if (workDir && workDir.includes('genforge-cdk-test-') && fs.existsSync(workDir)) {
    fs.rmSync(workDir, { recursive: true, force: true });
  }
}
