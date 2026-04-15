/**
 * ApplicationCard component renders a summary card for a loan application.
 * Used on the Dashboard page to display each application in a grid layout.
 */

import React from "react";
import { useNavigate } from "react-router-dom";
import StatusBadge from "./StatusBadge";

const ApplicationCard = ({ application }) => {
  const navigate = useNavigate();

  // Format currency values for display
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
    }).format(amount);
  };

  // Format date string for display
  const formatDate = (dateStr) => {
    if (!dateStr) return "N/A";
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <div
      style={styles.card}
      onClick={() => navigate(`/application/${application.application_id}`)}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = "translateY(-2px)";
        e.currentTarget.style.boxShadow = "0 6px 20px rgba(0,0,0,0.12)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = "translateY(0)";
        e.currentTarget.style.boxShadow = "0 2px 8px rgba(0,0,0,0.06)";
      }}
    >
      <div style={styles.header}>
        <span style={styles.loanType}>{application.loan_type} Loan</span>
        <StatusBadge status={application.status} />
      </div>

      <h3 style={styles.name}>{application.applicant_name}</h3>

      <div style={styles.details}>
        <div style={styles.detailRow}>
          <span style={styles.label}>Amount</span>
          <span style={styles.value}>
            {formatCurrency(application.loan_amount)}
          </span>
        </div>
        <div style={styles.detailRow}>
          <span style={styles.label}>Term</span>
          <span style={styles.value}>
            {application.loan_term_months} months
          </span>
        </div>
        <div style={styles.detailRow}>
          <span style={styles.label}>Credit Score</span>
          <span style={styles.value}>{application.credit_score}</span>
        </div>
        <div style={styles.detailRow}>
          <span style={styles.label}>Income</span>
          <span style={styles.value}>
            {formatCurrency(application.annual_income)}
          </span>
        </div>
      </div>

      {application.eligibility_result && (
        <div style={styles.scoreBar}>
          <span style={styles.scoreLabel}>Eligibility Score</span>
          <div style={styles.progressBg}>
            <div
              style={{
                ...styles.progressFill,
                width: `${application.eligibility_result.eligibility_score}%`,
                backgroundColor:
                  application.eligibility_result.eligibility_score >= 65
                    ? "#28a745"
                    : application.eligibility_result.eligibility_score >= 45
                    ? "#ffc107"
                    : "#dc3545",
              }}
            />
          </div>
          <span style={styles.scoreValue}>
            {application.eligibility_result.eligibility_score}/100
          </span>
        </div>
      )}

      <div style={styles.footer}>
        <span style={styles.date}>
          Applied: {formatDate(application.created_at)}
        </span>
        <span style={styles.viewLink}>View Details &rarr;</span>
      </div>
    </div>
  );
};

const styles = {
  card: {
    backgroundColor: "#ffffff",
    borderRadius: "12px",
    padding: "20px",
    boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
    cursor: "pointer",
    transition: "all 0.2s ease",
    border: "1px solid #f0f0f0",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "12px",
  },
  loanType: {
    fontSize: "12px",
    fontWeight: "600",
    color: "#6c757d",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  name: {
    margin: "0 0 16px 0",
    fontSize: "18px",
    fontWeight: "600",
    color: "#1a1a2e",
  },
  details: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "8px",
    marginBottom: "16px",
  },
  detailRow: {
    display: "flex",
    flexDirection: "column",
    gap: "2px",
  },
  label: {
    fontSize: "11px",
    color: "#999",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  value: {
    fontSize: "14px",
    fontWeight: "600",
    color: "#333",
  },
  scoreBar: {
    marginBottom: "16px",
  },
  scoreLabel: {
    fontSize: "11px",
    color: "#999",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  progressBg: {
    height: "6px",
    backgroundColor: "#f0f0f0",
    borderRadius: "3px",
    marginTop: "4px",
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    borderRadius: "3px",
    transition: "width 0.5s ease",
  },
  scoreValue: {
    fontSize: "12px",
    fontWeight: "600",
    color: "#333",
    marginTop: "2px",
    display: "inline-block",
  },
  footer: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    paddingTop: "12px",
    borderTop: "1px solid #f0f0f0",
  },
  date: {
    fontSize: "12px",
    color: "#999",
  },
  viewLink: {
    fontSize: "13px",
    color: "#e94560",
    fontWeight: "600",
  },
};

export default ApplicationCard;
