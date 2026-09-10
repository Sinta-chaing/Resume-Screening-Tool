export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function getScoreColor(score: number): string {
  if (score >= 80) return "var(--good)";
  if (score >= 60) return "var(--warn)";
  if (score >= 40) return "var(--mid)";
  return "var(--bad)";
}

export function getScoreLabel(score: number): string {
  if (score >= 80) return "Strong match";
  if (score >= 60) return "Good match";
  if (score >= 40) return "Partial match";
  return "Low match";
}

export const SUGGESTED_QUESTIONS = [
  "What are the candidate's key skills?",
  "Does the candidate have Python experience?",
  "Why did the candidate receive this match score?",
  "Summarize the candidate's work experience.",
];
