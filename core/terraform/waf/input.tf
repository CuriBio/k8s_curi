variable "aws_region" {
  description = "Region of the ALB (REGIONAL Web ACL lives here). CONFIGURE."
  type        = string
  default     = "us-east-2"
}

variable "alb_arn" {
  description = "ARN of the ALB to attach the REGIONAL Web ACL to. CONFIGURE."
  type        = string
  # No default on purpose — you must supply this, or comment out the
  # aws_wafv2_web_acl_association.api resource below if the ALB is managed
  # elsewhere and you'll wire up the association separately.
  # >>> CONFIGURE: e.g. "arn:aws:elasticloadbalancing:us-east-1:1234:loadbalancer/app/my-alb/abc123"
}

variable "enable_logging" {
  description = "Create a CloudWatch log group (named aws-waf-logs-<name>) plus its resource policy, and enable WAF logging to it."
  type        = bool
  default     = true
}

variable "log_blocked_requests_only" {
  description = "Log only requests that were blocked. Cuts log volume sharply, at the cost of losing the allowed-request record you need for tuning."
  type        = bool
  default     = false
}

# --- OS/application groups we can toggle ---
variable "enable_php_protection" {
  description = "PHP rule group. Keep true only if ANY PHP exists in the request path behind these WAFs."
  type        = bool
  default     = true # Requested. If we confirm zero PHP anywhere, set false.
}

variable "enable_windows_protection" {
  description = "Windows rule group. Strip out (set false) once confirmed unneeded."
  type        = bool
  default     = true # Requested as a placeholder. Likely -> false after review.
}

# --- Rate-limit thresholds ---
# These are COUNT-mode starting values. In Count the exact number does not gate
# anyone; it's just the line above which requests get tagged in the logs. Ship
# these, watch the Count data, then set real numbers before flipping to Block.
variable "global_rate_limit" {
  description = "Requests per evaluation window, per IP, across all traffic. Loose on purpose."
  type        = number
  default     = 2000 # Valid range is 10 .. 2,000,000,000 (min lowered from 100 in Aug 2024).
}

variable "auth_rate_limit" {
  description = "Requests per window, per IP, to auth endpoints. The brute-force throttle — tune this most carefully."
  type        = number
  default     = 100 # Humans don't hit login/change-password 100x in a window; real bots do.
}

variable "auth_rate_eval_window" {
  description = "Evaluation window (seconds) for the auth rate rule. Valid: 60, 120, 300, 600."
  type        = number
  default     = 60 # Shorter window surfaces brute-force bursts faster. Default WAF window is 300.
}

variable "auth_path_prefix" {
  description = "URI path prefix identifying auth endpoints (login, change-password, etc.). CONFIGURE."
  type        = string
  default     = "/api/auth/" # >>> CONFIGURE: set to the real prefix your auth endpoints share.
}

# --- Body size ---
variable "max_body_size_bytes" {
  description = "Flag request bodies larger than this many bytes."
  type        = number
  default     = 10240 # 10 KB. Raise if you have legitimate large JSON/uploads on these paths.
}

# --- Manual IP blocklist ---
variable "blocklist_ip_addresses" {
  description = "IPs/CIDRs to block outright. Starts empty; add reactively."
  type        = list(string)
  default     = [] # >>> CONFIGURE (as needed): e.g. ["203.0.113.10/32", "198.51.100.0/24"]
}

# -- redact sensitive info --
variable "redacted_header_names" {
  description = "Request headers to redact from the logs, e.g. [\"authorization\", \"cookie\"]. Names are lowercased automatically."
  type        = list(string)
  default = [
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
    "x-amz-security-token"
  ]
}

variable "data_protections" {
  description = <<-EOT
    Web ACL level data protection. Requires provider >= 5.98.0.

    Unlike logging redaction this also covers sampled requests and the BODY
    field, and it applies to every collection path (logs, sampling, Security
    Lake). Max 26 entries.

      field_type - SINGLE_HEADER | SINGLE_COOKIE | SINGLE_QUERY_ARGUMENT |
                   QUERY_STRING | BODY
      field_keys - required for the SINGLE_* types, must be omitted for
                   QUERY_STRING and BODY
      action     - SUBSTITUTION (constant placeholder) or HASH (stable hash,
                   still correlatable across requests)
  EOT

  type = list(object({
    action                     = optional(string, "SUBSTITUTION")
    field_type                 = string
    field_keys                 = optional(list(string))
    exclude_rule_match_details = optional(bool, false)
    exclude_rate_based_details = optional(bool, false)
  }))

  default = []

  validation {
    condition     = length(var.data_protections) <= 26
    error_message = "A web ACL supports at most 26 data protection entries."
  }

  validation {
    condition     = alltrue([for p in var.data_protections : contains(["SUBSTITUTION", "HASH"], p.action)])
    error_message = "action must be \"SUBSTITUTION\" or \"HASH\"."
  }

  validation {
    condition = alltrue([
      for p in var.data_protections :
      contains(["SINGLE_HEADER", "SINGLE_COOKIE", "SINGLE_QUERY_ARGUMENT", "QUERY_STRING", "BODY"], p.field_type)
    ])
    error_message = "field_type must be one of: SINGLE_HEADER, SINGLE_COOKIE, SINGLE_QUERY_ARGUMENT, QUERY_STRING, BODY."
  }

  validation {
    condition = alltrue([
      for p in var.data_protections :
      startswith(p.field_type, "SINGLE_") ? (p.field_keys != null && length(p.field_keys) > 0) : p.field_keys == null
    ])
    error_message = "field_keys is required for SINGLE_HEADER, SINGLE_COOKIE and SINGLE_QUERY_ARGUMENT, and must be omitted for QUERY_STRING and BODY."
  }
}
