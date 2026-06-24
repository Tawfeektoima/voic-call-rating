# Voice Call Rating Project Hierarchy

هذا الملف يقدّم خريطة **hierarchical** للمشروع، مع تقسيم الـ backend والـ frontend والـ data layer والـ workers، ثم يوضح وظيفة كل component أو module وعلاقته بباقي الأجزاء. كل المعلومات هنا مبنية على ملف `repomix` المرفق الذي يحتوي على شجرة المشروع وكود الملفات الأساسية [file:1].

## 1) System Map

```text
Voice Call Rating Platform
├── Backend (FastAPI)
│   ├── app/main.py
│   ├── routers/
│   ├── services/
│   ├── workers/
│   ├── models.py
│   ├── schemas.py
│   ├── permissions.py
│   ├── violations.py
│   ├── config.py / database.py / security.py / limiter.py
│   └── recovery.py
├── Frontend (React + Vite)
│   ├── src/components/
│   ├── src/pages/
│   ├── src/hooks/
│   ├── src/context/
│   ├── src/lib/
│   ├── routes.tsx / App.tsx / main.tsx
│   └── tests/
├── Infra / Ops
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   ├── Dockerfile
│   ├── alembic/
│   └── .github/workflows/ci.yml
└── Tests
    ├── backend tests/
    └── frontend vitest suites
```

المنصة مكوّنة من backend رئيسي بـ FastAPI، وواجهة React/Vite، وطبقة async processing عبر Celery/Redis، مع قاعدة بيانات SQLAlchemy/Alembic، إضافة إلى مسار live processing وRAG محلي وواجهات تقارير وإدارة وHR وnotes [file:1].

## 2) Backend Root

### 2.1 `app/main.py`

**الدور:** نقطة التشغيل وتجميع التطبيق [file:1].

**المسؤوليات الأساسية:**
- إنشاء `FastAPI` app وتعريف `lifespan` startup/shutdown logic [file:1].
- تفعيل `Prometheus Instrumentator` وmetrics إضافية مثل suggestion latency وASR latency وGPU VRAM وactive sessions [file:1].
- تهيئة CORS للواجهة الأمامية [file:1].
- تشغيل `redislistener()` لإرسال updates عبر WebSocket manager [file:1].
- تشغيل `configure_redis_limits()` لتطبيق سياسات memory/eviction على Redis أثناء startup [file:1].
- تشغيل heartbeat loop من `app.workers.asrworker` لمتابعة الـ GPU/live ASR health [file:1].
- تضمين routers الأساسية والاختيارية: `auth`, `admin`, `audio`, `analytics`, `system`, `export`, `hr`, `notes`, `websocketrouter`, `live`, `review`, وoptional routers مثل `ops`, `teamleader`, `teammanager` [file:1].

**العلاقات:**
- يعتمد على `config.py` و`database.py` لتهيئة البيئة والـ DB [file:1].
- يربط `services.websocket.manager` مع `routers.websocketrouter` و`redislistener()` [file:1].
- ينسّق مع `workers.asrworker` لمراقبة live ASR health [file:1].

### 2.2 `app/config.py`

**الدور:** إدارة إعدادات البيئة المركزية عبر `Settings` [file:1].

**أهم الحقول والدوال:**
- إعدادات الأمن: `SECRETKEY`, `ENVIRONMENT` [file:1].
- إعدادات DB: `DATABASEURL` مع منع SQLite في production [file:1].
- إعدادات الصوت: `UPLOADDIR`, `MAXFILESIZEMB`, `ALLOWEDEXTENSIONS` [file:1].
- إعدادات Redis/Celery: `REDISHOST`, `REDISPORT`, `REDISURL`, `CELERYBROKERURL` [file:1].
- `allowedextensionslist` لتحويل النص لقائمة extensions [file:1].
- `maxfilesizebytes` لحساب الحجم الأقصى الفعلي [file:1].
- `buildredisurl()` و`redisurlhaspassword()` [file:1].
- `normalizeredissettings()` لتوحيد REDISURL وCELERYBROKERURL والتحقق من متطلبات production [file:1].
- `getsettings()` كمزوّد cached للإعدادات [file:1].

**العلاقات:**
- تستخدمه معظم الملفات: `main.py`, `database.py`, `security.py`, `worker.py`, `ragworker.py` [file:1].

### 2.3 `app/database.py`

**الدور:** تهيئة SQLAlchemy engine وsession factory و`Base` [file:1].

**الدوال:**
- `getdb()` لتوفير DB session داخل FastAPI dependencies [file:1].

**العلاقات:**
- جميع routers/services التي تتعامل مع DB تعتمد على `getdb()` [file:1].
- `SessionLocal` يُستخدم أيضاً داخل workers وWebSocket/live handlers [file:1].

### 2.4 `app/security.py`

**الدور:** المصادقة والتشفير وإنشاء JWT [file:1].

**الدوال:**
- `verify_password()` [file:1].
- `get_password_hash()` [file:1].
- `create_access_token()` [file:1].

**العلاقات:**
- يستخدمها `routers/auth.py` لتسجيل الدخول والتسجيل [file:1].

### 2.5 `app/limiter.py`

**الدور:** rate limiting بسيط داخل الذاكرة لمحاولات login [file:1].

**المكوّنات:**
- `RateLimiter` class مع `prune()`, `is_limited()`, `record_failure()`, `reset_key()`, `check()`, `reset()` [file:1].
- `loginiplimiter` و`loginemaillimiter` كـ global instances [file:1].

**العلاقات:**
- `routers/auth.py` يستخدمهما أثناء login لمنع brute-force [file:1].

## 3) Data Model Layer

### 3.1 Core Entities in `app/models.py`

#### `Employee`

**الدور:** يمثل المستخدم/الموظف داخل النظام [file:1].

