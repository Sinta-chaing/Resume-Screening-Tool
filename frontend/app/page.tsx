"use client";

import Link from "next/link";
import { useState } from "react";
import { AnalysisDetail } from "@/components/AnalysisDetail";
import { AppNav } from "@/components/AppNav";
import { FileUploadZone } from "@/components/FileUploadZone";
import { StepCard } from "@/components/StepCard";
import { analyzeResume } from "@/lib/api";
import type { AnalyzeResponse } from "@/types";

type AppStep = "upload" | "results";

export default function HomePage() {
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [jdFile, setJdFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const step: AppStep = data ? "results" : "upload";
  const canAnalyze = Boolean(resumeFile && jdFile && !uploading);
  const missingFiles = !resumeFile || !jdFile;

  async function handleAnalyze() {
    if (!resumeFile || !jdFile) return;

    setUploading(true);
    setError(null);
    setData(null);

    try {
      const result = await analyzeResume(resumeFile, jdFile);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analyze failed");
    } finally {
      setUploading(false);
    }
  }

  function handleReset() {
    setResumeFile(null);
    setJdFile(null);
    setData(null);
    setError(null);
  }

  return (
    <div className="app">
      <header className="hero">
        <div className="hero-top">
          <span className="pill">RAG · Ollama · Local LLM</span>
          <div className="hero-top-right">
            <AppNav />
            <nav className="step-nav" aria-label="Progress">
              <span className={`step-nav-item ${step === "upload" ? "active" : "done"}`}>
                1 Upload
              </span>
              <span className="step-nav-sep" />
              <span className={`step-nav-item ${step === "results" ? "active" : ""}`}>
                2 Results
              </span>
            </nav>
          </div>
        </div>
        <h1>Resume Screener</h1>
        <p>
          Upload a resume and job description to get an ATS-style match score,
          skill gap analysis, and contextual Q&amp;A powered by RAG.
        </p>
      </header>

      <StepCard
        step={1}
        title="Upload documents"
        description="Both files are required before analysis can run."
      >
        <div className="grid2">
          <FileUploadZone
            id="resume"
            label="Resume"
            hint="PDF or TXT · max 20 MB"
            accept=".pdf,.txt"
            file={resumeFile}
            disabled={uploading}
            onFileChange={setResumeFile}
          />
          <FileUploadZone
            id="jd"
            label="Job description"
            hint="PDF or TXT · max 20 MB"
            accept=".pdf,.txt"
            file={jdFile}
            disabled={uploading}
            onFileChange={setJdFile}
          />
        </div>

        <div className="actions">
          <button
            className="primary"
            disabled={!canAnalyze}
            onClick={handleAnalyze}
          >
            {uploading ? "Analyzing…" : "Analyze match"}
          </button>
          <button className="ghost" type="button" onClick={handleReset} disabled={uploading}>
            Reset
          </button>
        </div>

        {missingFiles && !uploading && (
          <p className="hint-text">Select both a resume and a job description to continue.</p>
        )}

        {uploading && (
          <div className="progress-banner">
            <div className="progress-bar" />
            <p>Extracting text, building embeddings, and running ATS evaluation…</p>
          </div>
        )}

        {error && (
          <div className="error" role="alert">
            <strong>Analysis failed</strong>
            <p>{error}</p>
          </div>
        )}
      </StepCard>

      {data && (
        <>
          <div className="saved-banner">
            <p>
              Saved to records
              {data.candidateName ? ` · ${data.candidateName}` : ""}
              {data.position ? ` · ${data.position}` : ""}
            </p>
            <Link href={`/records/${data.sessionId}`} className="ghost inline-link">
              View in records →
            </Link>
          </div>
          <AnalysisDetail data={data} />
        </>
      )}

      <footer className="footer">
        Backend: Django REST · Frontend: Next.js · AI: Ollama (local)
      </footer>
    </div>
  );
}
