/**
 * SageMaker LLM Fine-Tuning Template Validation Tests
 *
 * Validates the SageMaker LLM Fine-Tuning template YAML structure,
 * parameter groups, steps, and skeleton files.
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
  '../../templates/fmops/sagemaker-llm-finetune',
);

describe('SageMaker LLM Fine-Tuning Template Validation', () => {
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
        'genforge-sagemaker-llm-finetune-template',
      );
    });

    test('has genforge tag', () => {
      expect(template.metadata.tags).toContain('genforge');
    });

    test('has sagemaker tag', () => {
      expect(template.metadata.tags).toContain('sagemaker');
    });

    test('has fine-tuning tag', () => {
      expect(template.metadata.tags).toContain('fine-tuning');
    });

    test('has lora tag', () => {
      expect(template.metadata.tags).toContain('lora');
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

    test('passes full schema validation', () => {
      const result = validateSchema(template);
      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });
  });

  describe('Parameters', () => {
    test('has exactly 6 parameter groups', () => {
      expect(template.spec.parameters).toHaveLength(6);
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
      expect(template.spec.parameters[3].title).toBe(
        'Training Configuration',
      );
    });

    test('has Data Configuration group', () => {
      expect(template.spec.parameters[4].title).toBe('Data Configuration');
    });

    test('last group is Repository Configuration', () => {
      expect(template.spec.parameters[5].title).toBe(
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

    test('environment has dev/staging/prod', () => {
      const envProperty = getPropertyDefinition(
        template,
        'AWS Configuration',
        'environment',
      );
      expect(envProperty.enum).toEqual(['dev', 'staging', 'prod']);
    });

    test('baseModel has HuggingFace model options', () => {
      const modelProperty = getPropertyDefinition(
        template,
        'Model Configuration',
        'baseModel',
      );
      expect(modelProperty).toBeDefined();
      expect(modelProperty.enum).toContain('meta-llama/Llama-2-7b-hf');
      expect(modelProperty.enum).toContain('meta-llama/Llama-2-13b-hf');
      expect(modelProperty.enum).toContain('mistralai/Mistral-7B-v0.1');
      expect(modelProperty.enum).toContain('codellama/CodeLlama-7b-hf');
      expect(modelProperty.enum).toContain('tiiuae/falcon-7b');
    });

    test('instanceType has GPU options', () => {
      const instanceProperty = getPropertyDefinition(
        template,
        'Training Configuration',
        'instanceType',
      );
      expect(instanceProperty).toBeDefined();
      expect(instanceProperty.enum).toContain('ml.g5.xlarge');
      expect(instanceProperty.enum).toContain('ml.g5.2xlarge');
      expect(instanceProperty.enum).toContain('ml.p4d.24xlarge');
    });

    test('epochs has min/max bounds', () => {
      const epochProperty = getPropertyDefinition(
        template,
        'Training Configuration',
        'epochs',
      );
      expect(epochProperty).toBeDefined();
      expect(epochProperty.type).toBe('integer');
      expect(epochProperty.minimum).toBe(1);
      expect(epochProperty.maximum).toBe(20);
    });

    test('loraRank has valid options', () => {
      const loraProperty = getPropertyDefinition(
        template,
        'Training Configuration',
        'loraRank',
      );
      expect(loraProperty).toBeDefined();
      expect(loraProperty.enum).toEqual([8, 16, 32, 64]);
    });

    test('instanceCount has min/max bounds', () => {
      const countProperty = getPropertyDefinition(
        template,
        'Training Configuration',
        'instanceCount',
      );
      expect(countProperty).toBeDefined();
      expect(countProperty.minimum).toBe(1);
      expect(countProperty.maximum).toBe(8);
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

    test('validationSplit has min/max bounds', () => {
      const splitProperty = getPropertyDefinition(
        template,
        'Data Configuration',
        'validationSplit',
      );
      expect(splitProperty).toBeDefined();
      expect(splitProperty.minimum).toBe(0);
      expect(splitProperty.maximum).toBe(0.5);
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
      expect(template.spec.output.links.length).toBeGreaterThanOrEqual(2);
    });

    test('has SageMaker Console output link', () => {
      const consoleLink = template.spec.output.links.find(
        (l: any) => l.title === 'SageMaker Console',
      );
      expect(consoleLink).toBeDefined();
    });
  });
});
