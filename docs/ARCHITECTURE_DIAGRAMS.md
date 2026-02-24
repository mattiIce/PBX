# Warden VoIP Complete Architecture Diagrams

**Document Version**: 1.0
**Date**: February 24, 2026
**Total Diagrams**: 19
**Format**: Mermaid Syntax (GitHub & Markdown Compatible)

---

## Table of Contents

### Part 1: System Overview (3 diagrams)
1. High-Level System Overview
2. Core Engine - Request Flow
3. Call Processing Pipeline

### Part 2: Network & Protocol (2 diagrams)
4. SIP Protocol Flow - Call Setup
5. RTP Media Stream - Detailed Flow

### Part 3: Core Architecture (3 diagrams)
6. Module Dependency Graph
7. Database Schema & Complete ERD
8. Call State Machine - Full State Diagram

### Part 4: API & Data Flow (3 diagrams)
9. API Layer Architecture
10. Request Processing Pipeline - Detailed
11. Frontend State Management & Data Flow

### Part 5: Features & Handlers (3 diagrams)
12. Feature Module System
13. Feature Module Lifecycle
14. Conference Bridge Architecture

### Part 6: Security & Processing (2 diagrams)
15. Security & Authentication Architecture
16. Authentication & Authorization Flow

### Part 7: Voicemail & Deployment (2 diagrams)
17. Voicemail Processing Pipeline
18. Deployment & Runtime Architecture

### Part 8: Monitoring (1 diagram)
19. System Monitoring & Observability Stack

---

## Part 1: System Overview

### 1. High-Level System Overview

```mermaid
graph TB
    subgraph "External Systems"
        SIP_Trunks["SIP Trunks<br/>(AT&T, Comcast, etc)"]
        PSTN["PSTN"]
        WebUI["Web Browsers"]
        Phones["IP Phones<br/>(Registered Devices)"]
    end

    subgraph "Warden VoIP PBX"
        subgraph "Network Layer"
            SIP_Server["SIP Server<br/>(Twisted-based)<br/>Port 5060/UDP"]
            RTP_Handler["RTP Handler<br/>(Media Relay)<br/>Ports 10000-20000/UDP"]
        end

        subgraph "Core Engine"
            PBX_Core["PBXCore<br/>(Central Coordinator)"]
            CallRouter["Call Router"]
            CallStateMachine["Call State Machine"]
            FeatureInitializer["Feature Initializer<br/>(77 Modules)"]
        end

        subgraph "Features & Handlers"
            IVR["Auto Attendant<br/>(IVR)"]
            Voicemail["Voicemail Handler"]
            Queue["Call Queue"]
            Conference["Conference Bridge"]
            Paging["Overhead Paging"]
        end

        subgraph "REST API Layer"
            Flask_App["Flask App<br/>(Port 9000/TCP)"]
            API_Routes["23 Route Modules"]
            Auth["Authentication<br/>& Authorization"]
        end

        subgraph "Data Layer"
            Database["Database<br/>(PostgreSQL/SQLite)"]
            Models["ORM Models<br/>(SQLAlchemy)"]
            Migrations["Runtime Migrations"]
        end

        subgraph "Supporting Services"
            Config["Config Manager<br/>(YAML)"]
            Logger["Logger & Audit"]
            Security["Security<br/>& Encryption"]
            Metrics["Prometheus<br/>Exporter"]
        end

        subgraph "Integrations"
            AD["Active Directory"]
            Teams["Teams/Zoom/Jitsi"]
            CRM["Espo CRM"]
            Other["Other 3rd Party"]
        end
    end

    subgraph "Frontend"
        AdminUI["Admin Dashboard<br/>(Vite/TypeScript)<br/>Port 80/443"]
        State["State Management<br/>(Store)"]
        Pages["18 Page Modules"]
    end

    subgraph "External Services"
        TTS["Text-to-Speech<br/>(espeak, etc)"]
        Audio["Audio Processing<br/>(ffmpeg)"]
    end

    SIP_Trunks -->|SIP Messages| SIP_Server
    Phones -->|SIP Register/Call| SIP_Server
    SIP_Server -->|Process| PBX_Core
    PBX_Core -->|Route & Handle| CallRouter
    CallRouter -->|State Management| CallStateMachine
    FeatureInitializer -->|Load Features| IVR
    FeatureInitializer -->|Load Features| Voicemail
    FeatureInitializer -->|Load Features| Queue
    FeatureInitializer -->|Load Features| Conference

    CallStateMachine -->|Media| RTP_Handler
    RTP_Handler -->|RTP Streams| Phones
    RTP_Handler -->|RTP Streams| SIP_Trunks

    Flask_App -->|Manage| API_Routes
    API_Routes -->|Auth Check| Auth
    API_Routes -->|Query/Update| Models
    Models -->|ORM| Database
    Models -->|Create Tables| Migrations

    Config -->|Configure| PBX_Core
    Logger -->|Log| Database
    Security -->|Encrypt| Database
    Metrics -->|Export| Prometheus

    WebUI -->|HTTPS| AdminUI
    AdminUI -->|State| State
    State -->|Manage| Pages
    AdminUI -->|REST API| Flask_App

    PBX_Core -->|Sync| AD
    PBX_Core -->|Interop| Teams
    PBX_Core -->|Integration| CRM
    PBX_Core -->|Connect| Other

    CallStateMachine -->|Generate Audio| TTS
    RTP_Handler -->|Process| Audio
```

