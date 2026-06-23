# Warden VoIP — Planned Features

This document tracks capabilities that were previously described in the project
documentation but are **not yet implemented** in the code. They were extracted
here during a documentation accuracy audit so that the user-facing guides describe
only what currently ships, while the intended roadmap is preserved in one place.

Where a specific function, method, enum, or config key was originally documented,
it is shown in backticks to aid future implementation. Nothing in this document is
implemented today — treat every item as planned/aspirational.

## Architecture Diagrams

`docs/ARCHITECTURE_DIAGRAMS.md` currently contains 6 diagrams. The following 13 were
referenced but never written; adding them would complete the originally planned
19-diagram set:

- **Database Schema & Complete ERD** — entity-relationship diagram of all SQLAlchemy ORM models and their foreign-key relationships
- **Call State Machine** — full state-transition diagram of the call lifecycle (new → ringing → active → ended and edge states)
- **API Layer Architecture** — structure of the Flask app factory, the 22 route modules, schemas, and auth wiring
- **Request Processing Pipeline (Detailed)** — end-to-end sequence of an inbound REST request through middleware, auth, route, and database
- **Frontend State Management & Data Flow** — how the Vite/TypeScript admin store, pages, and API client move data through the UI
- **Feature Module System** — how the 76 pluggable feature modules are registered and exposed
- **Feature Module Lifecycle** — load/enable/disable/event-hook lifecycle driven by `FeatureInitializer`
- **Conference Bridge Architecture** — media mixing and participant management for conference calls
- **Security & Authentication Architecture** — layered view of TLS, encryption, security middleware, and the security monitor
- **Authentication & Authorization Flow** — login → token validation → role/permission checks across the API
- **Voicemail Processing Pipeline** — flow from no-answer to recording, storage, and notification
- **Deployment & Runtime Architecture** — Docker/Kubernetes runtime topology and service dependencies
- **System Monitoring & Observability Stack** — Prometheus exporter, Grafana dashboards, and audit/metric flows

Related documentation artifacts that were referenced but do not exist yet:

- **PDF export** — a generated `docs/ARCHITECTURE_DIAGRAMS.pdf` shareable artifact (the generation procedure is documented; the file is not produced/committed)
- **`docs/SYSTEM_ARCHITECTURE.md`** — planned narrative "Part 1" source the diagrams were to be compiled from
- **`docs/DETAILED_COMPONENT_DIAGRAMS.md`** — planned detailed "Part 2" companion to `SYSTEM_ARCHITECTURE.md`

## Voice Biometrics

The shipping implementation (`pbx/features/voice_biometrics.py`) is a local/open-source
speaker-verification engine. The following were documented but are not implemented:

