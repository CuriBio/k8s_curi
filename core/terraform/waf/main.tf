# =============================================================================
#  AWS WAF — Tier 1 baseline (+ PHP, + Windows), COUNT MODE
# =============================================================================
#
#  WHAT THIS BUILDS
#    Two WAF Web ACLs, matching our two internet-facing front doors:
#      1. REGIONAL   -> attached to the ALB that fronts our APIs
#      2. CLOUDFRONT -> attached to the CloudFront distribution (the website)
#    Both get the same Tier 1 managed rule groups plus PHP and Windows
#    protection. Everything is deployed in COUNT mode (logs what it *would*
#    have blocked, blocks nothing), so applying this cannot break production.
#
#  HOW TO READ THIS FILE
#    - Every spot that needs a value specific to OUR environment is marked:
#          # >>> CONFIGURE: <what to set>
#      Search the file for "CONFIGURE" to find them all.
#    - "COUNT MODE" appears wherever a rule is deliberately non-blocking.
#      Promoting a rule to Block later is a one-line change, noted inline.
#
#  WHAT IS INTENTIONALLY NOT HERE (Tier 2 / Tier 3 — decide later)
#    Bot Control, Account Takeover Prevention (ATP), Account Creation Fraud
#    Prevention (ACFP), Anonymous IP list, Geographic restriction. Those are
#    either paid, or need environment facts we haven't settled, or (ATP/ACFP)
#    need per-endpoint configuration. They are deliberately excluded here.
#
#  ONE SIMPLIFICATION TO KNOW ABOUT
#    The wizard lists separate "GET" and "POST/PUT/DELETE" rate limits. Here we
#    ship a global rate limit plus an auth-endpoint rate limit (the one that
#    actually matters for brute force). Adding method-specific limits is easy;
#    the pattern is shown in a comment on the auth rule below.
# =============================================================================


# -----------------------------------------------------------------------------
#  PROVIDERS
#
#  WHY TWO PROVIDERS:
#  A CLOUDFRONT-scoped Web ACL and any IP sets it references MUST be created in
#  us-east-1, regardless of where the rest of our infrastructure lives. This is
#  a hard AWS requirement, not a preference. REGIONAL resources (for the ALB)
#  live in the ALB's own region. So we declare a default provider for the ALB
#  region and an aliased provider pinned to us-east-1 for the CloudFront pieces.
# -----------------------------------------------------------------------------
terraform {
  required_version = ">= 1.5.2"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.98.0"    # Pin the major version. WAF resource schemas (esp.
                          # ATP/ACFP config blocks, added later) have changed
                          # across provider versions, so pinning avoids surprises.
    }
  }
}

provider "aws" {
  region = var.aws_region
}

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1" # Required for CLOUDFRONT-scoped WAF resources. Do not change.
}

data "aws_region" "current" {}
data "aws_partition" "current" {}
data "aws_caller_identity" "current" {}

# -----------------------------------------------------------------------------
#  LOCALS — the shared list of AWS Managed rule groups
#
#  WHY A LIST + dynamic BLOCK:
#  Both Web ACLs use the exact same managed groups. Defining them once here (and
#  expanding them with a `dynamic "rule"` block in each Web ACL) keeps the two
#  ACLs from drifting apart. Each entry is a free, "works out of the box" group:
#  AWS maintains the signatures; we supply nothing but the on/off decision and
#  a priority. (Priorities set evaluation ORDER and must be unique per Web ACL.)
# -----------------------------------------------------------------------------
locals {
  # Always-on Tier 1 groups.
  base_managed_groups = [
    { group = "AWSManagedRulesCommonRuleSet", priority = 100, metric = "core_rule_set" },
    { group = "AWSManagedRulesKnownBadInputsRuleSet", priority = 110, metric = "known_bad_inputs" },
    { group = "AWSManagedRulesSQLiRuleSet", priority = 120, metric = "sqli" },
    { group = "AWSManagedRulesLinuxRuleSet", priority = 130, metric = "linux" },
    { group = "AWSManagedRulesUnixRuleSet", priority = 140, metric = "posix" },
    { group = "AWSManagedRulesAdminProtectionRuleSet", priority = 150, metric = "admin_protection" },
    { group = "AWSManagedRulesAmazonIpReputationList", priority = 160, metric = "ip_reputation" },
  ]

  # Header keys are matched lowercase. Writing "Authorization" silently
  # protects nothing, so normalise here. Query argument names stay as-is,
  # since those are case-sensitive.
  data_protections = [
    for p in var.data_protections : merge(p, {
      field_keys = (
        p.field_type == "SINGLE_HEADER" && p.field_keys != null
        ? [for k in p.field_keys : lower(k)]
        : p.field_keys
      )
    })
  ]

  # Toggleable groups, appended only when their variable is true.
  optional_managed_groups = concat(
    var.enable_php_protection ? [{ group = "AWSManagedRulesPHPRuleSet", priority = 170, metric = "php" }] : [],
    var.enable_windows_protection ? [{ group = "AWSManagedRulesWindowsRuleSet", priority = 180, metric = "windows" }] : [],
  )

  managed_groups = concat(local.base_managed_groups, local.optional_managed_groups)
}

