"""
Risk Assessment module for the Loan Eligibility Engine.

This module evaluates the overall risk profile of a loan application
by analyzing multiple financial and personal factors such as income
stability, debt burden, employment history, and loan characteristics.
"""

from .models import (
    LoanApplication,
    Applicant,
    RiskLevel,
    EmploymentType,
    LoanType,
)


class RiskAssessor:
    """
    Evaluates the risk profile of a loan application across multiple dimensions.

    The assessor computes individual risk factors for income stability,
    debt burden, employment history, loan-to-value ratio, and applicant
    age. These factors are weighted and combined into an overall risk
    score and classification.

    Attributes:
        MAX_DTI_RATIO: Maximum acceptable debt-to-income ratio (50 percent).
        MAX_LOAN_TO_INCOME: Maximum acceptable loan-to-income ratio (5x).
        MIN_EMPLOYMENT_YEARS: Minimum employment years for favorable scoring.
    """

    MAX_DTI_RATIO = 50.0
    MAX_LOAN_TO_INCOME = 5.0
    MIN_EMPLOYMENT_YEARS = 2.0

    # Weights for each risk dimension
    WEIGHTS = {
        "income_stability": 0.25,
        "debt_burden": 0.25,
        "employment": 0.20,
        "loan_ratio": 0.20,
        "age": 0.10,
    }

    def __init__(self, conservative_mode: bool = False):
        """
        Initialize the RiskAssessor.

        Args:
            conservative_mode: When True, applies stricter thresholds
                               for all risk calculations. Defaults to False.
        """
        self._conservative = conservative_mode
        if conservative_mode:
            self.MAX_DTI_RATIO = 40.0
            self.MAX_LOAN_TO_INCOME = 3.5

    def assess_income_stability(self, applicant: Applicant) -> float:
        """
        Evaluate income stability based on employment type and income level.

        Salaried employees receive the highest stability score, while
        unemployed applicants receive the lowest. Income level provides
        an additional modifier.

        Args:
            applicant: The Applicant whose income stability is being assessed.

        Returns:
            A float between 0.0 and 1.0 representing income stability.
        """
        # Base stability by employment type
        stability_map = {
            EmploymentType.SALARIED: 0.9,
            EmploymentType.SELF_EMPLOYED: 0.7,
            EmploymentType.FREELANCER: 0.5,
            EmploymentType.RETIRED: 0.6,
            EmploymentType.UNEMPLOYED: 0.1,
        }
        base = stability_map.get(applicant.employment_type, 0.3)

        # Income level modifier: higher income slightly increases stability
        if applicant.annual_income >= 100000:
            income_mod = 0.1
        elif applicant.annual_income >= 50000:
            income_mod = 0.05
        else:
            income_mod = 0.0

        return min(1.0, base + income_mod)

    def assess_debt_burden(self, applicant: Applicant) -> float:
        """
        Evaluate the debt burden of the applicant.

        Considers the debt-to-income ratio and the number of existing
        loans to determine how burdened the applicant is with current debt.

        Args:
            applicant: The Applicant whose debt burden is being assessed.

        Returns:
            A float between 0.0 and 1.0 where 1.0 means no debt burden.
        """
        dti = applicant.debt_to_income_ratio

        # DTI scoring: lower is better
        if dti <= 20:
            dti_score = 1.0
        elif dti <= 30:
            dti_score = 0.8
        elif dti <= 40:
            dti_score = 0.6
        elif dti <= 50:
            dti_score = 0.3
        else:
            dti_score = 0.1

        # Existing loans penalty
        loan_penalty = min(0.3, applicant.existing_loans * 0.08)

        return max(0.0, dti_score - loan_penalty)

    def assess_employment_history(self, applicant: Applicant) -> float:
        """
        Evaluate employment history duration and stability.

        Longer employment duration indicates greater job stability
        and a more predictable income stream for loan repayment.

        Args:
            applicant: The Applicant whose employment history is assessed.

        Returns:
            A float between 0.0 and 1.0 representing employment stability.
        """
        years = applicant.years_of_employment

        if applicant.employment_type == EmploymentType.UNEMPLOYED:
            return 0.05

        if years >= 10:
            return 1.0
        elif years >= 5:
            return 0.8
        elif years >= self.MIN_EMPLOYMENT_YEARS:
            return 0.6
        elif years >= 1:
            return 0.4
        else:
            return 0.2

    def assess_loan_ratio(self, application: LoanApplication) -> float:
        """
        Evaluate the loan amount relative to the applicants income.

        A lower loan-to-income ratio indicates a more manageable loan
        relative to the applicants earning capacity.

        Args:
            application: The LoanApplication containing loan and income data.

        Returns:
            A float between 0.0 and 1.0 where higher is better (lower ratio).
        """
        ratio = application.loan_to_income_ratio

        if ratio <= 1.0:
            return 1.0
        elif ratio <= 2.0:
            return 0.85
        elif ratio <= 3.0:
            return 0.7
        elif ratio <= self.MAX_LOAN_TO_INCOME:
            return 0.4
        else:
            return 0.15

    def assess_age_factor(self, applicant: Applicant, loan_term_months: int) -> float:
        """
        Evaluate age-related risk considering loan term and retirement.

        Applicants who would reach typical retirement age before the loan
        term completes receive a lower score due to income uncertainty.

        Args:
            applicant: The Applicant whose age is being assessed.
            loan_term_months: The requested loan duration in months.

        Returns:
            A float between 0.0 and 1.0 representing age-related risk.
        """
        age_at_completion = applicant.age + (loan_term_months / 12.0)

        if applicant.age < 21:
            return 0.5  # Very young, limited credit history expected
        elif applicant.age < 25:
            return 0.7
        elif age_at_completion <= 60:
            return 1.0  # Completes well before retirement
        elif age_at_completion <= 65:
            return 0.7  # Close to retirement at completion
        elif age_at_completion <= 70:
            return 0.4
        else:
            return 0.2

    def calculate_risk_score(self, application: LoanApplication) -> float:
        """
        Calculate the composite risk score for a loan application.

        Combines all individual risk dimensions using configured weights
        to produce a single score between 0 and 100.

        Args:
            application: The LoanApplication to be assessed.

        Returns:
            A float between 0 and 100 representing overall risk score.
            Higher scores indicate lower risk (better for approval).
        """
        applicant = application.applicant

        factors = {
            "income_stability": self.assess_income_stability(applicant),
            "debt_burden": self.assess_debt_burden(applicant),
            "employment": self.assess_employment_history(applicant),
            "loan_ratio": self.assess_loan_ratio(application),
            "age": self.assess_age_factor(applicant, application.loan_term_months),
        }

        weighted_sum = sum(
            factors[key] * self.WEIGHTS[key] for key in factors
        )

        # Collateral bonus: reduces risk if applicant has collateral
        collateral_bonus = 5.0 if applicant.has_collateral else 0.0

        return min(100.0, (weighted_sum * 100.0) + collateral_bonus)

    def classify_risk(self, risk_score: float) -> RiskLevel:
        """
        Classify a numeric risk score into a risk level category.

        Args:
            risk_score: A float between 0 and 100.

        Returns:
            A RiskLevel enum value corresponding to the score range.
        """
        if risk_score >= 75:
            return RiskLevel.LOW
        elif risk_score >= 55:
            return RiskLevel.MEDIUM
        elif risk_score >= 35:
            return RiskLevel.HIGH
        else:
            return RiskLevel.VERY_HIGH

    def get_risk_factors(self, application: LoanApplication) -> list:
        """
        Identify and describe the notable risk factors in an application.

        Args:
            application: The LoanApplication to analyze.

        Returns:
            A list of strings describing identified risk factors.
        """
        applicant = application.applicant
        factors = []

        if applicant.debt_to_income_ratio > 40:
            factors.append(
                f"High debt-to-income ratio of {applicant.debt_to_income_ratio:.1f}%"
            )

        if applicant.employment_type == EmploymentType.UNEMPLOYED:
            factors.append("Applicant is currently unemployed")

        if applicant.credit_score < self.POOR_THRESHOLD if hasattr(self, 'POOR_THRESHOLD') else applicant.credit_score < 550:
            factors.append(f"Low credit score of {applicant.credit_score}")

        if application.loan_to_income_ratio > 3.0:
            factors.append(
                f"Loan amount is {application.loan_to_income_ratio:.1f}x annual income"
            )

        if applicant.existing_loans >= 3:
            factors.append(f"Multiple existing loans ({applicant.existing_loans})")

        if applicant.years_of_employment < 1:
            factors.append("Less than 1 year of employment history")

        if not factors:
            factors.append("No significant risk factors identified")

        return factors

    def full_assessment(self, application: LoanApplication) -> dict:
        """
        Perform a complete risk assessment and return a detailed report.

        Args:
            application: The LoanApplication to assess.

        Returns:
            A dictionary containing the risk score, classification,
            individual factor scores, and identified risk factors.
        """
        applicant = application.applicant

        individual_scores = {
            "income_stability": round(self.assess_income_stability(applicant), 4),
            "debt_burden": round(self.assess_debt_burden(applicant), 4),
            "employment_history": round(self.assess_employment_history(applicant), 4),
            "loan_ratio": round(self.assess_loan_ratio(application), 4),
            "age_factor": round(
                self.assess_age_factor(applicant, application.loan_term_months), 4
            ),
        }

        risk_score = self.calculate_risk_score(application)
        risk_level = self.classify_risk(risk_score)
        risk_factors = self.get_risk_factors(application)

        return {
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level.value,
            "individual_scores": individual_scores,
            "risk_factors": risk_factors,
            "conservative_mode": self._conservative,
        }
