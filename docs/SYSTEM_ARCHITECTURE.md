# Warden VoIP System Architecture Diagrams

## 1. High-Level System Overview

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

## 2. Core Engine - Request Flow Diagram

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

## 3. Database Schema & Data Model

```mermaid
erDiagram
    Extension ||--o{ RegisteredPhone : registers
    Extension ||--o{ Voicemail : owns
    Extension ||--o{ CallRecord : participates
    Extension ||--o{ CallQueueStats : "queue member"

    Extension {
        int id PK
        string extension_number UK
        string display_name
        string user_uuid FK
        string auth_secret
        string voicemail_pin
        boolean enabled
        timestamp created_at
        timestamp updated_at
    }

    RegisteredPhone {
        int id PK
        int extension_id FK
        string device_name
        string ip_address
        string user_agent
        datetime last_registered
        boolean active
    }

    Voicemail {
        int id PK
        int extension_id FK
        string message_file_path
        string transcription
        boolean is_read
        datetime recorded_at
        int duration_seconds
    }

    CallRecord {
        int id PK
        int from_extension_id FK
        int to_extension_id FK
        string call_id UK
        string direction
        string status
        datetime start_time
        datetime end_time
        int duration_seconds
        string recording_path
    }

    CallQueueStats {
        int id PK
        int extension_id FK
        int calls_handled
        int total_wait_time
        int avg_handle_time
        datetime period
    }
```

## 4. API Layer Architecture

```mermaid
graph TD
    subgraph "API Server Port 9000"
        Flask["Flask App<br/>(create_app factory)"]

        subgraph "Route Modules - 23 endpoints"
            R1["Extensions API"]
            R2["Calls API"]
            R3["Voicemail API"]
            R4["Queues API"]
            R5["Features API"]
            R6["Reports API"]
            R7["Auth API"]
            R8["Config API"]
            R9["Monitoring API"]
        end

        subgraph "Request Processing"
            Auth["Authentication<br/>(JWT/Session)"]
            Validation["Request Validation<br/>(JSON Schema)"]
            ErrorHandler["Error Handler<br/>(Consistent Responses)"]
        end

        subgraph "Response Layer"
            Schemas["Response Schemas<br/>(5 modules)"]
            Serialization["JSON Serialization"]
        end
    end

    subgraph "Support Systems"
        PBX["PBXCore<br/>(Injected)"]
        DB["Database"]
        Logger["Audit Logger"]
    end

    Client["Web Client<br/>Browser"] -->|REST<br/>JSON| Flask

    Flask -->|Route| R1
    Flask -->|Route| R2
    Flask -->|Route| R3
    Flask -->|Route| R4
    Flask -->|Route| R5
    Flask -->|Route| R6
    Flask -->|Route| R7
    Flask -->|Route| R8
    Flask -->|Route| R9

    R1 -->|Check| Auth
    R2 -->|Check| Auth
    R3 -->|Check| Auth
    R4 -->|Check| Auth
    R5 -->|Check| Auth
    R6 -->|Check| Auth
    R7 -->|Check| Auth
    R8 -->|Check| Auth
    R9 -->|Check| Auth

    Auth -->|Validate| Validation
    Validation -->|Pass| R1
    Validation -->|Pass| R2

    R1 -->|Query| PBX
    R2 -->|Query| PBX
    R3 -->|Query| PBX

    PBX -->|Access| DB

    R1 -->|Format| Schemas
    Schemas -->|Serialize| Serialization
    Serialization -->|Response| Client

    R1 -->|Log| Logger
    R2 -->|Log| Logger

    ErrorHandler -->|Catch| Client

    style Flask fill:#bbdefb
    style Auth fill:#c8e6c9
    style Validation fill:#fff9c4
```

## 5. Feature Module System

