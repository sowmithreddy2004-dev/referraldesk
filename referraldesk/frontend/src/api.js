const API_BASE = "http://localhost:8000/api";

async function handle(res) {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export const api = {
  listReferrals: () => fetch(`${API_BASE}/referrals`).then(handle),
  getReferral: (id) => fetch(`${API_BASE}/referrals/${id}`).then(handle),
  listPatients: () => fetch(`${API_BASE}/patients`).then(handle),

  createReferral: (payload) =>
    fetch(`${API_BASE}/referrals`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(handle),

  updateStatus: (id, status) =>
    fetch(`${API_BASE}/referrals/${id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    }).then(handle),

  uploadDocument: (id, file) => {
    const formData = new FormData();
    formData.append("file", file);
    return fetch(`${API_BASE}/referrals/${id}/documents`, {
      method: "POST",
      body: formData,
    }).then(handle);
  },

  fetchFromEhr: (ehrPatientId) =>
    fetch(`${API_BASE}/ehr/patients/${ehrPatientId}`).then(handle),

  simulateBurst: (count) =>
    fetch(`${API_BASE}/demo/simulate-burst?count=${count}`, { method: "POST" }).then(handle),
};
