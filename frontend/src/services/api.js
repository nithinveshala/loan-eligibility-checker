/**
 * API service layer for the Loan Eligibility Checker frontend.
 *
 * Provides functions to interact with the backend REST API through
 * API Gateway. All functions return promises that resolve to the
 * response data.
 */

import axios from "axios";

// Base URL - uses relative /api path when served from the same EC2 instance,
// or an absolute URL when configured via environment variable
const API_BASE_URL = process.env.REACT_APP_API_URL || "/api";

// Create an axios instance with default configuration
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
});

/**
 * Create a new loan application.
 * @param {Object} applicationData - The loan application form data.
 * @returns {Promise<Object>} The created application response with ID.
 */
export const createApplication = async (applicationData) => {
  const response = await api.post("/applications", applicationData);
  return response.data;
};

/**
 * Retrieve all loan applications with optional filters.
 * @param {Object} filters - Optional query parameters (status, loan_type).
 * @returns {Promise<Object>} Object containing applications array and count.
 */
export const getApplications = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.status) params.append("status", filters.status);
  if (filters.loan_type) params.append("loan_type", filters.loan_type);

  const response = await api.get(`/applications?${params.toString()}`);
  return response.data;
};

/**
 * Retrieve a single loan application by its ID.
 * @param {string} id - The application ID.
 * @returns {Promise<Object>} The full application details.
 */
export const getApplication = async (id) => {
  const response = await api.get(`/applications/${id}`);
  return response.data;
};

/**
 * Update an existing loan application.
 * @param {string} id - The application ID to update.
 * @param {Object} updateData - The fields to update.
 * @returns {Promise<Object>} The updated application response.
 */
export const updateApplication = async (id, updateData) => {
  const response = await api.put(`/applications/${id}`, updateData);
  return response.data;
};

/**
 * Delete a loan application.
 * @param {string} id - The application ID to delete.
 * @returns {Promise<Object>} Deletion confirmation response.
 */
export const deleteApplication = async (id) => {
  const response = await api.delete(`/applications/${id}`);
  return response.data;
};

export default api;
