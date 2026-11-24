/**
 * Bedrock Fine-Tuning Template Validation Tests
 *
 * Validates the Bedrock Fine-Tuning template YAML structure, parameter groups,
 * steps, and skeleton files.
 */

import path from 'path';
import {
  loadTemplate,
  validateSchema,
  validateParameterGroups,
  validateSteps,
  validateSkeletonFiles,
  getPropertyDefinition,
} from '../helpers/template-validator';

const TEMPLATE_DIR = path.resolve(
  __dirname,
  '../../templates/fmops/bedrock-finetuning',
);

describe('Bedrock Fine-Tuning Template Validation', () => {
  let template: any;

  beforeAll(async () => {
    template = await loadTemplate(path.join(TEMPLATE_DIR, 'template.yaml'));
  });

  describe('Schema', () => {
    test('has valid apiVersion', () => {
      expect(template.apiVersion).toBe('scaffolder.backstage.io/v1beta3');
    });

    test('has kind Template', () => {
      expect(template.kind).toBe('Template');
    });

    test('has correct metadata.name', () => {
      expect(template.metadata.name).toBe(
        'genforge-bedrock-finetuning-template',
      );
    });

    test('has genforge tag', () => {
      expect(template.metadata.tags).toContain('genforge');
    });

    test('has bedrock tag', () => {
      expect(template.metadata.tags).toContain('bedrock');
    });

    test('has fine-tuning tag', () => {
      expect(template.metadata.tags).toContain('fine-tuning');
    });

    test('has fmops tag', () => {
      expect(template.metadata.tags).toContain('fmops');
    });

    test('has correct spec.type', () => {
      expect(template.spec.type).toBe('fmops');
    });

    test('has correct spec.owner', () => {
      expect(template.spec.owner).toBe('platform-team');
    });

    test('has a title', () => {
      expect(template.metadata.title).toBeDefined();
    });

    test('has a description', () => {
      expect(template.metadata.description).toBeDefined();
    });

    test('passes full schema validation', () => {
      const result = validateSchema(template);
      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });
  });

  describe('Parameters', () => {
    test('has exactly 8 parameter groups', () => {
      expect(template.spec.parameters).toHaveLength(8);
    });

    test('first group is Component Information', () => {
      expect(template.spec.parameters[0].title).toBe('Component Information');
    });

    test('second group is AWS Configuration', () => {
      expect(template.spec.parameters[1].title).toBe('AWS Configuration');
    });

    test('has Model Configuration group', () => {
      expect(template.spec.parameters[2].title).toBe('Model Configuration');
    });

    test('has Training Configuration group', () => {
      expect(template.spec.parameters[3].title).toBe('Training Configuration');
    });

    test('has Data Configuration group', () => {
      expect(template.spec.parameters[4].title).toBe('Data Configuration');
    });

    test('has Output Configuration group', () => {
      expect(template.spec.parameters[5].title).toBe('Output Configuration');
    });

    test('has Notifications group', () => {
      expect(template.spec.parameters[6].title).toBe('Notifications');
    });

    test('last group is Repository Configuration', () => {
      expect(template.spec.parameters[7].title).toBe(
        'Repository Configuration',
      );
    });

    test('passes parameter group validation', () => {
      const result = validateParameterGroups(template);
      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    test('name field has correct pattern', () => {
      const nameProperty = getPropertyDefinition(
        template,
        'Component Information',
        'name',
      );
      expect(nameProperty).toBeDefined();
      expect(nameProperty.pattern).toBe('^[a-z0-9-]+$');
    });

    test('awsRegion has valid enum values', () => {
      const regionProperty = getPropertyDefinition(
        template,
        'AWS Configuration',
        'awsRegion',
      );
      expect(regionProperty).toBeDefined();
      expect(regionProperty.enum).toContain('us-east-1');
      expect(regionProperty.enum).toContain('us-west-2');
    });

    test('environment has dev/staging/prod', () => {
      const envProperty = getPropertyDefinition(
        template,
        'AWS Configuration',
        'environment',
      );
      expect(envProperty.enum).toEqual(['dev', 'staging', 'prod']);
    });

    test('baseModelId has 7 model options', () => {
      const modelProperty = getPropertyDefinition(
        template,
        'Model Configuration',
        'baseModelId',
      );
      expect(modelProperty).toBeDefined();
      expect(modelProperty.enum).toHaveLength(7);
      expect(modelProperty.enum).toContain('amazon.titan-text-express-v1');
      expect(modelProperty.enum).toContain('amazon.titan-text-lite-v1');
      expect(modelProperty.enum).toContain(
        'anthropic.claude-3-haiku-20240307-v1:0',
      );
    });

    test('customizationType has FINE_TUNING and CONTINUED_PRE_TRAINING', () => {
      const custProperty = getPropertyDefinition(
        template,
        'Model Configuration',
        'customizationType',
      );
      expect(custProperty).toBeDefined();
      expect(custProperty.enum).toContain('FINE_TUNING');
      expect(custProperty.enum).toContain('CONTINUED_PRE_TRAINING');
    });

    test('trainingEpochs has min/max bounds', () => {
      const epochProperty = getPropertyDefinition(
        template,
        'Training Configuration',
        'trainingEpochs',
      );
      expect(epochProperty).toBeDefined();
      expect(epochProperty.type).toBe('integer');
      expect(epochProperty.minimum).toBe(1);
      expect(epochProperty.maximum).toBe(10);
    });

    test('batchSize has min/max bounds', () => {
      const batchProperty = getPropertyDefinition(
        template,
        'Training Configuration',
        'batchSize',
      );
      expect(batchProperty).toBeDefined();
      expect(batchProperty.minimum).toBe(1);
      expect(batchProperty.maximum).toBe(64);
    });

    test('learningRate is a number', () => {
      const lrProperty = getPropertyDefinition(
        template,
        'Training Configuration',
        'learningRate',
      );
      expect(lrProperty).toBeDefined();
      expect(lrProperty.type).toBe('number');
    });

    test('enableDataValidation is boolean', () => {
      const validationProperty = getPropertyDefinition(
        template,
        'Data Configuration',
        'enableDataValidation',
      );
      expect(validationProperty).toBeDefined();
      expect(validationProperty.type).toBe('boolean');
    });

    test('notificationEmail has email pattern', () => {
      const emailProperty = getPropertyDefinition(
        template,
        'Notifications',
        'notificationEmail',
      );
      expect(emailProperty).toBeDefined();
      expect(emailProperty.pattern).toBeDefined();
    });
  });

  describe('Steps', () => {
    test('has exactly 3 steps', () => {
      expect(template.spec.steps).toHaveLength(3);
    });

    test('first step is fetch:template', () => {
      expect(template.spec.steps[0].action).toBe('fetch:template');
    });

    test('second step is publish:github', () => {
      expect(template.spec.steps[1].action).toBe('publish:github');
    });

    test('third step is catalog:register', () => {
      expect(template.spec.steps[2].action).toBe('catalog:register');
    });

    test('passes step validation', () => {
      const result = validateSteps(template);
      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });
  });

  describe('Skeleton Files', () => {
    test('has all required skeleton files', () => {
      validateSkeletonFiles(TEMPLATE_DIR, [
        'skeleton/cdk/app.py',
        'skeleton/cdk/stack.py',
        'skeleton/cdk/requirements.txt',
        'skeleton/cdk/cdk.json',
        'skeleton/.github/workflows/deploy.yml',
        'skeleton/.github/workflows/destroy.yml',
        'skeleton/catalog-info.yaml',
        'skeleton/README.md',
      ]);
    });
  });

  describe('Output', () => {
    test('has output links', () => {
      expect(template.spec.output.links).toBeDefined();
      expect(template.spec.output.links.length).toBeGreaterThanOrEqual(2);
    });

    test('has repository output link', () => {
      const repoLink = template.spec.output.links.find(
        (l: any) => l.title === 'Repository',
      );
      expect(repoLink).toBeDefined();
    });

    test('has Bedrock Console output link', () => {
      const consoleLink = template.spec.output.links.find(
        (l: any) => l.title === 'Bedrock Console',
      );
      expect(consoleLink).toBeDefined();
    });
  });
});
