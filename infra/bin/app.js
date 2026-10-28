// Interest form backend: one DynamoDB table, one Lambda behind a public function URL.
// Read the rows with: aws dynamodb scan --table-name IndieGoPunkInterest --region ap-south-1
const cdk = require('aws-cdk-lib');
const dynamodb = require('aws-cdk-lib/aws-dynamodb');
const lambda = require('aws-cdk-lib/aws-lambda');

const app = new cdk.App();
const stack = new cdk.Stack(app, 'IndieGoPunkInterestStack', { env: { region: 'ap-south-1', account: process.env.CDK_DEFAULT_ACCOUNT } });

const table = new dynamodb.Table(stack, 'Interest', {
  tableName: 'IndieGoPunkInterest',
  partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING },
  billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
  pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
  removalPolicy: cdk.RemovalPolicy.RETAIN,
});

const fn = new lambda.Function(stack, 'Submit', {
  runtime: lambda.Runtime.NODEJS_20_X,
  handler: 'index.handler',
  timeout: cdk.Duration.seconds(5),
  memorySize: 128,
  environment: { TABLE: table.tableName },
  code: lambda.Code.fromInline(`
const { DynamoDBClient, PutItemCommand } = require('@aws-sdk/client-dynamodb');
const { randomUUID } = require('crypto');
const db = new DynamoDBClient({});
const res = (code, body) => ({ statusCode: code, headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
exports.handler = async (event) => {
  let d;
  try { d = JSON.parse(event.body || '{}'); } catch (e) { return res(400, { ok: false }); }
  if (d.website) return res(200, { ok: true }); // honeypot: bots fill this, people do not
  const clip = (v, n) => String(v || '').trim().slice(0, n);
  const email = clip(d.email, 200), studio = clip(d.studio, 200), note = clip(d.note, 1000);
  if (!/^[^@\\\\s]+@[^@\\\\s]+\\\\.[^@\\\\s]+$/.test(email) || !studio) return res(400, { ok: false, error: 'Add a studio name and a valid email.' });
  await db.send(new PutItemCommand({ TableName: process.env.TABLE, Item: {
    id: { S: randomUUID() }, at: { S: new Date().toISOString() },
    email: { S: email }, studio: { S: studio }, note: { S: note || '-' } } }));
  return res(200, { ok: true });
};
`),
});
table.grantWriteData(fn);

// CORS is answered by the function URL itself.
const url = fn.addFunctionUrl({
  authType: lambda.FunctionUrlAuthType.NONE,
  cors: { allowedOrigins: ['https://indiegopunk.com', 'https://www.indiegopunk.com', 'http://127.0.0.1:8765'], allowedMethods: [lambda.HttpMethod.POST], allowedHeaders: ['content-type'] },
});
new cdk.CfnOutput(stack, 'SubmitUrl', { value: url.url });