**أهم الحقول:**
- `name`, `email`, `department`, `employeecode`, `hashedpassword`, `role`, `avatar`, `tier`, `status`, `skills`, `phonenumber`, `emotionhistory`, `agenttenuredays` [file:1].

**العلاقات:**
- `calls`, `masterystats`, `coachingsessions`, `violations`, `attendancerecords` [file:1].
- يرتبط أيضاً كمرسل/مستقبل/مراجع في notes وtransfer requests [file:1].

#### `Campaign`

**الدور:** تعريف الحملة business context لكل call [file:1].

**أهم الحقول:**
- `name`, `description`, `type`, `status`, `kpis`, `color`, `evaluationprompt` [file:1].

**العلاقات:**
- `calls`, `violations`, `operationaltargets` [file:1].

#### `Call`

**الدور:** الكيان المركزي للمكالمة المسجلة أو live [file:1].

**أهم الحقول:**
- `employeeid`, `campaignid`, `audiofilepath`, `originalfilename`, `audioduration`, `source`, `status`, `errormessage`, `transcript`, `reasoning`, `evaluationscore`, `strengths`, `weaknesses`, `overriddenscore`, `reviewernotes`, `reviewedat` [file:1].

**العلاقات:**
- `employee`, `campaign`, `outcome`, `qapairs`, `annotations`, `violations` [file:1].

#### `CallOutcome`

**الدور:** business intelligence layer فوق call evaluation [file:1].

**أهم الحقول:**
- `primaryoutcome`, `outcomevalue`, `followuprequired`, `followupdate`, `agenttalktime`, `customertalktime`, `talkratio`, `campaignspecificdata` [file:1].

**العلاقات:**
- one-to-one مع `Call` [file:1].

#### `AgentViolation`

**الدور:** تسجيل المخالفات المستخرجة من التقييم [file:1].

**العلاقات:**
- ترتبط بـ `Employee`, `Call`, `Campaign` [file:1].

#### `RoleNote`

**الدور:** internal workflow messaging + KPI-linked notes [file:1].

**أهم الحقول:**
- `senderid`, `recipientid`, `recipientrole`, `visibility`, `teamid`, `campaignid`, `employeeid`, `callid`, `parentnoteid`, `title`, `body`, `notetype`, `priority`, `status`, `kpikey`, `kpilabel`, `currentvalue`, `targetvalue`, `periodstart`, `periodend`, snapshots, resolution/deletion metadata [file:1].

**العلاقات:**
- مع `Employee`, `Team`, `Campaign`, `Call`, وself-referencing thread عبر `parent` [file:1].

#### `Team`

**الدور:** grouping للوكلاء مع manager/leader وربط بالحملات [file:1].

**العلاقات:**
- `campaign`, `manager`, `leader`, `assignments` [file:1].

#### `EmployeeTeamAssignment`

**الدور:** ربط many-to-many شبه زمني بين الموظف والفريق [file:1].

**العلاقات:**
- `employee`, `team`, `createdby` [file:1].

#### `AgentTransferRequest`

**الدور:** workflow لنقل agent بين فرق [file:1].

**العلاقات:**
- `agent`, `fromteam`, `toteam`, `requestedby`, `reviewedby` [file:1].

#### `AttendanceRecord`

**الدور:** تتبع الحضور والالتزام الزمني [file:1].

#### `OperationalTarget`

**الدور:** targets للـ ops KPIs مع scope campaign/segment/global [file:1].

#### `KpiThresholdConfig`

**الدور:** تعريف thresholds على مستوى team/campaign لمتابعة KPI notes [file:1].

#### `LiveSession` و`LiveTranscriptSegment`

**الدور:** طبقة live pipeline قبل تحويل الجلسة إلى `Call` عادية [file:1].

#### `CallQAPair`, `CallAnnotation`, `CoachingSession`, `AgentMasteryStats`, `SystemLog`

**الأدوار:**
- `CallQAPair`: objection/response pairs للـ RAG والتدريب [file:1].
- `CallAnnotation`: ملاحظات supervisor زمنية [file:1].
- `CoachingSession`: جلسات coaching وتأثيرها [file:1].
- `AgentMasteryStats`: performance aggregates طويلة المدى [file:1].
- `SystemLog`: سجل أخطاء وتشغيل ومراقبة النظام [file:1].

## 4) Schema Layer

`app/schemas.py` يعرّف Pydantic contracts التي تربط الـ routers بالـ frontend وتمنع تسرب الـ ORM مباشرة [file:1]. من أبرز الـ groups الموجودة: auth schemas، audio/call schemas، HR/violations schemas، notes schemas، ops schemas، team leader/manager schemas، وsystem monitoring schemas [file:1].

**أمثلة بارزة:**
- `RoleNoteOut`, `RoleNoteThreadOut` للـ notes [file:1].
- `OpsDashboardOut`, `OpsCampaignRow`, `OpsQAOverviewOut`, `OpsViolationsOverviewOut` للـ operations [file:1].
- `TeamLeaderDashboardOut`, `TeamLeaderAgentRowOut`, `TeamLeaderKpisOut` لواجهات team leader [file:1].

## 5) Router Layer

## 5.1 `app/routers/auth.py`

**الدور:** authentication وidentity [file:1].

**الدوال/الـ endpoints:**
- `get_user_from_token()` لفك JWT وتحميل المستخدم [file:1].
- `get_current_user()` dependency شائعة لباقي الـ routers [file:1].
- `register_user()` لتسجيل مستخدم جديد، وصلاحيتها admin فقط [file:1].
- `login_user()` لإصدار access token مع rate limiting على IP وemail [file:1].
- `get_me()` لإرجاع بيانات المستخدم الحالي [file:1].

