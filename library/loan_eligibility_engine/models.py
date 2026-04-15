"""
Data models for the Loan Eligibility Engine.

This module defines the core data structures used throughout the library
for representing loan applicants, applications, and eligibility decisions.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime, timezone


class LoanType(Enum):
    """Enumeration of supported loan types with associated base interest rates."""
    PERSONAL = "personal"
    HOME = "home"
    AUTO = "auto"
    EDUCATION = "education"


class EmploymentType(Enum):
    """Enumeration of employment categories for income stability assessment."""
    SALARIED = "salaried"
    SELF_EMPLOYED = "self_employed"
    FREELANCER = "freelancer"
    UNEMPLOYED = "unemployed"
    RETIRED = "retired"


class RiskLevel(Enum):
    """Risk classification levels for loan applications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class DecisionStatus(Enum):
    """Possible outcomes of a loan eligibility assessment."""
    APPROVED = "approved"
    CONDITIONAL = "conditional"
    DENIED = "denied"
    PENDING_REVIEW = "pending_review"


@dataclass
class Applicant:
    """
    Represents a loan applicant with personal and financial information.

    Attributes:
        name: Full name of the applicant.
        age: Age of the applicant in years.
        annual_income: Gross annual income in the applicants currency.
        employment_type: Category of employment for income stability scoring.
        credit_score: Credit score ranging from 300 to 900.
        existing_loans: Number of currently active loans.
        monthly_expenses: Total recurring monthly expenses.
        years_of_employment: Duration of current employment in years.
        has_collateral: Whether the applicant can provide collateral.
        dependents: Number of financial dependents.
    """
    name: str
    age: int
    annual_income: float
    employment_type: EmploymentType
    credit_score: int
    existing_loans: int = 0
    monthly_expenses: float = 0.0
    years_of_employment: float = 0.0
    has_collateral: bool = False
    dependents: int = 0

    @property
    def monthly_income(self) -> float:
        """Calculate the monthly income from annual income."""
        return self.annual_income / 12.0

    @property
    def debt_to_income_ratio(self) -> float:
        """Calculate the debt-to-income ratio as a percentage."""
        if self.monthly_income == 0:
            return 100.0
        return (self.monthly_expenses / self.monthly_income) * 100.0


@dataclass
class LoanApplication:
    """
    Represents a complete loan application combining applicant data with loan details.

    Attributes:
        applicant: The Applicant object containing personal and financial data.
        loan_type: The category of loan being requested.
        loan_amount: The total amount of money requested.
        loan_term_months: Requested duration of the loan in months.
        purpose: A brief description of the intended use of the loan funds.
        application_id: Unique identifier assigned to this application.
        application_date: Timestamp when the application was submitted.
    """
    applicant: Applicant
    loan_type: LoanType
    loan_amount: float
    loan_term_months: int
    purpose: str = ""
    application_id: Optional[str] = None
    application_date: Optional[str] = None

    @property
    def loan_to_income_ratio(self) -> float:
        """Calculate the ratio of loan amount to annual income."""
        if self.applicant.annual_income == 0:
            return float("inf")
        return self.loan_amount / self.applicant.annual_income

    @property
    def monthly_payment_estimate(self) -> float:
        """Estimate the monthly payment using a simplified calculation."""
        if self.loan_term_months == 0:
            return self.loan_amount
        # Simplified monthly payment estimate (principal / months + basic interest factor)
        base_rate = {
            LoanType.PERSONAL: 0.12,
            LoanType.HOME: 0.07,
            LoanType.AUTO: 0.09,
            LoanType.EDUCATION: 0.06,
        }
        rate = base_rate.get(self.loan_type, 0.10)
        monthly_rate = rate / 12.0
        # Amortization formula: P * [r(1+r)^n] / [(1+r)^n - 1]
        if monthly_rate == 0:
            return self.loan_amount / self.loan_term_months
        factor = (1 + monthly_rate) ** self.loan_term_months
        return self.loan_amount * (monthly_rate * factor) / (factor - 1)


@dataclass
class LoanDecision:
    """
    Represents the outcome of a loan eligibility assessment.

    Attributes:
        status: The eligibility decision (approved, denied, conditional, pending).
        eligibility_score: Numerical score from 0 to 100 indicating overall eligibility.
        risk_level: Assessed risk level associated with this application.
        max_eligible_amount: Maximum loan amount the applicant qualifies for.
        recommended_interest_rate: Suggested annual interest rate based on risk profile.
        reasons: List of human-readable explanations supporting the decision.
        conditions: Any conditions that must be met for conditional approvals.
        assessed_at: Timestamp of when the assessment was performed.
    """
    status: DecisionStatus
    eligibility_score: float
    risk_level: RiskLevel
    max_eligible_amount: float
    recommended_interest_rate: float
    reasons: list = field(default_factory=list)
    conditions: list = field(default_factory=list)
    assessed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        """Convert the decision to a dictionary for serialization."""
        return {
            "status": self.status.value,
            "eligibility_score": round(self.eligibility_score, 2),
            "risk_level": self.risk_level.value,
            "max_eligible_amount": round(self.max_eligible_amount, 2),
            "recommended_interest_rate": round(self.recommended_interest_rate, 4),
            "reasons": self.reasons,
            "conditions": self.conditions,
            "assessed_at": self.assessed_at,
        }

    @property
    def is_eligible(self) -> bool:
        """Check if the application resulted in any form of approval."""
        return self.status in (DecisionStatus.APPROVED, DecisionStatus.CONDITIONAL)
