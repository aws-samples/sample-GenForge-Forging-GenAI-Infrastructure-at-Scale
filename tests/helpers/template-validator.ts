/**
 * Template Validator Helper
 *
 * Utility functions for loading and validating Backstage scaffolder template YAML files.
 * Validates schema compliance, parameter group ordering, step sequences, and skeleton
 * file presence for GenForge templates.
 */

import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'yaml';

/**
 * Expected parameter group ordering for GenForge templates.
 * First group is always "Component Information" and last is always "Repository Configuration".
 */
const FIRST_GROUP_TITLE = 'Component Information';
const LAST_GROUP_TITLE = 'Repository Configuration';

/**
 * Expected scaffolder step actions in order.
 */
const EXPECTED_STEP_ACTIONS = [
  'fetch:template',
  'publish:github',
  'catalog:register',
];

/**
 * Common skeleton files that every template must have.
 */
const COMMON_SKELETON_FILES = [
  'skeleton/cdk/app.py',
  'skeleton/cdk/stack.py',
  'skeleton/cdk/requirements.txt',
  'skeleton/cdk/cdk.json',
  'skeleton/.github/workflows/deploy.yml',
  'skeleton/.github/workflows/destroy.yml',
  'skeleton/catalog-info.yaml',
  'skeleton/README.md',
];

