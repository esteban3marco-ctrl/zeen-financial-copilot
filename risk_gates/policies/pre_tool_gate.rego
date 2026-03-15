package staq.gates.pre_tool

import rego.v1

default decision := {
    "action": "allow",
    "reason": "Tool execution authorized",
}

# --- TOOL WHITELIST PER ROLE ---

tool_whitelist := {
    "anonymous": {"market_data_lookup", "currency_converter"},
    "basic":     {"market_data_lookup", "currency_converter", "portfolio_view",
                  "expense_tracker", "budget_calculator"},
    "premium":   {"market_data_lookup", "currency_converter", "portfolio_view",
                  "expense_tracker", "budget_calculator", "financial_report",
                  "tax_estimator", "investment_screener"},
    "advisor":   {"market_data_lookup", "currency_converter", "portfolio_view",
                  "expense_tracker", "budget_calculator", "financial_report",
                  "tax_estimator", "investment_screener", "client_portfolio",
                  "compliance_check", "trade_executor"},
    "admin":     {"*"},
}

tool_authorized if {
    role_tools := tool_whitelist[input.risk_context.user_role]
    role_tools[input.tool_name]
}

tool_authorized if {
    role_tools := tool_whitelist[input.risk_context.user_role]
    role_tools["*"]
}

# --- SANDBOX REQUIREMENT ---

sandbox_tools := {"code_executor", "python_sandbox", "script_runner"}

requires_sandbox if {
    sandbox_tools[input.tool_name]
}

# --- TOOL-LEVEL RATE LIMITS ---

tool_rate_limits := {
    "trade_executor":   5,
    "financial_report": 10,
    "code_executor":    20,
}

tool_rate_exceeded if {
    limit := tool_rate_limits[input.tool_name]
    input.risk_context.tools_called_in_window > limit
}

# --- PARAMETER SAFETY ---

dangerous_param_patterns := [
    `(?i)(DROP\s+TABLE|DELETE\s+FROM|INSERT\s+INTO|UPDATE\s+.*SET)`,
    `(?i)(;\s*--)`,
    `(?i)(\bunion\b.*\bselect\b)`,
]

has_dangerous_params if {
    some _key, value in input.tool_params
    is_string(value)
    some pattern in dangerous_param_patterns
    regex.match(pattern, value)
}

# --- MCP SERVER AUTHORIZATION ---

authorized_mcp_servers := {
    "financial-data-server",
    "supabase-server",
    "e2b-sandbox-server",
}

mcp_unauthorized if {
    mcp_server := input.tool_params.mcp_server
    mcp_server != null
    not authorized_mcp_servers[mcp_server]
}

# --- DECISIONS ---

decision := {
    "action": "deny",
    "reason": sprintf("Tool '%v' not authorized for role '%v'", [input.tool_name, input.risk_context.user_role]),
} if {
    not tool_authorized
}

decision := {
    "action": "deny",
    "reason": sprintf("Rate limit exceeded for tool '%v'", [input.tool_name]),
} if {
    tool_authorized
    tool_rate_exceeded
}

decision := {
    "action": "deny",
    "reason": "Dangerous parameter patterns detected (possible injection)",
} if {
    tool_authorized
    not tool_rate_exceeded
    has_dangerous_params
}

decision := {
    "action": "deny",
    "reason": sprintf("MCP server '%v' not authorized", [input.tool_params.mcp_server]),
} if {
    tool_authorized
    not tool_rate_exceeded
    not has_dangerous_params
    mcp_unauthorized
}
