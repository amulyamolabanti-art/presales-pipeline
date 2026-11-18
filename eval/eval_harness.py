"""
AI Proposal Assistant - Sprint 0 Evaluation Harness Skeleton
Author: Likhitha Yada (Track A Backup Lead)
Ticket: APA-15 (S0-LY-05)

Description:
  Automated evaluation harness that runs benchmark questions and prompts
  against a model (offline MockModel for Sprint 0) and computes pass/fail metrics.
"""

import json
import os
import sys
import time
from typing import Dict, Any, List

class MockModel:
    """
    Offline Mock LLM to test evaluation harness pipeline without requiring
    Azure OpenAI API keys or incurring inference costs.
    """
    def __init__(self, simulate_flaws: bool = False):
        self.simulate_flaws = simulate_flaws

    def answer_question(self, question: Dict[str, Any]) -> str:
        """Simulate generating an answer for a golden-set question."""
        qid = question.get("id", "")
        is_refusal = question.get("is_not_found", False)

        # Refusal trap handling
        if is_refusal:
            if self.simulate_flaws and qid == "Q14":
                # Intentionally simulate hallucination if flaws enabled
                return "The client requires an on-premise mainframe deployment in Austin, Texas."
            return "This information is not specified in the provided RFP document."

        # Realistic canned responses based on question category
        expected = question.get("expected_answer", "")
        return expected

    def extract_intake_metadata(self, rfp_text: str) -> Dict[str, Any]:
        """Simulate extracting structured JSON from raw RFP text."""
        if "Horizon Health" in rfp_text:
            return {
                "opportunityName": "Horizon Health Patient Portal Modernization",
                "clientName": "Horizon Health Systems Inc.",
                "submissionDeadline": "2026-12-15",
                "domain": "Healthcare",
                "contractType": "Fixed Price",
                "estimatedBudgetUSD": 450000,
                "complianceCertifications": ["HIPAA"]
            }
        elif "Apex Global Payments" in rfp_text:
            return {
                "opportunityName": "Apex Real-Time Payment Fraud Scoring Engine",
                "clientName": "Apex Global Payments Corp",
                "submissionDeadline": "2026-11-30",
                "domain": "FinTech",
                "contractType": "Time & Materials",
                "estimatedBudgetUSD": None,
                "complianceCertifications": ["PCI-DSS v4.0", "SOC2 Type II"]
            }
        return {}


