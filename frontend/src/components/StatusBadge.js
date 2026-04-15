/**
 * StatusBadge component displays a colored badge for application status.
 * Each status has a distinct color for quick visual identification.
 */

import React from "react";

const STATUS_STYLES = {
  pending: { backgroundColor: "#fff3cd", color: "#856404", label: "Pending" },
  approved: { backgroundColor: "#d4edda", color: "#155724", label: "Approved" },
  denied: { backgroundColor: "#f8d7da", color: "#721c24", label: "Denied" },
  conditional: { backgroundColor: "#d1ecf1", color: "#0c5460", label: "Conditional" },
  under_review: { backgroundColor: "#e2e3f1", color: "#383d6e", label: "Under Review" },
  withdrawn: { backgroundColor: "#e2e2e2", color: "#6c757d", label: "Withdrawn" },
};

const StatusBadge = ({ status }) => {
  const config = STATUS_STYLES[status] || STATUS_STYLES.pending;

  return (
    <span
      style={{
        ...styles.badge,
        backgroundColor: config.backgroundColor,
        color: config.color,
      }}
    >
      {config.label}
    </span>
  );
};

const styles = {
  badge: {
    padding: "4px 12px",
    borderRadius: "12px",
    fontSize: "12px",
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
    display: "inline-block",
  },
};

export default StatusBadge;
