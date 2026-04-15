"""
Eligibility Calculator module for the Loan Eligibility Engine.

This is the main orchestrator module that combines credit scoring, risk
assessment, and validation to produce a final loan eligibility decision.
It serves as the primary entry point for processing loan applications.
"""

from .models import (
    LoanApplication,
    LoanDecision,
    DecisionStatus,
    RiskLevel,
    LoanType,
)
from .scoring import CreditScoreAnalyzer
from .risk_assessor import RiskAssessor
from .validators import ApplicationValidator


class EligibilityCalculator:
    """
    Main orchestrator for the loan eligibility assessment process.

    Combines credit score analysis, risk assessment, and business rules
    to produce a comprehensive eligibility decision for a loan application.
    This class coordinates all sub-components and applies final decision
    logic based on their outputs.

    Attributes:
        BASE_RATES: Base annual interest rates by loan type.
        APPROVAL_THRESHOLD: Minimum eligibility score for approval (65).
        CONDITIONAL_THRESHOLD: Minimum eligibility score for conditional approval (45).
    """

    BASE_RATES = {
        LoanType.PERSONAL: 0.12,
        LoanType.HOME: 0.07,
        LoanType.AUTO: 0.09,
        LoanType.EDUCATION: 0.06,
    }

    APPROVAL_THRESHOLD = 65.0
    CONDITIONAL_THRESHOLD = 45.0

    def __init__(self, conservative: bool = False):
        """
        Initialize the EligibilityCalculator with all sub-components.

        Args:
            conservative: When True, applies stricter thresholds throughout
                          the assessment pipeline. Defaults to False.
        """
        self._credit_analyzer = CreditScoreAnalyzer(weight=0.35)
        self._risk_assessor = RiskAssessor(conservative_mode=conservative)
        self._validator = ApplicationValidator()
        self._conservative = conservative

    @property
    def credit_analyzer(self) -> CreditScoreAnalyzer:
        """Access the credit score analyzer component."""
        return self._credit_analyzer

    @property
    def risk_assessor(self) -> RiskAssessor:
        """Access the risk assessor component."""
        return self._risk_assessor

    @property
    def validator(self) -> ApplicationValidator:
        """Access the application validator component."""
        return self._validator

    def _calculate_eligibility_score(self, application: LoanApplication) -> float:
        """
        Compute the overall eligibility score combining credit and risk factors.

        The eligibility score is a weighted combination of the credit score
        factor and the risk assessment score, scaled to a 0-100 range.

        Args:
            application: The LoanApplication to score.

        Returns:
            A float between 0 and 100 representing overall eligibility.
        """
        # Credit component (35% weight)
        credit_factor = self._credit_analyzer.compute_score_factor(
            application.applicant.credit_score
        )
        credit_component = credit_factor * 100 * self._credit_analyzer.weight

        # Risk component (65% weight)
        risk_score = self._risk_assessor.calculate_risk_score(application)
        risk_component = risk_score * (1 - self._credit_analyzer.weight)

        return min(100.0, credit_component + risk_component)

    def _determine_max_eligible_amount(self, application: LoanApplication) -> float:
        """
        Calculate the maximum loan amount the applicant qualifies for.

        Based on annual income, credit score, employment stability,
        and the requested loan type. The max amount is capped at the
        type-specific limit defined by the validator.

        Args:
            application: The LoanApplication for which to compute the limit.

        Returns:
            A float representing the maximum eligible loan amount.
        """
        applicant = application.applicant
        base_multiplier = 3.0  # Base: 3x annual income

        # Credit score modifier
        if applicant.credit_score >= 750:
            base_multiplier += 2.0
        elif applicant.credit_score >= 700:
            base_multiplier += 1.5
        elif applicant.credit_score >= 650:
            base_multiplier += 0.5

        # Employment modifier
        income_stability = self._risk_assessor.assess_income_stability(applicant)
        base_multiplier *= (0.5 + income_stability * 0.5)

        # Debt burden modifier
        debt_factor = self._risk_assessor.assess_debt_burden(applicant)
        base_multiplier *= (0.6 + debt_factor * 0.4)

        # Collateral bonus
        if applicant.has_collateral:
            base_multiplier *= 1.2

        max_amount = applicant.annual_income * base_multiplier

        # Cap at loan-type limit
        type_limit = self._validator.MAX_LOAN_AMOUNTS.get(
            application.loan_type, 100000
        )
        return min(max_amount, type_limit)

    def _calculate_interest_rate(self, application: LoanApplication) -> float:
        """
        Determine the recommended interest rate for the application.

        Starts from a base rate for the loan type and adjusts based
        on the applicants credit score and risk profile.

        Args:
            application: The LoanApplication for which to calculate the rate.

        Returns:
            A float representing the recommended annual interest rate.
        """
        base_rate = self.BASE_RATES.get(application.loan_type, 0.10)

        # Credit score modifier
        credit_modifier = self._credit_analyzer.get_interest_rate_modifier(
            application.applicant.credit_score
        )

        # Risk modifier
        risk_score = self._risk_assessor.calculate_risk_score(application)
        if risk_score >= 75:
            risk_modifier = -0.01
        elif risk_score >= 55:
            risk_modifier = 0.01
        elif risk_score >= 35:
            risk_modifier = 0.03
        else:
            risk_modifier = 0.05

        final_rate = base_rate + credit_modifier + risk_modifier
        return max(0.03, min(0.25, final_rate))  # Clamp between 3% and 25%

    def _generate_decision_reasons(
        self, application: LoanApplication, score: float, risk_level: RiskLevel
    ) -> list:
        """
        Generate human-readable reasons supporting the eligibility decision.

        Args:
            application: The assessed LoanApplication.
            score: The computed eligibility score.
            risk_level: The classified risk level.

        Returns:
            A list of reason strings explaining the decision factors.
        """
        reasons = []
        applicant = application.applicant
        credit_rating = self._credit_analyzer.get_credit_rating(
            applicant.credit_score
        )

        reasons.append(
            f"Credit score of {applicant.credit_score} rated as {credit_rating}"
        )
        reasons.append(
            f"Overall eligibility score: {score:.1f} out of 100"
        )
        reasons.append(
            f"Risk level classified as {risk_level.value}"
        )

        if applicant.debt_to_income_ratio > 40:
            reasons.append(
                f"Debt-to-income ratio of {applicant.debt_to_income_ratio:.1f}% "
                f"exceeds recommended maximum"
            )

        if application.loan_to_income_ratio > 3:
            reasons.append(
                f"Requested loan is {application.loan_to_income_ratio:.1f}x "
                f"annual income"
            )

        if applicant.has_collateral:
            reasons.append("Collateral availability improves eligibility")

        return reasons

    def _generate_conditions(
        self, application: LoanApplication, score: float
    ) -> list:
        """
        Generate conditions for conditional approvals.

        Args:
            application: The LoanApplication being assessed.
            score: The eligibility score achieved.

        Returns:
            A list of condition strings that must be met for approval.
        """
        conditions = []
        applicant = application.applicant

        if applicant.credit_score < 650:
            conditions.append("Provide a guarantor with credit score above 700")

        if not applicant.has_collateral and application.loan_amount > 50000:
            conditions.append("Provide collateral for the requested loan amount")

        if applicant.debt_to_income_ratio > 40:
            conditions.append(
                "Reduce existing debt obligations to below 40% of income"
            )

        if applicant.years_of_employment < 2:
            conditions.append(
                "Provide additional proof of stable income for the past 12 months"
            )

        max_amount = self._determine_max_eligible_amount(application)
        if application.loan_amount > max_amount:
            conditions.append(
                f"Reduce loan amount to maximum eligible: {max_amount:.2f}"
            )

        return conditions

    def evaluate(self, application: LoanApplication) -> LoanDecision:
        """
        Perform a complete eligibility evaluation of a loan application.

        This is the main entry point for processing an application. It
        validates the application, computes eligibility and risk scores,
        determines the decision status, and returns a comprehensive
        LoanDecision object.

        Args:
            application: The LoanApplication to evaluate.

        Returns:
            A LoanDecision object containing the full assessment results.

        Raises:
            ValueError: If the application fails basic validation checks.
        """
        # Validate the application first
        validation = self._validator.validate_application(application)
        if not validation["is_valid"]:
            error_msgs = [e["message"] for e in validation["errors"]]
            return LoanDecision(
                status=DecisionStatus.DENIED,
                eligibility_score=0.0,
                risk_level=RiskLevel.VERY_HIGH,
                max_eligible_amount=0.0,
                recommended_interest_rate=0.0,
                reasons=["Application failed validation: " + "; ".join(error_msgs)],
            )

        # Calculate eligibility score
        eligibility_score = self._calculate_eligibility_score(application)

        # Determine risk level
        risk_score = self._risk_assessor.calculate_risk_score(application)
        risk_level = self._risk_assessor.classify_risk(risk_score)

        # Calculate max eligible amount and interest rate
        max_amount = self._determine_max_eligible_amount(application)
        interest_rate = self._calculate_interest_rate(application)

        # Generate reasons
        reasons = self._generate_decision_reasons(
            application, eligibility_score, risk_level
        )

        # Determine decision status
        if eligibility_score >= self.APPROVAL_THRESHOLD:
            if application.loan_amount <= max_amount:
                status = DecisionStatus.APPROVED
                conditions = []
            else:
                status = DecisionStatus.CONDITIONAL
                conditions = self._generate_conditions(application, eligibility_score)
        elif eligibility_score >= self.CONDITIONAL_THRESHOLD:
            status = DecisionStatus.CONDITIONAL
            conditions = self._generate_conditions(application, eligibility_score)
        else:
            status = DecisionStatus.DENIED
            conditions = []
            reasons.append(
                "Eligibility score below minimum threshold for approval"
            )

        return LoanDecision(
            status=status,
            eligibility_score=eligibility_score,
            risk_level=risk_level,
            max_eligible_amount=max_amount,
            recommended_interest_rate=interest_rate,
            reasons=reasons,
            conditions=conditions,
        )

    def quick_check(self, annual_income: float, credit_score: int,
                    loan_amount: float, loan_type_str: str) -> dict:
        """
        Perform a simplified eligibility check without full application data.

        Useful for pre-screening scenarios where the user wants a quick
        estimate before submitting a full application.

        Args:
            annual_income: The applicants gross annual income.
            credit_score: The applicants credit score (300-900).
            loan_amount: The requested loan amount.
            loan_type_str: The loan type as a string (personal, home, auto, education).

        Returns:
            A dictionary with estimated eligibility, risk level, and max amount.
        """
        from .models import Applicant, EmploymentType

        # Create a minimal applicant and application for estimation
        applicant = Applicant(
            name="Quick Check",
            age=30,
            annual_income=annual_income,
            employment_type=EmploymentType.SALARIED,
            credit_score=credit_score,
        )

        try:
            loan_type = LoanType(loan_type_str.lower())
        except ValueError:
            loan_type = LoanType.PERSONAL

        application = LoanApplication(
            applicant=applicant,
            loan_type=loan_type,
            loan_amount=loan_amount,
            loan_term_months=60,
        )

        score = self._calculate_eligibility_score(application)
        max_amount = self._determine_max_eligible_amount(application)
        credit_rating = self._credit_analyzer.get_credit_rating(credit_score)

        return {
            "estimated_eligibility_score": round(score, 2),
            "likely_eligible": score >= self.CONDITIONAL_THRESHOLD,
            "credit_rating": credit_rating,
            "estimated_max_amount": round(max_amount, 2),
            "note": "This is an estimate. Submit a full application for accurate results.",
        }
