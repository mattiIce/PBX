# Warden VoIP - Detailed Component Diagrams

## 1. Module Dependency Graph - Core System

```mermaid
graph TD
    Main["main.py<br/>(Entry Point)"]

    subgraph "Configuration & Initialization"
        EnvLoader["utils/env_loader.py<br/>(Load .env)"]
        ConfigMgr["utils/config.py<br/>(Parse YAML)"]
        Logger["utils/logger.py<br/>(Setup Logging)"]
    end

    subgraph "Database Layer"
        DB["utils/database.py<br/>(SQLAlchemy)"]
        Models["models/__init__.py<br/>(ORM Models)"]
        Migrations["utils/migrations.py<br/>(Runtime DDL)"]
    end

    subgraph "PBX Core"
        PBXCore["core/pbx.py<br/>(PBXCore)"]
        CallRouter["core/call_router.py<br/>(Routing)"]
        CallStateMachine["core/call.py<br/>(State Machine)"]
        FeatureInit["core/feature_initializer.py<br/>(Feature Loader)"]
    end

    subgraph "Protocol Handlers"
        SIPServer["sip/server.py<br/>(Twisted SIP)"]
        SIPMessage["sip/message.py<br/>(SIP Parser)"]
        SDP["sip/sdp.py<br/>(SDP Negotiation)"]
        RTPHandler["rtp/handler.py<br/>(RTP Relay)"]
        JitterBuffer["rtp/jitter_buffer.py"]
        RFC2833["rtp/rfc2833.py<br/>(DTMF)"]
        RTCPMonitor["rtp/rtcp_monitor.py"]
    end

    subgraph "Feature Handlers"
        AutoAttendant["core/auto_attendant_handler.py<br/>(IVR)"]
        VoicemailHandler["core/voicemail_handler.py"]
        EmergencyHandler["core/emergency_handler.py<br/>(E911)"]
        PagingHandler["core/paging_handler.py"]
        Features["features/*.py<br/>(77 Modules)"]
    end

    subgraph "API Layer"
        FlaskApp["api/app.py<br/>(Flask Factory)"]
        Routes["api/routes/*.py<br/>(23 Modules)"]
        Schemas["api/schemas/*.py<br/>(5 Schema Modules)"]
        Auth["api/routes/auth.py<br/>(JWT)"]
        Errors["api/errors.py<br/>(Error Handler)"]
        OpenAPI["api/openapi.py"]
    end

    subgraph "Security & Monitoring"
        Security["utils/security.py<br/>(Encryption)"]
        TLS["utils/tls_support.py"]
        Middleware["utils/security_middleware.py"]
        Monitor["utils/security_monitor.py"]
        Metrics["utils/prometheus_exporter.py<br/>(Metrics)"]
        AuditLog["utils/audit_logger.py"]
    end

    subgraph "Integrations"
        AD["integrations/active_directory.py"]
        Teams["integrations/teams.py"]
        Zoom["integrations/zoom.py"]
        CRM["integrations/espocrm.py"]
    end

    subgraph "Utilities"
        GracefulShutdown["utils/graceful_shutdown.py"]
        Audio["utils/audio_processor.py"]
        TTS["utils/tts_provider.py"]
        DTMF["utils/dtmf_handler.py"]
    end

    Main -->|Load Config| EnvLoader
    EnvLoader -->|Load Settings| ConfigMgr
    ConfigMgr -->|Initialize| Logger

    ConfigMgr -->|Connect| DB
    DB -->|Create ORM| Models
    Models -->|Create Tables| Migrations

    Main -->|Initialize| PBXCore
    ConfigMgr -->|Configure| PBXCore
    Models -->|Provide| PBXCore

    PBXCore -->|Own| CallRouter
    PBXCore -->|Own| FeatureInit
    CallRouter -->|Use| CallStateMachine

    PBXCore -->|Start| SIPServer
    SIPServer -->|Parse| SIPMessage
    SIPMessage -->|Negotiate| SDP
    SIPServer -->|Route Messages| PBXCore

    CallStateMachine -->|Handle Media| RTPHandler
    RTPHandler -->|Buffer| JitterBuffer
    RTPHandler -->|Detect DTMF| RFC2833
    RTPHandler -->|Monitor Quality| RTCPMonitor

    FeatureInit -->|Load| AutoAttendant
    FeatureInit -->|Load| VoicemailHandler
    FeatureInit -->|Load| EmergencyHandler
    FeatureInit -->|Load| PagingHandler
    FeatureInit -->|Load| Features

    PBXCore -->|Trigger Events| Features

    Main -->|Create| FlaskApp
    FlaskApp -->|Inject| PBXCore
    FlaskApp -->|Register| Routes
    Routes -->|Validate| Schemas
    Routes -->|Check| Auth
    Routes -->|Catch Errors| Errors
    FlaskApp -->|Document| OpenAPI

    Routes -->|Query| PBXCore
    Routes -->|Access| Models

    PBXCore -->|Encrypt Data| Security
    Security -->|Use| TLS
    FlaskApp -->|Apply| Middleware
    FlaskApp -->|Monitor| Monitor
    Routes -->|Log| AuditLog

    PBXCore -->|Sync| AD
    PBXCore -->|Integrate| Teams
    PBXCore -->|Integrate| Zoom
    PBXCore -->|Integrate| CRM

    CallStateMachine -->|Use| Audio
    CallStateMachine -->|Generate| TTS
    CallStateMachine -->|Handle| DTMF
    PBXCore -->|Graceful| GracefulShutdown

    style Main fill:#ffccbc
    style PBXCore fill:#c8e6c9
    style FlaskApp fill:#bbdefb
    style SIPServer fill:#f0f4c3
    style Features fill:#fff9c4
```

