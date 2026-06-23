# Call Tagging & Categorization Guide

## Overview

The Call Tagging & Categorization system provides automatic classification of calls with custom tagging capabilities. It combines keyword/rule-based tagging with optional ML (scikit-learn TF-IDF + Naive Bayes) and optional NLP (spaCy) classification, enabling better organization, searchability, and analytics of your call data.

## Features

- **Automatic Categorization** - Classify calls from their transcript and metadata
- **Custom Tags** - Create and apply custom tags
- **Rule-Based Tagging** - Keyword and metadata rules for automatic tagging
- **ML Classification** - Optional scikit-learn classifier (when installed)
- **Tag Statistics** - Tag usage counts and most-common tags
- **Search by Tags** - Find calls quickly using tags

## Predefined Categories

The system defines these call categories (`CallCategory`):

- **Sales** - Sales-related calls
- **Support** - Customer support inquiries
- **Billing** - Billing and payment questions
- **General Inquiry** - General questions
- **Complaint** - Customer complaints
- **Emergency** - Emergency calls
- **Technical** - Technical support
- **Other** - Uncategorized calls

## Optional Dependencies

Tagging works with built-in keyword rules out of the box. Classification accuracy improves with optional packages:

```bash
# ML classification (TF-IDF + Naive Bayes)
pip install scikit-learn numpy

# NLP entity extraction and sentiment (used during classification)
pip install spacy
python -m spacy download en_core_web_sm
```

## Configuration

### config.yml

```yaml
features:
  call_tagging:
    enabled: true
    auto_tag: true              # Enable automatic tagging
    min_confidence: 0.7         # Minimum confidence for auto-tags (0.0-1.0)
    max_tags: 10                # Maximum tags per call
```

## Usage

### Python API

```python
from pbx.features.call_tagging import get_call_tagging, CallCategory, TagSource

tagging = get_call_tagging()

# Tag a call manually (one tag per call)
tagging.tag_call(
    call_id="call-123",
    tag="urgent",
    source=TagSource.MANUAL,
)

# Classify a call (rule + ML/keyword based) and return the applied tags
tags = tagging.classify_call(
    call_id="call-123",
    transcript="I have a problem with my account",
)

# Auto-tag from transcript and/or metadata
tags = tagging.auto_tag_call(
    call_id="call-123",
    transcript="I want to buy your product",
    metadata={"queue": "8001", "duration": 420},
)

# Get tags for a call
call_tags = tagging.get_call_tags("call-123")

# Remove a tag
tagging.remove_tag("call-123", "urgent")

# Search calls by tag
calls = tagging.search_by_tag("urgent")

# Get tag statistics
stats = tagging.get_tag_statistics()
```

### REST API Endpoints

All endpoints are under the `/api/framework` prefix and require authentication.

#### List Tags

```bash
GET /api/framework/call-tagging/tags

Response:
{
  "tags": [{"tag": "billing"}, {"tag": "support"}]
}
```

#### List Tagging Rules

```bash
GET /api/framework/call-tagging/rules
```

#### Tagging Statistics

```bash
GET /api/framework/call-tagging/statistics
```

#### Create a Custom Tag

```bash
POST /api/framework/call-tagging/tag
{
  "name": "vip-customer",
  "description": "High-value customer",
  "color": "#007bff"
}

Response:
{
  "success": true,
  "tag_id": "vip-customer"
}
```

#### Create a Tagging Rule

```bash
POST /api/framework/call-tagging/rule
{
  "name": "Sales Queue",
  "conditions": {"queue": "8001"},
  "tag_id": "sales-queue",
  "priority": 100
}

Response:
{
  "success": true,
  "rule_id": "rule_5"
}
```

#### Classify a Call

```bash
POST /api/framework/call-tagging/classify/{call_id}

Response:
{
  "call_id": "call-123",
  "tags": ["support", "billing"]
}
```

#### Delete a Tag

```bash
DELETE /api/framework/call-tagging/tags/{tag_id}
```

#### Delete a Rule

```bash
DELETE /api/framework/call-tagging/rules/{rule_id}
```

#### Toggle a Rule

```bash
POST /api/framework/call-tagging/rules/{rule_id}/toggle
```

## Tagging Rules

### Keyword Rules

The simplest rules match keywords in the transcript. Add one with `add_tagging_rule(name, keywords, tag, category)`:

```python
from pbx.features.call_tagging import get_call_tagging, CallCategory

tagging = get_call_tagging()

tagging.add_tagging_rule(
    name="Long Support Calls",
    keywords=["escalate", "supervisor", "manager"],
    tag="complex-issue",
    category=CallCategory.SUPPORT,
)
```

> `add_tagging_rule` only succeeds when the feature is enabled (`features.call_tagging.enabled: true`).

### Metadata / Condition Rules

`create_rule(name, conditions, tag_id, priority)` builds a rule whose `conditions` are evaluated against call metadata during `classify_call`. Supported condition keys are `queue`, `disposition`, `min_duration`, and `max_duration`:

```python
tagging.create_rule(
    name="Long Calls",
    conditions={"min_duration": 600},  # 10 minutes or longer
    tag_id="extended-call",
    priority=100,
)
```

### Built-in Default Rules

On initialization the system loads keyword rules for `sales`, `support`, `billing`, and `complaint`. These are applied automatically during `classify_call` and `auto_tag_call`.

