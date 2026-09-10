import type { Evaluation } from "@/types";
import { isStructuredEvaluation } from "@/types";
import { getScoreColor, getScoreLabel } from "@/lib/utils";
import { ScoreRing } from "./ScoreRing";

interface MatchAnalysisProps {
  evaluation: Evaluation;
  chunks: number;
}

export function MatchAnalysis({ evaluation, chunks }: MatchAnalysisProps) {
  if (!isStructuredEvaluation(evaluation)) {
    return (
      <div className="analysis-fallback">
        <p className="muted">
          The model did not return structured JSON. Raw output:
        </p>
        <div className="raw">
          <pre>{evaluation.raw}</pre>
        </div>
      </div>
    );
  }

  const scoreColor = getScoreColor(evaluation.score);
  const scoreLabel = getScoreLabel(evaluation.score);
  const breakdown = evaluation.scoreBreakdown;

  return (
    <div className="analysis-grid">
      <div className="analysis-score-panel">
        <ScoreRing
          score={evaluation.score}
          color={scoreColor}
          label={scoreLabel}
        />
        <div className="analysis-meta">
          <span className="meta-chip">{chunks} resume chunks indexed</span>
          {breakdown && (
            <span className="meta-chip meta-chip--muted">
              Semantic matching · exact, alias, and embedding similarity
            </span>
          )}
        </div>
        {breakdown && (
          <div className="score-breakdown">
            <div className="score-breakdown-row">
              <span>Skill overlap</span>
              <strong>{breakdown.skillOverlap}%</strong>
            </div>
            <div className="score-breakdown-row">
              <span>Embedding similarity</span>
              <strong>{breakdown.embeddingSimilarity}%</strong>
            </div>
            <p className="score-breakdown-note">
              Compared {breakdown.jdSkillCount} requirements using text overlap, synonyms,
              and semantic similarity
              {breakdown.semanticThreshold
                ? ` (threshold ${Math.round(breakdown.semanticThreshold * 100)}%)`
                : ""}
              .
            </p>
            {breakdown.matchedSkills.length > 0 && (
              <div className="score-breakdown-block">
                <span className="score-breakdown-label">Matched requirements</span>
                <ul className="tag-list">
                  {breakdown.matchedSkills.slice(0, 12).map((item) => (
                    <li className="tag tag--good" key={item}>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {breakdown.missingSkills.length > 0 && (
              <div className="score-breakdown-block">
                <span className="score-breakdown-label">Unmatched requirements</span>
                <ul className="tag-list">
                  {breakdown.missingSkills.slice(0, 12).map((item) => (
                    <li className="tag tag--bad" key={item}>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="analysis-details">
        <div className="detail-block">
          <h3>
            <span className="detail-icon detail-icon--good">+</span>
            Strengths
          </h3>
          {evaluation.strengths.length === 0 ? (
            <p className="muted">No clear strengths identified.</p>
          ) : (
            <ul className="tag-list">
              {evaluation.strengths.map((item, index) => (
                <li className="tag tag--good" key={index}>
                  {item}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="detail-block">
          <h3>
            <span className="detail-icon detail-icon--bad">−</span>
            Skill gaps
          </h3>
          {evaluation.gaps.length === 0 ? (
            <p className="muted">No obvious gaps identified.</p>
          ) : (
            <ul className="tag-list">
              {evaluation.gaps.map((item, index) => (
                <li className="tag tag--bad" key={index}>
                  {item}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="detail-block detail-block--full">
          <h3>
            <span className="detail-icon detail-icon--info">→</span>
            Improvement suggestions
          </h3>
          {evaluation.suggestions.length === 0 ? (
            <p className="muted">No suggestions returned.</p>
          ) : (
            <ol className="suggestion-list">
              {evaluation.suggestions.map((item, index) => (
                <li key={index}>{item}</li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </div>
  );
}