## 2. Database Schema - Complete ERD

```mermaid
erDiagram
    "Extension" ||--o{ "RegisteredPhone" : ""
    "Extension" ||--o{ "Voicemail" : ""
    "Extension" ||--o{ "CallRecord" : "from_ext"
    "Extension" ||--o{ "CallRecord" : "to_ext"
    "Extension" ||--o{ "QueueMember" : ""
    "Extension" ||--o{ "PresenceStatus" : ""
    "CallRecord" ||--o{ "CallRecordingMetadata" : ""
    "Queue" ||--o{ "QueueMember" : ""
    "Conference" ||--o{ "ConferenceMember" : ""
    "Extension" ||--o{ "ConferenceMember" : ""
    "User" ||--o{ "Extension" : ""
    "User" ||--o{ "CallForwardingRule" : ""
    "Extension" ||--o{ "DNDRule" : ""
    "Extension" ||--o{ "HuntGroup" : ""
    "Extension" ||--o{ "ParkingLot" : ""

    "Extension" {
        int id PK
        string extension_number UK
        string display_name
        string user_uuid FK
        string auth_secret
        string voicemail_pin
        string voicemail_greeting_path
        int voicemail_max_messages
        boolean enabled
        string call_forward_enabled
        string call_forward_destination
        int dnd_enabled
        datetime created_at
        datetime updated_at
        int max_concurrent_calls
        string recording_policy
    }

    "User" {
        string id PK
        string username UK
        string email
        string password_hash
        string role
        boolean active
        datetime last_login
        string department
        string title
    }

    "RegisteredPhone" {
        int id PK
        int extension_id FK
        string device_name
        string ip_address
        string user_agent
        int port
        string protocol
        datetime last_registered
        datetime expires_at
        boolean active
        float signal_strength
    }

    "Voicemail" {
        int id PK
        int extension_id FK
        string message_file_path
        string transcription
        string caller_id
        boolean is_read
        datetime recorded_at
        int duration_seconds
        int file_size_bytes
        string codec
        int retry_count
    }

    "CallRecord" {
        int id PK
        int from_extension_id FK
        int to_extension_id FK
        string call_id UK
        string from_number
        string to_number
        string direction
        string status
        datetime start_time
        datetime end_time
        int duration_seconds
        int billable_duration
        string recording_path
        boolean recording_present
        string call_type
        int transfer_count
        string park_duration
        string hold_duration
    }

    "CallRecordingMetadata" {
        int id PK
        int call_record_id FK
        string file_path
        string format
        int bitrate
        int sample_rate
        string encryption_status
        datetime purge_date
    }

    "Queue" {
        int id PK
        string queue_name UK
        string description
        int max_wait_time
        boolean enabled
        int fallback_extension_id
        string strategy
        int ring_timeout
        int skip_busy_agents
        datetime created_at
    }

    "QueueMember" {
        int id PK
        int queue_id FK
        int extension_id FK
        int priority
        int calls_handled
        int avg_handle_time
        boolean active
        datetime joined_at
    }

    "Conference" {
        int id PK
        string conference_id UK
        string name
        datetime start_time
        datetime end_time
        int max_participants
        boolean is_active
        string moderator_pin
        string participant_pin
    }

    "ConferenceMember" {
        int id PK
        int conference_id FK
        int extension_id FK
        datetime joined_at
        datetime left_at
        boolean is_muted
        boolean is_moderator
    }

    "CallForwardingRule" {
        int id PK
        string user_id FK
        string rule_name
        string condition
        string destination
        int priority
        boolean enabled
        datetime created_at
    }

    "DNDRule" {
        int id PK
        int extension_id FK
        boolean enabled
        datetime start_time
        datetime end_time
        string voicemail_greeting
    }

    "HuntGroup" {
        int id PK
        string name UK
        string description
        string strategy
        boolean enabled
        datetime created_at
    }

    "ParkingLot" {
        int id PK
        int extension_id FK
        string parked_by
        string parked_for
        datetime parked_at
        int timeout_seconds
    }

    "PresenceStatus" {
        int id PK
        int extension_id FK
        string status
        string status_message
        datetime last_updated
        string device_state
    }
```