## Auto-Tagging

`auto_tag_call(call_id, transcript=None, metadata=None)` combines several signals (when enabled via `auto_tag`):

### Keyword Rules

Built-in and custom keyword rules are matched against the transcript.

### Transcript Classification

When a transcript is supplied, it is classified using:

- **spaCy** (if installed) - sentiment and entity signals (e.g. negative sentiment → `complaint`, money mentions → `billing`)
- **scikit-learn** (if installed) - TF-IDF + Naive Bayes classifier trained on built-in examples
- **Keyword scoring fallback** - a TF-IDF-inspired keyword scorer used when the ML libraries are unavailable

Only tags meeting `min_confidence` are applied.

### Metadata Tagging

Call metadata produces tags such as `queue_<id>`, time-of-day (`morning`/`afternoon`/`evening`/`night`), call length (`short_call`/`medium_call`/`long_call`), direction, disposition (`missed_call`/`abandoned`/`voicemail`), transfer/escalation (`transferred`/`escalated`), `long_hold`, `slow_answer`, `after_hours`, and repeat-caller tags.

## Tag Statistics

```python
stats = tagging.get_tag_statistics()
# Returns:
# {
#     "total_unique_tags": 12,
#     "tag_counts": {"support": 567, "billing": 342, ...},
#     "most_common": [("support", 567), ("billing", 342), ...]
# }
```

Overall counters (calls tagged, auto vs manual tags, rule counts, library availability) are available via `get_statistics()`:

```python
overall = tagging.get_statistics()
# {
#     "enabled": True,
#     "auto_tag_enabled": True,
#     "total_calls_tagged": 1523,
#     "total_tags_created": 3847,
#     "auto_tags_created": 2891,
#     "manual_tags_created": 956,
#     "custom_tags_count": 24,
#     "tagging_rules_count": 8,
#     "spacy_available": True
# }
```

## Admin Panel

Access Call Tagging in the admin panel:

1. Navigate to **Admin Panel** → **Framework Features** → **Call Tagging**
2. View tagged calls and statistics
3. Create and manage tagging rules
4. Search calls by tags

## Integration with Other Features

### Speech Analytics

Use a transcript produced elsewhere to classify a call:

```python
from pbx.features.speech_analytics import get_speech_analytics

speech = get_speech_analytics()
transcript = speech.get_call_transcript("call-123")

tags = tagging.classify_call("call-123", transcript=transcript)
```

### Call Queues

Tag calls based on the queue they came through using a metadata rule:

```python
tagging.create_rule(
    name="Sales Queue",
    conditions={"queue": "8001"},
    tag_id="sales-queue",
)
```

## Best Practices

### Tagging Strategy

- **Consistent Naming:** Use consistent tag names (lowercase, hyphenated)
- **Specific Tags:** Use specific tags like "billing-dispute" vs generic "billing"
- **Limit Tags:** Don't over-tag; `max_tags` caps the number per call

### Rule Management

- **Regular Review:** Review and update rules periodically
- **Monitor Performance:** Check auto-tag accuracy regularly
- **Adjust Confidence:** Fine-tune `min_confidence` based on results

### Performance

- **Index Tags:** Ensure tag columns are indexed for fast searching
- **Optional Libraries:** Install `scikit-learn`/`spaCy` for better classification

## Database Schema

The call tagging tables are created by `pbx/utils/migrations.py` (Migration 1003).

### call_tags

```sql
CREATE TABLE IF NOT EXISTS call_tags (
    id SERIAL PRIMARY KEY,
    tag_name VARCHAR(50) NOT NULL UNIQUE,
    category VARCHAR(50),
    color VARCHAR(20),
    auto_apply_rules TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### call_tag_assignments

```sql
CREATE TABLE IF NOT EXISTS call_tag_assignments (
    id SERIAL PRIMARY KEY,
    call_id VARCHAR(50) NOT NULL,
    tag_id INTEGER REFERENCES call_tags(id),
    assigned_by VARCHAR(50),
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    auto_assigned BOOLEAN DEFAULT FALSE
);
```

## Troubleshooting

### Low Auto-Tag Accuracy

**Solution:**

- Reduce `min_confidence` threshold
- Add keyword rules with `add_tagging_rule`
- Install `scikit-learn` and `spaCy` for stronger classification

### Too Many Tags per Call

**Solution:**

- Increase `min_confidence` threshold
- Reduce the `max_tags` limit
- Review and consolidate similar tags

### Search Performance Issues

**Solution:**

- Ensure indexes are created on tag columns
- Archive old tagged calls

## Next Steps

1. **Define Tag Strategy:** Plan your tagging taxonomy
2. **Configure Rules:** Set up initial keyword and metadata rules
3. **Enable Auto-Tagging:** Turn on `auto_tag`
4. **Monitor Accuracy:** Review auto-tag results
5. **Tune Settings:** Adjust `min_confidence` and `max_tags`

## Related Documentation

- [FRAMEWORK_FEATURES_COMPLETE_GUIDE.md](FRAMEWORK_FEATURES_COMPLETE_GUIDE.md)
- [PLANNED_FEATURES.md](../PLANNED_FEATURES.md) - Planned (not-yet-implemented) capabilities for this feature
- [COMPLETE_GUIDE.md - Section 9.2: REST API](../../COMPLETE_GUIDE.md#92-rest-api-reference)