- **Commercial provider integration** — `configure_provider()` for Nuance VocalPassword, AWS Connect Voice ID, and Pindrop (only a `provider` config label exists today, with no integration)
- **Text-dependent verification** — `verify_text_dependent(extension, audio, expected_text)` for passphrase-based verification
- **Text-independent verification** — `verify_text_independent(extension, audio)` for free-speech verification (today's `verify_speaker` is text-agnostic but unparameterized)
- **Continuous / streaming verification** — `start_continuous_verification`, `verify_audio_chunk`, `flag_suspicious_activity` for in-call verification
- **Phrase-based & passive enrollment** — `configure_enrollment_phrases`, `complete_enrollment`, `enable_passive_enrollment` (build profiles from regular calls)
- **Voice synthesis / deepfake detection** — a standalone `check_voice_synthesis(audio)` returning `is_synthetic` (only an internal heuristic inside `detect_fraud` exists)
- **Impersonation detection** — a standalone `check_impersonation(audio, extension)` method (only an internal heuristic exists)
- **Configurable fraud checks** — `detect_fraud(checks=[...])` with per-check toggles and a dedicated fraud REST endpoint (today all heuristics run together with no endpoint)
- **Liveness / replay-attack flagging** — `liveness_check` config and response field as a first-class feature
- **Call-flow fraud monitoring hooks** — `is_enabled`, `start_fraud_monitoring`, `process_fraud_check` IVR/call hooks

## Call Tagging

The shipping implementation (`pbx/features/call_tagging.py`) supports manual tagging,
rule-based tagging, and automatic classification. The following were documented but are
not implemented:

- **Tag distribution analytics** — `get_tag_distribution()` showing tag spread across categories
- **Tag trend analytics** — `get_tag_trends(start_date, end_date, interval)` for usage over time
- **Keyword-detection configuration** — `configure_keyword_detection({category: [keywords]})` (keyword sets are currently hard-coded; custom rules go through `add_tagging_rule`)
- **Sentiment-tagging configuration** — `enable_sentiment_tagging(negative_threshold, positive_threshold)` (sentiment is applied internally with no config)
- **ML classifier training** — `train_classifier(training_calls, features)` to learn from historical calls (the classifier auto-trains on built-in example data only)
- **ML classification toggle** — `enable_ml_classification(min_confidence)` (ML is used automatically when scikit-learn is installed)
- **Transcript-based auto-tagging helper** — `tag_from_transcript(call_id, transcript)` (use `classify_call` today)
- **Rich-condition tagging rules** — dict-form rules with `caller_id`, `time_range`, and `caller_id_prefix` conditions (real rule conditions support only `queue`, `disposition`, `min_duration`, `max_duration`)

## Geographic Redundancy

The shipping implementation (`pbx/features/geographic_redundancy.py`) supports region
registration, health scoring, and manual/automatic failover. The following were
documented but are not implemented:

- **Configurable health checks** — per-region interval/timeout/retry settings and pluggable check methods (SIP OPTIONS, HTTP ping, ICMP ping) plus custom check registration
- **Rich health-state model** — descriptive HEALTHY/WARNING/CRITICAL/DOWN/DEGRADED states (today: a numeric `health_score` + boolean `healthy` + the `RegionStatus` enum)
- **Tunable automatic-failover policy** — `min_failure_duration` and `failover_delay` beyond the simple `failover_threshold` counter
- **Scheduled / planned failover** — maintenance-window failover with start time, duration, and reason
- **Automatic failback** — delay, health-threshold, and manual-approval controls for returning to the primary region
- **Cross-region configuration replication** — sync extensions, voicemail, and call queues across regions
- **Cross-region CDR replication** — real-time replication of call detail records to backup regions
- **Geographic load balancing** — proximity-based or weighted call distribution across regions
- **Geo time-based routing** — follow-the-sun routing by time-of-day window
- **Failover alerting** — email/SMS/webhook notifications on failover and region up/down/degraded events
- **Per-region metrics** — uptime, average latency, calls handled, failover count, last-failover timestamp
- **Automated failover testing** — a dry-run failover test harness
- **Data-residency controls** — per-region storage-location and no-cross-border-transfer constraints
- **GDPR compliance mode** — per-region data-processing-agreement and consent enforcement

## Mobile Apps

The shipping implementation (`pbx/features/mobile_apps.py`, `pbx/features/mobile_push.py`)
supports device registration, mobile SIP configuration, and push notifications. The
following were documented but are not implemented:

- **Background keep-alive** — server-side configurable keep-alive interval/timeout and a handler for device keep-alive pings
- **Per-device battery optimization** — push-only mode, aggressive-timeout, and reduce-bandwidth settings applied per device (beyond the static hints `configure_sip_for_mobile` already returns)
- **Desk-to-mobile call continuity** — transferring an active call from a desk phone to a mobile device
- **Mobile call pickup / handoff** — picking up a ringing call on a mobile device
- **Visual voicemail on mobile** — in-app voicemail browsing (only `new_voicemail` push notifications exist today)
- **Mobile presence updates** — real-time status pushed from the mobile client

## AWS / Terraform Deployment

`terraform/aws/main.tf` is a simplified starting template (input variables plus the
`instructions`, `alb_dns_name`, and `nlb_dns_name` outputs). Its outputs reference
resources that are not yet defined. The following infrastructure is planned:

- **VPC / networking** — VPC with public and private subnets across two AZs, internet gateway, route tables, and security groups for the PBX, database, Redis, and load balancers
- **Launch template** — EC2 launch template with automated PBX setup via a user-data script
- **Auto Scaling Group** — ASG with two or more EC2 instances and CPU-based scaling policies
- **Application Load Balancer** — ALB for HTTPS API traffic (backs the `alb_dns_name` output)
- **Network Load Balancer** — NLB for SIP/RTP UDP traffic (backs the `nlb_dns_name` output)
- **RDS PostgreSQL 17** — multi-AZ, encrypted, with automated backups (needed for a `database_endpoint` output)
- **ElastiCache Redis** — multi-AZ Redis cluster for session state (needed for a `redis_endpoint` output)
- **ACM certificate** — TLS certificate with DNS validation (needed for a `certificate_arn` output)
- **AWS Secrets Manager** — storage for database credentials
- **IAM roles** — least-privilege instance roles and profiles
- **CloudWatch** — metrics and centralized logging
