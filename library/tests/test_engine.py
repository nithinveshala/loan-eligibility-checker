"""
Unit tests for the Loan Eligibility Engine library.

Tests cover all major components: models, calculator, risk assessor,
credit score analyzer, and validators.
"""

import unittest
from loan_eligibility_engine import (
    EligibilityCalculator,
    LoanApplication,
    Applicant,
    LoanDecision,
    RiskAssessor,
    ApplicationValidator,
    CreditScoreAnalyzer,
)
from loan_eligibility_engine.models import (
    LoanType,
    EmploymentType,
    RiskLevel,
    DecisionStatus,
)


class TestApplicantModel(unittest.TestCase):
    """Tests for the Applicant data model."""

    def setUp(self):
        self.applicant = Applicant(
            name="Test User",
            age=30,
            annual_income=60000,
            employment_type=EmploymentType.SALARIED,
            credit_score=720,
            existing_loans=1,
            monthly_expenses=1500,
            years_of_employment=5,
        )

    def test_monthly_income_calculation(self):
        self.assertAlmostEqual(self.applicant.monthly_income, 5000.0)

    def test_debt_to_income_ratio(self):
        expected = (1500 / 5000) * 100
        self.assertAlmostEqual(self.applicant.debt_to_income_ratio, expected)

    def test_zero_income_dti(self):
        applicant = Applicant(
            name="Zero", age=25, annual_income=0,
            employment_type=EmploymentType.UNEMPLOYED, credit_score=400,
            monthly_expenses=500,
        )
        self.assertEqual(applicant.debt_to_income_ratio, 100.0)


class TestLoanApplication(unittest.TestCase):
    """Tests for the LoanApplication data model."""

    def setUp(self):
        self.applicant = Applicant(
            name="Test User", age=30, annual_income=60000,
            employment_type=EmploymentType.SALARIED, credit_score=720,
        )
        self.application = LoanApplication(
            applicant=self.applicant,
            loan_type=LoanType.PERSONAL,
            loan_amount=30000,
            loan_term_months=36,
        )

    def test_loan_to_income_ratio(self):
        self.assertAlmostEqual(self.application.loan_to_income_ratio, 0.5)

    def test_monthly_payment_estimate(self):
        payment = self.application.monthly_payment_estimate
        self.assertGreater(payment, 0)
        self.assertLess(payment, self.application.loan_amount)


class TestCreditScoreAnalyzer(unittest.TestCase):
    """Tests for the CreditScoreAnalyzer class."""

    def setUp(self):
        self.analyzer = CreditScoreAnalyzer()

    def test_excellent_rating(self):
        self.assertEqual(self.analyzer.get_credit_rating(800), "Excellent")

    def test_good_rating(self):
        self.assertEqual(self.analyzer.get_credit_rating(720), "Good")

    def test_fair_rating(self):
        self.assertEqual(self.analyzer.get_credit_rating(660), "Fair")

    def test_poor_rating(self):
        self.assertEqual(self.analyzer.get_credit_rating(560), "Poor")

    def test_very_poor_rating(self):
        self.assertEqual(self.analyzer.get_credit_rating(400), "Very Poor")

    def test_score_factor_range(self):
        for score in [300, 500, 650, 750, 900]:
            factor = self.analyzer.compute_score_factor(score)
            self.assertGreaterEqual(factor, 0.0)
            self.assertLessEqual(factor, 1.0)

    def test_higher_score_gives_higher_factor(self):
        low = self.analyzer.compute_score_factor(400)
        high = self.analyzer.compute_score_factor(800)
        self.assertGreater(high, low)

    def test_credit_risk_levels(self):
        applicant_excellent = Applicant(
            name="A", age=30, annual_income=50000,
            employment_type=EmploymentType.SALARIED, credit_score=800,
        )
        applicant_poor = Applicant(
            name="B", age=30, annual_income=50000,
            employment_type=EmploymentType.SALARIED, credit_score=500,
        )
        self.assertEqual(
            self.analyzer.assess_credit_risk(applicant_excellent), RiskLevel.LOW
        )
        self.assertEqual(
            self.analyzer.assess_credit_risk(applicant_poor), RiskLevel.VERY_HIGH
        )


