/**
 * Navigation bar component displayed at the top of every page.
 * Provides links to the Dashboard and New Application pages.
 */

import React from "react";
import { Link, useLocation } from "react-router-dom";

const Navbar = () => {
  const location = useLocation();

  // Helper to determine if a nav link is active
  const isActive = (path) => location.pathname === path;

  return (
    <nav style={styles.nav}>
      <div style={styles.container}>
        <Link to="/" style={styles.brand}>
          LoanCheck
        </Link>
        <div style={styles.links}>
          <Link
            to="/"
            style={{
              ...styles.link,
              ...(isActive("/") ? styles.activeLink : {}),
            }}
          >
            Dashboard
          </Link>
          <Link
            to="/apply"
            style={{
              ...styles.link,
              ...styles.applyBtn,
              ...(isActive("/apply") ? styles.activeApply : {}),
            }}
          >
            + New Application
          </Link>
        </div>
      </div>
    </nav>
  );
};

const styles = {
  nav: {
    backgroundColor: "#1a1a2e",
    padding: "0 24px",
    boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
    position: "sticky",
    top: 0,
    zIndex: 1000,
  },
  container: {
    maxWidth: "1200px",
    margin: "0 auto",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    height: "64px",
  },
  brand: {
    color: "#e94560",
    fontSize: "22px",
    fontWeight: "700",
    textDecoration: "none",
    letterSpacing: "1px",
  },
  links: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  link: {
    color: "#a0a0b0",
    textDecoration: "none",
    padding: "8px 16px",
    borderRadius: "6px",
    fontSize: "14px",
    fontWeight: "500",
    transition: "all 0.2s",
  },
  activeLink: {
    color: "#ffffff",
    backgroundColor: "rgba(233,69,96,0.15)",
  },
  applyBtn: {
    color: "#ffffff",
    backgroundColor: "#e94560",
    padding: "8px 20px",
    borderRadius: "6px",
    fontWeight: "600",
  },
  activeApply: {
    backgroundColor: "#c73a52",
  },
};

export default Navbar;
