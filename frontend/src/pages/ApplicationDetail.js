/**
 * ApplicationDetail page component.
 *
 * Displays full details of a single loan application including
 * applicant info, loan details, eligibility results, and provides
 * actions to update or delete the application.
 */

import React, { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { getApplication, updateApplication, deleteApplication } from "../services/api";
import StatusBadge from "../components/StatusBadge";
import EligibilityResult from "../components/EligibilityResult";

const ApplicationDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [application, setApplication] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({});
  const [saving, setSaving] = useState(false);

  const fetchApplication = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getApplication(id);
      setApplication(data.application);
      setEditForm(data.application);
    } catch (err) {
      setError("Failed to load application details.");
      console.error("Error fetching application:", err);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchApplication();
  }, [fetchApplication]);

  // Handle editing field changes
  const handleEditChange = (field, value) => {
    setEditForm((prev) => ({ ...prev, [field]: value }));
  };

  // Save the edited application
  const handleSave = async () => {
    setSaving(true);
    try {
      const updatedFields = {};
      const editableFields = [
        "applicant_name", "applicant_email", "age", "annual_income",
        "employment_type", "credit_score", "existing_loans",
        "monthly_expenses", "years_of_employment", "has_collateral",
        "dependents", "loan_type", "loan_amount", "loan_term_months", "purpose",
      ];

      for (const field of editableFields) {
        if (editForm[field] !== application[field]) {
          let value = editForm[field];
          // Convert numeric fields
          if (["age", "credit_score", "existing_loans", "dependents", "loan_term_months"].includes(field)) {
            value = parseInt(value);
          } else if (["annual_income", "monthly_expenses", "years_of_employment", "loan_amount"].includes(field)) {
            value = parseFloat(value);
          }
          updatedFields[field] = value;
        }
      }

      if (Object.keys(updatedFields).length === 0) {
        toast.info("No changes to save");
        setEditing(false);
        return;
      }

      await updateApplication(id, updatedFields);
      toast.success("Application updated successfully!");
      setEditing(false);
      // Refresh to get updated data including re-evaluation
      fetchApplication();
    } catch (err) {
      toast.error("Failed to update application");
      console.error("Update error:", err);
    } finally {
      setSaving(false);
    }
  };

  // Handle application deletion
  const handleDelete = async () => {
    if (!window.confirm("Are you sure you want to delete this application? This action cannot be undone.")) {
      return;
    }

    try {
      await deleteApplication(id);
      toast.success("Application deleted successfully");
      navigate("/");
    } catch (err) {
      toast.error("Failed to delete application");
      console.error("Delete error:", err);
    }
  };

  // Format currency for display
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
    }).format(amount || 0);
  };

  // Format date for display
  const formatDate = (dateStr) => {
    if (!dateStr) return "N/A";
    return new Date(dateStr).toLocaleString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (loading) {
    return (
      <div style={styles.centerMessage}>
        <p>Loading application details...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.centerMessage}>
        <p style={{ color: "#dc3545" }}>{error}</p>
        <button onClick={fetchApplication} style={styles.retryBtn}>
          Retry
        </button>
      </div>
    );
  }

  if (!application) {
    return (
      <div style={styles.centerMessage}>
        <p>Application not found</p>
      </div>
    );
  }

  // Render an info row (view mode) or an editable field (edit mode)
  const renderInfoRow = (label, field, type = "text", options = {}) => (
    <div style={styles.infoRow}>
      <span style={styles.infoLabel}>{label}</span>
      {editing ? (
        options.type === "select" ? (
          <select
            value={editForm[field] || ""}
            onChange={(e) => handleEditChange(field, e.target.value)}
            style={styles.editInput}
          >
            {options.choices.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        ) : options.type === "checkbox" ? (
          <input
            type="checkbox"
            checked={editForm[field] || false}
            onChange={(e) => handleEditChange(field, e.target.checked)}
          />
        ) : (
          <input
            type={type}
            value={editForm[field] || ""}
            onChange={(e) => handleEditChange(field, e.target.value)}
            style={styles.editInput}
          />
        )
      ) : (
        <span style={styles.infoValue}>
          {options.format === "currency"
            ? formatCurrency(application[field])
            : options.format === "boolean"
            ? application[field]
              ? "Yes"
              : "No"
            : application[field] || "N/A"}
        </span>
      )}
    </div>
  );

  return (
    <div style={styles.page}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <button onClick={() => navigate("/")} style={styles.backBtn}>
            &larr; Back to Dashboard
          </button>
          <h1 style={styles.title}>{application.applicant_name}</h1>
          <div style={styles.headerMeta}>
            <StatusBadge status={application.status} />
            <span style={styles.appId}>
              ID: {application.application_id?.substring(0, 8)}...
            </span>
            <span style={styles.date}>
              Applied: {formatDate(application.created_at)}
            </span>
          </div>
        </div>
        <div style={styles.actions}>
          {editing ? (
            <>
              <button
                onClick={() => {
                  setEditing(false);
                  setEditForm(application);
                }}
                style={styles.cancelBtn}
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                style={styles.saveBtn}
              >
                {saving ? "Saving..." : "Save Changes"}
              </button>
            </>
          ) : (
            <>
              <button onClick={() => setEditing(true)} style={styles.editBtn}>
                Edit
              </button>
              <button onClick={handleDelete} style={styles.deleteBtn}>
                Delete
              </button>
            </>
          )}
        </div>
      </div>

      {/* Details Grid */}
      <div style={styles.detailsGrid}>
        {/* Personal Information Card */}
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Personal Information</h3>
          {renderInfoRow("Full Name", "applicant_name")}
          {renderInfoRow("Email", "applicant_email")}
          {renderInfoRow("Age", "age", "number")}
          {renderInfoRow("Dependents", "dependents", "number")}
        </div>

        {/* Financial Information Card */}
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Financial Information</h3>
          {renderInfoRow("Annual Income", "annual_income", "number", {
            format: "currency",
          })}
          {renderInfoRow("Monthly Expenses", "monthly_expenses", "number", {
            format: "currency",
          })}
          {renderInfoRow("Credit Score", "credit_score", "number")}
          {renderInfoRow("Existing Loans", "existing_loans", "number")}
          {renderInfoRow("Employment Type", "employment_type", "text", {
            type: "select",
            choices: [
              { value: "salaried", label: "Salaried" },
              { value: "self_employed", label: "Self Employed" },
              { value: "freelancer", label: "Freelancer" },
              { value: "retired", label: "Retired" },
              { value: "unemployed", label: "Unemployed" },
            ],
          })}
          {renderInfoRow("Years of Employment", "years_of_employment", "number")}
          {renderInfoRow("Has Collateral", "has_collateral", "text", {
            type: "checkbox",
            format: "boolean",
          })}
        </div>

        {/* Loan Details Card */}
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Loan Details</h3>
          {renderInfoRow("Loan Type", "loan_type", "text", {
            type: "select",
            choices: [
              { value: "personal", label: "Personal Loan" },
              { value: "home", label: "Home Loan" },
              { value: "auto", label: "Auto Loan" },
              { value: "education", label: "Education Loan" },
            ],
          })}
          {renderInfoRow("Loan Amount", "loan_amount", "number", {
            format: "currency",
          })}
          {renderInfoRow("Loan Term (months)", "loan_term_months", "number")}
          {renderInfoRow("Purpose", "purpose")}
        </div>

        {/* Timestamps Card */}
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Timeline</h3>
          <div style={styles.infoRow}>
            <span style={styles.infoLabel}>Created</span>
            <span style={styles.infoValue}>
              {formatDate(application.created_at)}
            </span>
          </div>
          <div style={styles.infoRow}>
            <span style={styles.infoLabel}>Last Updated</span>
            <span style={styles.infoValue}>
              {formatDate(application.updated_at)}
            </span>
          </div>
        </div>
      </div>

      {/* Eligibility Results */}
      {application.eligibility_result && (
        <EligibilityResult result={application.eligibility_result} />
      )}

      {/* Pending message */}
      {application.status === "pending" && !application.eligibility_result && (
        <div style={styles.pendingBanner}>
          <p style={styles.pendingText}>
            Your application is being processed. The eligibility assessment will
            appear here once complete.
          </p>
          <button onClick={fetchApplication} style={styles.refreshDetailBtn}>
            Check Status
          </button>
        </div>
      )}
    </div>
  );
};