## 3. Request Processing Pipeline - Detailed

```mermaid
sequenceDiagram
    participant Client as REST Client<br/>Browser
    participant Flask as Flask App<br/>Port 9000
    participant Auth as Auth Middleware<br/>JWT Verify
    participant Validation as Request<br/>Validator
    participant Route as Route Handler<br/>Logic
    participant PBX as PBXCore<br/>Engine
    participant DB as Database<br/>Query
    participant Response as Response<br/>Builder
    participant Client2 as Client<br/>Response

    Client->>Flask: POST /api/calls
    Flask->>Auth: Check Authorization
    Auth->>Auth: Extract JWT token
    Auth->>Auth: Verify signature & expiry
    alt Token Invalid
        Auth-->>Flask: 401 Unauthorized
        Flask-->>Client2: Reject
    else Token Valid
        Auth->>Validation: Request body
        Validation->>Validation: JSON Schema check
        alt Invalid Schema
            Validation-->>Flask: 400 Bad Request
            Flask-->>Client2: Error response
        else Valid Schema
            Validation->>Route: Call handler function
            Route->>Route: Extract parameters
            Route->>PBX: pbx.make_call(ext_101, ext_102)
            PBX->>PBX: Create CallStateMachine
            PBX->>DB: Query Extension models
            DB-->>PBX: Extension data
            PBX->>DB: Get RegisteredPhone
            DB-->>PBX: Phone IP/port
            PBX->>PBX: Send SIP INVITE
            PBX-->>Route: CallStateMachine instance
            Route->>DB: Create CallRecord entry
            DB-->>Route: CallRecord ID
            Route->>Response: Build 202 Accepted
            Response-->>Client2: JSON with call_id
        end
    end
```

## 4. RTP Media Stream - Detailed Flow

