"""
Credit Score Analysis module for the Loan Eligibility Engine.

This module provides the CreditScoreAnalyzer class which evaluates
credit scores and maps them to standardized ratings and risk factors
used in the eligibility calculation pipeline.
"""

from .models import Applicant, RiskLevel


class CreditScoreAnalyzer:
    """
    Analyzes credit scores and derives risk-related metrics.

    The analyzer uses configurable thresholds to classify credit scores
    into risk categories and compute numerical factors that feed into
    the broader eligibility assessment.

    Attributes:
        EXCELLENT_THRESHOLD: Minimum score considered excellent (750).
        GOOD_THRESHOLD: Minimum score considered good (700).
        FAIR_THRESHOLD: Minimum score considered fair (650).
        POOR_THRESHOLD: Minimum score considered poor (550).
    """

    EXCELLENT_THRESHOLD = 750
    GOOD_THRESHOLD = 700
    FAIR_THRESHOLD = 650
    POOR_THRESHOLD = 550

    def __init__(self, weight: float = 0.35):
        """
        Initialize the CreditScoreAnalyzer.

        Args:
            weight: The relative weight of credit score in overall eligibility
                    assessment. Defaults to 0.35 (35 percent of total score).
        """
        self._weight = weight

    @property
    def weight(self) -> float:
        """Return the configured weight for credit score analysis."""
        return self._weight

    def get_credit_rating(self, credit_score: int) -> str:
        """
        Map a numeric credit score to a human-readable rating.

        Args:
            credit_score: Integer credit score between 300 and 900.

        Returns:
            A string rating: Excellent, Good, Fair, Poor, or Very Poor.
        """
        if credit_score >= self.EXCELLENT_THRESHOLD:
            return "Excellent"
        elif credit_score >= self.GOOD_THRESHOLD:
            return "Good"
        elif credit_score >= self.FAIR_THRESHOLD:
            return "Fair"
        elif credit_score >= self.POOR_THRESHOLD:
            return "Poor"
        else:
            return "Very Poor"

    def compute_score_factor(self, credit_score: int) -> float:
        """
        Convert a credit score into a normalized factor between 0 and 1.

        The factor represents how strongly the credit score supports
        loan eligibility, where 1.0 is ideal and 0.0 is disqualifying.

        Args:
            credit_score: Integer credit score between 300 and 900.

        Returns:
            A float between 0.0 and 1.0 representing creditworthiness.
        """
        # Normalize credit score to 0-1 range using min-max scaling
        min_score = 300
        max_score = 900
        clamped = max(min_score, min(max_score, credit_score))
        normalized = (clamped - min_score) / (max_score - min_score)

        # Apply non-linear scaling to reward higher scores more
        # This gives diminishing returns below 550 and accelerating returns above 700
        if normalized < 0.4:
            return normalized * 0.5
        elif normalized < 0.67:
            return 0.2 + (normalized - 0.4) * 1.5
        else:
            return 0.6 + (normalized - 0.67) * 1.2

    def assess_credit_risk(self, applicant: Applicant) -> RiskLevel:
        """
        Determine the credit risk level based on the applicants credit score.

        Args:
            applicant: An Applicant object containing the credit_score field.

        Returns:
            A RiskLevel enum value indicating the assessed credit risk.
        """
        score = applicant.credit_score
        if score >= self.EXCELLENT_THRESHOLD:
            return RiskLevel.LOW
        elif score >= self.GOOD_THRESHOLD:
            return RiskLevel.MEDIUM
        elif score >= self.FAIR_THRESHOLD:
            return RiskLevel.HIGH
        else:
            return RiskLevel.VERY_HIGH

    def get_interest_rate_modifier(self, credit_score: int) -> float:
        """
        Calculate an interest rate modifier based on credit score.

        Higher credit scores receive a discount (negative modifier)
        while lower scores incur a premium (positive modifier).

        Args:
            credit_score: Integer credit score between 300 and 900.

        Returns:
            A float modifier to be added to the base interest rate.
            Ranges from -0.02 (excellent) to +0.08 (very poor).
        """
        if credit_score >= self.EXCELLENT_THRESHOLD:
            return -0.02
        elif credit_score >= self.GOOD_THRESHOLD:
            return 0.0
        elif credit_score >= self.FAIR_THRESHOLD:
            return 0.03
        elif credit_score >= self.POOR_THRESHOLD:
            return 0.05
        else:
            return 0.08

    def generate_credit_summary(self, applicant: Applicant) -> dict:
        """
        Produce a comprehensive summary of the applicants credit profile.

        Args:
            applicant: An Applicant object with credit and financial data.

        Returns:
            A dictionary containing rating, factor, risk level, rate modifier,
            and an explanatory remark about the credit profile.
        """
        score = applicant.credit_score
        rating = self.get_credit_rating(score)
        factor = self.compute_score_factor(score)
        risk = self.assess_credit_risk(applicant)
        rate_mod = self.get_interest_rate_modifier(score)

        remarks = {
            "Excellent": "Outstanding credit profile supports favorable terms.",
            "Good": "Solid credit history indicates reliable repayment behavior.",
            "Fair": "Adequate credit standing; some risk factors to consider.",
            "Poor": "Below-average credit raises concerns about repayment capacity.",
            "Very Poor": "Significant credit concerns may limit approval options.",
        }

        return {
            "credit_score": score,
            "rating": rating,
            "score_factor": round(factor, 4),
            "risk_level": risk.value,
            "interest_rate_modifier": rate_mod,
            "remark": remarks.get(rating, ""),
        }
