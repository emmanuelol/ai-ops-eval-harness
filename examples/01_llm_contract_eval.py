#!/usr/bin/env python3
"""Example 01: LLM Prompt Contract Assertion, Telemetry, and Blast Shield Isolation.

Demonstrates:
1. Simulating an LLM pipeline with telemetry token tracking.
2. Intercepting outbound notifications with BlastShield.
3. Asserting decoupled JSON contracts and ultra-concise disclosure.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from ai_ops_eval_harness import (
    BlastShield,
    assert_decoupled_json_contract,
    assert_prompt_context_integrity,
    assert_ultra_concise_disclosure,
    track_llm_telemetry,
)


def run_llm_evaluation() -> None:
    print("--- 1. Evaluating Prompt Context Integrity ---")
    prompt = (
        "=== SYSTEM PROMPT ===\n"
        "<CONTEXT>\n"
        "Store ID: 1042\n"
        "Date: 2026-10-22\n"
        "</CONTEXT>\n"
        "Generate a 3-bullet executive operational summary."
    )

    assert_prompt_context_integrity(
        prompt_context=prompt,
        required_markers=["=== SYSTEM PROMPT ===", "<CONTEXT>", "Store ID: 1042"],
        forbidden_markers=["<SECRET_KEY>", "API_KEY"],
    )
    print("✅ Prompt context verified: all required markers present, no secrets leaked.")

    print("\n--- 2. Executing Mock LLM Inference with Telemetry & Blast Shield ---")

    @track_llm_telemetry(retries=2, base_backoff=0.01)
    def mock_llm_call(prompt_text: str) -> dict[str, str]:
        # Simulate outbound alert protected by BlastShield
        with BlastShield(simulate_success=True) as shield:
            shield.record_dispatch(
                destination="+1-555-0199",
                payload={"event": "EVAL_START", "prompt_len": len(prompt_text)},
            )
            print(f"   [BlastShield] Intercepted outbound dispatch: {shield.intercepted_calls[0]['destination']}")

        # Simulated response from LLM
        return {
            "status": "success",
            "text": (
                "Resumen operativo:\n"
                "* Ventas consolidadas: $14,250.00 (+4.2% DoD)\n"
                "* Transacciones procesadas: 312\n"
                "* Ratio de cancelaciones: 0.8% (dentro de tolerancia)"
            ),
        }

    response = mock_llm_call(prompt)

    print("\n--- 3. Asserting Response Contracts ---")
    # Verify strict decoupled JSON schema
    assert_decoupled_json_contract(response)
    print("✅ Decoupled JSON contract passed: valid status and text payload.")

    # Verify UX progressive disclosure (max bullets, no unexpected markdown tables)
    disclosure_meta = assert_ultra_concise_disclosure(
        text=response["text"],
        user_prompt="Dame el resumen diario de la tienda",
        max_bullet_points=4,
    )
    print(f"✅ Progressive disclosure passed: {disclosure_meta['bullet_count']} bullets detected.")


if __name__ == "__main__":
    run_llm_evaluation()
