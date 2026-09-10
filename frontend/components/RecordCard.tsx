"use client";

import Link from "next/link";
import { getScoreColor } from "@/lib/utils";
import type { RecordSummary } from "@/types";

interface RecordCardProps {
  record: RecordSummary;
  deleting?: boolean;
  onDelete: (id: string) => void;
}

export function RecordCard({ record, deleting = false, onDelete }: RecordCardProps) {
  const scoreColor = getScoreColor(record.score);

  function handleDelete(event: React.MouseEvent<HTMLButtonElement>) {
    event.preventDefault();
    event.stopPropagation();
    onDelete(record.id);
  }

  return (
    <div className="record-card">
      <Link href={`/records/${record.id}`} className="record-card-link">
        <div className="record-card-top">
          <span className="record-score" style={{ color: scoreColor }}>
            {record.score}
          </span>
          <span className="record-score-label">match</span>
        </div>
        <h2 className="record-card-name">{record.candidateName}</h2>
        <p className="record-card-position">{record.position}</p>
        <p className="record-card-meta">
          Analyzed {new Date(record.createdAt).toLocaleDateString()}
        </p>
      </Link>
      <button
        type="button"
        className="record-delete"
        onClick={handleDelete}
        disabled={deleting}
        aria-label={`Delete record for ${record.candidateName}`}
      >
        {deleting ? "Deleting…" : "Delete"}
      </button>
    </div>
  );
}
