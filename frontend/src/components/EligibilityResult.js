/**
 * EligibilityResult component displays the detailed eligibility assessment
 * results for a loan application, including score, risk level, and reasons.
 */

import React from "react";

const EligibilityResult = ({ result }) => {
  if (!result) return null;

  const getScoreColor = (score) => {
    if (score >= 65) return "#28a745";
    if (score >= 45) return "#ffc107";
    return "#dc3545";
  };

  const getRiskColor = (level) => {
    const colors = {
      low: "#28a745",
      medium: "#ffc107",
      high: "#fd7e14",
      very_high: "#dc3545",
    };
    return colors[level] || "#6c757d";
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>Eligibility Assessment</h3>

      <div style={styles.grid}>
        {/* Score Circle */}
        <div style={styles.scoreSection}>
          <div
            style={{
              ...styles.scoreCircle,
              borderColor: getScoreColor(result.eligibility_score),
            }}
          >
            <span style={styles.scoreNumber}>
              {Math.round(result.eligibility_score)}
            </span>
            <span style={styles.scoreMax}>/100</span>
          </div>
          <span
            style={{
              ...styles.statusText,
              color: getScoreColor(result.eligibility_score),
            }}
          >
            {result.status?.toUpperCase().replace("_", " ")}
          </span>
        </div>

        {/* Key Metrics */}
        <div style={styles.metricsSection}>
          <div style={styles.metric}>
            <span style={styles.metricLabel}>Risk Level</span>
            <span
              style={{
                ...styles.metricValue,
                color: getRiskColor(result.risk_level),
              }}
            >
              {result.risk_level?.toUpperCase().replace("_", " ")}
            </span>
          </div>
          <div style={styles.metric}>
            <span style={styles.metricLabel}>Max Eligible Amount</span>
            <span style={styles.metricValue}>
              {formatCurrency(result.max_eligible_amount)}
            </span>
          </div>
          <div style={styles.metric}>
            <span style={styles.metricLabel}>Recommended Rate</span>
            <span style={styles.metricValue}>
              {(result.recommended_interest_rate * 100).toFixed(2)}%
            </span>
          </div>
        </div>
      </div>

      {/* Reasons */}
      {result.reasons && result.reasons.length > 0 && (
        <div style={styles.section}>
          <h4 style={styles.sectionTitle}>Assessment Details</h4>
          {result.reasons.map((reason, idx) => (
            <div key={idx} style={styles.reasonItem}>
              <span style={styles.bullet}>&#8226;</span>
              <span style={styles.reasonText}>{reason}</span>
            </div>
          ))}
        </div>
      )}

      {/* Conditions (for conditional approvals) */}
      {result.conditions && result.conditions.length > 0 && (
        <div style={{ ...styles.section, ...styles.conditionsSection }}>
          <h4 style={styles.sectionTitle}>Conditions to Meet</h4>
          {result.conditions.map((condition, idx) => (
            <div key={idx} style={styles.conditionItem}>
              <span style={styles.conditionIcon}>!</span>
              <span style={styles.reasonText}>{condition}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const styles = {
  container: {
    backgroundColor: "#f8f9fa",
    borderRadius: "12px",
    padding: "24px",
    marginTop: "20px",
    border: "1px solid #e9ecef",
  },
  title: {
    margin: "0 0 20px 0",
    fontSize: "18px",
    fontWeight: "700",
    color: "#1a1a2e",
  },
  grid: {
    display: "flex",
    gap: "32px",
    alignItems: "flex-start",
    flexWrap: "wrap",
  },
  scoreSection: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "8px",
  },
  scoreCircle: {
    width: "100px",
    height: "100px",
    borderRadius: "50%",
    border: "4px solid",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#ffffff",
  },
  scoreNumber: {
    fontSize: "28px",
    fontWeight: "700",
    color: "#333",
    lineHeight: "1",
  },
  scoreMax: {
    fontSize: "12px",
    color: "#999",
  },
  statusText: {
    fontSize: "14px",
    fontWeight: "700",
    letterSpacing: "0.5px",
  },
  metricsSection: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  metric: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "10px 16px",
    backgroundColor: "#ffffff",
    borderRadius: "8px",
    border: "1px solid #e9ecef",
  },
  metricLabel: {
    fontSize: "13px",
    color: "#6c757d",
    fontWeight: "500",
  },
  metricValue: {
    fontSize: "15px",
    fontWeight: "700",
    color: "#333",
  },
  section: {
    marginTop: "20px",
    paddingTop: "16px",
    borderTop: "1px solid #e9ecef",
  },
  conditionsSection: {
    backgroundColor: "#fff8e1",
    margin: "20px -24px -24px",
    padding: "16px 24px 24px",
    borderRadius: "0 0 12px 12px",
    borderTop: "2px solid #ffc107",
  },
  sectionTitle: {
    margin: "0 0 12px 0",
    fontSize: "14px",
    fontWeight: "600",
    color: "#333",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  reasonItem: {
    display: "flex",
    alignItems: "flex-start",
    gap: "8px",
    marginBottom: "6px",
  },
  bullet: {
    color: "#6c757d",
    fontSize: "16px",
    lineHeight: "1.4",
  },
  reasonText: {
    fontSize: "13px",
    color: "#555",
    lineHeight: "1.4",
  },
  conditionItem: {
    display: "flex",
    alignItems: "flex-start",
    gap: "8px",
    marginBottom: "6px",
  },
  conditionIcon: {
    color: "#856404",
    fontWeight: "700",
    fontSize: "14px",
    backgroundColor: "#ffc107",
    width: "20px",
    height: "20px",
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  },
};

export default EligibilityResult;