```mermaid
graph TB
    subgraph "Phone A - Extension 101"
        A1["Microphone<br/>Raw Audio"]
        A2["Codec Encode<br/>(opus/g711)"]
        A3["RTP Payload<br/>Port 15000"]
    end

    subgraph "RTP Handler - Port 10000-20000 UDP"
        R1["Allocate Port<br/>15000 for Phone A"]
        R2["Allocate Port<br/>15002 for Phone B"]
        R3["RTP Receiver<br/>Port 15000"]
        R4["Sequence Check<br/>& Reorder"]
        R5["Jitter Buffer<br/>Adaptive Delay"]
        R6["Packet Loss<br/>Detection"]
        R7["DTMF Detection<br/>RFC 2833"]
        R8["RTP Sender<br/>Port 15002"]
    end

    subgraph "Phone B - Extension 102"
        B1["RTP Payload<br/>Port 15002"]
        B2["Codec Decode<br/>(opus/g711)"]
        B3["Speaker<br/>Audio Output"]
    end

    subgraph "Monitoring & Stats"
        M1["RTCP Monitor<br/>Sender Reports"]
        M2["Call Statistics<br/>Metrics"]
        M3["QoS Tracking<br/>Jitter, Loss"]
    end

    A1 -->|Analog| A2
    A2 -->|Digital| A3
    A3 -->|Network| R1

    R1 -->|Bind Socket| R3
    R3 -->|Receive| R4
    R4 -->|Reorder| R5
    R5 -->|Buffer| R6
    R6 -->|Detect| R7
    R7 -->|Payload| R8

    R8 -->|Network| B1
    B1 -->|Digital| B2
    B2 -->|Analog| B3

    B3 -->|Response| B2
    B2 -->|Encode| B1
    B1 -->|Network| R2

    R2 -->|Bind Socket| R3

    R3 -->|Stats| M1
    R4 -->|Quality| M3
    M1 -->|Generate| M2
    M2 -->|Store| DB["Database<br/>Metrics"]

    style A1 fill:#ffccbc
    style B3 fill:#ffccbc
    style R1 fill:#bbdefb
    style M1 fill:#f0f4c3
```

## 5. Call State Machine - Full State Diagram

```mermaid
stateDiagram-v2
    [*] --> NEW

    NEW --> ROUTING: analyze_destination()

    ROUTING --> QUEUED: destination_is_queue
    ROUTING --> RINGING: destination_is_extension
    ROUTING --> IVR: destination_is_ivr
    ROUTING --> VOICEMAIL: destination_is_voicemail
    ROUTING --> CONFERENCE: destination_is_conference
    ROUTING --> FAILED: invalid_destination

    QUEUED --> RINGING: agent_available
    QUEUED --> HELD: no_agent
    HELD --> QUEUED: agent_available
    HELD --> VOICEMAIL: timeout

    RINGING --> ACTIVE: 200_OK_received
    RINGING --> BUSY: 486_received
    RINGING --> NO_ANSWER: timeout

    IVR --> RINGING: user_selected_extension
    IVR --> VOICEMAIL: user_pressed_voicemail
    IVR --> FAILED: invalid_selection

    ACTIVE --> HELD: hold_request
    HELD --> ACTIVE: unhold_request
    ACTIVE --> TRANSFER_INITIATED: transfer_request
    TRANSFER_INITIATED --> TRANSFER_COMPLETED: transfer_accepted
    TRANSFER_INITIATED --> ACTIVE: transfer_rejected

    ACTIVE --> RECORDED: recording_started
    RECORDED --> ACTIVE: recording_stopped

    ACTIVE --> CONFERENCE: conference_transfer
    CONFERENCE --> ACTIVE: conference_exit

    ACTIVE --> ENDED: bye_received
    NO_ANSWER --> VOICEMAIL: voicemail_enabled
    NO_ANSWER --> ENDED: voicemail_disabled
    BUSY --> VOICEMAIL: voicemail_enabled
    BUSY --> ENDED: voicemail_disabled
    VOICEMAIL --> ENDED: recording_complete
    TRANSFER_COMPLETED --> ENDED: call_complete
    CONFERENCE --> ENDED: conference_complete
    FAILED --> ENDED: immediate

    ENDED --> [*]: create_cdr()

    note right of NEW
        Created when SIP INVITE arrives
        Allocate call_id, initialize handlers
    end

    note right of ROUTING
        Determine destination type:
        - Extension lookup
        - Queue routing
        - IVR menu
        - Direct to voicemail
    end

    note right of RINGING
        SIP 180 RINGING sent
        Waiting for 200 OK
        Timeout after ring_timeout seconds
    end

    note right of ACTIVE
        Call in progress
        Media streams flowing
        Features active (hold, transfer, record)
    end

    note right of HELD
        Call on hold
        Music on Hold (MoH) playing
        Can resume or transfer
    end

    note right of VOICEMAIL
        Recording voicemail greeting played
        Recording message to storage
        Optional transcription
    end

    note right of TRANSFER_INITIATED
        Blind or attended transfer
        New call leg created
        Awaiting acceptance
    end

    note right of ENDED
        Call terminated
        Generate CallRecord CDR
        Publish call_ended event
        Release resources
    end
```