**العلاقات:**
- يعتمد على `security.py`, `limiter.py`, `models.Employee`, و`services.audit.log_audit_event` [file:1].
- كل routers تقريباً تعتمد على `get_current_user()` [file:1].

## 5.2 `app/routers/audio.py`

**الدور:** رفع المكالمات، استرجاع نتائجها، review overrides [file:1].

**الوظائف الرئيسية:**
- single upload endpoint لإنشاء `Call` جديدة بحالة `PENDING` وتشغيل worker [file:1].
- `bulk_upload_audio()` لرفع عدة ملفات مع metadata mapping والتحقق من employee/campaign والامتدادات والحجم [file:1].
- `get_call_status()` لإرجاع تفاصيل call بشكل مناسب للواجهة، بما فيه deductions وviolations وoverride audits [file:1].
- `get_call_audio_file()` لبث ملف الصوت نفسه [file:1].
- `review_call()` لإضافة `overriddenscore` و`reviewernotes` وإنشاء `ScoreOverrideAudit` [file:1].
- `update_lead_status()` لتحديث lead status من غير الـ agents [file:1].

**العلاقات:**
- يكتب إلى `Call` ويقرأ من `AgentViolation` و`ScoreOverrideAudit` [file:1].
- يشغّل `processcallaudiotask.delay()` في `worker.py` [file:1].

## 5.3 `app/routers/live.py`

**الدور:** live session orchestration عبر WebSocket وreconnect logic وflush [file:1].

**المسؤوليات العامة المستخرجة من الملف:**
- بدء session وربطها بـ GPU [file:1].
- استقبال chunks صوتية PCM داخل WebSocket [file:1].
- إدارة `activeasrsessions` و`pendingflushes` [file:1].
- التعامل مع disconnect/reconnect window ثم تشغيل `backgroundflushsession()` عند انتهاء المهلة [file:1].

**العلاقات:**
- يعتمد على `workers.asrworker`, `workers.sessionflusher`, `services.agentarchive`, و`models.LiveSession`/`LiveTranscriptSegment` [file:1].

## 5.4 `app/routers/review.py`

**الدور:** Human-in-the-Loop review لمرشحي الـ Golden Pairs [file:1].

**الدوال:**
- `require_review_access()` للتحقق من الصلاحيات [file:1].
- `get_review_queue()` لسحب المرشحين pending مع call context [file:1].
- `approve_candidate()` لتحديث الحالة إلى approved، وتوليد embedding، وتخزين document داخل ChromaDB مع `campaignid` metadata [file:1].
- `reject_candidate()` لرفض المرشح [file:1].

**العلاقات:**
- يعتمد على `workers.ragworker.collection` و`workers.ragworker.getmodel()` [file:1].
- يقرأ/يعدّل `GoldenPairCandidate` [file:1].

## 5.5 `app/routers/system.py`

**الدور:** health monitoring وsystem alerts [file:1].

**الدوال:**
- `get_system_metrics()` لقراءة CPU/GPU/uptime/disk/queue depth/pipeline latency/خدمات النظام [file:1].
- `get_system_alerts()` لإرجاع `SystemLog` entries [file:1].
- `resolve_alert()` لوسم alert على أنه resolved [file:1].

**العلاقات:**
- يستخدم `services.aggregation.calculate_core_kpis()` [file:1].
- يفحص Redis, DB, Celery, ASR heartbeat, RAG collection, Groq config, WebSocket manager [file:1].

## 5.6 `app/routers/export.py`

**الدور:** exports للـ CSV/XLSX/ZIP transcripts [file:1].

**الدوال:**
- `export_filters_summary()` لبناء وصف filters [file:1].
- `audit_export_attempt()` و`deny_export()` لفرض الصلاحيات وتسجيل المحاولة [file:1].
- `redact_text()` لإخفاء PII عبر regex [file:1].
- `redact_transcript()` لإخفاء البيانات الحساسة في transcript لغير admin [file:1].
- `export_calls_csv()` [file:1].
- `export_dataset_xlsx()` باستخدام `ExportService.build_dataset()` و`ExportService.to_styled_xlsx()` [file:1].
- `export_transcripts_zip()` [file:1].

**العلاقات:**
- يعتمد على `services.export.ExportService` و`services.audit` [file:1].
- يقرأ `Call`, `Campaign`, `Employee` [file:1].

## 5.7 `app/routers/hr.py`

**الدور:** HR violations + bulk onboarding + QA alarms [file:1].

**الدوال الأساسية:**
- `get_violations_summary()` لإحصاءات per-agent grouped by severity [file:1].
- `get_pending_hr_violations()` لسحب violations المعلمة بـ `hrflagged=True` [file:1].
- `get_violation_stats()` لإحصاءات المنصة اليومية/الأسبوعية [file:1].
- `get_violation_trends()` لعرض trend زمني [file:1].
- `get_agent_violations()` لسجل agent معين [file:1].
- `get_pending_qa_alarms()` لنداءات QA alarms [file:1].
- `download_template()` لقالب CSV onboarding [file:1].
- `preview_bulk_agents()` لقراءة CSV/XLSX والتحقق من البيانات قبل الإدخال [file:1].
- `import_bulk_agents()` لإدخال جماعي مع atomic/non-atomic behavior [file:1].

**العلاقات:**
- يعتمد على `Employee`, `Campaign`, `AgentViolation`, `Call` و`getpasswordhash()` [file:1].

## 5.8 `app/routers/notes.py`

**الدور:** threaded role-based notes وKPI workflows [file:1].