# -----------------------------------------------------------------------------
#  IP SETS (manual blocklist)
#
#  Scope-specific: an IP set used by a REGIONAL Web ACL must be REGIONAL, and one
#  used by a CLOUDFRONT Web ACL must be created in us-east-1. Hence two of them.
#
#  NOTE ON "IP ALLOWLIST": we deliberately do NOT build an allow-only gate. On a
#  public site an allow-*only* rule locks out everyone not listed. If you ever
#  need to exempt specific IPs from other rules, do it as a scope-down exception,
#  not as a standalone allow rule. Left out here on purpose.
# -----------------------------------------------------------------------------
resource "aws_wafv2_ip_set" "blocklist_regional" {
  name               = "manual-blocklist-regional"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = var.blocklist_ip_addresses
}

resource "aws_wafv2_ip_set" "blocklist_cloudfront" {
  provider           = aws.us_east_1 # CLOUDFRONT scope -> must be us-east-1
  name               = "manual-blocklist-cloudfront"
  scope              = "CLOUDFRONT"
  ip_address_version = "IPV4"
  addresses          = var.blocklist_ip_addresses
}


# =============================================================================
#  WEB ACL #1 — REGIONAL, for the ALB / APIs  (the higher-risk surface)
# =============================================================================
resource "aws_wafv2_web_acl" "api" {
  name  = "api-tier1-count"
  scope = "REGIONAL"

  # default_action = allow: this is a public API. WAF rules subtract from that
  # by matching bad traffic. Never set this to block {} on a public endpoint —
  # that denies everything not explicitly allowed.
  default_action {
    allow {}
  }

  # --- Custom rules first (low priority numbers = evaluated earliest) ---

  # Manual IP blocklist. In Count it only tags; flip to block {} to enforce.
  rule {
    name     = "manual-ip-blocklist"
    priority = 1
    action {
      count {} # COUNT MODE. -> To enforce later: replace with `block {}`.
    }
    statement {
      ip_set_reference_statement {
        arn = aws_wafv2_ip_set.blocklist_regional.arn
      }
    }
    visibility_config {
      sampled_requests_enabled   = true # REQUIRED to review what Count caught.
      cloudwatch_metrics_enabled = true
      metric_name                = "manual_ip_blocklist"
    }
  }

  # Global rate limit — gross-abuse ceiling across all traffic.
  rule {
    name     = "global-rate-limit"
    priority = 2
    action {
      count {} # COUNT MODE. Note: rate-based rules use `action`, NOT
               # `override_action`. override_action is only for managed groups.
    }
    statement {
      rate_based_statement {
        limit              = var.global_rate_limit
        aggregate_key_type = "IP"
        # evaluation_window_sec omitted -> defaults to 300 (5 min).
      }
    }
    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "global_rate_limit"
    }
  }

  # Auth-endpoint rate limit — the brute-force throttle. The scope_down_statement
  # restricts this tight limit to just the auth paths; without it, this low
  # threshold would apply to ALL traffic.
  #
  # TO ALSO NARROW BY METHOD (reproduce the wizard's POST/PUT/DELETE limit):
  # wrap the scope-down in an and_statement combining the path match below with
  # an or_statement of byte_match_statements on field_to_match { method {} }
  rule {
    name     = "auth-endpoint-rate-limit"
    priority = 3
    action {
      count {} # COUNT MODE. This is the rule to watch most closely in the data.
    }
    statement {
      rate_based_statement {
        limit                 = var.auth_rate_limit
        aggregate_key_type    = "IP"
        evaluation_window_sec = var.auth_rate_eval_window
        scope_down_statement {
          byte_match_statement {
            search_string         = var.auth_path_prefix # >>> CONFIGURE via var.auth_path_prefix
            positional_constraint = "STARTS_WITH"
            field_to_match {
              uri_path {}
            }
            text_transformation {
              priority = 0
              type     = "LOWERCASE" # normalize so /API/Auth also matches
            }
          }
        }
      }
    }
    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "auth_endpoint_rate_limit"
    }
  }

  # Body size restriction. oversize_handling = MATCH means bodies larger than
  # WAF's inspection limit are treated as matching (i.e., flagged), which is the
  # behavior you want for a size cap.
  rule {
    name     = "body-size-restriction"
    priority = 4
    action {
      count {} # COUNT MODE.
    }
    statement {
      size_constraint_statement {
        comparison_operator = "GT"
        size                = var.max_body_size_bytes
        field_to_match {
          body {
            oversize_handling = "MATCH"
          }
        }
        text_transformation {
          priority = 0
          type     = "NONE"
        }
      }
    }
    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "body_size_restriction"
    }
  }

  # --- AWS Managed rule groups (expanded from the shared locals list) ---
  # override_action { count {} } puts the ENTIRE group in Count. Later, to let a
  # group enforce, change it to `none {}` (which lets the group's own per-rule
  # actions apply). You can also keep the group enforcing but Count just one
  # noisy sub-rule via a rule_action_override block inside the statement.
  dynamic "rule" {
    for_each = { for g in local.managed_groups : g.group => g }
    content {
      name     = rule.value.group
      priority = rule.value.priority
      override_action {
        count {} # COUNT MODE for the whole group. -> enforce later: `none {}`.
      }
      statement {
        managed_rule_group_statement {
          vendor_name = "AWS"
          name        = rule.value.group
        }
      }
      visibility_config {
        sampled_requests_enabled   = true
        cloudwatch_metrics_enabled = true
        metric_name                = rule.value.metric
      }
    }
  }

  dynamic "data_protection_config" {
    for_each = length(var.data_protections) > 0 ? [1] : []

    content {
      dynamic "data_protection" {
        for_each = local.data_protections

        content {
          action                     = data_protection.value.action
          exclude_rule_match_details = data_protection.value.exclude_rule_match_details
          exclude_rate_based_details = data_protection.value.exclude_rate_based_details

          field {
            field_type = data_protection.value.field_type
            field_keys = data_protection.value.field_keys
          }
        }
      }
    }
  }

  visibility_config {
    sampled_requests_enabled   = true
    cloudwatch_metrics_enabled = true
    metric_name                = "api_tier1_count"
  }

  # WCU NOTE: each managed group + rule consumes Web ACL Capacity Units. The
  # default ceiling is 1,500 per Web ACL; this set fits, but if you later add
  # more groups you may need an AWS limit-increase request.
}