## 6. Feature Module Lifecycle

```mermaid
sequenceDiagram
    participant System as PBXCore
    participant Loader as Feature Loader
    participant Feature as Feature Module<br/>Instance
    participant Handler as Feature Handler<br/>Logic
    participant CallSM as Call State<br/>Machine

    System->>Loader: initialize_features()
    Loader->>Loader: scan features/ directory
    Loader->>Loader: discover *.py files
    Loader->>Feature: import_module()
    Feature->>Feature: Feature subclass defined
    Loader->>Feature: instantiate()
    Feature->>Feature: __init__()
    Feature->>Feature: on_initialize()
    Feature-->>Loader: Initialization complete
    Loader->>System: Features loaded

    System->>System: Accept SIP INVITE
    System->>CallSM: create(call_params)
    CallSM->>CallSM: State transition
    CallSM->>System: fire event: call_routing
    System->>Feature: on_call_event(call_routing)
    Feature->>Handler: check_conditions()
    Handler->>Handler: analyze call
    alt Feature applies
        Handler->>Feature: handle_call()
        Feature->>CallSM: modify call state
        Feature-->>System: event_handled: true
    else Feature not applicable
        Handler-->>System: event_handled: false
    end

    System->>CallSM: State: ACTIVE
    CallSM->>System: fire event: call_active
    System->>Feature: on_call_event(call_active)
    Feature->>Handler: on_active()
    Handler->>CallSM: attach hooks
    CallSM->>Feature: on_dtmf(digit)
    Feature->>Handler: handle_dtmf(digit)
    alt Action triggered
        Handler->>CallSM: execute_action()
    end

    CallSM->>System: fire event: call_ended
    System->>Feature: on_call_event(call_ended)
    Feature->>Handler: cleanup()
    Feature->>Feature: on_disable()
    Feature-->>System: Feature cleanup done

    System->>Loader: shutdown_features()
    Loader->>Feature: unload()
    Feature->>System: Resources released
```

## 7. Authentication & Authorization Flow

```mermaid
graph TD
    A["User Opens Admin UI<br/>port 443/HTTPS"] -->|GET /admin/| B["Serve login.html"]
    B -->|Display| C["Login Form"]
    C -->|User enters credentials| D["Client JavaScript"]
    D -->|POST /api/auth/login<br/>JSON: username, password| E["Flask Auth Route"]

    E -->|Look up| F["Query Extension<br/>or User table"]
    F -->|User Found| G{Password Match?}
    G -->|NO| H["Return 401<br/>Invalid Credentials"]
    H -->|Display| C

    G -->|YES| I["Generate JWT Token<br/>exp: 24 hours"]
    I -->|Payload: user_id, role,<br/>permissions| J["Sign with secret key<br/>HMAC-SHA256"]
    J -->|Return 200 OK<br/>+ JWT Token| K["Client Storage<br/>localStorage"]
    K -->|Store| L["JWT Token"]

    L -->|Subsequent Requests| M["Add to Header<br/>Authorization: Bearer {JWT}"]
    M -->|GET /api/extensions| N["Flask Route Handler"]

    N -->|Extract JWT| O["Auth Middleware"]
    O -->|Verify Signature| P{Signature Valid?}
    P -->|NO| Q["401 Unauthorized"]
    Q -->|Reject| M

    P -->|YES| R{Token Expired?}
    R -->|YES| Q
    R -->|NO| S["Extract Claims<br/>user_id, role"]
    S -->|Verify| T["Check RBAC<br/>user role"]
    T -->|Query| U["DB: User role +<br/>permissions"]
    U -->|Verify| V{Has Permission<br/>for resource?}

    V -->|NO| W["403 Forbidden"]
    W -->|Reject| M

    V -->|YES| X["Create context:<br/>current_user,<br/>permissions"]
    X -->|Pass| N
    N -->|Execute Logic| Y["Query Extensions<br/>Filter by user permissions"]
    Y -->|Return| Z["200 OK + JSON<br/>with data"]
    Z -->|Display| L

    N -->|Log| AA["Audit Log<br/>user_id, action, resource"]
    AA -->|Store| BB["Audit Table<br/>in Database"]

    style A fill:#ffccbc
    style I fill:#c8e6c9
    style L fill:#fff9c4
    style N fill:#bbdefb
    style AA fill:#f0f4c3
```

