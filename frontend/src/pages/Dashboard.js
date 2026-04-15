/**
 * Dashboard page component.
 *
 * Displays a summary of all loan applications in a responsive grid layout
 * with filtering options by status and loan type. Shows statistics at the top.
 */

import React, { useState, useEffect } from "react";
import { getApplications } from "../services/api";
import ApplicationCard from "../components/ApplicationCard";

const Dashboard = () => {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  // Fetch applications when component mounts or filters change
  useEffect(() => {
    fetchApplications();
  }, [statusFilter, typeFilter]);

  const fetchApplications = async () => {
    setLoading(true);
    setError(null);
    try {
      const filters = {};
      if (statusFilter) filters.status = statusFilter;
      if (typeFilter) filters.loan_type = typeFilter;

      const data = await getApplications(filters);
      setApplications(data.applications || []);
    } catch (err) {
      setError("Failed to load applications. Please check your connection.");
      console.error("Error fetching applications:", err);
    } finally {
      setLoading(false);
    }
  };

  // Calculate statistics from the current applications list
  const stats = {
    total: applications.length,
    approved: applications.filter((a) => a.status === "approved").length,
    pending: applications.filter((a) => a.status === "pending").length,
    denied: applications.filter((a) => a.status === "denied").length,
  };

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <h1 style={styles.title}>Loan Applications Dashboard</h1>
        <p style={styles.subtitle}>
          Monitor and manage all loan applications in one place
        </p>
      </div>

      {/* Statistics Cards */}
      <div style={styles.statsGrid}>
        <div style={{ ...styles.statCard, borderTopColor: "#6c63ff" }}>
          <span style={styles.statNumber}>{stats.total}</span>
          <span style={styles.statLabel}>Total Applications</span>
        </div>
        <div style={{ ...styles.statCard, borderTopColor: "#28a745" }}>
          <span style={{ ...styles.statNumber, color: "#28a745" }}>
            {stats.approved}
          </span>
          <span style={styles.statLabel}>Approved</span>
        </div>
        <div style={{ ...styles.statCard, borderTopColor: "#ffc107" }}>
          <span style={{ ...styles.statNumber, color: "#ffc107" }}>
            {stats.pending}
          </span>
          <span style={styles.statLabel}>Pending</span>
        </div>
        <div style={{ ...styles.statCard, borderTopColor: "#dc3545" }}>
          <span style={{ ...styles.statNumber, color: "#dc3545" }}>
            {stats.denied}
          </span>
          <span style={styles.statLabel}>Denied</span>
        </div>
      </div>

      {/* Filters */}
      <div style={styles.filters}>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={styles.select}
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="conditional">Conditional</option>
          <option value="denied">Denied</option>
          <option value="under_review">Under Review</option>
        </select>

        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          style={styles.select}
        >
          <option value="">All Loan Types</option>
          <option value="personal">Personal</option>
          <option value="home">Home</option>
          <option value="auto">Auto</option>
          <option value="education">Education</option>
        </select>

        <button onClick={fetchApplications} style={styles.refreshBtn}>
          Refresh
        </button>
      </div>

      {/* Applications Grid */}
      {loading ? (
        <div style={styles.centerMessage}>
          <div style={styles.spinner}></div>
          <p>Loading applications...</p>
        </div>
      ) : error ? (
        <div style={styles.errorMessage}>
          <p>{error}</p>
          <button onClick={fetchApplications} style={styles.retryBtn}>
            Retry
          </button>
        </div>
      ) : applications.length === 0 ? (
        <div style={styles.centerMessage}>
          <p style={styles.emptyText}>No applications found</p>
          <p style={styles.emptySubtext}>
            Create a new application to get started
          </p>
        </div>
      ) : (
        <div style={styles.grid}>
          {applications.map((app) => (
            <ApplicationCard key={app.application_id} application={app} />
          ))}
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
    marginBottom: "32px",
  },
  title: {
    margin: 0,
    fontSize: "28px",
    fontWeight: "700",
    color: "#1a1a2e",
  },
  subtitle: {
    margin: "8px 0 0",
    fontSize: "15px",
    color: "#6c757d",
  },
  statsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
    gap: "16px",
    marginBottom: "32px",
  },
  statCard: {
    backgroundColor: "#ffffff",
    padding: "20px",
    borderRadius: "12px",
    boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
    borderTop: "3px solid",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "4px",
  },
  statNumber: {
    fontSize: "32px",
    fontWeight: "700",
    color: "#6c63ff",
  },
  statLabel: {
    fontSize: "13px",
    color: "#6c757d",
    fontWeight: "500",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  filters: {
    display: "flex",
    gap: "12px",
    marginBottom: "24px",
    flexWrap: "wrap",
  },
  select: {
    padding: "10px 16px",
    borderRadius: "8px",
    border: "1px solid #dee2e6",
    backgroundColor: "#ffffff",
    fontSize: "14px",
    color: "#333",
    cursor: "pointer",
    outline: "none",
  },
  refreshBtn: {
    padding: "10px 20px",
    borderRadius: "8px",
    border: "none",
    backgroundColor: "#1a1a2e",
    color: "#ffffff",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
    gap: "20px",
  },
  centerMessage: {
    textAlign: "center",
    padding: "60px 20px",
    color: "#6c757d",
  },
  spinner: {
    width: "40px",
    height: "40px",
    border: "4px solid #f0f0f0",
    borderTop: "4px solid #e94560",
    borderRadius: "50%",
    animation: "spin 0.8s linear infinite",
    margin: "0 auto 16px",
  },
  errorMessage: {
    textAlign: "center",
    padding: "40px 20px",
    color: "#dc3545",
    backgroundColor: "#f8d7da",
    borderRadius: "12px",
  },
  retryBtn: {
    marginTop: "12px",
    padding: "8px 24px",
    borderRadius: "6px",
    border: "none",
    backgroundColor: "#dc3545",
    color: "#ffffff",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
  },
  emptyText: {
    fontSize: "18px",
    fontWeight: "600",
    color: "#333",
    margin: 0,
  },
  emptySubtext: {
    fontSize: "14px",
    color: "#999",
    margin: "8px 0 0",
  },
};

export default Dashboard;