export interface TemplateMetadata {
  name: string;
  title: string;
  type: string;
  tags: string[];
  owner: string;
  description: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

/**
 * Load and parse a template YAML file.
 * @param templatePath - Absolute path to the template.yaml file
 * @returns Parsed YAML object
 */
export async function loadTemplate(templatePath: string): Promise<any> {
  const content = fs.readFileSync(templatePath, 'utf-8');
  return yaml.parse(content);
}

/**
 * Validate the basic schema of a Backstage scaffolder template.
 * Checks apiVersion, kind, metadata required fields, and spec structure.
 * @param template - Parsed template object
 * @returns ValidationResult with any schema errors
 */
export function validateSchema(template: any): ValidationResult {
  const errors: string[] = [];

  if (!template) {
    errors.push('Template is null or undefined');
    return { valid: false, errors };
  }

  // apiVersion
  if (template.apiVersion !== 'scaffolder.backstage.io/v1beta3') {
    errors.push(
      `Invalid apiVersion: expected 'scaffolder.backstage.io/v1beta3', got '${template.apiVersion}'`,
    );
  }

  // kind
  if (template.kind !== 'Template') {
    errors.push(
      `Invalid kind: expected 'Template', got '${template.kind}'`,
    );
  }

  // metadata
  if (!template.metadata) {
    errors.push('Missing metadata section');
  } else {
    if (!template.metadata.name) {
      errors.push('Missing metadata.name');
    }
    if (!template.metadata.title) {
      errors.push('Missing metadata.title');
    }
    if (!template.metadata.description) {
      errors.push('Missing metadata.description');
    }
    if (!template.metadata.tags || !Array.isArray(template.metadata.tags)) {
      errors.push('Missing or invalid metadata.tags (must be array)');
    }
  }

  // spec
  if (!template.spec) {
    errors.push('Missing spec section');
  } else {
    if (!template.spec.owner) {
      errors.push('Missing spec.owner');
    }
    if (!template.spec.type) {
      errors.push('Missing spec.type');
    }
    if (!template.spec.parameters || !Array.isArray(template.spec.parameters)) {
      errors.push('Missing or invalid spec.parameters (must be array)');
    }
    if (!template.spec.steps || !Array.isArray(template.spec.steps)) {
      errors.push('Missing or invalid spec.steps (must be array)');
    }
    if (!template.spec.output) {
      errors.push('Missing spec.output');
    }
  }

  return { valid: errors.length === 0, errors };
}

/**
 * Validate parameter groups exist in the correct order.
 * First group must be "Component Information", last must be "Repository Configuration".
 * @param template - Parsed template object
 * @returns ValidationResult with any ordering errors
 */
export function validateParameterGroups(template: any): ValidationResult {
  const errors: string[] = [];
  const params = template?.spec?.parameters;

  if (!params || !Array.isArray(params) || params.length === 0) {
    errors.push('No parameter groups found');
    return { valid: false, errors };
  }

  // First group check
  if (params[0].title !== FIRST_GROUP_TITLE) {
    errors.push(
      `First parameter group should be '${FIRST_GROUP_TITLE}', got '${params[0].title}'`,
    );
  }

  // Last group check
  if (params[params.length - 1].title !== LAST_GROUP_TITLE) {
    errors.push(
      `Last parameter group should be '${LAST_GROUP_TITLE}', got '${params[params.length - 1].title}'`,
    );
  }

  // Check that AWS Configuration is second
  if (params.length >= 2 && params[1].title !== 'AWS Configuration') {
    errors.push(
      `Second parameter group should be 'AWS Configuration', got '${params[1].title}'`,
    );
  }

  // Check each group has a title
  params.forEach((group: any, index: number) => {
    if (!group.title) {
      errors.push(`Parameter group at index ${index} is missing a title`);
    }
  });

  return { valid: errors.length === 0, errors };
}

/**
 * Validate the scaffolder steps follow the expected pattern:
 * 1. fetch:template
 * 2. publish:github
 * 3. catalog:register
 * @param template - Parsed template object
 * @returns ValidationResult with any step errors
 */
export function validateSteps(template: any): ValidationResult {
  const errors: string[] = [];
  const steps = template?.spec?.steps;

  if (!steps || !Array.isArray(steps)) {
    errors.push('No steps found');
    return { valid: false, errors };
  }

  if (steps.length !== 3) {
    errors.push(`Expected exactly 3 steps, got ${steps.length}`);
  }

  EXPECTED_STEP_ACTIONS.forEach((expectedAction, index) => {
    if (index < steps.length) {
      if (steps[index].action !== expectedAction) {
        errors.push(
          `Step ${index + 1} should have action '${expectedAction}', got '${steps[index].action}'`,
        );
      }
    }
  });

  // Validate step IDs
  if (steps.length >= 1 && !steps[0].id) {
    errors.push('Step 1 (fetch:template) is missing an id');
  }
  if (steps.length >= 2 && !steps[1].id) {
    errors.push('Step 2 (publish:github) is missing an id');
  }
  if (steps.length >= 3 && !steps[2].id) {
    errors.push('Step 3 (catalog:register) is missing an id');
  }

  // Validate step names
  if (steps.length >= 1 && !steps[0].name) {
    errors.push('Step 1 (fetch:template) is missing a name');
  }
  if (steps.length >= 2 && !steps[1].name) {
    errors.push('Step 2 (publish:github) is missing a name');
  }
  if (steps.length >= 3 && !steps[2].name) {
    errors.push('Step 3 (catalog:register) is missing a name');
  }

  return { valid: errors.length === 0, errors };
}

/**
 * Validate that expected skeleton files exist in the template directory.
 * @param templateDir - Root directory of the template (containing skeleton/)
 * @param expectedFiles - Array of relative file paths expected under the template dir
 */
export function validateSkeletonFiles(
  templateDir: string,
  expectedFiles?: string[],
): void {
  const filesToCheck = expectedFiles || COMMON_SKELETON_FILES;

  for (const file of filesToCheck) {
    const fullPath = path.join(templateDir, file);
    if (!fs.existsSync(fullPath)) {
      throw new Error(
        `Missing expected skeleton file: ${file} (full path: ${fullPath})`,
      );
    }
  }
}

/**
 * Extract metadata from a parsed template for easy assertion.
 * @param template - Parsed template object
 * @returns TemplateMetadata object
 */
export function getTemplateMetadata(template: any): TemplateMetadata {
  return {
    name: template?.metadata?.name || '',
    title: template?.metadata?.title || '',
    type: template?.spec?.type || '',
    tags: template?.metadata?.tags || [],
    owner: template?.spec?.owner || '',
    description: template?.metadata?.description || '',
  };
}

/**
 * Get parameter group titles from a template.
 * @param template - Parsed template object
 * @returns Array of parameter group titles
 */
export function getParameterGroupTitles(template: any): string[] {
  const params = template?.spec?.parameters;
  if (!params || !Array.isArray(params)) return [];
  return params.map((group: any) => group.title);
}

/**
 * Get all property names from a specific parameter group.
 * @param template - Parsed template object
 * @param groupTitle - Title of the parameter group
 * @returns Array of property names in that group
 */
export function getGroupProperties(
  template: any,
  groupTitle: string,
): string[] {
  const params = template?.spec?.parameters;
  if (!params || !Array.isArray(params)) return [];

  const group = params.find((g: any) => g.title === groupTitle);
  if (!group || !group.properties) return [];

  return Object.keys(group.properties);
}

/**
 * Get a specific property definition from a parameter group.
 * @param template - Parsed template object
 * @param groupTitle - Title of the parameter group
 * @param propertyName - Name of the property
 * @returns Property definition object or undefined
 */
export function getPropertyDefinition(
  template: any,
  groupTitle: string,
  propertyName: string,
): any | undefined {
  const params = template?.spec?.parameters;
  if (!params || !Array.isArray(params)) return undefined;

  const group = params.find((g: any) => g.title === groupTitle);
  if (!group || !group.properties) return undefined;

  return group.properties[propertyName];
}