class EvaluationHarness:
    """Harness that executes test suites and computes accuracy & latency metrics."""

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.golden_set_file = os.path.join(base_dir, "golden_set_questions.json")
        self.fixtures_dir = os.path.join(base_dir, "fixtures")

    def run_golden_set_eval(self, model: MockModel) -> Dict[str, Any]:
        """Runs the 15 Golden Set benchmark questions."""
        if not os.path.exists(self.golden_set_file):
            print(f"[ERROR] Golden set file not found: {self.golden_set_file}")
            return {"error": "File not found"}

        with open(self.golden_set_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            questions = data
            benchmark_name = "Golden Set (15 Benchmark Questions)"
        else:
            questions = data.get("questions", [])
            benchmark_name = data.get("benchmark_name", "Golden Set")

        total = len(questions)
        passed = 0
        failed = 0
        results = []

        print(f"\n=======================================================")
        print(f" Running Golden Set Evaluation ({total} test cases)")
        print(f" Benchmark: {benchmark_name}")
        print(f"=======================================================")

        for q in questions:
            qid = q.get("id")
            category = q.get("category")
            prompt = q.get("question")
            is_refusal = q.get("is_not_found", False)
            expected = q.get("expected_answer")

            start_t = time.perf_counter()
            actual_answer = model.answer_question(q)
            latency_ms = round((time.perf_counter() - start_t) * 1000, 2)

            # Verification Logic
            test_passed = False
            notes = ""

            if is_refusal:
                # Check if model correctly refused to answer
                refusal_phrases = ["not specified", "not found", "cannot be determined", "does not mention"]
                if any(p in actual_answer.lower() for p in refusal_phrases):
                    test_passed = True
                    notes = "Correctly refused unanswerable trap question."
                else:
                    test_passed = False
                    notes = "HALLUCINATION: Model answered when it should have refused."
            else:
                # Check for answer alignment
                if actual_answer.strip() == expected.strip():
                    test_passed = True
                    notes = "Exact expected match."
                elif any(word in actual_answer.lower() for word in expected.lower().split()[:3]):
                    test_passed = True
                    notes = "Keyword match passed."
                else:
                    test_passed = False
                    notes = "Mismatch with expected answer."

            if test_passed:
                passed += 1
                status_str = "[PASS]"
            else:
                failed += 1
                status_str = "[FAIL]"

            print(f"{status_str} {qid} ({category}): {notes} ({latency_ms}ms)")

            results.append({
                "id": qid,
                "category": category,
                "status": "PASS" if test_passed else "FAIL",
                "is_refusal_test": is_refusal,
                "notes": notes,
                "latency_ms": latency_ms
            })

        pass_rate = round((passed / total) * 100, 1) if total > 0 else 0
        summary = {
            "total_questions": total,
            "passed": passed,
            "failed": failed,
            "pass_rate_pct": pass_rate,
            "results": results
        }

        print("-------------------------------------------------------")
        print(f"Results Summary: {passed}/{total} Passed ({pass_rate}%)")
        print("-------------------------------------------------------\n")
        return summary

    def run_intake_prompt_eval(self, model: MockModel) -> Dict[str, Any]:
        """Evaluates Intake prompt metadata extraction on sample RFP fixtures."""
        fixtures = [
            ("rfp_sample_01.txt", "expected_intake_01.json"),
            ("rfp_sample_02.txt", "expected_intake_02.json")
        ]

        print(f"=======================================================")
        print(f" Running Intake Prompt Fixture Checks ({len(fixtures)} fixtures)")
        print(f"=======================================================")

        intake_results = []
        for rfp_file, expected_file in fixtures:
            rfp_path = os.path.join(self.fixtures_dir, rfp_file)
            expected_path = os.path.join(self.fixtures_dir, expected_file)

            if not os.path.exists(rfp_path) or not os.path.exists(expected_path):
                print(f"[SKIP] Fixture {rfp_file} missing.")
                continue

            with open(rfp_path, "r", encoding="utf-8") as f:
                rfp_text = f.read()
            with open(expected_path, "r", encoding="utf-8") as f:
                expected_data = json.load(f)

            extracted = model.extract_intake_metadata(rfp_text)

            # Validate key schema fields
            client_match = extracted.get("clientName") == expected_data.get("clientName")
            deadline_match = extracted.get("submissionDeadline") == expected_data.get("submissionDeadline")
            domain_match = extracted.get("domain") == expected_data.get("domain")

            all_matched = client_match and deadline_match and domain_match
            status = "PASS" if all_matched else "FAIL"

            print(f"[{status}] Fixture: {rfp_file}")
            print(f"       Client: {extracted.get('clientName')} | Deadline: {extracted.get('submissionDeadline')} | Domain: {extracted.get('domain')}")

            intake_results.append({
                "fixture": rfp_file,
                "status": status,
                "client_match": client_match,
                "deadline_match": deadline_match,
                "domain_match": domain_match
            })

        print("-------------------------------------------------------\n")
        return {"fixtures_evaluated": len(intake_results), "details": intake_results}

    def save_report(self, report_data: Dict[str, Any], output_filename: str = "eval_results.json"):
        """Persists the evaluation output to disk."""
        output_path = os.path.join(self.base_dir, output_filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        print(f"[OK] Evaluation report saved to: {output_path}")


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    harness = EvaluationHarness(base_dir)
    model = MockModel(simulate_flaws=False)

    golden_summary = harness.run_golden_set_eval(model)
    intake_summary = harness.run_intake_prompt_eval(model)

    final_report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "author": "Likhitha Yada",
        "golden_set_eval": golden_summary,
        "intake_eval": intake_summary
    }

    harness.save_report(final_report)


if __name__ == "__main__":
    main()
