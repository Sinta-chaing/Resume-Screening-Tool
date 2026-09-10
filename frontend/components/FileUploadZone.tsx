"use client";

import { ChangeEvent, DragEvent, useRef, useState } from "react";
import { formatFileSize } from "@/lib/utils";

interface FileUploadZoneProps {
  id: string;
  label: string;
  hint: string;
  accept: string;
  file: File | null;
  onFileChange: (file: File | null) => void;
  disabled?: boolean;
}

export function FileUploadZone({
  id,
  label,
  hint,
  accept,
  file,
  onFileChange,
  disabled = false,
}: FileUploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function handleFiles(selected: File | null) {
    if (!selected) {
      onFileChange(null);
      return;
    }
    onFileChange(selected);
  }

  function handleInputChange(event: ChangeEvent<HTMLInputElement>) {
    handleFiles(event.target.files?.[0] ?? null);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    if (disabled) return;
    handleFiles(event.dataTransfer.files?.[0] ?? null);
  }

  return (
    <div
      className={`upload-zone ${dragging ? "upload-zone--dragging" : ""} ${file ? "upload-zone--filled" : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          inputRef.current?.click();
        }
      }}
    >
      <input
        ref={inputRef}
        id={id}
        type="file"
        accept={accept}
        disabled={disabled}
        onChange={handleInputChange}
        hidden
      />

      <div className="upload-zone-icon" aria-hidden="true">
        {file ? "✓" : "↑"}
      </div>

      <div className="upload-zone-body">
        <span className="upload-zone-label">{label}</span>
        {file ? (
          <>
            <span className="upload-zone-filename">{file.name}</span>
            <span className="upload-zone-meta">{formatFileSize(file.size)}</span>
          </>
        ) : (
          <>
            <span className="upload-zone-action">Click or drag file here</span>
            <span className="upload-zone-meta">{hint}</span>
          </>
        )}
      </div>

      {file && !disabled && (
        <button
          type="button"
          className="upload-zone-clear"
          onClick={(event) => {
            event.stopPropagation();
            onFileChange(null);
            if (inputRef.current) inputRef.current.value = "";
          }}
          aria-label={`Remove ${label}`}
        >
          ×
        </button>
      )}
    </div>
  );
}
