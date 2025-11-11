# Grafana Metrics Dashboard (Optional)

Navigator can optionally export metrics to visualize development progress and efficiency.

## Features

- Token usage tracking
- Cache hit rates
- Response times
- Cost optimization insights

## Setup

This feature requires:
1. OpenTelemetry integration (see `.agent/sops/integrations/opentelemetry-setup.md`)
2. Docker Compose for Grafana + Prometheus

## Quick Start

```bash
# Navigate to grafana directory
cd .agent/grafana

# Start Grafana + Prometheus
docker compose up -d

# Access dashboard
open http://localhost:3000
# Default credentials: admin/admin
```

## Dashboard Panels

1. **Token Usage Over Time** - Track context consumption
2. **Cache Hit Rate** - SSM parameter caching efficiency
3. **API Response Times** - Lambda performance
4. **Error Rate** - Track failures
5. **Cost Metrics** - AWS usage within free tier

## Note

This is an **optional** enhancement for power users. The bot works perfectly without metrics.

For basic monitoring, use AWS CloudWatch:
```bash
aws logs tail /aws/lambda/telegram-vps-bot --follow
```
