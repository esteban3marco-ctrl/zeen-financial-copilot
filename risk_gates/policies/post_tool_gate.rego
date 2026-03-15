package staq.gates.post_tool

import rego.v1

default decision := {
    "action": "allow",
    "reason": "Tool result passed all post-tool checks",
}

# --- SECRET DETECTION ---

secret_patterns := {
    "api_key":      `(?i)(api[_-]?key|apikey)\s*[:=]\s*[A-Za-z0-9_\-]{20,}`,
    "bearer_token": `(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}`,
    "aws_key":      `AKIA[0-9A-Z]{16}`,
    "private_key":  `-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----`,
    "password":     `(?i)(password|passwd|pwd)\s*[:=]\s*\S{6,}`,
    "supabase_key": `(?i)eyJ[A-Za-z0-9_\-]{30,}\.[A-Za-z0-9_\-]{30,}`,
}

result_str := sprintf("%v", [input.tool_result])

secrets_found contains secret_type if {
    some secret_type, pattern in secret_patterns
    regex.match(pattern, result_str)
}

# --- PII IN RESULTS ---

pii_in_result if {
    regex.match(`\b\d{3}-\d{2}-\d{4}\b`, result_str)
}

pii_in_result if {
    regex.match(`\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b`, result_str)
}

# --- DATA SIZE LIMITS ---

financial_data_row_limit := 500

data_too_large if {
    is_array(input.tool_result)
    count(input.tool_result) > financial_data_row_limit
}

data_too_large if {
    is_object(input.tool_result)
    rows := input.tool_result.rows
    is_array(rows)
    count(rows) > financial_data_row_limit
}

# --- OUTPUT SIZE ---

output_too_large if {
    count(result_str) > 500000
}

# --- DECISIONS ---

decision := {
    "action": "modify",
    "reason": sprintf("Secrets detected and must be redacted: %v", [concat(", ", secrets_found)]),
} if {
    count(secrets_found) > 0
}

decision := {
    "action": "modify",
    "reason": "PII detected in tool result, redaction required",
} if {
    count(secrets_found) == 0
    pii_in_result
}

decision := {
    "action": "modify",
    "reason": sprintf("Tool result exceeds %v row limit, truncation required", [financial_data_row_limit]),
} if {
    count(secrets_found) == 0
    not pii_in_result
    data_too_large
}

decision := {
    "action": "deny",
    "reason": "Tool output exceeds maximum allowed size (500KB)",
} if {
    count(secrets_found) == 0
    not pii_in_result
    not data_too_large
    output_too_large
}