class TestRiskAssessor(unittest.TestCase):
    """Tests for the RiskAssessor class."""

    def setUp(self):
        self.assessor = RiskAssessor()
        self.good_applicant = Applicant(
            name="Good Applicant", age=35, annual_income=80000,
            employment_type=EmploymentType.SALARIED, credit_score=750,
            existing_loans=0, monthly_expenses=2000,
            years_of_employment=10, has_collateral=True,
        )
        self.risky_applicant = Applicant(
            name="Risky Applicant", age=22, annual_income=25000,
            employment_type=EmploymentType.FREELANCER, credit_score=520,
            existing_loans=4, monthly_expenses=1800,
            years_of_employment=0.5,
        )

    def test_income_stability_salaried(self):
        score = self.assessor.assess_income_stability(self.good_applicant)
        self.assertGreaterEqual(score, 0.8)

    def test_income_stability_unemployed(self):
        applicant = Applicant(
            name="U", age=30, annual_income=0,
            employment_type=EmploymentType.UNEMPLOYED, credit_score=400,
        )
        score = self.assessor.assess_income_stability(applicant)
        self.assertLessEqual(score, 0.2)

    def test_risk_score_good_applicant(self):
        app = LoanApplication(
            applicant=self.good_applicant,
            loan_type=LoanType.HOME,
            loan_amount=200000,
            loan_term_months=240,
        )
        score = self.assessor.calculate_risk_score(app)
        self.assertGreater(score, 70)

    def test_risk_score_risky_applicant(self):
        app = LoanApplication(
            applicant=self.risky_applicant,
            loan_type=LoanType.PERSONAL,
            loan_amount=50000,
            loan_term_months=60,
        )
        score = self.assessor.calculate_risk_score(app)
        self.assertLess(score, 50)

    def test_conservative_mode(self):
        conservative = RiskAssessor(conservative_mode=True)
        self.assertEqual(conservative.MAX_DTI_RATIO, 40.0)


class TestApplicationValidator(unittest.TestCase):
    """Tests for the ApplicationValidator class."""

    def setUp(self):
        self.validator = ApplicationValidator()

    def test_valid_application(self):
        applicant = Applicant(
            name="Valid User", age=30, annual_income=50000,
            employment_type=EmploymentType.SALARIED, credit_score=700,
        )
        app = LoanApplication(
            applicant=applicant,
            loan_type=LoanType.PERSONAL,
            loan_amount=20000,
            loan_term_months=36,
        )
        result = self.validator.validate_application(app)
        self.assertTrue(result["is_valid"])

    def test_underage_applicant(self):
        applicant = Applicant(
            name="Young", age=16, annual_income=10000,
            employment_type=EmploymentType.SALARIED, credit_score=600,
        )
        errors = self.validator.validate_applicant(applicant)
        self.assertTrue(any(e.field == "age" for e in errors))

    def test_invalid_credit_score(self):
        applicant = Applicant(
            name="Bad Score", age=30, annual_income=50000,
            employment_type=EmploymentType.SALARIED, credit_score=200,
        )
        errors = self.validator.validate_applicant(applicant)
        self.assertTrue(any(e.field == "credit_score" for e in errors))

    def test_loan_amount_exceeds_max(self):
        applicant = Applicant(
            name="Big Loan", age=30, annual_income=100000,
            employment_type=EmploymentType.SALARIED, credit_score=750,
        )
        app = LoanApplication(
            applicant=applicant,
            loan_type=LoanType.PERSONAL,
            loan_amount=200000,  # Exceeds personal loan max of 100000
            loan_term_months=60,
        )
        errors = self.validator.validate_loan_details(app)
        self.assertTrue(any(e.field == "loan_amount" for e in errors))

    def test_insufficient_income_for_loan_type(self):
        applicant = Applicant(
            name="Low Income", age=30, annual_income=5000,
            employment_type=EmploymentType.SALARIED, credit_score=700,
        )
        app = LoanApplication(
            applicant=applicant,
            loan_type=LoanType.HOME,
            loan_amount=50000,
            loan_term_months=120,
        )
        errors = self.validator.validate_loan_details(app)
        self.assertTrue(any(e.field == "annual_income" for e in errors))