## 8. Voicemail Processing Pipeline

```mermaid
graph TB
    A["Call arrives<br/>call_type = VOICEMAIL"] -->|No answer<br/>or busy| B["Connect to<br/>Voicemail Handler"]
    B -->|Play| C["Greeting Audio<br/>${extension}/greeting.wav"]
    C -->|User hears| D["Please leave<br/>a message..."]
    D -->|User speaks| E["RTP Audio<br/>Received"]

    E -->|Write to| F["Temp Audio Buffer<br/>in-memory ring buffer"]
    F -->|Encode| G["Codec Selection<br/>opus/g711"]
    G -->|Save| H["Audio File<br/>/voicemail/{ext}/{uuid}.wav"]

    H -->|Async| I["Speech Recognition<br/>API Call"]
    I -->|Process| J["Transcription<br/>text_result"]
    J -->|Store| K["Voicemail DB Record<br/>+ transcription"]

    K -->|Notify| L["Send Email<br/>to user"]
    L -->|MTA| M["Email + WAV<br/>attachment"]
    M -->|Deliver| N["User Inbox"]

    K -->|Store| O["Create Voicemail<br/>Object in API"]
    O -->|Display in| P["Admin UI<br/>Voicemail Page"]
    P -->|User action| Q{Voicemail Action?}
    Q -->|Listen| R["Play Audio<br/>in browser"]
    Q -->|Delete| S["Mark deleted<br/>soft delete"]
    Q -->|Archive| T["Move to archive"]

    E -->|Also| U["Detect DTMF<br/>Hang up signal"]
    U -->|Listen for| V["User presses #<br/>to finish"]
    V -->|Complete| W["Message Complete"]
    W -->|Duration calc| X["Store duration_seconds"]
    X -->|Update DB| K

    style A fill:#ffccbc
    style E fill:#f0f4c3
    style H fill:#c8e6c9
    style K fill:#bbdefb
    style N fill:#fff9c4
```

## 9. Conference Bridge Architecture

```mermaid
graph TB
    subgraph "Conference Bridge Component"
        CB["Conference Bridge<br/>Mixer & Router"]
        Mix["Audio Mixer<br/>Combine streams"]
        Route["Stream Router<br/>Distribute mixed audio"]
        ResamplerPool["Resampler Pool<br/>Normalize sample rates"]
    end

    subgraph "Conference Members"
        M1["Member 1<br/>Extension 101<br/>8000 Hz"]
        M2["Member 2<br/>Extension 102<br/>16000 Hz"]
        M3["Member 3<br/>Extension 103<br/>8000 Hz"]
        M4["Member 4<br/>External SIP<br/>16000 Hz"]
    end

    subgraph "RTP Streams"
        RTP1["RTP Port 10000<br/>Member 1"]
        RTP2["RTP Port 10002<br/>Member 2"]
        RTP3["RTP Port 10004<br/>Member 3"]
        RTP4["RTP Port 10006<br/>Member 4"]
    end

    subgraph "Utilities"
        Mute["Mute Control<br/>per member"]
        Record["Recording<br/>Conference"]
        DTMFDet["DTMF Detection<br/>Conference commands"]
    end

    M1 -->|RTP Stream| RTP1
    M2 -->|RTP Stream| RTP2
    M3 -->|RTP Stream| RTP3
    M4 -->|RTP Stream| RTP4

    RTP1 -->|Decode| CB
    RTP2 -->|Decode| CB
    RTP3 -->|Decode| CB
    RTP4 -->|Decode| CB

    CB -->|Normalize| ResamplerPool
    ResamplerPool -->|Resample to 16kHz| Mix

    Mix -->|Combine audio streams<br/>sum and scale| Route

    Route -->|M1 doesn't hear self| RTP1
    Route -->|M1 hears M2,M3,M4| RTP1
    Route -->|M2 hears M1,M3,M4| RTP2
    Route -->|M3 hears M1,M2,M4| RTP3
    Route -->|M4 hears M1,M2,M3| RTP4

    Route -->|Check| Mute
    Mute -->|Muted?| Route
    Route -->|Record mixed stream| Record

    RTP1 -->|DTMF| DTMFDet
    RTP2 -->|DTMF| DTMFDet
    DTMFDet -->|*1 = Mute self| Mute
    DTMFDet -->|*2 = Unmute| Mute
    DTMFDet -->|*0 = Hang up| M1

    Record -->|Write| Audio["Conference<br/>Recording.wav"]
    Audio -->|Store| DB["Voicemail/<br/>Conferences/"]

    style CB fill:#c8e6c9
    style Mix fill:#fff9c4
    style Route fill:#bbdefb
    style Mute fill:#f0f4c3
```

