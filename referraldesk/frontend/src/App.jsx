import React, { useEffect, useState, useCallback } from "react";
import KanbanBoard from "./components/KanbanBoard.jsx";
import ReferralDetail from "./components/ReferralDetail.jsx";
import NewReferralForm from "./components/NewReferralForm.jsx";
import { api } from "./api.js";

export default function App() {
  const [referrals, setReferrals] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [showNewForm, setShowNewForm] = useState(false);
  const [error, setError] = useState(null);
  const [burstBusy, setBurstBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const data = await api.listReferrals();
      setReferrals(data);
      setError(null);
    } catch (e) {
      setError(
        "Can't reach the API at localhost:8000 — make sure the FastAPI backend is running."
      );
    }
  }, []);

  useEffect(() => {
    refresh();
    // Poll so newly-matched referrals (processed by the background worker)
    // show up on the board without a manual refresh — this is what makes the
    // async matching visible during a demo.
    const interval = setInterval(refresh, 3000);
    return () => clearInterval(interval);
  }, [refresh]);

  async function handleBurst() {
    setBurstBusy(true);
    try {
      await api.simulateBurst(10);
      await refresh();
    } finally {
      setBurstBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <div className="topbar">
        <div>
          <h1>ReferralDesk</h1>
          <div className="subtitle">Referral operations dashboard</div>
        </div>
        <div className="topbar-actions">
          <button className="btn secondary" onClick={handleBurst} disabled={burstBusy}>
            {burstBusy ? "Queuing burst…" : "Simulate 10x burst"}
          </button>
          <button className="btn" onClick={() => setShowNewForm(true)}>
            New referral
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: "12px 28px", color: "var(--rust)", fontSize: 13.5 }}>
          {error}
        </div>
      )}

      <KanbanBoard referrals={referrals} onOpen={setSelectedId} />

      {selectedId && (
        <ReferralDetail
          referralId={selectedId}
          onClose={() => setSelectedId(null)}
          onChanged={refresh}
        />
      )}

      {showNewForm && (
        <NewReferralForm
          onClose={() => setShowNewForm(false)}
          onCreated={() => {
            setShowNewForm(false);
            refresh();
          }}
        />
      )}
    </div>
  );
}
