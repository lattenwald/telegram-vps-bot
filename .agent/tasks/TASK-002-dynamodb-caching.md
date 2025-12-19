# TASK-002: DynamoDB Caching for Server-Provider Mapping

**Status**: ⏸️ Postponed
**Created**: 2025-12-19
**Depends On**: TASK-001

---

## Context

**Problem**:
In-memory cache for server→provider mapping is lost on Lambda cold starts, requiring re-querying all providers to find a server.

**Goal**:
Implement persistent DynamoDB cache to survive cold starts and reduce API calls to providers.

**Success Criteria**:
- [ ] DynamoDB table for server→provider mapping
- [ ] Cache lookup before provider queries
- [ ] Cache update on successful server operations
- [ ] TTL-based cache invalidation
- [ ] Stays within DynamoDB free tier (25 RCU/WCU)

---

## Implementation Plan

### Phase 1: Infrastructure
**Goal**: Create DynamoDB table

**Tasks**:
- [ ] Add DynamoDB table in Terraform
- [ ] Configure TTL attribute
- [ ] Add IAM permissions for Lambda

**Files**:
- `infrastructure/main.tf` - DynamoDB resource
- `infrastructure/iam.tf` - Lambda permissions

### Phase 2: Cache Layer
**Goal**: Implement cache read/write

**Tasks**:
- [ ] Create `ServerCache` class with get/set/delete
- [ ] Integrate with provider resolution logic
- [ ] Add TTL configuration (e.g., 24 hours)
- [ ] Fallback to in-memory if DynamoDB fails

**Files**:
- `src/cache.py` - New cache module
- `src/auth.py` - Integrate cache lookups

### Phase 3: Testing
**Goal**: Ensure cache works correctly

**Tasks**:
- [ ] Unit tests with mocked DynamoDB (moto)
- [ ] Integration tests for cache hit/miss scenarios
- [ ] Verify free tier limits not exceeded

**Files**:
- `tests/test_cache.py` - Cache tests

---

## Technical Decisions

| Decision | Options | Chosen | Reasoning |
|----------|---------|--------|-----------|
| Cache key | server_name, provider:server | server_name | Simple, one lookup per server |
| TTL | 1h, 24h, 7d | 24h (TBD) | Balance freshness vs API calls |
| Fallback | Error, In-memory, Skip | In-memory | Graceful degradation |

---

## DynamoDB Schema

```
Table: telegram-vps-bot-server-cache
Partition Key: server_name (String)

Attributes:
- server_name: String (PK)
- provider: String
- cached_at: Number (epoch)
- ttl: Number (epoch, for DynamoDB TTL)
```

---

## Notes

- DynamoDB free tier: 25 RCU/WCU, 25GB storage (permanent)
- Expected usage: <1 RCU/WCU (personal bot)
- Consider: Is this needed for a personal bot with few servers?

---

**Last Updated**: 2025-12-19
