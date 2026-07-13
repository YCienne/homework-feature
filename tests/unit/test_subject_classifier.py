from src.core.validator.subject_classifier import classify_subject


def test_math(): assert classify_subject("How do I solve this fraction equation?")[0] == "math"
def test_science(): assert classify_subject("Explain photosynthesis in plant cells")[0] == "science"
def test_english(): assert classify_subject("What is the difference between a verb and noun?")[0] == "english"
def test_history(): assert classify_subject("What caused the revolution last century?")[0] == "history"
def test_general_fallback(): assert classify_subject("Help me understand this")[0] == "general"

def test_config_returned():
    _, config = classify_subject("Calculate the area of a triangle")
    assert config.default_max_steps > 0 and config.curriculum_context != ""