**الدوال:**
- helper functions مثل `note_status_value()`, `visibility_value()`, `note_type_value()`, `priority_value()`, `get_note_or_404()`, `get_root_note()`, `load_thread()`, `ensure_can_view()` [file:1].
- `create_note()` لإنشاء note جديدة بعد `validate_note_context()` و`validate_note_recipient()` وبناء snapshots [file:1].
- `list_allowed_recipients()` [file:1].
- `get_inbox()` و`get_sent()` [file:1].
- `get_note_thread()` [file:1].
- `reply_to_note()` مع auto-resolve recipient أحياناً [file:1].
- `mark_note_read()` [file:1].
- `update_note_status()` مع transitions مضبوطة [file:1].
- `resolve_note()` [file:1].
- `archive_note()` admin only [file:1].
- `delete_note()` admin only عبر soft delete [file:1].

**العلاقات:**
- يعتمد على `services.noterecipients`, `services.notescope`, `services.noteretention`, `services.audit` [file:1].
- يرتبط بالـ teams/campaigns/employees/calls حسب context [file:1].

## 5.9 `app/routers/ops.py`

**الدور:** operations dashboard والتقارير العليا [file:1].

**الدوال:**
- `get_ops_filters()` لتحويل query params إلى `OpsFilters` [file:1].
- `read_ops_dashboard()` [file:1].
- `read_ops_sales_report()` [file:1].
- `read_ops_revenue_report()` [file:1].
- `read_ops_conversion_report()` [file:1].
- `read_ops_attendance_report()` [file:1].
- `read_ops_campaigns()` و`read_ops_campaign_detail()` [file:1].
- `read_ops_qa_overview()` [file:1].
- `read_ops_violations_overview()` [file:1].
- `read_ops_alerts()` [file:1].

**العلاقات:**
- يغلف `services.opsreporting` ويستخدم `permissions.requireopsreportingaccess` [file:1].

## 5.10 `app/routers/teamleader.py`

**الدور:** endpoints مخصصة لعرض scope الـ team leader [file:1].

**الدوال:**
- `getleaderteamids()` لتحديد الفريق/الفرق التابعة للقائد [file:1].
- `getteamleaderdashboard()` [file:1].
- `getteamleaderteams()` [file:1].
- `getteamleaderagents()` [file:1].
- `getteamleaderagentdetail()` [file:1].
- `getteamleadercalls()` [file:1].
- `getteamleadercalldetail()` [file:1].
- `getteamleaderkpis()` [file:1].

**العلاقات:**
- يعتمد على `services.teamscope` للتحقق من scope [file:1].
- يقرأ `RoleNote`, `AgentTransferRequest`, `Call`, `EmployeeTeamAssignment` [file:1].

## 5.11 `app/routers/teammanager.py`

**الدور:** endpoints وتقارير وtransfer workflow الخاصة بالـ team manager [file:1].

**الدوال:**
- `getdashboard()`, `getteams()`, `getteamdetail()`, `getagents()`, `getagentdetail()` [file:1].
- `getsalesreport()`, `getrevenuereport()`, `getconversionreport()`, `getattendancereport()`, `getkpis()` [file:1].
- `listtransferrequests()` [file:1].
- `gettransferrequestdetail()` [file:1].
- `createtransferrequest()` [file:1].
- `canceltransferrequest()` [file:1].

**العلاقات:**
- يغلف `services.teammanagerreporting` ويعتمد على `services.teamscope` و`services.audit` [file:1].

## 5.12 `app/routers/websocketrouter.py`

**الدور:** websocket updates المرتبطة بحالة calls [file:1].

**الدوال:**
- `websocketendpoint()` لتوصيل المستخدم بقناة call محددة بعد التحقق من token والحالة [file:1].

**العلاقات:**
- يعتمد على `auth.getuserfromtoken()` و`services.websocket.manager` [file:1].

## 5.13 Routers أخرى

وجود `admin.py` و`analytics.py` ضمن include routers يعني أن هناك طبقات إدارية وتحليلية إضافية للواجهة، حتى لو لم تظهر هنا كل تفاصيل دوالها في نتائج البحث الحالية [file:1].

## 6) Services Layer

## 6.1 `app/services/aggregation.py`

**الدور:** حساب KPIs مركزية مشتركة [file:1].

**الدالة الأساسية:**
- `calculate_core_kpis()` لحساب total calls, avg QA, pending, processing, pass rate, calls today مع optional agent/date filtering [file:1].

**العلاقات:**
- تستخدمها dashboards و`routers/system.py` [file:1].

## 6.2 `app/services/opsreporting.py`

**الدور:** محرك الـ operations dashboards [file:1].

**أهم الدوال:**
- `get_target_with_fallback()` لاختيار target بالترتيب: exact match ثم campaign ثم segment ثم global [file:1].
- `compute_status()` لتصنيف metric إلى `good/warning/critical` [file:1].
- `get_totals()` لحساب sales/revenue/conversion/attendance/QA/violations [file:1].
- `build_campaign_rows()` لتجميع البيانات على مستوى الحملات [file:1].
- `get_ops_dashboard()` [file:1].
- `get_ops_sales_report()` و`get_ops_revenue_report()` و`get_ops_conversion_report()` [file:1].
- `get_ops_attendance_report()` [file:1].
- `get_ops_qa_overview()` [file:1].
- `get_ops_violations_overview()` [file:1].

**العلاقات:**
- طبقة الأعمال خلف `routers/ops.py` [file:1].

## 6.3 `app/services/teammanagerreporting.py`

**الدور:** business logic لتقارير الـ team manager [file:1].

**الدوال المعلنة من خلال router الاستهلاكي:**
- `getteammanagerdashboard()` [file:1].
- `getteammanagerteams()` [file:1].
- `getteammanagerteamdetail()` [file:1].
- `getteammanageragents()` [file:1].
- `getteammanageragentdetail()` [file:1].
- `getteammanagersalesreport()` [file:1].
- `getteammanagerrevenuereport()` [file:1].
- `getteammanagerconversionreport()` [file:1].
- `getteammanagerattendancereport()` [file:1].
- `getteammanagerkpis()` [file:1].

