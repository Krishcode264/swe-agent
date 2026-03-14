import mongoose, { Schema, Document } from 'mongoose';

export interface ITimelineEvent extends Document {
  incidentId: string;
  timestamp: Date;
  message: string;
  status: string;
}

const TimelineEventSchema: Schema = new Schema({
  incidentId: { type: String, required: true, index: true },
  timestamp: { type: Date, default: Date.now },
  message: { type: String, required: true },
  status: { type: String, required: true }
});

export const TimelineEvent = mongoose.model<ITimelineEvent>('TimelineEvent', TimelineEventSchema);
