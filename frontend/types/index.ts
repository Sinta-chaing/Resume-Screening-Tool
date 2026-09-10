export type ScoreBreakdown = {
  skillOverlap: number;
  embeddingSimilarity: number;
  skillWeight: number;
  embeddingWeight: number;
  matchedSkills: string[];
  missingSkills: string[];
  jdSkillCount: number;
  semanticThreshold?: number;
};

export type Evaluation =
  | {
      score: number;
      scoreBreakdown?: ScoreBreakdown;
      strengths: string[];
      gaps: string[];
      suggestions: string[];
      narrativeRaw?: string;
    }
  | { raw: string };

export interface AnalyzeResponse {
  ok: boolean;
  sessionId: string;
  chunks: number;
  evaluation: Evaluation;
  resumeSummary: string;
  candidateName?: string;
  position?: string;
  error?: string;
}

export interface RecordSummary {
  id: string;
  candidateName: string;
  position: string;
  score: number;
  createdAt: string;
  resumeFilename: string;
  jdFilename: string;
}

export interface RecordsListResponse {
  ok: boolean;
  records: RecordSummary[];
  error?: string;
}

export interface RecordDetail {
  ok: boolean;
  sessionId: string;
  candidateName: string;
  position: string;
  chunks: number;
  evaluation: Evaluation;
  resumeSummary: string;
  createdAt: string;
  resumeFilename: string;
  jdFilename: string;
  error?: string;
}

export interface ChatRequest {
  question: string;
  sessionId: string;
}

export interface ChatSource {
  id: string;
  type?: "resume" | "analysis";
  documentName?: string;
  resumeFilename?: string;
  candidateName?: string;
  section?: string;
  part?: string;
  score: number;
  reason?: string;
  preview: string;
}

export interface ChatResponse {
  ok: boolean;
  answer: string;
  sources: ChatSource[];
  error?: string;
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
}

export function isStructuredEvaluation(
  evaluation: Evaluation
): evaluation is Extract<Evaluation, { score: number }> {
  return "score" in evaluation;
}