## 6.4 `app/services/teamscope.py`

**الدور:** scope resolution للأدوار manager/leader [file:1].

**الدوال الظاهرة عبر الاستخدام:**
- `getledteamids()` [file:1].
- `getteamleaderagentids()` [file:1].
- `isagentinleaderscope()` [file:1].
- `getmanagedteamids()` [file:1].
- `isagentinmanagerscope()` [file:1].
- `isteaminmanagerscope()` [file:1].
- `isagentassignedtoteam()` [file:1].

**العلاقات:**
- تستخدم في routers teamleader/teammanager وnotes recipient resolution [file:1].

## 6.5 `app/services/noterecipients.py`

**الدور:** تحديد الـ recipients المسموح لهم في workflow notes [file:1].

**الدوال الظاهرة:**
- `getallowednoterecipients()` [file:1].
- `validatenoterecipient()` [file:1].

## 6.6 `app/services/notescope.py`

**الدور:** enforcing note context + snapshots + permissions [file:1].

**الدوال الظاهرة:**
- `loademployee()` [file:1].
- `buildnotesnapshots()` [file:1].
- `canuserreadnote()` [file:1].
- `canuserreplytonote()` [file:1].
- `canuserresolvenote()` [file:1].
- `rootnoteid()` [file:1].
- `utcnow()` [file:1].
- `validatenotecontext()` [file:1].

## 6.7 `app/services/noteretention.py`

**الدور:** soft deletion للـ notes [file:1].

**الدالة:**
- `softdeletenote()` [file:1].

## 6.8 `app/services/audit.py`

**الدور:** audit trail للأحداث الحساسة [file:1].

**الدالة المستخدمة بكثرة:**
- `logauditevent()` [file:1].

**العلاقات:**
- مستخدمة في auth, notes, export, transfers, score override workflows [file:1].

## 6.9 `app/services/export.py`

**الدور:** تجهيز datasets وstyled XLSX [file:1].

**الدوال المستخدمة من router:**
- `ExportService.builddataset()` [file:1].
- `ExportService.tostyledxlsx()` [file:1].

## 6.10 `app/services/transcription.py`

**الدور:** transcription engine abstraction فوق WhisperX/Pyannote [file:1].

**العلاقات الملحوظة:**
- يوفّر `transcriber.processaudio()` و`transcriber.releaseresources()` التي يستخدمها `worker.py` و`sessionflusher.py` [file:1].

## 6.11 `app/services/analysis.py`

**الدور:** transcript analysis وLLM evaluation business logic [file:1].

**الدوال/الثوابت المستهلكة:**
- `evaluatetranscript()` [file:1].
- `assignspeakers()` [file:1].
- `CAMPAIGNEXTRACTIONRULES` [file:1].

## 6.12 `app/services/acoustic.py`

**الدور:** acoustic/emotion analysis فوق الصوت [file:1].

**العلاقات:**
- `AcousticAnalyzer` يُستخدم داخل `worker.py` [file:1].

## 6.13 `app/services/agentarchive.py`

**الدور:** تخزين واسترجاع audio chunks الخاصة بالـ live agent stream داخل Redis [file:1].

**الدوال الظاهرة:**
- `readagentstream()` [file:1].
- `flushagentstream()` [file:1].

## 6.14 `app/services/websocket.py`

**الدور:** connection manager للـ WebSocket [file:1].

**العلاقات:**
- يستخدمه `websocketrouter.py` و`main.py` وsystem probes [file:1].

## 6.15 `app/services/gpurouter.py` و`kpicatalog.py`

وجودهما ضمن هيكل المشروع يشير إلى طبقة مساعدة لتوزيع الحمل على GPU وتعريف catalog للـ KPIs المستخدمة في الواجهة والـ notes، حتى لو لم تُعرض تفاصيل كل دالة هنا [file:1].

## 7) Worker Layer

## 7.1 `app/worker.py`

**الدور:** Celery worker الأساسي لمعالجة call audio بعد الرفع أو بعد flush live session [file:1].

**المكوّنات الرئيسية:**
- `celeryapp = Celery(...)` مع إعدادات تمنع إعادة استخدام الـ worker لعدة tasks (`workermaxtasksperchild=1`) وتقليل race conditions [file:1].
- `forcecudacleanup()` لتحرير ذاكرة GPU [file:1].
- `releaseworkermodelresources()` لتحرير transcriber/acoustic analyzer state [file:1].
- `filterhallucinatedsegments()` لوضع علامات على segments منخفضة الثقة أو حذف الواضح منها [file:1].
- `formattranscriptforllm()` لتجهيز transcript للنموذج اللغوي [file:1].
- المهمة الأساسية `processcallaudiotask` أو ما يعادلها، التي تنفّذ transcription ثم speaker assignment ثم acoustic analysis ثم feature engineering ثم LLM evaluation ثم persistence [file:1].

**العلاقات:**
- يعتمد على `services.transcription`, `services.analysis`, `services.acoustic`, `violations.py`, و`models.Call/CallOutcome/GoldenPairCandidate` [file:1].

## 7.2 `app/workers/asrworker.py`

**الدور:** live ASR session buffering + transcription loop + trigger لـ RAG suggestions [file:1].

**الوظائف الظاهرة:**
- حفظ segments داخل `LiveTranscriptSegment` [file:1].
- trigger إلى `getagentsuggestion()` عند وجود trigger text [file:1].
- `startheartbeatloop()` لمتابعة health الخاصة بالـ ASR worker [file:1].

**العلاقات:**
- يتكامل مع `routers/live.py`, `workers/ragworker.py`, `models.LiveTranscriptSegment`, و`main.py` [file:1].

## 7.3 `app/workers/ragworker.py`

**الدور:** retrieval-only RAG لإعطاء agent suggestions محلية سريعة [file:1].

