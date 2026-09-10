"use client";

import { FormEvent, useEffect, useRef } from "react";
import type { ChatSource, ChatTurn } from "@/types";
import { SUGGESTED_QUESTIONS } from "@/lib/utils";
import { MarkdownContent } from "./MarkdownContent";

interface ChatPanelProps {
  chatLog: ChatTurn[];
  question: string;
  asking: boolean;
  disabled: boolean;
  onQuestionChange: (value: string) => void;
  onSubmit: () => void;
  onSuggestedQuestion: (question: string) => void;
}

function sourceTitle(source: ChatSource): string {
  const name = source.documentName || source.candidateName || source.resumeFilename || source.id;
  const section = source.section ? ` · ${source.section}` : "";
  const part = source.part ? ` (${source.part})` : "";
  return `${name}${section}${part}`;
}

function SourceList({ sources }: { sources: ChatSource[] }) {
  if (sources.length === 0) return null;

  return (
    <div className="msg-sources">
      <span className="msg-sources-title">Sources</span>
      {sources.map((source) => (
        <div className="msg-source" key={`${source.id}-${source.section ?? ""}`}>
          <div className="msg-source-header">
            <span className="msg-source-id">{sourceTitle(source)}</span>
            <span className="msg-source-score">
              {(source.score * 100).toFixed(0)}% relevance
            </span>
          </div>
          {source.reason && <p className="msg-source-reason">{source.reason}</p>}
          <p>{source.preview}</p>
        </div>
      ))}
    </div>
  );
}

export function ChatPanel({
  chatLog,
  question,
  asking,
  disabled,
  onQuestionChange,
  onSubmit,
  onSuggestedQuestion,
}: ChatPanelProps) {
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatLog, asking]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <div className="chat-panel">
      <div className="chatbox">
        {chatLog.length === 0 && !asking && (
          <div className="chat-empty">
            <p>Ask questions about the uploaded resume.</p>
            <div className="prompt-chips">
              {SUGGESTED_QUESTIONS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  className="prompt-chip"
                  disabled={disabled || asking}
                  onClick={() => onSuggestedQuestion(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {chatLog.map((message, index) => (
          <div key={index} className={`msg msg--${message.role}`}>
            <div className="msg-header">
              <span className="msg-avatar">{message.role === "user" ? "You" : "AI"}</span>
            </div>
            <div className="msg-body">
              {message.role === "assistant" ? (
                <MarkdownContent content={message.content} />
              ) : (
                message.content
              )}
            </div>
            {message.role === "assistant" && message.sources && (
              <SourceList sources={message.sources} />
            )}
          </div>
        ))}

        {asking && (
          <div className="msg msg--assistant msg--loading">
            <div className="msg-header">
              <span className="msg-avatar">AI</span>
            </div>
            <div className="typing-indicator">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      <form className="chat-form" onSubmit={handleSubmit}>
        <input
          value={question}
          placeholder="Ask about skills, experience, education..."
          disabled={disabled || asking}
          onChange={(event) => onQuestionChange(event.target.value)}
        />
        <button type="submit" className="primary" disabled={disabled || asking || !question.trim()}>
          {asking ? "Thinking..." : "Send"}
        </button>
      </form>
    </div>
  );
}
