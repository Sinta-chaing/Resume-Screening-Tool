"use client";

import { MarkdownContent } from "./MarkdownContent";

interface ResumeSummaryProps {
  summary: string;
}

export function ResumeSummary({ summary }: ResumeSummaryProps) {
  return (
    <div className="summary-panel">
      <div className="summary-body">
        <MarkdownContent content={summary} />
      </div>
    </div>
  );
}
