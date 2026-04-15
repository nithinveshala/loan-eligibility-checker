# Loan Eligibility Engine

A comprehensive Python library for assessing loan eligibility using credit scoring, risk assessment, and financial analysis.

## Installation

```bash
pip install loan-eligibility-engine
```

## Quick Start

```python
from loan_eligibility_engine import (
    EligibilityCalculator,
    LoanApplication,
    Applicant,
    LoanType,
    EmploymentType,
)

# Create an applicant
applicant = Applicant(
    name="John Doe",
    age=35,
    annual_income=75000,
    employment_type=EmploymentType.SALARIED,
    credit_score=720,
    existing_loans=1,
    monthly_expenses=2000,
    years_of_employment=8,
    has_collateral=True,
    dependents=2,
)

# Create a loan application
application = LoanApplication(
    applicant=applicant,
    loan_type=LoanType.HOME,
    loan_amount=250000,
    loan_term_months=240,
    purpose="Purchase primary residence",
)

# Evaluate eligibility
calculator = EligibilityCalculator()
decision = calculator.evaluate(application)

print(f"Status: {decision.status.value}")
print(f"Score: {decision.eligibility_score}")
print(f"Max Amount: {decision.max_eligible_amount}")
print(f"Interest Rate: {decision.recommended_interest_rate:.2%}")
```

## Features

- Credit score analysis with configurable thresholds
- Multi-factor risk assessment (income, debt, employment, age)
- Application validation with detailed error reporting
- Support for personal, home, auto, and education loans
- Quick pre-screening checks
- Conservative mode for stricter assessments

## License

MIT
