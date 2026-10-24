"""Решение по заявке. TODO (22 октября): make_decision() и save_assessment_and_events().

Цепочка: validate_application -> run_checks -> calculate_risk -> make_decision
-> save_assessment_and_events. При повторном рассмотрении создаётся НОВЫЙ Assessment.
"""


def make_decision(application, product, risk: dict) -> dict:
    raise NotImplementedError
