import mongoose, { Schema, Document } from 'mongoose';

export interface IIncident extends Document {
  incidentId: string;
  title: string;
  severity: string;
  service: string;
  reported_by: string;
  environment: string;
  timestamp: Date;
  repository: string;
  description: string;
  steps_to_reproduce: string[];
  error_log: string;
  expected_behavior: string;
  actual_behavior: string;
  recent_changes: string;
  tags: string[];
  status: 'queued' | 'running' | 'fix_generated' | 'tests_passed' | 'pr_created' | 'completed' | 'failed';
}

const IncidentSchema: Schema = new Schema({
  incidentId: { type: String, required: true, unique: true },
  title: { type: String, required: true },
  severity: { type: String },
  service: { type: String },
  reported_by: { type: String },
  environment: { type: String },
  timestamp: { type: Date, default: Date.now },
  repository: { type: String },
  description: { type: String },
  steps_to_reproduce: { type: [String] },
  error_log: { type: String },
  expected_behavior: { type: String },
  actual_behavior: { type: String },
  recent_changes: { type: String },
  tags: { type: [String] },
  status: { type: String, enum: ['queued', 'running', 'fix_generated', 'tests_passed', 'pr_created', 'completed', 'failed'], default: 'queued' }
}, { timestamps: true });

export const Incident = mongoose.model<IIncident>('Incident', IncidentSchema);
