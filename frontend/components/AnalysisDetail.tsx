"use client";

import { ChatPanel } from "@/components/ChatPanel";
import { MatchAnalysis } from "@/components/MatchAnalysis";
import { ResumeSummary } from "@/components/ResumeSummary";
import { StepCard } from "@/components/StepCard";
import { askQuestion } from "@/lib/api";
import type { ChatTurn, Evaluation } from "@/types";
import { useState } from "react";

interface AnalysisDetailProps {
  data: {
    sessionId: string;
    evaluation: Evaluation;
    chunks: number;
    resumeSummary: string;
  };
}

export function AnalysisDetail({ data }: AnalysisDetailProps) {
  const [question, setQuestion] = useState("");
  const [chatLog, setChatLog] = useState<ChatTurn[]>([]);
  const [asking, setAsking] = useState(false);

  async function submitQuestion(text: string) {
    const q = text.trim();
    if (!q || asking) return;

    setQuestion("");
    setAsking(true);
    setChatLog((current) => [...current, { role: "user", content: q }]);

    try {
      const result = await askQuestion(q, data.sessionId);
      setChatLog((current) => [
        ...current,
        { role: "assistant", content: result.answer, sources: result.sources },
      ]);
    } catch (e) {
      const message = e instanceof Error ? e.message : "Chat failed";
      setChatLog((current) => [
        ...current,
        { role: "assistant", content: `Sorry, I couldn't answer that: ${message}` },
      ]);
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="results-layout">
      <StepCard
        step={1}
        title="Match analysis"
        description="AI-generated comparison of resume vs. job requirements."
      >
        <MatchAnalysis evaluation={data.evaluation} chunks={data.chunks} />
      </StepCard>

      <StepCard
        step={2}
        title="Ask about the candidate"
        description="RAG chat retrieves relevant resume sections before answering."
      >
        <ChatPanel
          chatLog={chatLog}
          question={question}
          asking={asking}
          disabled={false}
          onQuestionChange={setQuestion}
          onSubmit={() => submitQuestion(question)}
          onSuggestedQuestion={submitQuestion}
        />
      </StepCard>

      <StepCard
        step={3}
        title="Resume summary"
        description="AI-generated overview of the candidate based on their resume."
      >
        <ResumeSummary summary={data.resumeSummary} />
      </StepCard>
    </div>
  );
}