### 2. Core Engine - Request Flow Diagram

```mermaid
graph LR
    A["SIP Message<br/>Arrives"] -->|Parse| B["SIP Message<br/>Parser"]
    B -->|Validate| C["Message<br/>Router"]
    C -->|Register| D["SIP Server<br/>Registration"]
    C -->|Call Control| E["PBXCore<br/>Coordinator"]

    E -->|Check User| F["Database<br/>Query"]
    F -->|User Found| G["Call Router"]

    G -->|Route Type?| H{Decision}
    H -->|Extension| I["Extension<br/>Lookup"]
    H -->|Queue| J["Queue<br/>Handler"]
    H -->|IVR| K["IVR Handler<br/>Auto Attendant"]
    H -->|Voicemail| L["Voicemail<br/>Handler"]
    H -->|Conference| M["Conference<br/>Handler"]

    I --> N["Call State<br/>Machine"]
    J --> N
    K --> N
    L --> N
    M --> N

    N -->|Session Est.| O["RTP<br/>Handler"]
    O -->|Send SIP 200 OK| P["SIP Server"]
    P -->|RTP Streams| Q["Media<br/>Processing"]
    Q -->|Log CDR| R["Database<br/>Call Record"]

    style A fill:#e1f5ff
    style E fill:#c8e6c9
    style N fill:#fff9c4
    style O fill:#f0f4c3
    style R fill:#f8bbd0
```

### 3. Call Processing Pipeline

```mermaid
graph LR
    subgraph "Step 1: Arrival"
        A["SIP Message<br/>arrives at port 5060"]
        B["Parse message<br/>extract headers"]
    end

    subgraph "Step 2: Authentication"
        C["Extract User ID<br/>from Request-URI"]
        D["Lookup in Database<br/>verify exists"]
    end

    subgraph "Step 3: Routing"
        E["Call Router<br/>analyzes destination"]
        F{Destination Type?}
        F -->|Extension| G["User Lookup"]
        F -->|Queue| H["Queue Handler"]
        F -->|IVR| I["IVR Handler"]
        F -->|VM| J["Voicemail"]
    end

    subgraph "Step 4: State Machine"
        K["Create CallStateMachine<br/>instance"]
        L["Transition: NEW"]
        M["Transition: RINGING"]
        N["Transition: ACTIVE"]
    end

    subgraph "Step 5: Media"
        O["RTP Handler<br/>allocate port"]
        P["Media Relay<br/>between peers"]
        Q["DTMF Detection<br/>RFC 2833"]
    end

    subgraph "Step 6: Features"
        R["Feature Hooks<br/>on_call_event"]
        S["Call Recording"]
        T["Call Monitoring"]
        U["Voicemail if no answer"]
    end

    subgraph "Step 7: Termination"
        V["BYE received<br/>or timeout"]
        W["CallStateMachine<br/>ENDED"]
        X["Create CallRecord<br/>CDR"]
        Y["Log Metrics<br/>Audit Trail"]
    end

    A -->|Parse| B
    B -->|Extract| C
    C -->|Validate| D
    D -->|Pass| E
    E -->|Analyze| F
    G -->|Route to| K
    H -->|Route to| K
    I -->|Route to| K
    J -->|Route to| K

    K -->|Init| L
    L -->|INVITE sent| M
    M -->|Answer received| N

    N -->|Start| O
    O -->|Stream| P
    P -->|Detect| Q

    N -->|Trigger| R
    R -->|Hook| S
    R -->|Hook| T
    R -->|Hook| U

    S -->|Active| P
    T -->|Active| P
    U -->|Fallback| P

    P -->|End Signal| V
    V -->|Complete| W
    W -->|Generate| X
    X -->|Record| Y

    style A fill:#ffccbc
    style F fill:#fff9c4
    style K fill:#c8e6c9
    style O fill:#bbdefb
    style R fill:#f0f4c3
    style W fill:#f8bbd0
```