```mermaid
graph TB
    subgraph "Feature Loader"
        FeatureInit["Feature Initializer<br/>(pbx/features/__init__.py)"]
        Scanner["Feature Scanner<br/>(Discover .py files)"]
        Loader["Dynamic Loader<br/>(importlib)"]
    end

    subgraph "Core Features"
        F1["Call Transfer"]
        F2["Call Hold"]
        F3["Call Park"]
        F4["Call Pickup"]
        F5["Do Not Disturb"]
        F6["Call Forwarding"]
        F7["Call Waiting"]
        F8["Caller ID"]
    end

    subgraph "Advanced Features"
        F9["Auto Attendant"]
        F10["Queue Management"]
        F11["Conference Bridge"]
        F12["Call Recording"]
        F13["Voicemail"]
        F14["IVR"]
        F15["Paging"]
        F16["Presence"]
    end

    subgraph "Integration Features"
        F17["Teams Integration"]
        F18["Zoom Integration"]
        F19["CRM Connector"]
        F20["Directory Sync"]
    end

    subgraph "Feature Base Class"
        Base["Feature<br/>(Abstract Base)"]
        LifeCycle["Lifecycle Methods:<br/>on_initialize()<br/>on_call_event()<br/>on_disable()"]
    end

    PBX["PBXCore"] -->|Start| FeatureInit
    FeatureInit -->|Find| Scanner
    Scanner -->|Discover| F1
    Scanner -->|Discover| F2
    Scanner -->|Discover| F9

    Loader -->|Register| F1
    Loader -->|Register| F2
    Loader -->|Register| F9

    F1 -->|Extends| Base
    F2 -->|Extends| Base
    F9 -->|Extends| Base

    Base -->|Defines| LifeCycle

    F1 -->|Hook into| CallRouter["Call Router"]
    F2 -->|Hook into| CallRouter
    F9 -->|Hook into| CallRouter

    CallRouter -->|Fire Events| LifeCycle

    style FeatureInit fill:#c8e6c9
    style Base fill:#fff9c4
    style CallRouter fill:#bbdefb
```

## 6. SIP Protocol Flow - Call Setup

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

## 7. Frontend State Management & Data Flow

```mermaid
graph TB
    subgraph "Browser"
        UI["Admin Dashboard UI<br/>(Vite + React/Vue)"]

        subgraph "Pages (18 modules)"
            P1["Dashboard"]
            P2["Extensions"]
            P3["Calls"]
            P4["Reports"]
            P5["Settings"]
        end

        subgraph "State Management"
            Store["Central Store<br/>(Redux/Pinia)"]
            Actions["Async Actions<br/>(API calls)"]
            Getters["State Getters<br/>(Selectors)"]
        end

        subgraph "API Client"
            Client["API Client<br/>(fetch wrapper)"]
            Auth["Auth Module<br/>(JWT/Session)"]
            Cache["Response Cache"]
        end

        subgraph "UI Components"
            C1["Notifications"]
            C2["Tabs"]
            C3["Forms"]
            C4["Tables"]
        end
    end

    subgraph "Backend API"
        API["REST API<br/>Port 9000"]
    end

    User["User<br/>Browser Input"] -->|Interact| UI
    UI -->|Render| P1
    UI -->|Render| P2
    UI -->|Render| P3

    P1 -->|Dispatch| Actions
    P2 -->|Dispatch| Actions
    P3 -->|Dispatch| Actions

    Actions -->|Call| Client
    Client -->|Check| Auth
    Auth -->|Add JWT| Client
    Client -->|Check| Cache
    Cache -->|Miss| API
    Cache -->|Hit| Store

    API -->|Response| Client
    Client -->|Dispatch| Store

    Store -->|Update| Getters
    Getters -->|Provide| P1
    Getters -->|Provide| P2
    Getters -->|Provide| P3

    P1 -->|Use| C1
    P2 -->|Use| C3
    P2 -->|Use| C4

    C1 -->|Display| User
    C3 -->|Display| User
    C4 -->|Display| User
```

## 8. Security & Authentication Architecture

```mermaid
graph TB
    subgraph "Authentication"
        Login["Login Form<br/>(Username/Password)"]
        Validate["Validate Credentials<br/>vs Database"]
        JWT["Issue JWT Token<br/>(exp: 24h)"]
    end

    subgraph "Authorization"
        RoleCheck["Role-Based Access<br/>Control RBAC"]
        PermCheck["Permission Check<br/>on each request"]
        Audit["Audit Log<br/>All actions"]
    end

    subgraph "Encryption"
        TLS["TLS 1.3<br/>(HTTPS)"]
        DBEnc["Database Encryption<br/>(FIPS 140-2)"]
        PasswdHash["Password Hashing<br/>(bcrypt)"]
    end

    subgraph "Security Middleware"
        CSP["Content Security<br/>Policy"]
        CORS["CORS Policy<br/>Restricted"]
        RateLimit["Rate Limiting"]
        SecurityMon["Security Monitor<br/>(Threat Detection)"]
    end

    User["User"] -->|Submit Creds| Login
    Login -->|POST /auth/login| Validate
    Validate -->|Hash & Compare| PasswdHash
    PasswdHash -->|Valid| JWT
    JWT -->|Token| User

    User -->|Request + JWT| TLS
    TLS -->|Secure Channel| API["API Endpoint"]

    API -->|Verify JWT| Auth["Auth Middleware"]
    Auth -->|Extract User| RoleCheck
    RoleCheck -->|User Role?| PermCheck
    PermCheck -->|Allowed?| Handler["Route Handler"]
    Handler -->|Yes| Execute["Execute Logic"]
    Handler -->|No| Deny["Deny 403"]

    Execute -->|Query| DBEnc
    DBEnc -->|Decrypt| Data["Sensitive Data"]

    Handler -->|Log| Audit
    API -->|Apply| CSP
    API -->|Apply| CORS
    API -->|Apply| RateLimit
    API -->|Monitor| SecurityMon

    style Login fill:#ffccbc
    style JWT fill:#c8e6c9
    style TLS fill:#bbdefb
    style DBEnc fill:#f0f4c3
```