**المكوّنات:**
- تهيئة `chromadb.PersistentClient` وcollection `agentsuggestions` [file:1].
- lazy loader `getmodel()` لنموذج `all-MiniLM-L6-v2` [file:1].
- `getcompanytriggerkeywords()` لتعريف الكلمات المفتاحية حسب الشركة/السياق [file:1].
- `getagentsuggestion()` التي تتحقق من trigger keyword، ثم cache Redis، ثم embedding، ثم query على ChromaDB مع filter إجباري `campaignid`، ثم confidence threshold [file:1].

**العلاقات:**
- يستهلكه `asrworker.py` أثناء الـ live pipeline [file:1].
- يستهلكه `review.py` عند approve candidate لتخزين golden pair في vector store [file:1].

## 7.4 `app/workers/sessionflusher.py`

**الدور:** إنهاء live session وتحويلها إلى `Call` قياسية قابلة للتقييم [file:1].

**الدوال:**
- `flushtranscriptionresources()` [file:1].
- `assembleagentwav()` لتجميع PCM chunks من Redis وبناء WAV [file:1].
- `flushlivesession()` لتغيير حالة الـ session إلى `FLUSHING`، ثم transcription لصوت agent، ثم دمج transcript مع customer live segments، ثم إنشاء `Call` جديدة، ثم تشغيل تقييم async [file:1].

**العلاقات:**
- يعتمد على `services.agentarchive`, `services.transcription`, `worker.evaluatelivecalltask`, و`models.LiveSession/Call/LiveTranscriptSegment` [file:1].

## 8) Domain Logic Modules

## 8.1 `app/violations.py`

**الدور:** registry ثابت للمخالفات + rules لتطبيق العقوبات [file:1].

**المكوّنات:**
- `VIOLATIONREGISTRY` ويحتوي 26 مخالفة تقريباً موزعة على high/medium/low [file:1].
- `SCOREDEDUCTIONS` لحساب الخصومات حسب severity وpenalty tier [file:1].
- `getoccurrence()` لحساب رقم التكرار للمخالفة على agent معين [file:1].
- `getpenalty()` لاختيار العقوبة المناسبة حسب occurrence [file:1].
- `applyviolations()` لحفظ المخالفات، جمع الخصومات، وتحديد `hrflag` و`autofail` وحساب `finalscore` [file:1].
- `buildviolationprompt()` لبناء الجزء الخاص بالمخالفات في prompt المرسل للـ LLM [file:1].

**العلاقات:**
- worker evaluation pipeline يعتمد عليه مباشرة بعد خروج raw violations من LLM [file:1].
- HR dashboards والتقارير تعتمد على الـ records الناتجة [file:1].

## 8.2 `app/permissions.py`

**الدور:** guards للأدوار مثل `requireopsreportingaccess`, `requireteamleaderaccess`, `requireteammanageraccess` [file:1].

**العلاقات:**
- تُستدعى داخل routers متعددة لضمان عزل scope الصحيح [file:1].

## 8.3 `app/recovery.py`

**الدور:** recovery للمهام العالقة عند startup عندما يكون `ENABLESTARTUPRECOVERY=True` [file:1].

## 9) Frontend Root

## 9.1 `src/main.tsx`

**الدور:** bootstrap لتطبيق React [file:1].

## 9.2 `src/App.tsx`

**الدور:** root app composition وربط routing/layout/context [file:1].

## 9.3 `src/routes.tsx`

**الدور:** تعريف مسارات الصفحات وربطها بالأدوار والصفحات المناسبة [file:1].

## 9.4 `src/context/AppContext.tsx`

**الدور:** global app state مثل `currentUser`, `userRole`, `sidebarCollapsed`, `piiMaskingEnabled` [file:1].

**العلاقات:**
- تستهلكه pages وcomponents وtests عبر `useApp()` [file:1].

## 9.5 `src/lib/api.ts`

**الدور:** طبقة استدعاء API من الواجهة [file:1].

**العلاقات الواضحة من الاختبارات:**
- تحتوي دوال مثل `getNotesInbox`, `getSentNotes`, `getNoteThread`, `markNoteRead`, `resolveNote`, `updateNoteStatus`, `archiveNote`, `deleteNote`, `createNote`, `replyToNote`, `getNoteRecipients` [file:1].

## 9.6 `src/lib/types.ts`, `roles.ts`, `kpiCatalog.ts`, `noteNavigation.ts`

**الأدوار:**
- `types.ts`: تعريف الـ TS types المشتركة [file:1].
- `roles.ts`: خرائط وصلاحيات الأدوار [file:1].
- `kpiCatalog.ts`: catalog للـ KPI labels/metadata [file:1].
- `noteNavigation.ts`: helpers مرتبطة بتنقلات note workflows [file:1].

## 10) Frontend Pages

الصفحات الأساسية الظاهرة في شجرة المشروع تمثّل الـ workspaces الرئيسية في النظام [file:1].