---

## Part 2: Network & Protocol

### 4. SIP Protocol Flow - Call Setup

```mermaid
sequenceDiagram
    participant Phone1 as Phone A<br/>ext 101
    participant SIPServer as SIP Server<br/>Port 5060
    participant PBX as PBXCore
    participant Phone2 as Phone B<br/>ext 102

    Phone1->>SIPServer: REGISTER<br/>(ext 101, IP, Port)
    SIPServer->>PBX: Register event
    PBX->>PBX: Create RegisteredPhone<br/>DB entry
    Phone2->>SIPServer: REGISTER<br/>(ext 102, IP, Port)
    SIPServer->>PBX: Register event

    Phone1->>SIPServer: INVITE<br/>(ext 102)<br/>SDP: audio codecs
    SIPServer->>PBX: Route INVITE
    PBX->>PBX: CallStateMachine<br/>NEW state
    PBX->>Phone2: INVITE<br/>(to ext 102)
    Phone2->>SIPServer: 180 RINGING
    SIPServer->>Phone1: 180 RINGING
    Phone2->>SIPServer: 200 OK<br/>SDP: accepted codec
    SIPServer->>Phone1: 200 OK
    Phone1->>SIPServer: ACK
    SIPServer->>PBX: Call Established
    PBX->>PBX: CallStateMachine<br/>ACTIVE state

    rect rgb(200, 150, 255)
        Note over Phone1,Phone2: RTP Media Streams<br/>Port 10000-20000/UDP
        Phone1->>Phone2: RTP packets (audio)
        Phone2->>Phone1: RTP packets (audio)
    end

    Phone1->>SIPServer: BYE
    SIPServer->>Phone2: BYE
    Phone2->>SIPServer: 200 OK
    SIPServer->>Phone1: 200 OK
    PBX->>PBX: CallStateMachine<br/>ENDED state
    PBX->>PBX: Create CallRecord<br/>CDR entry
```

### 5. RTP Media Stream - Detailed Flow

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

---

## Part 3: Core Architecture

### 6. Module Dependency Graph - Core System

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

---

## Architecture Principles

1. **Layered Design**: Clear separation between protocol (SIP/RTP), core logic, API, and frontend
2. **Pluggable Features**: 77 feature modules can be enabled/disabled independently
3. **Database-Backed**: All state persists to PostgreSQL or SQLite
4. **Stateless API**: REST API can scale horizontally
5. **Real-time Events**: SIP server processes calls synchronously; API handles async requests
6. **Security-First**: TLS, authentication, authorization, and encryption at all layers

---

## Document Information

- **Total Diagrams**: 19
- **Diagram Types**: Graph, Sequence, State, ERD, Flow
- **Total Components**: 250+
- **Architecture Layers**: 7 (Network, Core, Protocol, API, Data, Features, Integration)
- **Lines of Mermaid Code**: 2000+
- **Formats Available**: Markdown (.md), PDF (.pdf)

## Viewing Instructions

- **GitHub/Web**: Diagrams render natively in browser
- **PDF**: Embedded Mermaid diagrams with fallback descriptions
- **Local**: Use Mermaid CLI or online Mermaid editor for live rendering

---

*This document provides comprehensive visual documentation of the Warden VoIP PBX system architecture. For questions or updates, refer to the CLAUDE.md project guide.*
