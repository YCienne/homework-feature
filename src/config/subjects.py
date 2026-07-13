from dataclasses import dataclass, field
from typing import List


@dataclass
class SubjectConfig:
    keywords: List[str]
    default_max_steps: int
    curriculum_context: str


SUBJECTS: dict[str, SubjectConfig] = {
    "math": SubjectConfig(
        keywords=[
            "calculate", "solve", "equation", "fraction", "percentage", "area",
            "multiply", "divide", "algebra", "geometry", "triangle", "square",
            "angle", "volume", "perimeter", "ratio", "proportion", "integer",
            "decimal", "exponent", "root", "derivative", "integral", "matrix",
        ],
        default_max_steps=5,
        curriculum_context=(
            "Focus on showing working step by step. "
            "Do not skip steps. Always define variables before using them."
        ),
    ),
    "science": SubjectConfig(
        keywords=[
            "photosynthesis", "atom", "cell", "energy", "force", "gravity",
            "chemical", "reaction", "biology", "physics", "organism", "molecule",
            "element", "compound", "ecosystem", "evolution", "DNA", "velocity",
            "acceleration", "mass", "density", "pressure", "temperature",
        ],
        default_max_steps=5,
        curriculum_context=(
            "Use age-appropriate scientific language. "
            "Define technical terms before using them. Use real-world examples."
        ),
    ),
    "english": SubjectConfig(
        keywords=[
            "grammar", "sentence", "verb", "noun", "essay", "paragraph",
            "punctuation", "synonym", "meaning", "spelling", "adjective",
            "adverb", "tense", "clause", "metaphor", "simile", "theme",
            "character", "plot", "narrative", "comprehension", "vocabulary",
        ],
        default_max_steps=4,
        curriculum_context=(
            "Focus on language rules and structure. "
            "Give clear examples. Correct gently and explain why."
        ),
    ),
    "history": SubjectConfig(
        keywords=[
            "when", "year", "who", "event", "war", "revolution", "century",
            "cause", "effect", "period", "dynasty", "empire", "colony",
            "independence", "apartheid", "democracy", "treaty", "constitution",
        ],
        default_max_steps=4,
        curriculum_context=(
            "Encourage the student to think about causes and effects. "
            "Relate events to their historical context."
        ),
    ),
    "general": SubjectConfig(
        keywords=[],
        default_max_steps=4,
        curriculum_context=(
            "Break the problem into logical steps. "
            "Keep explanations simple and clear."
        ),
    ),
}
