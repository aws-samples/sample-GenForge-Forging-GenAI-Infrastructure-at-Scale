/**
 * Bedrock Fine-Tuning CDK Synthesis Tests
 *
 * Tests that CDK synth succeeds for the Bedrock Fine-Tuning template skeleton
 * after substituting template variables with test values.
 */

import path from 'path';
import { prepareSkeleton, runCdkSynth, cleanup } from '../helpers/cdk-synth-runner';

const TEMPLATE_DIR = path.resolve(
  __dirname,
  '../../templates/fmops/bedrock-finetuning',
);

describe('Bedrock Fine-Tuning CDK Synthesis', () => {
  let workDir: string;
  let synthResult: Awaited<ReturnType<typeof runCdkSynth>> | null = null;

  beforeAll(async () => {
    workDir = await prepareSkeleton(TEMPLATE_DIR, {
      name: 'test-bedrock-ft',
      description: 'Test Bedrock fine-tuning for synthesis validation',
      owner: 'platform-team',
      awsRegion: 'us-east-1',
      awsAccountId: '111111111111',
      accountId: '111111111111',
      environment: 'dev',
      baseModelId: 'amazon.titan-text-express-v1',
      customizationType: 'FINE_TUNING',
      trainingEpochs: '3',
      batchSize: '8',
      learningRate: '0.00001',
      warmupRatio: '0.1',
      enableDataValidation: 'True',
      maxTrainingDataSizeMb: '100',
      validationDataRatio: '0.2',
      enableProvisionedThroughput: 'False',
      provisionedModelUnits: '1',
      enableNotifications: 'True',
      notificationEmail: 'test@example.com',
      repoUrl: 'github.com?repo=test-repo&owner=test-owner',
    });
  }, 120000);

  afterAll(async () => {
    if (workDir) await cleanup(workDir);
  });

  test('cdk synth succeeds', async () => {
    synthResult = await runCdkSynth(workDir);
    expect(synthResult.exitCode).toBe(0);
  }, 120000);

  test('produces valid CloudFormation template', async () => {
    if (!synthResult) {
      synthResult = await runCdkSynth(workDir);
    }
    expect(synthResult.cfnTemplate).toBeDefined();
    expect(synthResult.cfnTemplate).not.toBeNull();
  }, 120000);

  test('CloudFormation template contains S3 bucket resources', async () => {
    if (!synthResult || !synthResult.cfnTemplate) {
      synthResult = await runCdkSynth(workDir);
    }
    if (synthResult.cfnTemplate) {
      const resources = synthResult.cfnTemplate.Resources || {};
      const s3Buckets = Object.values(resources).filter(
        (r: any) => r.Type === 'AWS::S3::Bucket',
      );
      expect(s3Buckets.length).toBeGreaterThan(0);
    }
  }, 120000);

  test('CloudFormation template contains IAM roles', async () => {
    if (!synthResult || !synthResult.cfnTemplate) {
      synthResult = await runCdkSynth(workDir);
    }
    if (synthResult.cfnTemplate) {
      const resources = synthResult.cfnTemplate.Resources || {};
      const iamRoles = Object.values(resources).filter(
        (r: any) => r.Type === 'AWS::IAM::Role',
      );
      expect(iamRoles.length).toBeGreaterThan(0);
    }
  }, 120000);
});