| Page | الدور | العلاقات الأساسية |
|---|---|---|
| `Login.tsx` | تسجيل الدخول | `api.ts`, `AppContext` [file:1] |
| `Dashboard.tsx` | لوحة معلومات عامة حسب الدور | hooks مثل `useDashboard`, `useCalls`, `useLeads`, `useMyPerformance` [file:1] |
| `CallExplorer.tsx` | استعراض المكالمات | `useCalls`, navigation إلى التفاصيل [file:1] |
| `CallDetail.tsx` | صفحة تفاصيل المكالمة | call analysis components [file:1] |
| `AgentProfile.tsx` | ملف agent وتاريخه | `useAgentDetails`, notes launchers [file:1] |
| `Campaigns.tsx` / `CampaignManager.tsx` | إدارة الحملات | campaigns hooks/API [file:1] |
| `BusinessIntelligence.tsx` | تقارير وتحليلات | analytics/ops data [file:1] |
| `HRDashboard.tsx` / `HRManagement.tsx` | HR workflows | violations/alarms/imports [file:1] |
| `SystemHealth.tsx` | مراقبة النظام | `useSystemHealth` [file:1] |
| `DataCenter.tsx` | data/export hub | export APIs [file:1] |
| `SuccessLibrary.tsx` | مكتبة أفضل الممارسات/Golden content | review/RAG related data [file:1] |
| `NotesInbox.tsx` | inbox/sent للـ notes | note APIs/components [file:1] |
| `NoteThread.tsx` | عرض thread والردود | note APIs/components [file:1] |
| `TeamLeaderDashboard.tsx`, `TeamLeaderAgents.tsx`, `TeamLeaderCalls.tsx`, `TeamLeaderKpis.tsx` | واجهات team leader | team leader endpoints [file:1] |

## 11) Frontend Components

## 11.1 Layout Components

### `components/layout/Layout.tsx`

**الدور:** shell الرئيسي للواجهة [file:1].

### `components/layout/Header.tsx`

**الدور:** top bar/navigation/state actions [file:1].

### `components/layout/Sidebar.tsx`

**الدور:** التنقل حسب الدور، وإظهار modules المتاحة بناءً على `RoleGuard` و`AppContext` [file:1].

## 11.2 Auth Components

### `components/auth/RoleGuard.tsx`

**الدور:** حماية أجزاء الواجهة أو الصفحات حسب role [file:1].

**العلاقات:**
- يعتمد على `AppContext` و`roles.ts` [file:1].

## 11.3 Call Analysis Components

هذه المجموعة تبني واجهة `CallDetail` والتحليل المرئي للمكالمة [file:1].

| Component | الوظيفة |
|---|---|
| `CallAnalysis.tsx` | container رئيسي لتحليل المكالمة [file:1] |
| `InteractiveTranscript.tsx` | عرض transcript تفاعلياً [file:1] |
| `EmotionalWaveform.tsx` | عرض تغيّر المشاعر/energy على الخط الزمني [file:1] |
| `OfferFunnel.tsx` | تمثيل funnel للعروض والبيع [file:1] |
| `PenaltiesTable.tsx` | عرض deductions والمخالفات رقمياً [file:1] |
| `SalesScoreBreakdown.tsx` | تفصيل score breakdown [file:1] |
| `TalkListenGauge.tsx` | gauge لنسبة الكلام/الاستماع [file:1] |
| `ViolationItem.tsx` | card/row لمخالفة واحدة [file:1] |
| `ViolationsPanel.tsx` | قائمة/لوحة المخالفات [file:1] |

## 11.4 Notes Components

هذه المجموعة تبني workflow notes في الواجهة [file:1].

| Component | الوظيفة | العلاقات |
|---|---|---|
| `KpiNoteCard.tsx` | عرض KPI note مع القيم الحالية والهدف | `kpiCatalog`, note data [file:1] |
| `NoteComposer.tsx` | إنشاء note أو reply | `api.ts`, `NoteRecipientPicker` [file:1] |
| `NoteContextCard.tsx` | عرض سياق note المرتبطة بـ team/campaign/agent/call | notes pages [file:1] |
| `NoteRecipientPicker.tsx` | تحميل recipient المناسب حسب note type/context | `getNoteRecipients` API [file:1] |

## 11.5 Campaign Components

### `components/campaigns/GuardrailModal.tsx`

**الدور:** واجهة policy/config guardrails للحملات [file:1].

## 11.6 Utility Components

### `components/figma/ImageWithFallback.tsx`

**الدور:** helper لعرض الصور مع fallback [file:1].

## 11.7 UI Primitives

مجلد `components/ui/` يحتوي design-system كبيراً من primitive components مثل `accordion`, `alert-dialog`, `button`, `card`, `chart`, `dialog`, `dropdown-menu`, `form`, `input`, `pagination`, `select`, `sheet`, `sidebar`, `table`, `tabs`, `textarea`, `toast/sonner`, وغيرها [file:1]. هذه الطبقة لا تمثل business logic بحد ذاتها، بل هي building blocks يُعاد استخدامها داخل pages والـ feature components [file:1].

## 12) Frontend Hooks

الـ hooks هي طبقة data fetching/state abstraction فوق `api.ts`، وغالباً مبنية على React Query [file:1].

| Hook | الوظيفة |
|---|---|
| `useAgentDetails.ts` | تحميل تفاصيل agent [file:1] |
| `useAgents.ts` | تحميل قائمة agents [file:1] |
| `useCalls.ts` | تحميل calls list أو subsets [file:1] |
| `useCallStatus.ts` | polling أو fetch لحالة call [file:1] |
| `useCampaigns.ts` | تحميل الحملات [file:1] |
| `useCommonErrors.ts` | تحميل common error analytics [file:1] |
| `useDashboard.ts` | dashboard aggregate data [file:1] |
| `useGoldenMoments.ts` | بيانات golden moments/success content [file:1] |
| `useLeads.ts` | leads overview [file:1] |
| `useMyPerformance.ts` | performance الشخصي للوكيل [file:1] |
| `useRanking.ts` | ranking بين الوكلاء [file:1] |
| `useSystemHealth.ts` | system metrics/alerts [file:1] |
| `useViolations.ts` | violation data للـ HR أو agent views [file:1] |

## 13) Frontend Tests as Architectural Evidence

الاختبارات الموجودة تكشف علاقات عملية بين المكونات حتى عندما لا يظهر الكود كاملاً [file:1].

### `kpiNotes.test.tsx`

يثبت أن `NotesInbox` و`KpiNoteCard` و`NoteRecipientPicker` تدعم KPI workflows مثل `Create KPI Follow-up`, `Request QA Review`, و`Coaching Note` حسب role والسياق [file:1].

