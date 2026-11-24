/**
 * SageMaker JumpStart Endpoint CDK Synthesis Tests
 *
 * Tests that CDK synth succeeds for the SageMaker JumpStart Endpoint
 * template skeleton after substituting template variables with test values.
 */

import path from 'path';
import { prepareSkeleton, runCdkSynth, cleanup } from '../helpers/cdk-synth-runner';

const TEMPLATE_DIR = path.resolve(
  __dirname,
  '../../templates/fmops/sagemaker-jumpstart-endpoint',
);

describe('SageMaker JumpStart Endpoint CDK Synthesis', () => {
  let workDir: string;
  let synthResult: Awaited<ReturnType<typeof runCdkSynth>> | null = null;

  beforeAll(async () => {
    workDir = await prepareSkeleton(TEMPLATE_DIR, {
      name: 'test-jumpstart',
      description: 'Test JumpStart endpoint for synthesis validation',
      owner: 'platform-team',
      awsRegion: 'us-east-1',
      awsAccountId: '111111111111',
      accountId: '111111111111',
      environment: 'dev',
      jumpstartModelId: 'meta-textgeneration-llama-3-8b',
      instanceType: 'ml.g5.xlarge',
      initialInstanceCount: '1',
      enableDataCapture: 'False',
      dataCapturePercent: '10',
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