# Attach the REGIONAL Web ACL to the ALB. (CloudFront attaches differently —
# see below. This association resource is ONLY for ALB/API Gateway/etc.)
resource "aws_wafv2_web_acl_association" "api" {
  resource_arn = var.alb_arn # >>> CONFIGURE via var.alb_arn
  web_acl_arn  = aws_wafv2_web_acl.api.arn
}


# =============================================================================
#  WEB ACL #2 — CLOUDFRONT, for the website
#  Same managed groups; custom rules mirror the API ACL (lighter comments — see
#  the API ACL above for the full rationale). Created via the us-east-1 provider.
# =============================================================================
resource "aws_wafv2_web_acl" "website" {
  provider = aws.us_east_1 # Mandatory for CLOUDFRONT scope.
  name     = "website-tier1-count"
  scope    = "CLOUDFRONT"

  default_action {
    allow {}
  }

  rule {
    name     = "manual-ip-blocklist"
    priority = 1
    action {
      count {} # COUNT MODE.
    }
    statement {
      ip_set_reference_statement {
        arn = aws_wafv2_ip_set.blocklist_cloudfront.arn
      }
    }
    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "manual_ip_blocklist"
    }
  }

  rule {
    name     = "global-rate-limit"
    priority = 2
    action {
      count {} # COUNT MODE.
    }
    statement {
      rate_based_statement {
        limit              = var.global_rate_limit
        aggregate_key_type = "IP"
      }
    }
    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "global_rate_limit"
    }
  }

  # No auth-endpoint rate rule here: login/change-password are API concerns and
  # live behind the ALB. Add one only if the website itself serves auth paths.

  rule {
    name     = "body-size-restriction"
    priority = 4
    action {
      count {} # COUNT MODE.
    }
    statement {
      size_constraint_statement {
        comparison_operator = "GT"
        size                = var.max_body_size_bytes
        field_to_match {
          body {
            oversize_handling = "MATCH"
          }
        }
        text_transformation {
          priority = 0
          type     = "NONE"
        }
      }
    }
    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "body_size_restriction"
    }
  }

  dynamic "rule" {
    for_each = { for g in local.managed_groups : g.group => g }
    content {
      name     = rule.value.group
      priority = rule.value.priority
      override_action {
        count {} # COUNT MODE for the whole group.
      }
      statement {
        managed_rule_group_statement {
          vendor_name = "AWS"
          name        = rule.value.group
        }
      }
      visibility_config {
        sampled_requests_enabled   = true
        cloudwatch_metrics_enabled = true
        metric_name                = rule.value.metric
      }
    }
  }

  visibility_config {
    sampled_requests_enabled   = true
    cloudwatch_metrics_enabled = true
    metric_name                = "website_tier1_count"
  }
}

