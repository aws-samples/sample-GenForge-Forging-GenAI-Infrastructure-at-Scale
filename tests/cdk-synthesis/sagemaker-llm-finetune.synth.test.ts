/**
 * SageMaker LLM Fine-Tuning CDK Synthesis Tests
 *
 * Tests that CDK synth succeeds for the SageMaker LLM Fine-Tuning template
 * skeleton after substituting template variables with test values.
 */

import path from 'path';
import { prepareSkeleton, runCdkSynth, cleanup } from '../helpers/cdk-synth-runner';

const TEMPLATE_DIR = path.resolve(
  __dirname,
  '../../templates/fmops/sagemaker-llm-finetune',
);

describe('SageMaker LLM Fine-Tuning CDK Synthesis', () => {
  let workDir: string;
  let synthResult: Awaited<ReturnType<typeof runCdkSynth>> | null = null;

  beforeAll(async () => {
    workDir = await prepareSkeleton(TEMPLATE_DIR, {
      name: 'test-llm-ft',
      description: 'Test LLM fine-tuning for synthesis validation',
      owner: 'platform-team',
      awsRegion: 'us-east-1',
      awsAccountId: '111111111111',
      accountId: '111111111111',
      environment: 'dev',
      baseModel: 'meta-llama/Llama-2-7b-hf',
      instanceType: 'ml.g5.2xlarge',
      instanceCount: '1',
      epochs: '3',
      loraRank: '16',
      learningRate: '0.0002',
      trainingDataS3Path: '',
      validationSplit: '0.1',
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
