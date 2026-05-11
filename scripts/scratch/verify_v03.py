import sys
import os

# Mock groq to avoid Client.__init__ errors during test
import sys
from unittest.mock import MagicMock
sys.modules['groq'] = MagicMock()

# Ensure the root directory is in the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.analysis import build_system_message

def test_prompt_generation():
    msg = build_system_message(
        campaign_prompt="Evaluate for quality.",
        campaign_type="sales",
        agent_name="Ahmed"
    )
    
    assert "violation_id" in msg, "Missing violation_id in prompt"
    assert "flagged" not in msg, "Old format (flagged) is still in the prompt"
    assert "🔴 HIGH" in msg, "Missing high severity section"
    
    print("Prompt update verified")
    
    word_count = len(msg.split())
    assert word_count < 800, f"Prompt too long: {word_count} words. Should be under 800."
    print(f"Prompt word count: {word_count}")
    
if __name__ == "__main__":
    test_prompt_generation()

