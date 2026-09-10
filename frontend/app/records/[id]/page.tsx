"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AnalysisDetail } from "@/components/AnalysisDetail";
import { AppNav } from "@/components/AppNav";
import { fetchRecord } from "@/lib/api";
import type { RecordDetail } from "@/types";

export default function RecordDetailPage() {
  const params = useParams<{ id: string }>();
  const [data, setData] = useState<RecordDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const sessionId = params.id;

    if (!sessionId) {
      setError("Missing record id");
      setLoading(false);
      return;
    }

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const result = await fetchRecord(sessionId);
        if (!cancelled) {
          setData(result);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load record");
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
  }, [params.id]);

  return (
    <div className="app">
      <header className="hero">
        <div className="hero-top">
          <span className="pill">Record detail</span>
          <AppNav />
        </div>
        {data ? (
          <>
            <h1>{data.candidateName}</h1>
            <p>
              {data.position} · Analyzed{" "}
              {new Date(data.createdAt).toLocaleString()}
            </p>
          </>
        ) : (
          <>
            <h1>Candidate record</h1>
            <p>Full match analysis, chat, and resume summary.</p>
          </>
        )}
        <div className="hero-actions">
          <Link href="/records" className="ghost inline-link">
            ← Back to records
          </Link>
        </div>
      </header>

      {loading && (
        <div className="records-state">
          <div className="progress-bar" />
          <p>Loading analysis…</p>
        </div>
      )}

      {error && (
        <div className="error" role="alert">
          <strong>Could not load record</strong>
          <p>{error}</p>
          <Link href="/records" className="ghost inline-link">
            Back to records
          </Link>
        </div>
      )}

      {data && <AnalysisDetail data={data} />}

      <footer className="footer">
        Backend: Django REST · Frontend: Next.js · AI: Ollama (local)
      </footer>
    </div>
  );
}