const styles = {
  page: {
    maxWidth: "1200px",
    margin: "0 auto",
    padding: "32px 24px",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    flexWrap: "wrap",
    gap: "16px",
    marginBottom: "32px",
  },
  backBtn: {
    background: "none",
    border: "none",
    color: "#e94560",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
    padding: "0",
    marginBottom: "12px",
    display: "block",
  },
  title: {
    margin: "0 0 8px 0",
    fontSize: "28px",
    fontWeight: "700",
    color: "#1a1a2e",
  },
  headerMeta: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    flexWrap: "wrap",
  },
  appId: {
    fontSize: "13px",
    color: "#6c757d",
    fontFamily: "monospace",
  },
  date: {
    fontSize: "13px",
    color: "#6c757d",
  },
  actions: {
    display: "flex",
    gap: "8px",
  },
  editBtn: {
    padding: "10px 24px",
    borderRadius: "8px",
    border: "1px solid #1a1a2e",
    backgroundColor: "#ffffff",
    color: "#1a1a2e",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
  },
  deleteBtn: {
    padding: "10px 24px",
    borderRadius: "8px",
    border: "none",
    backgroundColor: "#dc3545",
    color: "#ffffff",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
  },
  cancelBtn: {
    padding: "10px 24px",
    borderRadius: "8px",
    border: "1px solid #dee2e6",
    backgroundColor: "#ffffff",
    color: "#6c757d",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
  },
  saveBtn: {
    padding: "10px 24px",
    borderRadius: "8px",
    border: "none",
    backgroundColor: "#28a745",
    color: "#ffffff",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
  },
  detailsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
    gap: "20px",
  },
  card: {
    backgroundColor: "#ffffff",
    borderRadius: "12px",
    padding: "24px",
    boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
    border: "1px solid #f0f0f0",
  },
  cardTitle: {
    margin: "0 0 16px 0",
    fontSize: "16px",
    fontWeight: "600",
    color: "#1a1a2e",
    paddingBottom: "12px",
    borderBottom: "1px solid #f0f0f0",
  },
  infoRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "8px 0",
    borderBottom: "1px solid #fafafa",
  },
  infoLabel: {
    fontSize: "13px",
    color: "#6c757d",
    fontWeight: "500",
  },
  infoValue: {
    fontSize: "14px",
    fontWeight: "600",
    color: "#333",
    textAlign: "right",
  },
  editInput: {
    padding: "6px 10px",
    borderRadius: "6px",
    border: "1px solid #dee2e6",
    fontSize: "13px",
    width: "140px",
    textAlign: "right",
  },
  pendingBanner: {
    marginTop: "24px",
    padding: "24px",
    backgroundColor: "#fff3cd",
    borderRadius: "12px",
    textAlign: "center",
    border: "1px solid #ffc107",
  },
  pendingText: {
    margin: "0 0 12px 0",
    fontSize: "14px",
    color: "#856404",
    fontWeight: "500",
  },
  refreshDetailBtn: {
    padding: "8px 20px",
    borderRadius: "6px",
    border: "none",
    backgroundColor: "#ffc107",
    color: "#856404",
    fontSize: "13px",
    fontWeight: "600",
    cursor: "pointer",
  },
  centerMessage: {
    textAlign: "center",
    padding: "60px 20px",
    color: "#6c757d",
  },
  retryBtn: {
    marginTop: "12px",
    padding: "8px 24px",
    borderRadius: "6px",
    border: "none",
    backgroundColor: "#e94560",
    color: "#ffffff",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
  },
};

export default ApplicationDetail;
