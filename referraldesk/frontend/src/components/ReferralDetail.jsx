import React, { useEffect, useState, useCallback } from "react";
import { api } from "../api.js";

const STATUS_OPTIONS = ["New", "Matching", "Scheduled", "Completed", "Overdue"];

export default function ReferralDetail({ referralId, onClose, onChanged }) {
  const [referral, setReferral] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getReferral(referralId);
      setReferral(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [referralId]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleStatusChange(e) {
    const newStatus = e.target.value;
    await api.updateStatus(referralId, newStatus);
    await load();
    onChanged();
  }

  async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    try {
      await api.uploadDocument(referralId, file);
      await load();
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  return (
    <div className="overlay" onClick={onClose}>
      <div className="panel" onClick={(e) => e.stopPropagation()}>
        <button className="panel-close" onClick={onClose}>
          Close ×
        </button>

        {loading && <p>Loading referral…</p>}
        {error && <p style={{ color: "var(--rust)" }}>{error}</p>}

        {referral && (
          <>
            <h2>
              {referral.patient.first_name} {referral.patient.last_name}
            </h2>
            <div className="mono" style={{ fontSize: 12, color: "var(--ink-soft)" }}>
              Referral #{referral.id.slice(0, 8)}
            </div>

            <div className="field-label">Requested specialty</div>
            <div>{referral.specialty_requested}</div>

            <div className="field-label">Status</div>
            <select
              className="status-select"
              value={referral.status}
              onChange={handleStatusChange}
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>

            <div className="field-label">Matched provider</div>
            <div>
              {referral.matched_provider
                ? `${referral.matched_provider.name} — ${referral.matched_provider.specialty}`
                : "Not yet matched (background matching may still be running)"}
            </div>

            {referral.notes && (
              <>
                <div className="field-label">Notes</div>
                <div>{referral.notes}</div>
              </>
            )}

            <div className="field-label">Documents</div>
            {referral.documents.length === 0 && (
              <div style={{ fontSize: 13, color: "var(--ink-soft)" }}>
                No documents attached.
              </div>
            )}
            {referral.documents.map((d) => (
              <div className="doc-row" key={d.id}>
                <span>{d.file_name}</span>
                <span className="mono" style={{ fontSize: 11, color: "var(--ink-soft)" }}>
                  {new Date(d.uploaded_at).toLocaleDateString()}
                </span>
              </div>
            ))}
            <div className="upload-row">
              <input type="file" onChange={handleUpload} disabled={uploading} />
              {uploading && <span style={{ fontSize: 12 }}> Uploading…</span>}
            </div>

            <div className="field-label">Audit history</div>
            {referral.events.map((ev) => (
              <div className="event-item" key={ev.id}>
                <div className="event-type">{ev.event_type.replaceAll("_", " ")}</div>
                {ev.detail && <div className="event-detail">{ev.detail}</div>}
                <div className="event-time">
                  {new Date(ev.created_at).toLocaleString()}
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
