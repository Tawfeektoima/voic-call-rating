from app.violations import VIOLATION_REGISTRY, get_penalty, build_violation_prompt

def test_registry_length():
    length = len(VIOLATION_REGISTRY)
    print(f"{length} violations loaded")
    assert length == 26, f"Expected 26 violations, got {length}"

def test_penalty_logic():
    # First offense abusive language → should be "2 HR", deduction 20, hr_flag True
    p = get_penalty("abusive_language", 1)
    assert p["penalty_tier"] == "2 HR"
    assert p["score_deduction"] == 20
    assert p["hr_flagged"] == True

    # First offense dead_air → should be "1 HR", deduction 5, hr_flag False
    p2 = get_penalty("dead_air", 1)
    assert p2["penalty_tier"] == "1 HR"
    assert p2["score_deduction"] == 5
    assert p2["hr_flagged"] == False

    # Third offense forced_sale → should be "3 HR"
    p3 = get_penalty("forced_sale", 3)
    assert p3["penalty_tier"] == "3 HR"

    print("All penalty tests passed")

def test_prompt_builder():
    prompt = build_violation_prompt("sales")
    assert "abusive_language" in prompt
    assert "skipped_offer" in prompt
    assert "HIGH" in prompt
    assert "MEDIUM" in prompt
    assert "LOW" in prompt
    print("Prompt builder generated expected sales prompt length:", len(prompt))

    non_sales_prompt = build_violation_prompt("customer_service")
    assert "skipped_offer" not in non_sales_prompt
    print("Prompt builder omitted sales-only violations in customer service prompt")

if __name__ == "__main__":
    test_registry_length()
    test_penalty_logic()
    test_prompt_builder()
