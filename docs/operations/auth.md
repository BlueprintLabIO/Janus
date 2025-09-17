# Authentication & Authorization

## Overview

Janus uses a **dual-layer permission model**: input sources define trust levels, AI teammates define capabilities. Effective permissions are the intersection of both layers.

## Architecture

```
Input Source Permissions ∩ AI Teammate Permissions = Effective Permissions
```

### Input Sources
Each input source (Slack, API, webhooks) has its own permission profile:

```yaml
input_sources:
  slack_public:
    auth_method: "webhook_signature"
    permissions:
      tools: { allowed: ["web_search"], denied: ["filesystem"] }
      cost_limits: { max_per_request: 0.50 }
      
  admin_api:
    auth_method: "api_key" 
    permissions:
      tools: { allowed: ["*"] }
      cost_limits: { max_per_request: 10.00 }
```

### AI Teammate Instance
Each teammate instance defines its maximum capabilities:

```yaml
teammate:
  capabilities:
    tools: { available: ["web_search", "filesystem", "git"] }
    cost_limits: { daily_budget: 100.00 }
```

## Authentication Adapters

- **Slack**: Webhook signature validation
- **API**: Bearer token/API key validation  
- **GitHub**: Webhook signature validation
- **Email**: OAuth2 verification

## Permission Resolution

```javascript
effectivePermissions = intersect(inputPermissions, teammatePermissions)
```

## Request Flow

1. Input Gateway detects source type
2. Source-specific adapter validates authentication
3. Permission resolver calculates effective permissions
4. Unified request sent to orchestrator with resolved permissions

## Security Benefits

- **Defense in Depth**: Compromised input ≠ compromised teammate
- **Principle of Least Privilege**: Each source gets minimum necessary access
- **Clear Boundaries**: Trust (input) vs capability (teammate) separation
- **Auditability**: Full permission trace in request metadata