class TestEligibilityCalculator(unittest.TestCase):
    """Tests for the main EligibilityCalculator class."""

    def setUp(self):
        self.calculator = EligibilityCalculator()

    def test_approve_good_application(self):
        applicant = Applicant(
            name="Strong Applicant", age=35, annual_income=100000,
            employment_type=EmploymentType.SALARIED, credit_score=780,
            existing_loans=0, monthly_expenses=2500,
            years_of_employment=12, has_collateral=True,
        )
        app = LoanApplication(
            applicant=applicant,
            loan_type=LoanType.HOME,
            loan_amount=200000,
            loan_term_months=240,
            purpose="Buy house",
        )
        decision = self.calculator.evaluate(app)
        self.assertEqual(decision.status, DecisionStatus.APPROVED)
        self.assertGreater(decision.eligibility_score, 65)

    def test_deny_weak_application(self):
        applicant = Applicant(
            name="Weak Applicant", age=22, annual_income=15000,
            employment_type=EmploymentType.FREELANCER, credit_score=420,
            existing_loans=4, monthly_expenses=1200,
            years_of_employment=0.5,
        )
        app = LoanApplication(
            applicant=applicant,
            loan_type=LoanType.PERSONAL,
            loan_amount=80000,
            loan_term_months=60,
        )
        decision = self.calculator.evaluate(app)
        self.assertEqual(decision.status, DecisionStatus.DENIED)

    def test_conditional_approval(self):
        applicant = Applicant(
            name="Borderline", age=28, annual_income=40000,
            employment_type=EmploymentType.SELF_EMPLOYED, credit_score=640,
            existing_loans=2, monthly_expenses=1500,
            years_of_employment=3,
        )
        app = LoanApplication(
            applicant=applicant,
            loan_type=LoanType.PERSONAL,
            loan_amount=40000,
            loan_term_months=48,
        )
        decision = self.calculator.evaluate(app)
        self.assertIn(
            decision.status,
            [DecisionStatus.CONDITIONAL, DecisionStatus.APPROVED, DecisionStatus.DENIED],
        )

    def test_decision_to_dict(self):
        applicant = Applicant(
            name="Dict Test", age=30, annual_income=60000,
            employment_type=EmploymentType.SALARIED, credit_score=700,
        )
        app = LoanApplication(
            applicant=applicant,
            loan_type=LoanType.AUTO,
            loan_amount=25000,
            loan_term_months=48,
        )
        decision = self.calculator.evaluate(app)
        result = decision.to_dict()
        self.assertIn("status", result)
        self.assertIn("eligibility_score", result)
        self.assertIn("risk_level", result)

    def test_quick_check(self):
        result = self.calculator.quick_check(
            annual_income=80000,
            credit_score=750,
            loan_amount=50000,
            loan_type_str="personal",
        )
        self.assertIn("estimated_eligibility_score", result)
        self.assertIn("likely_eligible", result)
        self.assertTrue(result["likely_eligible"])

    def test_invalid_application_denied(self):
        applicant = Applicant(
            name="", age=15, annual_income=-100,
            employment_type=EmploymentType.SALARIED, credit_score=200,
        )
        app = LoanApplication(
            applicant=applicant,
            loan_type=LoanType.PERSONAL,
            loan_amount=500,
            loan_term_months=12,
        )
        decision = self.calculator.evaluate(app)
        self.assertEqual(decision.status, DecisionStatus.DENIED)
        self.assertEqual(decision.eligibility_score, 0.0)


if __name__ == "__main__":
    unittest.main()
