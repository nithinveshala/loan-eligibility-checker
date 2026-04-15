"""
Loan Eligibility Engine - A Python library for assessing loan eligibility.

This library provides a comprehensive object-oriented framework for evaluating
loan applications based on financial metrics, credit scoring, risk assessment,
and eligibility determination. It supports multiple loan types including
personal, home, auto, and education loans.

Author: Aditya
Version: 1.0.0
"""

from .models import LoanApplication, Applicant, LoanDecision
from .calculator import EligibilityCalculator
from .risk_assessor import RiskAssessor
from .validators import ApplicationValidator
from .scoring import CreditScoreAnalyzer

__version__ = "1.0.0"
__all__ = [
    "LoanApplication",
    "Applicant",
    "LoanDecision",
    "EligibilityCalculator",
    "RiskAssessor",
    "ApplicationValidator",
    "CreditScoreAnalyzer",
]
