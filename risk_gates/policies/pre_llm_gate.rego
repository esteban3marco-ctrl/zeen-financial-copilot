package staq.gates.pre_llm

import rego.v1

default decision := {
    "action": "allow",
    "reason": "Input passed all pre-LLM checks",
}

# --- PII DETECTION ---

pii_patterns := {
    "ssn":         `\b\d{3}-\d{2}-\d{4}\b`,
    "credit_card": `\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b`,
    "iban":        `\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b`,
    "email":       `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`,
}

pii_found contains pii_type if {
    some pii_type, pattern in pii_patterns
    regex.match(pattern, input.user_input)
}

# --- PROMPT INJECTION DETECTION ---

injection_patterns := [
    `(?i)ignore\s+(previous|above|all)\s+(instructions|prompts)`,
    `(?i)you\s+are\s+now\s+`,
    `(?i)system\s*:\s*`,
    `(?i)act\s+as\s+(a\s+)?different`,
    `(?i)\<\|.*?\|\>`,
    `(?i)reveal\s+(your|the)\s+(system|initial)\s+prompt`,
]

injection_detected if {
    some pattern in injection_patterns
    regex.match(pattern, input.user_input)
}

# --- RATE LIMITING ---

rate_exceeded if {
    input.risk_context.requests_in_window > rate_limit_for_role[input.risk_context.user_role]
}

rate_limit_for_role := {
    "anonymous": 10,
    "basic":     30,
    "premium":   100,
    "advisor":   200,
    "admin":     500,
}

# --- INPUT LENGTH ---

input_too_long if {
    count(input.user_input) > 32000
}

# --- DECISION RULES (priority: deny > modify > allow) ---

decision := {
    "action": "deny",
    "reason": "Prompt injection detected",
} if {
    injection_detected
}

decision := {
    "action": "deny",
    "reason": "Rate limit exceeded for user role",
} if {
    not injection_detected
    rate_exceeded
}

decision := {
    "action": "deny",
    "reason": "Input exceeds maximum length",
} if {
    not injection_detected
    not rate_exceeded
    input_too_long
}

decision := {
    "action": "modify",
    "reason": sprintf("PII detected and redacted: %v", [concat(", ", pii_found)]),
} if {
    not injection_detected
    not rate_exceeded
    not input_too_long
    count(pii_found) > 0
}
