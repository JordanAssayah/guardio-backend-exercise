# PokeProxy Architecture

## System Architecture

[![](https://mermaid.ink/img/pako:eNqlVU1z2jAQ_SsaXWvAfKS1PZ3MpCQN7ZSGAdrp1OQg8GJ7YiRXlpLQhP9eWbKxDSQ51AeQdve9Xb1dy094xQLAHg45SSM0_7SgSD2ZXBrD1aMATklizPlzLQkPYuYX_2gU85iGaAb8Pl7BxyXvnEfa1IYC2w5NaDuA-1tDBDRY0INUE3YHE84etyVXlXMfM2VScWaVJ39mggPZGJc_uZnNUSfTJl2M8RbI2ybyCzUVFtjrKwWNgCQi0lC9zwQRmd6W0cdcteM0yi0OclgvrCSPxdYvFw3xRuOLIfpJkjggImb0oGIt0FQmkPlGK71uEOQWNCZiFakmnIL7DZUNBv5IyAT6zPhD3qsj4CxXwde_DeAYBI9XGRqyJIHVQcEvyqJooMl_kaba6quF8Wv6IaPrOLRyyTgIC43m8wkaJjFQ8XKe-jygVut8L_grIZWubwW9lieXp-Yv25v7ygNW7irlawEv-EwnTvuaU31Y2alX75I9UPPKnBjZuRqM3KpekFpcbkXGrDs1YVwg17a7etdJIFSJCN9aqJOyB-BrmahlAGsik3rv1CGDgj1fSj1DtYJqYyA5WarR_jH9lh1fI-V1pE77fHQHKGbBlnKN3qFfrWsetGZxSImQHJ4bXTRUh33VfJrn6-zmu-IYAQnULbRnmwLJGH2uKfWfRJUohqgi1jRTyFJGs5PFV9A3Q4_Kq4ILNbGlvgtxgD3BJVh4A3xD8i1-yhkWWESwgQX21FL1-m6BF3SnMCmhvxnblDDOZBhhb02STO1kqi42uIyJGr3N3spVK4EPmaQCe_3-QJNg7wk_Ym_Qb7sfHPfM6fZcx-k5XQtvldVpd5XVcQdde2DbfXdn4b86q912z87euz134PZtp2vbzu4futM4cg?type=png)](https://mermaid.live/edit#pako:eNqlVU1z2jAQ_SsaXWvAfKS1PZ3MpCQN7ZSGAdrp1OQg8GJ7YiRXlpLQhP9eWbKxDSQ51AeQdve9Xb1dy094xQLAHg45SSM0_7SgSD2ZXBrD1aMATklizPlzLQkPYuYX_2gU85iGaAb8Pl7BxyXvnEfa1IYC2w5NaDuA-1tDBDRY0INUE3YHE84etyVXlXMfM2VScWaVJ39mggPZGJc_uZnNUSfTJl2M8RbI2ybyCzUVFtjrKwWNgCQi0lC9zwQRmd6W0cdcteM0yi0OclgvrCSPxdYvFw3xRuOLIfpJkjggImb0oGIt0FQmkPlGK71uEOQWNCZiFakmnIL7DZUNBv5IyAT6zPhD3qsj4CxXwde_DeAYBI9XGRqyJIHVQcEvyqJooMl_kaba6quF8Wv6IaPrOLRyyTgIC43m8wkaJjFQ8XKe-jygVut8L_grIZWubwW9lieXp-Yv25v7ygNW7irlawEv-EwnTvuaU31Y2alX75I9UPPKnBjZuRqM3KpekFpcbkXGrDs1YVwg17a7etdJIFSJCN9aqJOyB-BrmahlAGsik3rv1CGDgj1fSj1DtYJqYyA5WarR_jH9lh1fI-V1pE77fHQHKGbBlnKN3qFfrWsetGZxSImQHJ4bXTRUh33VfJrn6-zmu-IYAQnULbRnmwLJGH2uKfWfRJUohqgi1jRTyFJGs5PFV9A3Q4_Kq4ILNbGlvgtxgD3BJVh4A3xD8i1-yhkWWESwgQX21FL1-m6BF3SnMCmhvxnblDDOZBhhb02STO1kqi42uIyJGr3N3spVK4EPmaQCe_3-QJNg7wk_Ym_Qb7sfHPfM6fZcx-k5XQtvldVpd5XVcQdde2DbfXdn4b86q912z87euz134PZtp2vbzu4futM4cg)

## Request Flow Process

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         REQUEST PROCESSING FLOW                            │
└─────────────────────────────────────────────────────────────────────────────┘

1. INCOMING REQUEST
   ┌─────────────────────────────────────────────────────────────┐
   │ Guardio Hiring Service                                      │
   │ POST https://your-proxy.com/stream                           │
   │ Headers: X-Grd-Signature: <hmac-sha256>                     │
   │ Body: <Pokemon Protobuf Binary>                             │
   └───────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
   ┌─────────────────────────────────────────────────────────────┐
   │ PokeProxy: POST /stream                                     │
   │ Router: app/routers/stream.py                               │
   └───────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
2. SIGNATURE VALIDATION
   ┌─────────────────────────────────────────────────────────────┐
   │ Security Service: validate_request_signature()              │
   │ • Extract X-Grd-Signature header                            │
   │ • Read request body                                         │
   │ • Validate body size (max 4KB)                              │
   │ • Compute HMAC-SHA256(body, secret)                         │
   │ • Compare with signature (timing-safe)                      │
   └───────────────────────┬─────────────────────────────────────┘
                           │
                    ┌──────┴──────┐
                    │   Valid?    │
                    └──────┬──────┘
                      No   │   Yes
                      │    │
                      ▼    │
              ┌───────────┐│
              │ 401 Error ││
              └───────────┘│
                           │
                           ▼
3. PROTOBUF PARSING
   ┌─────────────────────────────────────────────────────────────┐
   │ Parse Pokemon Protobuf                                       │
   │ • ParseFromString(body)                                     │
   │ • Validate required fields (name)                           │
   │ • Extract Pokemon data                                      │
   └───────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
4. ROUTING RULE MATCHING
   ┌─────────────────────────────────────────────────────────────┐
   │ Proxy Rules Service: find_matching_rule()                    │
   │ • Load rules from config.json                                │
   │ • Evaluate conditions (==, !=, >, <)                         │
   │ • Match first rule (all conditions must match)               │
   │ • Return matched rule with URL and reason                     │
   └───────────────────────┬─────────────────────────────────────┘
                           │
                    ┌──────┴──────┐
                    │ Rule Found? │
                    └──────┬──────┘
                      No   │   Yes
                      │    │
                      ▼    │
              ┌───────────┐│
              │{"status": ││
              │"no_match"}││
              └───────────┘│
                           │
                           ▼
5. DATA TRANSFORMATION
   ┌─────────────────────────────────────────────────────────────┐
   │ Proxy Service: pokemon_to_json()                             │
   │ • Convert protobuf → JSON dict                               │
   │ • Preserve snake_case field names                             │
   │ • Encode to JSON bytes                                        │
   └───────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
6. HEADER PREPARATION
   ┌─────────────────────────────────────────────────────────────┐
   │ Proxy Service: forward_request()                             │
   │ • Strip X-Grd-Signature (security)                          │
   │ • Strip hop-by-hop headers (connection, etc.)                │
   │ • Forward original headers (x-forwarded-*, etc.)              │
   │ • Add X-Grd-Reason: <matched rule reason>                    │
   │ • Set Content-Type: application/json                          │
   └───────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
7. FORWARD TO DOWNSTREAM
   ┌─────────────────────────────────────────────────────────────┐
   │ HTTP Client: POST to downstream URL                           │
   │ • Use shared httpx.AsyncClient (connection pooling)          │
   │ • POST <matched_rule.url>                                   │
   │ • Body: JSON bytes                                           │
   │ • Headers: Prepared headers                                  │
   └───────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
   ┌─────────────────────────────────────────────────────────────┐
   │ Downstream Service (e.g., downstream-test:9001/legendary)    │
   │ • Receives JSON Pokemon data                                 │
   │ • Receives forwarded headers + X-Grd-Reason                  │
   │ • Processes request                                          │
   │ • Returns response                                           │
   └───────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
8. RESPONSE PROCESSING
   ┌─────────────────────────────────────────────────────────────┐
   │ Stats Service: record_request()                              │
   │ • Record request count                                       │
   │ • Track error count (if status >= 400)                     │
   │ • Calculate response time                                   │
   │ • Track bytes (incoming/outgoing)                            │
   └───────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
   ┌─────────────────────────────────────────────────────────────┐
   │ Filter Response Headers                                       │
   │ • Remove hop-by-hop headers                                  │
   │ • Keep other headers                                         │
   └───────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
9. RETURN RESPONSE
   ┌─────────────────────────────────────────────────────────────┐
   │ Return to Guardio                                            │
   │ • Status code from downstream                                │
   │ • Response body from downstream                              │
   │ • Filtered headers                                          │
   └─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              ERROR HANDLING                                 │
└─────────────────────────────────────────────────────────────────────────────┘

Invalid Signature     → 401 Unauthorized
Invalid Protobuf      → 400 Bad Request
No Rule Match         → 200 OK {"status": "no_match"}
Downstream Timeout    → 504 Gateway Timeout
Downstream Error      → 502 Bad Gateway
Config Not Loaded     → 500 Internal Server Error
```

## Component Details

### Routers
- **Stream Router** (`app/routers/stream.py`): Main entry point for `/stream` endpoint
- **Internal Router** (`app/routers/internal.py`): Health checks and stats endpoints

### Services
- **Security Service** (`app/services/security.py`): HMAC-SHA256 signature validation
- **Proxy Rules Service** (`app/services/proxy_rules.py`): Rule matching engine
- **Proxy Service** (`app/services/proxy.py`): Request forwarding and data transformation
- **Stats Service** (`app/services/stats.py`): Metrics collection per endpoint

### State Management
- **App State** (`app/state.py`): Shared state for config, secret, and HTTP client
- Loaded once at startup via FastAPI lifespan events

### Data Flow
1. **Protobuf → JSON**: Binary protobuf is parsed and converted to JSON
2. **Header Transformation**: Signature stripped, reason added, hop-by-hop filtered
3. **Async Forwarding**: Non-blocking HTTP requests using httpx
4. **Response Proxying**: Downstream response returned to original client