## 10. System Monitoring & Observability Stack

```mermaid
graph TB
    subgraph "Metrics Collection"
        Metrics["Prometheus Exporter<br/>utils/prometheus_exporter.py"]
        PBXMetrics["PBX Metrics<br/>- active_calls<br/>- call_duration_histogram<br/>- extensions_registered<br/>- feature_usage"]
        APIMetrics["API Metrics<br/>- request_count<br/>- response_time<br/>- error_rate<br/>- auth_failures"]
        SystemMetrics["System Metrics<br/>- cpu_usage<br/>- memory_usage<br/>- disk_usage<br/>- db_connections"]
    end

    subgraph "Data Persistence"
        TimeSeries["Prometheus Server<br/>Time Series DB<br/>Port 9090"]
        TSDB["TSDB Storage<br/>Retained 15 days"]
    end

    subgraph "Visualization"
        Grafana["Grafana Dashboard<br/>Port 3000"]
        Dashboard1["PBX Overview<br/>Dashboard"]
        Dashboard2["Call Statistics<br/>Dashboard"]
        Dashboard3["System Health<br/>Dashboard"]
    end

    subgraph "Alerting"
        AlertMgr["Alert Manager"]
        Rules["Alert Rules"]
        Notifier["Notification Channel"]
    end

    subgraph "Logging"
        AppLog["Application Logs<br/>utils/logger.py"]
        AuditLog["Audit Logs<br/>utils/audit_logger.py"]
    end

    subgraph "Log Storage & Analysis"
        LogStore["Log Aggregation<br/>ELK/Loki"]
        LogSearch["Log Search<br/>Kibana/Grafana Loki"]
    end

    PBXMetrics -->|Scrape| Metrics
    APIMetrics -->|Scrape| Metrics
    SystemMetrics -->|Scrape| Metrics

    Metrics -->|HTTP /metrics| TimeSeries
    TimeSeries -->|15s interval| TSDB

    TimeSeries -->|Query| Grafana
    Grafana -->|Display| Dashboard1
    Grafana -->|Display| Dashboard2
    Grafana -->|Display| Dashboard3

    TimeSeries -->|Evaluate| Rules
    Rules -->|Alert if| AlertMgr
    AlertMgr -->|Send| Notifier
    Notifier -->|Email/Slack/PagerDuty| DevTeam["On-Call Team"]

    AppLog -->|Write JSON| LogStore
    AuditLog -->|Write JSON| LogStore
    LogStore -->|Index| LogSearch
    LogSearch -->|Query/Display| Grafana

    style Metrics fill:#c8e6c9
    style TimeSeries fill:#bbdefb
    style Grafana fill:#f0f4c3
    style AlertMgr fill:#ffccbc
    style LogStore fill:#fff9c4
```

---

## Summary

These diagrams provide comprehensive views of:

1. **Module Dependencies**: How all backend components interconnect
2. **Database Design**: Complete entity relationships and schema
3. **Request Processing**: End-to-end REST API flow
4. **RTP Media**: Low-level audio stream handling
5. **State Machine**: Call lifecycle with all transitions
6. **Feature Lifecycle**: How 77 feature modules work
7. **Authentication**: JWT, RBAC, and authorization
8. **Voicemail**: Message recording, storage, and retrieval
9. **Conference**: Multi-party mixing and routing
10. **Observability**: Monitoring, metrics, logs, and alerts

Together with the main architecture document, these provide a complete technical picture of Warden VoIP.