## 9. Deployment & Runtime Architecture

```mermaid
graph TB
    subgraph "Development"
        DevPC["Developer Machine"]
        Git["Git Repository"]
        PreCommit["Pre-commit Hooks<br/>(ruff, mypy, bandit)"]
    end

    subgraph "CI/CD Pipeline"
        GHA["GitHub Actions"]
        Tests["pytest + coverage<br/>(80% minimum)"]
        Lint["ruff lint + mypy"]
        Security["Bandit + Trivy<br/>Scanning"]
        Build["Docker Build<br/>Multi-stage"]
    end

    subgraph "Container Registry"
        DockerHub["Docker Hub<br/>or Private Registry"]
    end

    subgraph "Production Deployment"
        K8S["Kubernetes Cluster<br/>or Docker Swarm"]

        subgraph "PBX Pod/Container"
            PBXApp["Python App<br/>(pbx-server)"]
            Port5060["Port 5060/UDP<br/>SIP"]
            Port9000["Port 9000/TCP<br/>REST API"]
            Port10K["Ports 10000-20000/UDP<br/>RTP"]
        end

        subgraph "Support Services"
            PG["PostgreSQL 17<br/>(Database)"]
            Redis["Redis 7<br/>(Cache/Queue)"]
            Monitor["Prometheus<br/>Monitoring"]
        end

        subgraph "Storage"
            PVC["Persistent Volume<br/>Config & Voicemail"]
            Backup["Backup Storage"]
        end

        subgraph "Networking"
            LB["Load Balancer<br/>(TCP 9000)"]
            Ingress["Ingress Controller<br/>(HTTPS)"]
        end
    end

    DevPC -->|git push| Git
    Git -->|Webhook| GHA

    GHA -->|Run| PreCommit
    GHA -->|Run| Tests
    GHA -->|Run| Lint
    GHA -->|Run| Security
    GHA -->|On Success| Build

    Build -->|Push| DockerHub

    DockerHub -->|Pull| K8S
    K8S -->|Deploy| PBXApp

    PBXApp -->|Listen| Port5060
    PBXApp -->|Listen| Port9000
    PBXApp -->|Listen| Port10K

    PBXApp -->|Query| PG
    PBXApp -->|Cache| Redis
    PBXApp -->|Mount| PVC

    PBXApp -->|Export Metrics| Monitor
    Monitor -->|Scrape| Prometheus

    PG -->|Backup to| Backup
    PVC -->|Backup to| Backup

    Users["End Users<br/>Phones/Browsers"] -->|SIP| Port5060
    Users -->|HTTPS| Ingress
    Ingress -->|Proxy| LB
    LB -->|Forward| Port9000

    style DevPC fill:#fff9c4
    style GHA fill:#c8e6c9
    style K8S fill:#bbdefb
    style PBXApp fill:#f0f4c3
```

## 10. Call Processing Pipeline

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

## Legend

- **Solid Lines**: Direct data flow or method calls
- **Dashed Lines**: Asynchronous events or callbacks
- **Bold Text**: Key components or decisions
- **Color Coding**:
  - 🔴 Network/Protocol layer
  - 🟢 Core engine
  - 🟡 State/Configuration
  - 🔵 API/REST layer
  - 🟠 Features/Integrations
  - 🟣 Storage/Database

## Architecture Principles

1. **Layered Design**: Clear separation between protocol (SIP/RTP), core logic, API, and frontend
2. **Pluggable Features**: 77 feature modules can be enabled/disabled independently
3. **Database-Backed**: All state persists to PostgreSQL or SQLite
4. **Stateless API**: REST API can scale horizontally
5. **Real-time Events**: SIP server processes calls synchronously; API handles async requests
6. **Security-First**: TLS, authentication, authorization, and encryption at all layers
