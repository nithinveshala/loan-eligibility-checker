"""
Validation module for the Loan Eligibility Engine.

This module provides the ApplicationValidator class which performs
comprehensive validation of loan application data before it enters
the eligibility assessment pipeline.
"""

from .models import LoanApplication, Applicant, LoanType, EmploymentType


class ValidationError(Exception):
    """Custom exception raised when application data fails validation."""

    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"Validation error on '{field}': {message}")


class ApplicationValidator:
    """
    Validates loan application data for completeness and correctness.

    Enforces business rules such as minimum age, income requirements,
    credit score ranges, and loan amount limits. All validation methods
    return a list of ValidationError objects; an empty list indicates
    the data passed all checks.

    Attributes:
        MIN_AGE: Minimum applicant age (18).
        MAX_AGE: Maximum applicant age (70).
        MIN_CREDIT_SCORE: Minimum valid credit score (300).
        MAX_CREDIT_SCORE: Maximum valid credit score (900).
        MIN_LOAN_AMOUNT: Minimum loan amount (1000).
        MAX_LOAN_TERM_MONTHS: Maximum loan term in months (360).
    """

    MIN_AGE = 18
    MAX_AGE = 70
    MIN_CREDIT_SCORE = 300
    MAX_CREDIT_SCORE = 900
    MIN_LOAN_AMOUNT = 1000
    MAX_LOAN_TERM_MONTHS = 360

    # Maximum loan amounts per loan type
    MAX_LOAN_AMOUNTS = {
        LoanType.PERSONAL: 100000,
        LoanType.HOME: 2000000,
        LoanType.AUTO: 500000,
        LoanType.EDUCATION: 300000,
    }

    # Minimum income requirements per loan type
    MIN_INCOME_REQUIREMENTS = {
        LoanType.PERSONAL: 15000,
        LoanType.HOME: 30000,
        LoanType.AUTO: 20000,
        LoanType.EDUCATION: 10000,
    }

    def validate_applicant(self, applicant: Applicant) -> list:
        """
        Validate all fields of an Applicant object.

        Checks name, age, income, credit score, employment type,
        and other personal data for completeness and valid ranges.

        Args:
            applicant: The Applicant object to validate.

        Returns:
            A list of ValidationError objects. Empty if all checks pass.
        """
        errors = []

        # Name validation
        if not applicant.name or not applicant.name.strip():
            errors.append(ValidationError("name", "Applicant name is required"))

        # Age validation
        if applicant.age < self.MIN_AGE:
            errors.append(
                ValidationError(
                    "age",
                    f"Applicant must be at least {self.MIN_AGE} years old"
                )
            )
        elif applicant.age > self.MAX_AGE:
            errors.append(
                ValidationError(
                    "age",
                    f"Applicant must be at most {self.MAX_AGE} years old"
                )
            )

        # Income validation
        if applicant.annual_income < 0:
            errors.append(
                ValidationError("annual_income", "Annual income cannot be negative")
            )

        # Credit score validation
        if applicant.credit_score < self.MIN_CREDIT_SCORE:
            errors.append(
                ValidationError(
                    "credit_score",
                    f"Credit score must be at least {self.MIN_CREDIT_SCORE}"
                )
            )
        elif applicant.credit_score > self.MAX_CREDIT_SCORE:
            errors.append(
                ValidationError(
                    "credit_score",
                    f"Credit score must be at most {self.MAX_CREDIT_SCORE}"
                )
            )

        # Employment validation
        if not isinstance(applicant.employment_type, EmploymentType):
            errors.append(
                ValidationError(
                    "employment_type", "Invalid employment type provided"
                )
            )

        # Existing loans validation
        if applicant.existing_loans < 0:
            errors.append(
                ValidationError(
                    "existing_loans", "Number of existing loans cannot be negative"
                )
            )

        # Monthly expenses validation
        if applicant.monthly_expenses < 0:
            errors.append(
                ValidationError(
                    "monthly_expenses", "Monthly expenses cannot be negative"
                )
            )

        # Dependents validation
        if applicant.dependents < 0:
            errors.append(
                ValidationError("dependents", "Number of dependents cannot be negative")
            )

        return errors

    def validate_loan_details(self, application: LoanApplication) -> list:
        """
        Validate loan-specific details of the application.

        Checks loan amount, term, type, and enforces loan-type-specific
        limits and requirements.

        Args:
            application: The LoanApplication whose loan details are validated.

        Returns:
            A list of ValidationError objects. Empty if all checks pass.
        """
        errors = []

        # Loan type validation
        if not isinstance(application.loan_type, LoanType):
            errors.append(
                ValidationError("loan_type", "Invalid loan type provided")
            )
            return errors  # Cannot proceed with type-specific checks

        # Loan amount validation
        if application.loan_amount < self.MIN_LOAN_AMOUNT:
            errors.append(
                ValidationError(
                    "loan_amount",
                    f"Loan amount must be at least {self.MIN_LOAN_AMOUNT}"
                )
            )

        max_amount = self.MAX_LOAN_AMOUNTS.get(application.loan_type, 100000)
        if application.loan_amount > max_amount:
            errors.append(
                ValidationError(
                    "loan_amount",
                    f"Maximum loan amount for {application.loan_type.value} "
                    f"loans is {max_amount}"
                )
            )

        # Loan term validation
        if application.loan_term_months <= 0:
            errors.append(
                ValidationError("loan_term_months", "Loan term must be positive")
            )
        elif application.loan_term_months > self.MAX_LOAN_TERM_MONTHS:
            errors.append(
                ValidationError(
                    "loan_term_months",
                    f"Loan term cannot exceed {self.MAX_LOAN_TERM_MONTHS} months"
                )
            )

        # Income requirement check
        min_income = self.MIN_INCOME_REQUIREMENTS.get(application.loan_type, 10000)
        if application.applicant.annual_income < min_income:
            errors.append(
                ValidationError(
                    "annual_income",
                    f"Minimum annual income for {application.loan_type.value} "
                    f"loans is {min_income}"
                )
            )

        return errors

    def validate_application(self, application: LoanApplication) -> dict:
        """
        Perform full validation of a loan application.

        Runs both applicant validation and loan detail validation,
        then returns a structured result indicating pass or fail.

        Args:
            application: The LoanApplication to validate.

        Returns:
            A dictionary with 'is_valid' boolean, a list of 'errors',
            and a count of total errors found.
        """
        applicant_errors = self.validate_applicant(application.applicant)
        loan_errors = self.validate_loan_details(application)

        all_errors = applicant_errors + loan_errors

        return {
            "is_valid": len(all_errors) == 0,
            "errors": [
                {"field": e.field, "message": e.message} for e in all_errors
            ],
            "error_count": len(all_errors),
        }
