import React, { useEffect, useState } from "react";
import { api } from "../api.js";

const SPECIALTIES = ["Cardiology", "Dermatology", "Orthopedics", "Endocrinology"];

export default function NewReferralForm({ onClose, onCreated }) {
  const [patients, setPatients] = useState([]);
  const [patientId, setPatientId] = useState("");
  const [specialty, setSpecialty] = useState(SPECIALTIES[0]);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.listPatients().then((data) => {
      setPatients(data);
      if (data.length) setPatientId(data[0].id);
    });
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.createReferral({
        patient_id: patientId,
        specialty_requested: specialty,
        notes: notes || undefined,
      });
      onCreated();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-form" onClick={onClose}>
      <div className="modal-form-inner" onClick={(e) => e.stopPropagation()}>
        <h3>New referral</h3>
        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <label>Patient</label>
            <select value={patientId} onChange={(e) => setPatientId(e.target.value)}>
              {patients.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.first_name} {p.last_name}
                </option>
              ))}
            </select>
          </div>

          <div className="form-row">
            <label>Specialty requested</label>
            <select value={specialty} onChange={(e) => setSpecialty(e.target.value)}>
              {SPECIALTIES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <div className="form-row">
            <label>Notes (optional)</label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Reason for referral, urgency, etc."
            />
          </div>

          {error && <p style={{ color: "var(--rust)", fontSize: 13 }}>{error}</p>}

          <div className="form-actions">
            <button type="button" className="btn secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn" disabled={submitting || !patientId}>
              {submitting ? "Creating…" : "Create referral"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
