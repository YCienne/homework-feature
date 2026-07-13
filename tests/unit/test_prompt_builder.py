import pytest
from src.core.prompt.prompt_builder import build_prompt
from src.core.session.session_schema import Session, StepRecord


def make_session(**kw) -> Session:
    return Session(student_id="s-1", question_raw="What is gravity?",
                   question_clean="What is gravity?", subject="science",
                   topic="forces", max_steps_allowed=5, **kw)


def test_start_returns_messages():
    msgs = build_prompt("START", make_session())
    assert isinstance(msgs, list)
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
    assert "gravity" in msgs[0]["content"].lower()


def test_start_contains_no_answer():
    msgs = build_prompt("START", make_session())
    content = msgs[0]["content"].lower()
    assert "do not solve" in content or "never give" in content or "guide" in content


def test_continue_references_student_response():
    session = make_session(current_step_index=1)
    session.step_history.append(StepRecord(step_index=0, step_question="What do you know?", student_response="I know gravity pulls things down"))
    msgs = build_prompt("CONTINUE", session, student_response="I know gravity pulls things down")
    assert "gravity pulls things down" in msgs[0]["content"]


def test_im_not_sure_references_current_question():
    session = make_session()
    session.last_step_question = "What force keeps planets in orbit?"
    msgs = build_prompt("IM_NOT_SURE", session)
    assert "orbit" in msgs[0]["content"]


def test_explain_again_references_explanation():
    session = make_session()
    session.last_step_explanation = "Gravity is a force of attraction."
    session.last_step_question = "What is the formula?"
    msgs = build_prompt("EXPLAIN_AGAIN", session)
    assert "attraction" in msgs[0]["content"]


def test_invalid_action_raises():
    with pytest.raises(ValueError):
        build_prompt("INVALID", make_session())


def test_all_actions_return_messages():
    session = make_session()
    session.last_step_question = "Test question?"
    session.last_step_explanation = "Test explanation."
    for action in ["START", "IM_NOT_SURE", "SHOW_NEXT_STEP", "EXPLAIN_AGAIN", "FINALIZE"]:
        msgs = build_prompt(action, session)
        assert isinstance(msgs, list) and len(msgs) > 0
