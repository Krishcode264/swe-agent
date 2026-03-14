import express from 'express';
import cors from 'cors';
import { connectDB } from './config/db';
import { connectRedis } from './config/redis';
import webhookRoutes from './routes/webhook';
import incidentRoutes from './routes/incidents';
import { logger } from './utils/logger';

const app = express();
const PORT = process.env.PORT || 4000;

app.use(cors());
app.use(express.json());

app.use('/webhook', webhookRoutes);
app.use('/api/incidents', incidentRoutes);

app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok' });
});

const startServer = async () => {
  await connectDB();
  await connectRedis();

  app.listen(PORT, () => {
    logger.info(`Backend orchestrated started on port ${PORT}`);
  });
};

startServer();
