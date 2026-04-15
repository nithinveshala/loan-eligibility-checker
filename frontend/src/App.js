/**
 * Root application component.
 *
 * Sets up routing, navigation, and toast notifications for the
 * Loan Eligibility Checker single-page application.
 */

import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

import Navbar from "./components/Navbar";
import Dashboard from "./pages/Dashboard";
import NewApplication from "./pages/NewApplication";
import ApplicationDetail from "./pages/ApplicationDetail";

function App() {
  return (
    <Router>
      <div style={styles.app}>
        <Navbar />
        <main style={styles.main}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/apply" element={<NewApplication />} />
            <Route path="/application/:id" element={<ApplicationDetail />} />
          </Routes>
        </main>
        <ToastContainer
          position="top-right"
          autoClose={4000}
          hideProgressBar={false}
          newestOnTop
          closeOnClick
          pauseOnHover
          theme="colored"
        />
      </div>
    </Router>
  );
}

const styles = {
  app: {
    minHeight: "100vh",
    backgroundColor: "#f5f6fa",
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  },
  main: {
    minHeight: "calc(100vh - 64px)",
  },
};

export default App;
