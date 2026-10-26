import express from 'express';
import cors from 'cors';
import { taxonomyRouter } from './routes/taxonomy';
import { domainRouter } from './routes/domain';
import { companyRouter } from './routes/company';
import { instanceRouter } from './routes/instance';
import { errorHandler } from './middleware/errorHandler';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

app.use('/api/taxonomies', taxonomyRouter);
app.use('/api/domains', domainRouter);
app.use('/api/companies', companyRouter);
app.use('/api/instances', instanceRouter);

app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.use(errorHandler);

app.listen(PORT, () => {
  console.log(`✓ zyPlat API server running on http://localhost:${PORT}`);
  console.log(`  Health check: http://localhost:${PORT}/health`);
  console.log(`  API endpoints:`);
  console.log(`    - Taxonomies: http://localhost:${PORT}/api/taxonomies`);
  console.log(`    - Domains: http://localhost:${PORT}/api/domains`);
  console.log(`    - Companies: http://localhost:${PORT}/api/companies`);
  console.log(`    - Instances: http://localhost:${PORT}/api/instances`);
});

export default app;
