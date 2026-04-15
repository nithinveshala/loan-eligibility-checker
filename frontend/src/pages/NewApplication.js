/**
 * NewApplication page component.
 *
 * Provides a multi-section form for submitting a new loan application.
 * Includes client-side validation and submits data to the backend API.
 */

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { createApplication } from "../services/api";

const INITIAL_FORM = {
  applicant_name: "",
  applicant_email: "",
  age: "",
  annual_income: "",
  employment_type: "salaried",
  credit_score: "",
  existing_loans: "0",
  monthly_expenses: "",
  years_of_employment: "",
  has_collateral: false,
  dependents: "0",
  loan_type: "personal",
  loan_amount: "",
  loan_term_months: "",
  purpose: "",
};

const NewApplication = () => {
  const navigate = useNavigate();
  const [form, setForm] = useState(INITIAL_FORM);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  // Handle form field changes
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
    // Clear error for the field being edited
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: "" }));
    }
  };

  // Client-side validation
  const validate = () => {
    const newErrors = {};

    if (!form.applicant_name.trim())
      newErrors.applicant_name = "Name is required";
    if (!form.age || parseInt(form.age) < 18 || parseInt(form.age) > 70)
      newErrors.age = "Age must be between 18 and 70";
    if (!form.annual_income || parseFloat(form.annual_income) <= 0)
      newErrors.annual_income = "Annual income must be positive";
    if (
      !form.credit_score ||
      parseInt(form.credit_score) < 300 ||
      parseInt(form.credit_score) > 900
    )
      newErrors.credit_score = "Credit score must be between 300 and 900";
    if (!form.loan_amount || parseFloat(form.loan_amount) < 1000)
      newErrors.loan_amount = "Loan amount must be at least 1,000";
    if (
      !form.loan_term_months ||
      parseInt(form.loan_term_months) < 1 ||
      parseInt(form.loan_term_months) > 360
    )
      newErrors.loan_term_months = "Loan term must be 1-360 months";
    if (!form.monthly_expenses || parseFloat(form.monthly_expenses) < 0)
      newErrors.monthly_expenses = "Monthly expenses cannot be negative";
    if (!form.years_of_employment || parseFloat(form.years_of_employment) < 0)
      newErrors.years_of_employment = "Employment years cannot be negative";

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    try {
      // Convert string values to proper types for the API
      const payload = {
        ...form,
        age: parseInt(form.age),
        annual_income: parseFloat(form.annual_income),
        credit_score: parseInt(form.credit_score),
        existing_loans: parseInt(form.existing_loans),
        monthly_expenses: parseFloat(form.monthly_expenses),
        years_of_employment: parseFloat(form.years_of_employment),
        dependents: parseInt(form.dependents),
        loan_amount: parseFloat(form.loan_amount),
        loan_term_months: parseInt(form.loan_term_months),
      };

      const result = await createApplication(payload);
      toast.success("Application submitted successfully!");
      navigate(`/application/${result.application_id}`);
    } catch (err) {
      const message =
        err.response?.data?.error || "Failed to submit application";
      toast.error(message);
      console.error("Submission error:", err);
    } finally {
      setSubmitting(false);
    }
  };

  // Render a form field with label and error display
  const renderField = (label, name, type = "text", options = {}) => (
    <div style={styles.field}>
      <label style={styles.label} htmlFor={name}>
        {label}
        {options.required !== false && <span style={styles.required}>*</span>}
      </label>
      {options.type === "select" ? (
        <select
          id={name}
          name={name}
          value={form[name]}
          onChange={handleChange}
          style={{
            ...styles.input,
            ...(errors[name] ? styles.inputError : {}),
          }}
        >
          {options.choices.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      ) : options.type === "checkbox" ? (
        <label style={styles.checkboxLabel}>
          <input
            type="checkbox"
            name={name}
            checked={form[name]}
            onChange={handleChange}
            style={styles.checkbox}
          />
          {options.checkboxText || "Yes"}
        </label>
      ) : (
        <input
          id={name}
          name={name}
          type={type}
          value={form[name]}
          onChange={handleChange}
          placeholder={options.placeholder || ""}
          min={options.min}
          max={options.max}
          step={options.step}
          style={{
            ...styles.input,
            ...(errors[name] ? styles.inputError : {}),
          }}
        />
      )}
      {errors[name] && <span style={styles.errorText}>{errors[name]}</span>}
    </div>
  );

  return (
    <div style={styles.page}>
      <div style={styles.formContainer}>
        <h1 style={styles.title}>New Loan Application</h1>
        <p style={styles.subtitle}>
          Fill in the details below to submit a loan application for eligibility
          assessment.
        </p>

        <form onSubmit={handleSubmit}>
          {/* Personal Information Section */}
          <div style={styles.section}>
            <h2 style={styles.sectionTitle}>Personal Information</h2>
            <div style={styles.fieldGrid}>
              {renderField("Full Name", "applicant_name", "text", {
                placeholder: "John Doe",
              })}
              {renderField("Email Address", "applicant_email", "email", {
                placeholder: "john@example.com",
                required: false,
              })}
              {renderField("Age", "age", "number", {
                placeholder: "30",
                min: 18,
                max: 70,
              })}
              {renderField("Number of Dependents", "dependents", "number", {
                placeholder: "0",
                min: 0,
                required: false,
              })}
            </div>
          </div>

          {/* Financial Information Section */}
          <div style={styles.section}>
            <h2 style={styles.sectionTitle}>Financial Information</h2>
            <div style={styles.fieldGrid}>
              {renderField("Annual Income ($)", "annual_income", "number", {
                placeholder: "75000",
                min: 0,
                step: "1000",
              })}
              {renderField("Monthly Expenses ($)", "monthly_expenses", "number", {
                placeholder: "2000",
                min: 0,
                step: "100",
              })}
              {renderField("Credit Score", "credit_score", "number", {
                placeholder: "720",
                min: 300,
                max: 900,
              })}
              {renderField("Existing Loans", "existing_loans", "number", {
                placeholder: "0",
                min: 0,
                required: false,
              })}
              {renderField("Employment Type", "employment_type", "text", {
                type: "select",
                choices: [
                  { value: "salaried", label: "Salaried" },
                  { value: "self_employed", label: "Self Employed" },
                  { value: "freelancer", label: "Freelancer" },
                  { value: "retired", label: "Retired" },
                  { value: "unemployed", label: "Unemployed" },
                ],
              })}
              {renderField(
                "Years of Employment",
                "years_of_employment",
                "number",
                { placeholder: "5", min: 0, step: "0.5" }
              )}
              {renderField("Collateral Available", "has_collateral", "text", {
                type: "checkbox",
                checkboxText: "I can provide collateral for this loan",
                required: false,
              })}
            </div>
          </div>

          {/* Loan Details Section */}
          <div style={styles.section}>
            <h2 style={styles.sectionTitle}>Loan Details</h2>
            <div style={styles.fieldGrid}>
              {renderField("Loan Type", "loan_type", "text", {
                type: "select",
                choices: [
                  { value: "personal", label: "Personal Loan" },
                  { value: "home", label: "Home Loan" },
                  { value: "auto", label: "Auto Loan" },
                  { value: "education", label: "Education Loan" },
                ],
              })}
              {renderField("Loan Amount ($)", "loan_amount", "number", {
                placeholder: "50000",
                min: 1000,
                step: "1000",
              })}
              {renderField("Loan Term (months)", "loan_term_months", "number", {
                placeholder: "60",
                min: 1,
                max: 360,
              })}
              {renderField("Purpose", "purpose", "text", {
                placeholder: "e.g., Home purchase, Car purchase, Education",
                required: false,
              })}
            </div>
          </div>

          {/* Submit Button */}
          <div style={styles.actions}>
            <button
              type="button"
              onClick={() => navigate("/")}
              style={styles.cancelBtn}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              style={{
                ...styles.submitBtn,
                ...(submitting ? styles.submitBtnDisabled : {}),
              }}
            >
              {submitting ? "Submitting..." : "Submit Application"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const styles = {
  page: {
    maxWidth: "900px",
    margin: "0 auto",
    padding: "32px 24px",
  },
  formContainer: {
    backgroundColor: "#ffffff",
    borderRadius: "16px",
    padding: "40px",
    boxShadow: "0 4px 12px rgba(0,0,0,0.06)",
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
  section: {
    marginTop: "32px",
    paddingTop: "24px",
    borderTop: "1px solid #f0f0f0",
  },
  sectionTitle: {
    margin: "0 0 20px 0",
    fontSize: "18px",
    fontWeight: "600",
    color: "#1a1a2e",
  },
  fieldGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
    gap: "20px",
  },
  field: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  label: {
    fontSize: "13px",
    fontWeight: "600",
    color: "#333",
  },
  required: {
    color: "#e94560",
    marginLeft: "4px",
  },
  input: {
    padding: "10px 14px",
    borderRadius: "8px",
    border: "1px solid #dee2e6",
    fontSize: "14px",
    color: "#333",
    outline: "none",
    transition: "border-color 0.2s",
    backgroundColor: "#fafafa",
  },
  inputError: {
    borderColor: "#dc3545",
    backgroundColor: "#fff5f5",
  },
  errorText: {
    fontSize: "12px",
    color: "#dc3545",
    fontWeight: "500",
  },
  checkboxLabel: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    fontSize: "14px",
    color: "#555",
    cursor: "pointer",
    padding: "8px 0",
  },
  checkbox: {
    width: "18px",
    height: "18px",
    cursor: "pointer",
  },
  actions: {
    marginTop: "40px",
    display: "flex",
    justifyContent: "flex-end",
    gap: "12px",
    paddingTop: "24px",
    borderTop: "1px solid #f0f0f0",
  },
  cancelBtn: {
    padding: "12px 28px",
    borderRadius: "8px",
    border: "1px solid #dee2e6",
    backgroundColor: "#ffffff",
    color: "#6c757d",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
  },
  submitBtn: {
    padding: "12px 32px",
    borderRadius: "8px",
    border: "none",
    backgroundColor: "#e94560",
    color: "#ffffff",
    fontSize: "14px",
    fontWeight: "700",
    cursor: "pointer",
    transition: "background-color 0.2s",
  },
  submitBtnDisabled: {
    backgroundColor: "#ccc",
    cursor: "not-allowed",
  },
};

export default NewApplication;
