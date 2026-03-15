package staq.gates.post_llm

import rego.v1

default decision := {
    "action": "allow",
    "reason": "LLM response passed all post-LLM checks",
}

# --- REGULATED ADVICE DETECTION ---

regulated_topic_patterns := [
    `(?i)\b(you\s+should\s+(buy|sell|invest|short))\b`,
    `(?i)\b(i\s+recommend\s+(buying|selling|investing))\b`,
    `(?i)\b(guaranteed\s+returns?)\b`,
    `(?i)\b(tax\s+advice\s*:)`,
    `(?i)\b(insurance\s+recommendation)\b`,
]

contains_regulated_advice if {
    some pattern in regulated_topic_patterns
    regex.match(pattern, input.llm_response)
}

user_is_advisor if {
    input.risk_context.user_role == "advisor"
}

# --- DISCLAIMER DETECTION ---

has_disclaimer if {
    regex.match(
        `(?i)(disclaimer|not\s+financial\s+advice|for\s+informational\s+purposes|consult\s+a\s+(licensed\s+)?financial\s+advisor)`,
        input.llm_response,
    )
}

# --- HALLUCINATION MARKERS ---

has_fabricated_numbers if {
    regex.match(`\$\d{1,3}(,\d{3})*(\.\d{2})?\s+(will|should|is going to)\b`, input.llm_response)
}

# --- RESPONSE LENGTH ---

response_too_long if {
    count(input.llm_response) > 64000
}

# --- DECISIONS ---

decision := {
    "action": "deny",
    "reason": "Response contains regulated financial advice without advisor role or disclaimer",
} if {
    contains_regulated_advice
    not user_is_advisor
    not has_disclaimer
}

decision := {
    "action": "modify",
    "reason": "Response may contain fabricated financial data",
    "compliance_flags": ["hallucination_risk"],
} if {
    not contains_regulated_advice
    has_fabricated_numbers
}

decision := {
    "action": "deny",
    "reason": "Response exceeds maximum allowed length",
} if {
    not contains_regulated_advice
    not has_fabricated_numbers
    response_too_long
}
