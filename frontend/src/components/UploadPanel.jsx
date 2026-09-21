import { useRef, useState } from "react";
import { getUploadStatus, uploadFeed } from "../api/client.js";

const POLL_INTERVAL_MS = 1000;

export default function UploadPanel({ onUploadComplete }) {
  const [job, setJob] = useState(null);
  const [error, setError] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef(null);

  const pollJob = (jobId) => {
    const timer = setInterval(async () => {
      try {
        const status = await getUploadStatus(jobId);
        setJob(status);
        if (status.status === "COMPLETED" || status.status === "FAILED") {
          clearInterval(timer);
          setIsUploading(false);
          if (status.status === "COMPLETED") onUploadComplete();
        }
      } catch (err) {
        clearInterval(timer);
        setIsUploading(false);
        setError(err.message);
      }
    }, POLL_INTERVAL_MS);
  };

  const handleFileSelected = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setError(null);
    setJob(null);
    setIsUploading(true);
    try {
      const created = await uploadFeed(file);
      setJob(created);
      pollJob(created.id);
    } catch (err) {
      setIsUploading(false);
      setError(err.message);
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <section className="panel">
      <h2>Upload Pricing Feed</h2>
      <p className="hint">CSV columns required: Store ID, SKU, Product Name, Price, Date</p>
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        disabled={isUploading}
        onChange={handleFileSelected}
      />

      {error && <p className="error">{error}</p>}

      {job && (
        <div className="job-status">
          <p>
            <strong>{job.filename}</strong> &mdash; <span className={`badge ${job.status.toLowerCase()}`}>{job.status}</span>
          </p>
          {job.status !== "PENDING" && (
            <ul>
              <li>Processed: {job.processed_rows} / {job.total_rows || "?"}</li>
              <li>Inserted: {job.inserted_rows}</li>
              <li>Updated: {job.updated_rows}</li>
              <li>Errors: {job.error_rows}</li>
            </ul>
          )}
          {job.errors && job.errors.length > 0 && (
            <details>
              <summary>Row errors ({job.errors.length})</summary>
              <ul className="error-list">
                {job.errors.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
    </section>
  );
}