### `launcherCoverage.test.tsx`

يثبت أن `Dashboard` و`AgentProfile` يطلقان إجراءات workflow مختلفة حسب الدور، مثل `Coaching Note` للـ team leader و`Escalate` للـ team manager [file:1].

### `notesFoundation.test.tsx`

يثبت الربط بين `Sidebar`, `RoleGuard`, `NotesInbox`, `NoteThread`, وطبقة API للـ notes [file:1].

## 14) End-to-End Relationship Map

## 14.1 Upload Call Flow

```text
Frontend Upload UI
  -> API /audio
  -> Call row (PENDING)
  -> Celery worker
  -> Transcription
  -> Analysis + Violations
  -> CallOutcome / Violations / GoldenPairCandidates
  -> Call status becomes EVALUATED
  -> Frontend CallDetail / Dashboard / HR / Ops consume results
```

هذا المسار يربط `audio.py` مع `worker.py` ثم `analysis.py` و`violations.py` وmodels مثل `Call`, `CallOutcome`, `AgentViolation`, ثم يعيد النتائج إلى صفحات مثل `CallDetail`, `Dashboard`, و`HRDashboard` [file:1].

## 14.2 Live Call Flow

```text
Frontend Live Session
  -> /api/live session start
  -> WebSocket audio stream
  -> asrworker buffers + transcript segments
  -> ragworker suggestion retrieval
  -> disconnect/reconnect handling
  -> sessionflusher assembles agent WAV + merges transcript
  -> Call row created with source=live
  -> standard evaluation pipeline runs
```

هذا المسار يربط `live.py` و`asrworker.py` و`ragworker.py` و`sessionflusher.py` مع `LiveSession`, `LiveTranscriptSegment`, ثم يعيد استخدام pipeline نفسها الخاصة بالـ uploaded calls [file:1].

## 14.3 Notes Workflow

```text
Frontend NotesInbox / NoteThread / NoteComposer
  -> notes API
  -> recipient + scope validation
  -> RoleNote persistence
  -> inbox/sent/thread queries
  -> status transitions / resolution / archive / delete
```

العلاقات هنا تمر عبر `routers/notes.py` و`services.noterecipients` و`services.notescope` و`services.noteretention`، وتنعكس في مكونات مثل `KpiNoteCard`, `NoteComposer`, و`NoteRecipientPicker` [file:1].

## 14.4 Team Management Workflow

```text
Team Manager UI
  -> team-manager API
  -> teammanagerreporting + teamscope
  -> Team / EmployeeTeamAssignment / AgentTransferRequest
  -> dashboards + transfer requests + KPI views
```

هذا workflow يربط `TeamManager` pages بالـ router والخدمات وبالـ models التنظيمية الخاصة بالفرق والنقل [file:1].

## 14.5 Operations Workflow

```text
Business Intelligence / Ops UI
  -> /api/ops
  -> opsreporting service
  -> Calls + Attendance + Violations + OperationalTargets
  -> dashboard / campaign rows / QA overview / alerts
```

المنطق هنا يعتمد على تجميعات SQL مباشرة وfallback targets وstatus computation لإخراج dashboard تنفيذي متعدد المؤشرات [file:1].

## 15) Dependency Hierarchy Summary

```text
Frontend Pages
├── useX hooks
│   └── lib/api.ts
│       └── FastAPI routers
│           ├── permissions + auth dependency
│           ├── services layer
│           │   ├── reporting / scope / export / notes logic
│           │   ├── transcription / analysis / acoustic logic
│           │   └── websocket / archive helpers
│           ├── models + schemas
│           └── workers (for async/life-cycle actions)
└── UI components / feature components

Workers
├── worker.py
│   ├── transcription.py
│   ├── analysis.py
│   ├── acoustic.py
│   ├── violations.py
│   └── models persistence
├── asrworker.py
│   └── ragworker.py
└── sessionflusher.py
    └── worker.py evaluation path
```

## 16) Practical Reading Order

للوصول إلى فهم معماري سريع وعميق، أفضل ترتيب قراءة للكود هو [file:1]:

1. `app/main.py` لفهم الـ composition العام [file:1].
2. `app/models.py` لفهم domain entities والعلاقات [file:1].
3. `app/routers/audio.py`, `live.py`, `notes.py`, `ops.py`, `teammanager.py`, `teamleader.py` لفهم الـ APIs [file:1].
4. `app/worker.py`, `workers/asrworker.py`, `workers/ragworker.py`, `workers/sessionflusher.py` لفهم الـ async/live pipelines [file:1].
5. `services/analysis.py`, `transcription.py`, `opsreporting.py`, `notescope.py`, `teamscope.py` لفهم business logic الحقيقي [file:1].
6. `src/pages/CallDetail.tsx`, `Dashboard.tsx`, `NotesInbox.tsx`, `AgentProfile.tsx`, `SystemHealth.tsx` لفهم استهلاك البيانات في الواجهة [file:1].
7. الاختبارات، لأنها تكشف الـ use-cases الفعلية والعلاقات بين المكونات بوضوح [file:1].

## 17) Final Architectural View

هذا المشروع ليس مجرد call scoring app؛ بل هو منصة تشغيل متكاملة فيها call ingestion، AI evaluation، live monitoring، RAG coaching، violations/HR workflows، operations dashboards، internal notes، وإدارة فرق متعددة المستويات [file:1]. طبقة الـ backend مصممة على شكل routers + services + workers + models، بينما الـ frontend مبني على pages + hooks + feature components + UI primitives، والعلاقة بينهما واضحة ومنظمة حول domain entities مثل `Call`, `Employee`, `Campaign`, `RoleNote`, `Team`, و`AgentViolation` [file:1].
