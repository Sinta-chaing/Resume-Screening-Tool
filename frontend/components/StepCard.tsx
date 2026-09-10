import { ReactNode } from "react";

interface StepCardProps {
  step: number;
  title: string;
  description?: string;
  children: ReactNode;
}

export function StepCard({ step, title, description, children }: StepCardProps) {
  return (
    <section className="card">
      <header className="card-header">
        <span className="step-badge">{step}</span>
        <div>
          <h2>{title}</h2>
          {description && <p className="card-desc">{description}</p>}
        </div>
      </header>
      {children}
    </section>
  );
}
