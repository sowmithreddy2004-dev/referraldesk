import React from "react";
import ReferralCard from "./ReferralCard.jsx";

const COLUMNS = [
  { key: "New", label: "New", color: "#0e6b62" },
  { key: "Matching", label: "Matching", color: "#a97a1f" },
  { key: "Scheduled", label: "Scheduled", color: "#0e6b62" },
  { key: "Completed", label: "Completed", color: "#5b6663" },
  { key: "Overdue", label: "Overdue", color: "#b54a34" },
];

export default function KanbanBoard({ referrals, onOpen }) {
  return (
    <div className="board">
      {COLUMNS.map((col) => {
        const items = referrals.filter((r) => r.status === col.key);
        return (
          <div className="column" key={col.key} style={{ "--col-color": col.color }}>
            <div className="column-header">
              <span className="title">{col.label}</span>
              <span className="count mono">{items.length}</span>
            </div>
            <div className="column-body">
              {items.length === 0 && (
                <div className="empty-column">No referrals here</div>
              )}
              {items.map((r) => (
                <ReferralCard key={r.id} referral={r} onOpen={onOpen} />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
