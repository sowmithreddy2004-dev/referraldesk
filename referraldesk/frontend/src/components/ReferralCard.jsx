import React from "react";

export default function ReferralCard({ referral, onOpen }) {
  const patient = referral.patient;
  return (
    <button className="referral-card" onClick={() => onOpen(referral.id)}>
      <div className="patient-name">
        {patient.first_name} {patient.last_name}
      </div>
      <div className="specialty">{referral.specialty_requested}</div>
      <div className="meta-row">
        <span className="mono">#{referral.id.slice(0, 8)}</span>
        <span>{new Date(referral.created_at).toLocaleDateString()}</span>
      </div>
    </button>
  );
}
