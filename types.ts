export interface Coordinates {
  x: number;
  y: number;
  z: number;
}

export interface EvidenceItem {
  id: string;
  name: string;
  type: 'biological' | 'weapon' | 'trace' | 'document' | 'person' | 'other';
  description: string;
  position: Coordinates;
  significance: number; // 0-100
}

export interface TimelineEvent {
  timeOffset: string;
  description: string;
  confidence: number;
}

export interface CrimeSceneAnalysis {
  summary: string;
  locationDetails: string;
  evidence: EvidenceItem[];
  timeline: TimelineEvent[];
  hypotheses: { theory: string; probability: number }[];
  stats: {
    typeDistribution: { label: string; value: number }[];
    confidenceMetrics: { label: string; value: number }[];
  };
  imageUrls?: string[];
}

export enum AnalysisStatus {
  IDLE = 'IDLE',
  UPLOADING = 'UPLOADING',
  ANALYZING = 'ANALYZING',
  COMPLETE = 'COMPLETE',
  ERROR = 'ERROR'
}

export interface UserProfile {
  name: string;
  email: string;
  badgeId: string;
}