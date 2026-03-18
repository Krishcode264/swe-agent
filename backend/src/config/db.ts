import mongoose from 'mongoose';
import { logger } from '../utils/logger';
import dotenv from 'dotenv';
dotenv.config();

const MONGO_URL = process.env.MONGO_URL || 'mongodb://localhost:27017/incident_db';

export const connectDB = async () => {
  try {
    await mongoose.connect(MONGO_URL);
    logger.info('MongoDB connected');
  } catch (error) {
    logger.error('MongoDB connection error:', error);
    process.exit(1);
  }
};
