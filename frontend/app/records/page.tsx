"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppNav } from "@/components/AppNav";
import { RecordCard } from "@/components/RecordCard";
import { deleteRecord, fetchRecords } from "@/lib/api";
import type { RecordSummary } from "@/types";

export default function RecordsPage() {
  const [records, setRecords] = useState<RecordSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const result = await fetchRecords("asc");
        if (!cancelled) {
          setRecords(result.records);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load records");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleDelete(id: string) {
    const record = records.find((item) => item.id === id);
    const label = record?.candidateName ?? "this record";
    const confirmed = window.confirm(`Delete ${label}? This cannot be undone.`);
    if (!confirmed) return;

    setDeletingId(id);
    setError(null);

    try {
      await deleteRecord(id);
      setRecords((current) => current.filter((item) => item.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete record");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="app">
      <header className="hero">
        <div className="hero-top">
          <span className="pill">Candidate history</span>
          <AppNav />
        </div>
        <h1>Analysis records</h1>
        <p>
          Every analyzed resume is saved here. Cards are sorted by match score
          (lowest to highest). Click a card to view the full analysis.
        </p>
      </header>

      {loading && (
        <div className="records-state">
          <div className="progress-bar" />
          <p>Loading records…</p>
        </div>
      )}

      {error && (
        <div className="error" role="alert">
          <strong>Could not load records</strong>
          <p>{error}</p>
        </div>
      )}

      {!loading && !error && records.length === 0 && (
        <div className="records-empty">
          <h2>No records yet</h2>
          <p>Upload and analyze a resume to create your first record.</p>
          <Link href="/" className="primary inline-link">
            Go to analyze
          </Link>
        </div>
      )}

      {!loading && !error && records.length > 0 && (
        <div className="records-grid">
          {records.map((record) => (
            <RecordCard
              key={record.id}
              record={record}
              deleting={deletingId === record.id}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      <footer className="footer">
        Backend: Django REST · Frontend: Next.js · AI: Ollama (local)
      </footer>
    </div>
  );
}