data "aws_iam_policy_document" "waf_logs_website" {
  statement {
    sid    = "AWSLogDeliveryWrite"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["delivery.logs.amazonaws.com"]
    }

    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.waf_website.arn}:*"]

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }

    condition {
      # Hardcoded us-east-1, NOT data.aws_region.current.name — that data source
      # reads the default provider (us-east-2) and would produce a condition
      # that never matches, reproducing this same silent failure.
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:${data.aws_partition.current.partition}:logs:us-east-1:${data.aws_caller_identity.current.account_id}:*"]
    }
  }
}

resource "aws_cloudwatch_log_resource_policy" "waf_website" {
  provider        = aws.us_east_1
  policy_name     = "waf_website-logs"
  policy_document = data.aws_iam_policy_document.waf_logs_website.json
}

resource "aws_wafv2_web_acl_logging_configuration" "website" {
  provider                = aws.us_east_1
  resource_arn            = aws_wafv2_web_acl.website.arn
  log_destination_configs = [aws_cloudwatch_log_group.waf_website.arn]

  depends_on = [aws_cloudwatch_log_resource_policy.waf_website]
}

# HOW CLOUDFRONT ATTACHES (different from ALB):
# CloudFront does NOT use an aws_wafv2_web_acl_association resource. Instead you
# set web_acl_id on the distribution itself:
#
#   resource "aws_cloudfront_distribution" "site" {
#     # ...
#     web_acl_id = aws_wafv2_web_acl.website.arn   # note: the ARN, not the ID
#   }
#
# Left commented because the distribution is likely managed elsewhere.
# >>> CONFIGURE: wire aws_wafv2_web_acl.website.arn into your distribution.


# =============================================================================
#  LOGGING — send WAF logs (including Count matches) to CloudWatch Logs
#
#  This is what makes the Count period useful: it's how you review what each
#  rule WOULD have blocked. From here you can also forward to S3 / the SIEM.
#
#  GOTCHA: the log group name MUST start with "aws-waf-logs-" or the logging
#  configuration API rejects it.
# =============================================================================
resource "aws_cloudwatch_log_group" "waf_api" {
  #count = var.enable_logging ? 1 : 0
  name              = "aws-waf-logs-api-tier1"
  retention_in_days = 90 # >>> CONFIGURE: set the retention you want to state (days).
}

# WAF delivers logs via the CloudWatch Logs delivery service, which needs an
# explicit resource policy on the log group. The console adds this for you;
# Terraform does not, and without it the logging configuration fails.
data "aws_iam_policy_document" "waf_logs" {
  #count = var.enable_logging ? 1 : 0

  statement {
    sid    = "AWSLogDeliveryWrite"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["delivery.logs.amazonaws.com"]
    }

    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.waf_api.arn}:*"]

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:${data.aws_partition.current.partition}:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"]
    }
  }
}

resource "aws_cloudwatch_log_resource_policy" "waf_api" {
  #count = var.enable_logging ? 1 : 0
  policy_name     = "waf_api-logs"
  policy_document = data.aws_iam_policy_document.waf_logs.json
}

resource "aws_wafv2_web_acl_logging_configuration" "api" {
  #count = var.enable_logging ? 1 : 0

  resource_arn            = aws_wafv2_web_acl.api.arn
  log_destination_configs = [aws_cloudwatch_log_group.waf_api.arn]

  dynamic "logging_filter" {
    for_each = var.log_blocked_requests_only ? [1] : []

    content {
      default_behavior = "DROP"

      filter {
        behavior    = "KEEP"
        requirement = "MEETS_ANY"

        condition {
          action_condition {
            action = "BLOCK"
          }
        }
      }
    }
  }

  # Header names must be lowercase to match what WAF stores.
  dynamic "redacted_fields" {
    for_each = var.redacted_header_names

    content {
      single_header {
        name = lower(redacted_fields.value)
      }
    }
  }

  depends_on = [aws_cloudwatch_log_resource_policy.waf_api]
}

resource "aws_cloudwatch_log_group" "waf_website" {
  provider          = aws.us_east_1 # keep alongside the CLOUDFRONT Web ACL
  name              = "aws-waf-logs-website-tier1"
  retention_in_days = 90 # >>> CONFIGURE.
}
