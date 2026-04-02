"""Korean locale — 한국어 메시지 정의."""

MESSAGES: dict[str, str] = {
    # ── 유효성 검사 ───────────────────────────────────────────────────
    "validation.invalid_name": (
        "잘못된 프로젝트 이름입니다. 영문자, 숫자, 하이픈, 밑줄만 사용할 수 있습니다."
    ),
    "validation.reserved_name": "'{name}'은(는) 예약된 이름입니다.",
    "validation.name_too_long": (
        "프로젝트 이름이 너무 깁니다. 최대 50자까지 허용됩니다."
    ),
    "validation.invalid_python": (
        "잘못된 Python 버전 '{version}'입니다. 다음 중 하나여야 합니다: {supported}"
    ),
    "validation.unknown_service": "알 수 없는 서비스: {name}",
    "validation.unknown_services": "알 수 없는 서비스: {names}",
    "validation.unknown_component": "알 수 없는 컴포넌트: {name}",
    # ── init 명령 ─────────────────────────────────────────────────────
    "init.title": "Aegis Stack 프로젝트 초기화",
    "init.location": "경로:",
    "init.template_version": "템플릿 버전:",
    "init.dir_exists": "디렉토리 '{path}'이(가) 이미 존재함",
    "init.dir_exists_hint": "--force로 덮어쓰거나 다른 이름을 사용하세요",
    "init.overwriting": "기존 디렉토리 덮어쓰는 중: {path}",
    "init.services_require": "서비스에 필요한 컴포넌트: {components}",
    "init.compat_errors": "서비스-컴포넌트 호환성 오류:",
    "init.suggestion_add": (
        "제안: 누락된 컴포넌트를 추가하세요 --components {components}"
    ),
    "init.suggestion_remove": (
        "또는 --components를 생략하면 서비스가 필요한 의존성을 자동으로 추가합니다."
    ),
    "init.suggestion_interactive": (
        "대화형 모드를 사용하면 서비스 의존성이 자동으로 처리됩니다."
    ),
    "init.auto_detected_scheduler": (
        "자동 감지: 스케줄러가 {backend} 영속화를 사용합니다"
    ),
    "init.auto_added_deps": "자동 추가된 의존성: {deps}",
    "init.auto_added_by_services": "서비스에 의해 자동 추가됨:",
    "init.required_by": "{services}에서 필요",
    "init.config_title": "프로젝트 설정",
    "init.config_name": "이름:",
    "init.config_core": "핵심:",
    "init.config_infra": "인프라:",
    "init.config_services": "서비스:",
    "init.component_files": "컴포넌트 파일:",
    "init.entrypoints": "진입점:",
    "init.worker_queues": "워커 큐:",
    "init.dependencies": "설치할 의존성:",
    "init.confirm_create": "이 프로젝트를 생성하시겠습니까?",
    "init.cancelled": "프로젝트 생성이 취소되었습니다",
    "init.removing_dir": "기존 디렉토리 삭제 중: {path}",
    "init.creating": "프로젝트 생성 중: {name}",
    "init.error": "프로젝트 생성 오류: {error}",
    # ── 대화형: 섹션 헤더 ─────────────────────────────────────────────
    "interactive.component_selection": "컴포넌트 선택",
    "interactive.service_selection": "서비스 선택",
    "interactive.core_included": ("핵심 컴포넌트({components})는 자동으로 포함됩니다"),
    "interactive.infra_header": "인프라 컴포넌트:",
    "interactive.services_intro": (
        "서비스는 애플리케이션에 비즈니스 로직 기능을 제공합니다."
    ),
    # ── 컴포넌트 설명 ──────────────────────────────────────────────────
    "component.backend": "FastAPI 백엔드 서버",
    "component.frontend": "Flet 프론트엔드 인터페이스",
    "component.redis": "Redis 캐시 및 메시지 브로커",
    "component.worker": "백그라운드 작업 처리 (arq, Dramatiq 또는 TaskIQ)",
    "component.scheduler": "예약 작업 실행 인프라",
    "component.database": "SQLModel ORM 기반 데이터베이스 (SQLite 또는 PostgreSQL)",
    "component.ingress": "Traefik 리버스 프록시 및 로드 밸런서",
    "component.observability": "Logfire 관측성, 추적 및 메트릭",
    # ── 서비스 설명 ────────────────────────────────────────────────────
    "service.auth": "JWT 토큰 기반 사용자 인증 및 권한 관리",
    "service.ai": "멀티 프레임워크 지원 AI 챗봇 서비스",
    "service.comms": "이메일, SMS, 음성 통신 서비스",
    # ── 대화형: 컴포넌트 프롬프트 ─────────────────────────────────────
    "interactive.add_prompt": "{description}을(를) 추가하시겠습니까?",
    "interactive.add_with_redis": "{description}을(를) 추가하시겠습니까? (Redis 자동 추가)",
    "interactive.worker_configured": "워커가 {backend} 백엔드로 구성 완료",
    # ── 대화형: 스케줄러 ──────────────────────────────────────────────
    "interactive.scheduler_persistence": "스케줄러 영속화:",
    "interactive.persist_prompt": (
        "예약 작업을 영속화하시겠습니까? (작업 이력 저장, 재시작 후 복구 지원)"
    ),
    "interactive.scheduler_db_configured": "스케줄러 + {engine} 데이터베이스 구성 완료",
    "interactive.bonus_backup": "보너스: 데이터베이스 백업 작업 추가",
    "interactive.backup_desc": (
        "일일 데이터베이스 백업 작업이 포함됩니다 (매일 오전 2시 실행)"
    ),
    # ── 대화형: 데이터베이스 엔진 ─────────────────────────────────────
    "interactive.db_engine_label": "{context} 데이터베이스 엔진:",
    "interactive.db_select": "데이터베이스 엔진을 선택하세요:",
    "interactive.db_sqlite": "SQLite - 간단한 파일 기반 (개발용으로 적합)",
    "interactive.db_postgres": ("PostgreSQL - 프로덕션급, 멀티 컨테이너 지원"),
    "interactive.db_reuse": "이전에 선택한 데이터베이스 사용: {engine}",
    # ── 대화형: 워커 백엔드 ───────────────────────────────────────────
    "interactive.worker_label": "워커 백엔드:",
    "interactive.worker_select": "워커 백엔드를 선택하세요:",
    "interactive.worker_arq": "arq - 비동기, 경량 (기본값)",
    "interactive.worker_dramatiq": ("Dramatiq - 프로세스 기반, CPU 집약적 작업에 적합"),
    "interactive.worker_taskiq": (
        "TaskIQ - 비동기, 프레임워크 스타일, 큐별 브로커 지원"
    ),
    # ── 대화형: 인증 ──────────────────────────────────────────────────
    "interactive.auth_header": "인증 서비스:",
    "interactive.auth_level_label": "인증 수준:",
    "interactive.auth_select": "어떤 유형의 인증을 사용하시겠습니까?",
    "interactive.auth_basic": "기본 - 이메일/비밀번호 로그인",
    "interactive.auth_rbac": "역할 기반 - + 역할 기반 접근 제어 (실험적)",
    "interactive.auth_org": "조직 기반 - + 멀티 테넌트 지원 (실험적)",
    "interactive.auth_selected": "선택된 인증 수준: {level}",
    "interactive.auth_db_required": "데이터베이스 필요:",
    "interactive.auth_db_reason": (
        "인증 기능은 사용자 정보 저장을 위해 데이터베이스가 필요합니다"
    ),
    "interactive.auth_db_details": "(사용자 계정, 세션, JWT 토큰)",
    "interactive.auth_db_already": "데이터베이스 컴포넌트가 이미 선택됨",
    "interactive.auth_db_confirm": "계속 진행하고 데이터베이스 컴포넌트를 추가하시겠습니까?",
    "interactive.auth_cancelled": "인증 서비스가 취소되었습니다",
    "interactive.auth_db_configured": "인증 + 데이터베이스 구성 완료",
    # ── 대화형: AI 서비스 ─────────────────────────────────────────────
    "interactive.ai_header": "AI 및 머신러닝 서비스:",
    "interactive.ai_framework_label": "AI 프레임워크 선택:",
    "interactive.ai_framework_intro": "AI 프레임워크를 선택하세요:",
    "interactive.ai_pydanticai": (
        "PydanticAI - 타입 안전, Pythonic AI 프레임워크 (권장)"
    ),
    "interactive.ai_langchain": (
        "LangChain - 광범위한 통합을 지원하는 인기 프레임워크"
    ),
    "interactive.ai_use_pydanticai": "PydanticAI를 사용하시겠습니까? (권장)",
    "interactive.ai_selected_framework": "선택된 프레임워크: {framework}",
    "interactive.ai_tracking_context": "AI 사용량 추적",
    "interactive.ai_tracking_label": "LLM 사용량 추적:",
    "interactive.ai_tracking_prompt": (
        "사용량 추적을 활성화하시겠습니까? (토큰 수, 비용, 대화 이력)"
    ),
    "interactive.ai_sync_label": "LLM 카탈로그 동기화:",
    "interactive.ai_sync_desc": (
        "동기화는 OpenRouter/LiteLLM API에서 최신 모델 데이터를 가져옵니다"
    ),
    "interactive.ai_sync_time": ("네트워크 접속이 필요하며 약 30~60초 소요됩니다"),
    "interactive.ai_sync_prompt": "프로젝트 생성 시 LLM 카탈로그를 동기화하시겠습니까?",
    "interactive.ai_sync_will": "프로젝트 생성 후 LLM 카탈로그가 동기화됩니다",
    "interactive.ai_sync_skipped": (
        "LLM 동기화를 건너뛰었습니다 - 정적 픽스처 데이터를 사용합니다"
    ),
    "interactive.ai_provider_label": "AI 프로바이더 선택:",
    "interactive.ai_provider_intro": (
        "포함할 AI 프로바이더를 선택하세요 (복수 선택 가능)"
    ),
    "interactive.ai_provider_options": "프로바이더 옵션:",
    "interactive.ai_provider_recommended": "(권장)",
    "interactive.ai_provider.openai": "OpenAI - GPT 모델 (유료)",
    "interactive.ai_provider.anthropic": "Anthropic - Claude 모델 (유료)",
    "interactive.ai_provider.google": "Google - Gemini 모델 (무료 티어)",
    "interactive.ai_provider.groq": "Groq - 고속 추론 (무료 티어)",
    "interactive.ai_provider.mistral": "Mistral - 오픈 모델 (대부분 유료)",
    "interactive.ai_provider.cohere": "Cohere - 엔터프라이즈 특화 (제한적 무료)",
    "interactive.ai_provider.ollama": "Ollama - 로컬 추론 (무료)",
    "interactive.ai_no_providers": (
        "선택된 프로바이더가 없어 권장 기본값을 추가합니다..."
    ),
    "interactive.ai_selected_providers": "선택된 프로바이더: {providers}",
    "interactive.ai_deps_optimized": ("선택한 항목에 맞게 의존성이 최적화됩니다"),
    "interactive.ai_ollama_label": "Ollama 배포 모드:",
    "interactive.ai_ollama_intro": "Ollama를 어떻게 실행하시겠습니까?",
    "interactive.ai_ollama_host": (
        "호스트 - 로컬 머신에서 실행 중인 Ollama에 연결 (Mac/Windows)"
    ),
    "interactive.ai_ollama_docker": (
        "Docker - Docker 컨테이너에서 Ollama 실행 (Linux/배포)"
    ),
    "interactive.ai_ollama_host_prompt": (
        "호스트 Ollama에 연결하시겠습니까? (Mac/Windows 권장)"
    ),
    "interactive.ai_ollama_host_ok": (
        "Ollama가 host.docker.internal:11434에 연결됩니다"
    ),
    "interactive.ai_ollama_host_hint": "Ollama가 실행 중인지 확인하세요: ollama serve",
    "interactive.ai_ollama_docker_ok": (
        "Ollama 서비스가 docker-compose.yml에 추가됩니다"
    ),
    "interactive.ai_ollama_docker_hint": (
        "참고: 첫 실행 시 모델 다운로드에 시간이 걸릴 수 있습니다"
    ),
    "interactive.ai_rag_label": "RAG (검색 증강 생성):",
    "interactive.ai_rag_warning": (
        "경고: RAG는 Python <3.14가 필요합니다 (chromadb/onnxruntime 제한)"
    ),
    "interactive.ai_rag_compat_note": (
        "RAG를 활성화하면 Python 3.11-3.13이 필요한 프로젝트가 생성됩니다"
    ),
    "interactive.ai_rag_compat_prompt": (
        "Python 3.14 비호환에도 불구하고 RAG를 활성화하시겠습니까?"
    ),
    "interactive.ai_rag_prompt": (
        "문서 인덱싱 및 시맨틱 검색을 위해 RAG를 활성화하시겠습니까?"
    ),
    "interactive.ai_rag_enabled": "RAG가 ChromaDB 벡터 스토어와 함께 활성화되었습니다",
    "interactive.ai_voice_label": "음성 (텍스트 음성 변환 및 음성 텍스트 변환):",
    "interactive.ai_voice_prompt": (
        "음성 기능을 활성화하시겠습니까? (음성 상호작용을 위한 TTS 및 STT)"
    ),
    "interactive.ai_voice_enabled": "음성 기능이 TTS 및 STT 지원과 함께 활성화되었습니다",
    "interactive.ai_db_already": "데이터베이스가 이미 선택됨 - 사용량 추적 활성화됨",
    "interactive.ai_db_added": "사용량 추적을 위해 데이터베이스({backend}) 추가됨",
    "interactive.ai_configured": "AI 서비스가 구성 완료",
    # ── 공용: 유효성 검사 ──────────────────────────────────────────────
    "shared.not_copier_project": "{path}의 프로젝트는 Copier로 생성되지 않았습니다.",
    "shared.copier_only": (
        "'aegis {command}' 명령은 Copier로 생성된 프로젝트에서만 사용할 수 있습니다."
    ),
    "shared.regenerate_hint": (
        "컴포넌트를 추가하려면 새 컴포넌트를 포함하여 프로젝트를 재생성하세요."
    ),
    "shared.git_not_initialized": "프로젝트가 git 저장소 안에 있지 않습니다",
    "shared.git_required": "Copier 업데이트는 변경 사항 추적을 위해 git이 필요합니다",
    "shared.git_init_hint": (
        "'aegis init'으로 생성된 프로젝트는 git이 자동으로 초기화되어야 합니다"
    ),
    "shared.git_manual_init": (
        "수동으로 생성한 프로젝트의 경우 다음을 실행하세요: "
        "git init && git add . && git commit -m 'Initial commit'"
    ),
    "shared.empty_component": "빈 컴포넌트 이름은 허용되지 않습니다",
    "shared.empty_service": "빈 서비스 이름은 허용되지 않습니다",
    # ── 공용: 다음 단계 / 검토 ────────────────────────────────────────
    "shared.next_steps": "다음 단계:",
    "shared.next_make_check": "   1. 'make check'를 실행하여 업데이트를 검증하세요",
    "shared.next_test": "   2. 애플리케이션을 테스트하세요",
    "shared.next_commit": "   3. 변경 사항을 커밋하세요: git add . && git commit",
    "shared.review_header": "변경 사항 확인:",
    "shared.review_docker": "   git diff docker-compose.yml",
    "shared.review_pyproject": "   git diff pyproject.toml",
    "shared.operation_cancelled": "작업이 취소되었습니다",
    "shared.interactive_ignores_args": (
        "경고: --interactive 플래그를 사용하면 컴포넌트 인수가 무시됩니다"
    ),
    "shared.no_components_selected": "선택된 컴포넌트가 없습니다",
    "shared.no_services_selected": "선택된 서비스가 없습니다",
    # ── add 명령 ──────────────────────────────────────────────────────
    "add.title": "Aegis Stack - 컴포넌트 추가",
    "add.project": "프로젝트: {path}",
    "add.error_no_args": (
        "오류: components 인수가 필요합니다 (또는 --interactive 사용)"
    ),
    "add.usage_hint": "사용법: aegis add scheduler,worker",
    "add.interactive_hint": "또는: aegis add --interactive",
    "add.auto_added_deps": "자동 추가된 의존성: {deps}",
    "add.validation_failed": "컴포넌트 유효성 검사 실패: {error}",
    "add.load_config_failed": "프로젝트 설정 로드 실패: {error}",
    "add.already_enabled": "이미 활성화됨: {components}",
    "add.all_enabled": "요청한 모든 컴포넌트가 이미 활성화됨!",
    "add.components_to_add": "추가할 컴포넌트:",
    "add.scheduler_backend": "스케줄러 백엔드: {backend}",
    "add.confirm": "이 컴포넌트를 추가하시겠습니까?",
    "add.updating": "프로젝트 업데이트 중...",
    "add.adding": "{component} 추가 중...",
    "add.added_files": "{count}개 파일 추가됨",
    "add.skipped_files": "{count}개 기존 파일 건너뜀",
    "add.success": "컴포넌트가 추가 완료!",
    "add.failed_component": "{component} 추가 실패: {error}",
    "add.failed": "컴포넌트 추가 실패: {error}",
    "add.invalid_format": "잘못된 컴포넌트 형식: {error}",
    "add.bracket_override": (
        "대괄호 구문 'scheduler[{engine}]'이(가) --backend {backend}을(를) 덮어씁니다"
    ),
    "add.invalid_scheduler_backend": "잘못된 스케줄러 백엔드: '{backend}'",
    "add.valid_backends": "사용 가능한 옵션: {options}",
    "add.postgres_coming": "참고: PostgreSQL 지원은 향후 릴리스에서 제공 예정",
    "add.auto_added_db": "스케줄러 영속화를 위해 데이터베이스 컴포넌트가 자동 추가됨",
    # ── remove 명령 ───────────────────────────────────────────────────
    "remove.title": "Aegis Stack - 컴포넌트 제거",
    "remove.project": "프로젝트: {path}",
    "remove.error_no_args": (
        "오류: components 인수가 필요합니다 (또는 --interactive 사용)"
    ),
    "remove.usage_hint": "사용법: aegis remove scheduler,worker",
    "remove.interactive_hint": "또는: aegis remove --interactive",
    "remove.no_selected": "제거할 컴포넌트가 선택되지 않았습니다",
    "remove.validation_failed": "컴포넌트 유효성 검사 실패: {error}",
    "remove.load_config_failed": "프로젝트 설정 로드 실패: {error}",
    "remove.cannot_remove_core": "핵심 컴포넌트는 제거할 수 없습니다: {component}",
    "remove.not_enabled": "활성화되지 않음: {components}",
    "remove.nothing_to_remove": "제거할 컴포넌트가 없습니다!",
    "remove.auto_remove_redis": (
        "Redis를 자동 제거합니다 (독립 기능 없음, 워커에서만 사용)"
    ),
    "remove.scheduler_persistence_warn": "중요: 스케줄러 영속화 경고",
    "remove.scheduler_persistence_detail": (
        "스케줄러가 작업 영속화에 SQLite를 사용하고 있습니다."
    ),
    "remove.scheduler_db_remains": (
        "data/scheduler.db의 데이터베이스 파일은 유지됩니다."
    ),
    "remove.scheduler_keep_hint": (
        "작업 이력을 유지하려면 데이터베이스 컴포넌트를 남겨두세요"
    ),
    "remove.scheduler_remove_hint": (
        "모든 데이터를 삭제하려면 데이터베이스 컴포넌트도 제거하세요"
    ),
    "remove.components_to_remove": "제거할 컴포넌트:",
    "remove.warning_delete": ("경고: 프로젝트에서 컴포넌트 파일이 삭제됩니다!"),
    "remove.commit_hint": "git에 변경 사항을 커밋했는지 확인하세요.",
    "remove.confirm": "이 컴포넌트를 제거하시겠습니까?",
    "remove.removing_all": "컴포넌트 제거 중...",
    "remove.removing": "{component} 제거 중...",
    "remove.removed_files": "{count}개 파일 제거됨",
    "remove.failed_component": "{component} 제거 실패: {error}",
    "remove.success": "컴포넌트가 제거 완료!",
    "remove.failed": "컴포넌트 제거 실패: {error}",
    # ── 수동 업데이터 ─────────────────────────────────────────────────
    "updater.processing_files": "컴포넌트 파일 {count}개 처리 중...",
    "updater.updating_shared": "공유 템플릿 파일 업데이트 중...",
    "updater.running_postgen": "후처리 작업 실행 중...",
    "updater.deps_synced": "의존성 동기화 완료 (uv sync)",
    "updater.code_formatted": "코드 포맷팅 완료 (make fix)",
    # ── 프로젝트 맵 ──────────────────────────────────────────────────
    "projectmap.new": "신규",
    # ── 후처리: 설정 작업 ─────────────────────────────────────────────
    "postgen.setup_start": "프로젝트 환경을 설정하는 중...",
    "postgen.deps_installing": "uv로 의존성을 설치하는 중...",
    "postgen.deps_success": "의존성이 설치 완료",
    "postgen.deps_failed": "프로젝트 생성 실패: 의존성 설치 실패",
    "postgen.deps_failed_detail": (
        "생성된 프로젝트 파일은 남아있지만 프로젝트를 사용할 수 없습니다."
    ),
    "postgen.deps_failed_hint": (
        "의존성 문제를 해결하고 (Python 버전 호환성 확인) 다시 시도하세요."
    ),
    "postgen.deps_warn_failed": "경고: 의존성 설치 실패",
    "postgen.deps_manual": "프로젝트 생성 후 'uv sync'를 수동으로 실행하세요",
    "postgen.deps_timeout": (
        "경고: 의존성 설치 시간 초과 - 'uv sync'를 수동으로 실행하세요"
    ),
    "postgen.deps_uv_missing": "경고: PATH에서 uv를 찾을 수 없습니다",
    "postgen.deps_uv_install": "먼저 uv를 설치하세요: https://github.com/astral-sh/uv",
    "postgen.deps_warn_error": "경고: 의존성 설치 실패: {error}",
    "postgen.env_setup": "환경 설정을 구성하는 중...",
    "postgen.env_created": ".env.example로부터 환경 파일이 생성되었습니다",
    "postgen.env_exists": "환경 파일이 이미 존재함",
    "postgen.env_missing": "경고: .env.example 파일을 찾을 수 없습니다",
    "postgen.env_error": "경고: 환경 설정 실패: {error}",
    "postgen.env_manual": ".env.example을 .env로 수동 복사하세요",
    # ── 후처리: 데이터베이스/마이그레이션 ──────────────────────────────
    "postgen.db_setup": "데이터베이스 스키마를 설정하는 중...",
    "postgen.db_success": "데이터베이스 테이블이 생성 완료",
    "postgen.db_alembic_missing": "경고: {path}에서 Alembic 설정 파일을 찾을 수 없습니다",
    "postgen.db_alembic_hint": (
        "데이터베이스 마이그레이션을 건너뜁니다. 설정 파일이 존재하는지 확인하고 "
        "'alembic upgrade head'를 수동으로 실행하세요."
    ),
    "postgen.db_failed": "경고: 데이터베이스 마이그레이션 설정 실패",
    "postgen.db_manual": "프로젝트 생성 후 'alembic upgrade head'를 수동으로 실행하세요",
    "postgen.db_timeout": (
        "경고: 마이그레이션 설정 시간 초과 - 'alembic upgrade head'를 수동으로 실행하세요"
    ),
    "postgen.db_error": "경고: 마이그레이션 설정 실패: {error}",
    # ── 후처리: LLM 픽스처/동기화 ─────────────────────────────────────
    "postgen.llm_seeding": "LLM 픽스처를 시딩하는 중...",
    "postgen.llm_seed_success": "LLM 픽스처가 시딩 완료",
    "postgen.llm_seed_failed": "경고: LLM 픽스처 시딩 실패",
    "postgen.llm_seed_manual": (
        "픽스처 로더를 실행하여 수동으로 픽스처를 시딩할 수 있습니다"
    ),
    "postgen.llm_seed_timeout": "경고: LLM 픽스처 시딩 시간 초과",
    "postgen.llm_seed_error": "경고: LLM 픽스처 시딩 실패: {error}",
    "postgen.llm_syncing": "외부 API에서 LLM 카탈로그를 동기화하는 중...",
    "postgen.llm_sync_success": "LLM 카탈로그가 동기화 완료",
    "postgen.llm_sync_failed": "경고: LLM 카탈로그 동기화 실패",
    "postgen.llm_sync_manual": (
        "카탈로그를 채우려면 '{slug} llm sync'를 수동으로 실행하세요"
    ),
    "postgen.llm_sync_timeout": "경고: LLM 카탈로그 동기화 시간 초과",
    "postgen.llm_sync_error": "경고: LLM 카탈로그 동기화 실패: {error}",
    # ── 후처리: 포맷팅 ────────────────────────────────────────────────
    "postgen.format_timeout": (
        "경고: 포맷팅 시간 초과 - 준비되면 'make fix'를 수동으로 실행하세요"
    ),
    "postgen.format_error": "경고: 자동 포맷팅 건너뜀: {error}",
    "postgen.format_error_manual": "코드를 포맷팅하려면 'make fix'를 수동으로 실행하세요",
    "postgen.format_start": "생성된 코드를 자동 포맷팅하는 중...",
    "postgen.format_success": "코드 포맷팅이 성공적으로 완료되었습니다",
    "postgen.format_partial": ("일부 포맷팅 문제가 감지되었지만 프로젝트는 생성 완료"),
    "postgen.format_manual": "남은 문제를 해결하려면 'make fix'를 수동으로 실행하세요",
    "postgen.format_hint": "준비되면 'make fix'를 실행하여 코드를 포맷팅하세요",
    "postgen.llm_sync_skipped": "LLM 카탈로그 동기화를 건너뛰었습니다",
    "postgen.llm_fixtures_outdated": "정적 픽스처 데이터가 로드되었습니다 (오래되었을 수 있음)",
    "postgen.llm_sync_hint": "최신 모델 데이터를 가져오려면 나중에 '{slug} llm sync'를 실행하세요",
    "postgen.llm_fixtures_fallback": (
        "정적 픽스처 데이터를 사용할 수 있지만 오래되었을 수 있습니다"
    ),
    "postgen.ready": "프로젝트가 실행 준비되었습니다!",
    "postgen.next_steps": "다음 단계:",
    "postgen.next_cd": "   cd {path}",
    "postgen.next_serve": "   make serve",
    "postgen.next_dashboard": "   Overseer 열기: http://localhost:8000/dashboard/",
    # ── 후처리: 프로젝트 맵 ───────────────────────────────────────────
    "projectmap.title": "프로젝트 구조:",
    "projectmap.components": "컴포넌트",
    "projectmap.services": "비즈니스 로직",
    "projectmap.models": "데이터베이스 모델",
    "projectmap.cli": "CLI 명령",
    "projectmap.entrypoints": "실행 대상",
    "projectmap.tests": "테스트 스위트",
    "projectmap.migrations": "마이그레이션",
    "projectmap.auth": "인증",
    "projectmap.ai": "AI 대화",
    "projectmap.comms": "통신",
    "projectmap.docs": "문서",
    # ── 후처리: 푸터 ──────────────────────────────────────────────────
    "postgen.docs_link": "문서: https://lbedner.github.io/aegis-stack",
    "postgen.star_prompt": ("Aegis Stack이 도움이 되셨다면 별표를 남겨주세요:"),
    # ── add-service 명령 ──────────────────────────────────────────────
    "add_service.title": "Aegis Stack - 서비스 추가",
    "add_service.project": "프로젝트: {path}",
    "add_service.error_no_args": (
        "오류: services 인수가 필요합니다 (또는 --interactive 사용)"
    ),
    "add_service.usage_hint": "사용법: aegis add-service auth,ai",
    "add_service.interactive_hint": "또는: aegis add-service --interactive",
    "add_service.interactive_ignores_args": (
        "경고: --interactive 플래그를 사용하면 서비스 인수가 무시됩니다"
    ),
    "add_service.no_selected": "선택된 서비스가 없습니다",
    "add_service.already_enabled": "이미 활성화됨: {services}",
    "add_service.all_enabled": "요청한 모든 서비스가 이미 활성화됨!",
    "add_service.validation_failed": "서비스 유효성 검사 실패: {error}",
    "add_service.load_config_failed": "프로젝트 설정 로드 실패: {error}",
    "add_service.services_to_add": "추가할 서비스:",
    "add_service.required_components": "필수 컴포넌트 (자동 추가됨):",
    "add_service.already_have_components": ("이미 포함된 필수 컴포넌트: {components}"),
    "add_service.confirm": "이 서비스를 추가하시겠습니까?",
    "add_service.adding_component": "필수 컴포넌트 추가 중: {component}...",
    "add_service.failed_component": "컴포넌트 {component} 추가 실패: {error}",
    "add_service.added_files": "{count}개 파일 추가됨",
    "add_service.skipped_files": "{count}개 기존 파일 건너뜀",
    "add_service.adding_service": "서비스 추가 중: {service}...",
    "add_service.failed_service": "서비스 {service} 추가 실패: {error}",
    "add_service.resolve_failed": "서비스 의존성 해결 실패: {error}",
    "add_service.bootstrap_alembic": "Alembic 인프라를 부트스트랩하는 중...",
    "add_service.created_file": "생성됨: {file}",
    "add_service.generated_migration": "마이그레이션 생성됨: {name}",
    "add_service.applying_migrations": "데이터베이스 마이그레이션 적용 중...",
    "add_service.migration_failed": (
        "경고: 자동 마이그레이션 실패. 'make migrate'를 수동으로 실행하세요."
    ),
    "add_service.success": "서비스가 추가 완료!",
    "add_service.failed": "서비스 추가 실패: {error}",
    "add_service.auth_setup": "인증 서비스 설정:",
    "add_service.auth_create_users": "   1. 테스트 사용자 생성: {cmd}",
    "add_service.auth_view_routes": "   2. 인증 라우트 확인: {url}",
    "add_service.ai_setup": "AI 서비스 설정:",
    "add_service.ai_set_provider": (
        "   1. .env에 {env_var} 설정 (openai, anthropic, google, groq)"
    ),
    "add_service.ai_set_api_key": "   2. 프로바이더 API 키 설정 ({env_var} 등)",
    "add_service.ai_test_cli": "   3. CLI로 테스트: {cmd}",
    # ── remove-service 명령 ───────────────────────────────────────────
    "remove_service.title": "Aegis Stack - 서비스 제거",
    "remove_service.project": "프로젝트: {path}",
    "remove_service.error_no_args": (
        "오류: services 인수가 필요합니다 (또는 --interactive 사용)"
    ),
    "remove_service.usage_hint": "사용법: aegis remove-service auth,ai",
    "remove_service.interactive_hint": "또는: aegis remove-service --interactive",
    "remove_service.interactive_ignores_args": (
        "경고: --interactive 플래그를 사용하면 서비스 인수가 무시됩니다"
    ),
    "remove_service.no_selected": "제거할 서비스가 선택되지 않았습니다",
    "remove_service.not_enabled": "활성화되지 않음: {services}",
    "remove_service.nothing_to_remove": "제거할 서비스가 없습니다!",
    "remove_service.validation_failed": "서비스 유효성 검사 실패: {error}",
    "remove_service.load_config_failed": ("프로젝트 설정 로드 실패: {error}"),
    "remove_service.services_to_remove": "제거할 서비스:",
    "remove_service.auth_warning": "중요: 인증 서비스 경고",
    "remove_service.auth_delete_intro": "인증 서비스를 제거하면 다음이 삭제됩니다:",
    "remove_service.auth_delete_endpoints": "사용자 인증 API 엔드포인트",
    "remove_service.auth_delete_models": "사용자 모델 및 인증 서비스",
    "remove_service.auth_delete_jwt": "JWT 토큰 처리 코드",
    "remove_service.auth_db_note": (
        "참고: 데이터베이스 테이블과 Alembic 마이그레이션은 삭제되지 않습니다."
    ),
    "remove_service.warning_delete": ("경고: 프로젝트에서 서비스 파일이 삭제됩니다!"),
    "remove_service.confirm": "이 서비스를 제거하시겠습니까?",
    "remove_service.removing": "서비스 제거 중: {service}...",
    "remove_service.failed_service": "서비스 {service} 제거 실패: {error}",
    "remove_service.removed_files": "{count}개 파일 제거됨",
    "remove_service.success": "서비스가 제거 완료!",
    "remove_service.failed": "서비스 제거 실패: {error}",
    "remove_service.deps_not_removed": (
        "참고: 서비스 의존성(데이터베이스 등)은 제거되지 않았습니다."
    ),
    "remove_service.deps_remove_hint": (
        "컴포넌트를 별도로 제거하려면 'aegis remove <component>'를 사용하세요."
    ),
    # ── version 명령 ──────────────────────────────────────────────────
    "version.info": "Aegis Stack CLI v{version}",
    # ── components 명령 ───────────────────────────────────────────────
    "components.core_title": "핵심 컴포넌트",
    "components.backend_desc": ("  backend      - FastAPI 백엔드 서버 (항상 포함)"),
    "components.frontend_desc": (
        "  frontend     - Flet 프론트엔드 인터페이스 (항상 포함)"
    ),
    "components.infra_title": "인프라 컴포넌트",
    "components.requires": "필수: {deps}",
    "components.recommends": "권장: {deps}",
    "components.usage_hint": (
        "컴포넌트를 선택하려면 'aegis init PROJECT_NAME --components redis,worker'를 사용하세요"
    ),
    # ── services 명령 ─────────────────────────────────────────────────
    "services.title": "사용 가능한 서비스",
    "services.type_auth": "인증 서비스",
    "services.type_payment": "결제 서비스",
    "services.type_ai": "AI 및 머신러닝 서비스",
    "services.type_notification": "알림 서비스",
    "services.type_analytics": "분석 서비스",
    "services.type_storage": "스토리지 서비스",
    "services.requires_components": "필수 컴포넌트: {deps}",
    "services.recommends_components": "권장 컴포넌트: {deps}",
    "services.requires_services": "필수 서비스: {deps}",
    "services.none_available": "  아직 사용 가능한 서비스가 없습니다.",
    "services.usage_hint": (
        "서비스를 추가하려면 'aegis init PROJECT_NAME --services auth'를 사용하세요"
    ),
    # ── update 명령 ───────────────────────────────────────────────────
    "update.title": "Aegis Stack - 템플릿 업데이트",
    "update.not_copier": "{path}의 프로젝트는 Copier로 생성되지 않았습니다.",
    "update.copier_only": (
        "'aegis update' 명령은 Copier로 생성된 프로젝트에서만 사용할 수 있습니다."
    ),
    "update.need_regen": "v0.2.0 이전에 생성된 프로젝트는 재생성이 필요합니다.",
    "update.project": "프로젝트: {path}",
    "update.commit_or_stash": (
        "'aegis update'를 실행하기 전에 변경 사항을 커밋하거나 스태시하세요."
    ),
    "update.clean_required": (
        "Copier가 안전하게 변경 사항을 병합하려면 깨끗한 git 트리가 필요합니다."
    ),
    "update.git_clean": "git 트리가 깨끗합니다",
    "update.dirty_tree": "git 트리에 커밋되지 않은 변경 사항이 있습니다",
    "update.changelog_breaking": "호환성 변경 사항:",
    "update.changelog_features": "새로운 기능:",
    "update.changelog_fixes": "버그 수정:",
    "update.changelog_other": "기타 변경 사항:",
    "update.current_commit": "   현재: {commit}...",
    "update.target_commit": "   대상: {commit}...",
    "update.unknown_version": "경고: 현재 템플릿 버전을 확인할 수 없습니다",
    "update.untagged_commit": (
        "프로젝트가 태그되지 않은 커밋에서 생성되었을 수 있습니다"
    ),
    "update.custom_template": "사용자 지정 템플릿 ({source}): {path}",
    "update.version_info": "버전 정보:",
    "update.current_cli": "   현재 CLI:      {version}",
    "update.current_template": "   현재 템플릿: {version}",
    "update.current_template_commit": "   현재 템플릿: {commit}... (커밋)",
    "update.current_template_unknown": "   현재 템플릿: 알 수 없음",
    "update.target_template": "   대상 템플릿:  {version}",
    "update.already_at_version": "프로젝트가 이미 요청한 버전입니다",
    "update.already_at_commit": "프로젝트가 이미 대상 커밋 상태입니다",
    "update.downgrade_blocked": "다운그레이드가 지원되지 않습니다",
    "update.downgrade_reason": (
        "Copier는 이전 템플릿 버전으로의 다운그레이드를 지원하지 않습니다."
    ),
    "update.changelog": "변경 로그:",
    "update.dry_run": "시뮬레이션 모드 - 변경 사항이 적용되지 않습니다",
    "update.dry_run_hint": "이 업데이트를 적용하려면 다음을 실행하세요:",
    "update.confirm": "이 업데이트를 적용하시겠습니까?",
    "update.cancelled": "업데이트가 취소되었습니다",
    "update.creating_backup": "백업 포인트를 생성하는 중...",
    "update.backup_created": "   백업 생성됨: {tag}",
    "update.backup_failed": "백업 포인트를 생성할 수 없습니다",
    "update.updating": "프로젝트 업데이트 중...",
    "update.updating_to": "템플릿 버전 {version}(으)로 업데이트 중",
    "update.moved_files": "   중첩 디렉토리에서 {count}개의 새 파일 이동됨",
    "update.synced_files": "   {count}개의 템플릿 변경 사항 동기화됨",
    "update.merge_conflicts": (
        "   {count}개 파일에 병합 충돌이 있습니다 (<<<<<<< 검색으로 해결하세요):"
    ),
    "update.running_postgen": "후처리 작업 실행 중...",
    "update.version_updated": "   __aegis_version__이(가) {version}(으)로 업데이트됨",
    "update.success": "업데이트가 완료!",
    "update.partial_success": (
        "업데이트가 완료되었지만 일부 후처리 작업이 실패했습니다"
    ),
    "update.partial_detail": "   일부 설정 작업이 실패했습니다. 위의 세부 사항을 확인하세요.",
    "update.next_steps": "다음 단계:",
    "update.next_review": "   1. 변경 사항 확인: git diff",
    "update.next_conflicts": "   2. 충돌 확인 (*.rej 파일)",
    "update.next_test": "   3. 테스트 실행: make check",
    "update.next_commit": "   4. 변경 사항 커밋: git add . && git commit",
    "update.failed": "업데이트 실패: {error}",
    "update.rollback_prompt": "이전 상태로 롤백하시겠습니까?",
    "update.manual_rollback": "수동 롤백: git reset --hard {tag}",
    "update.troubleshooting": "문제 해결:",
    "update.troubleshoot_clean": "   - 깨끗한 git 트리인지 확인하세요",
    "update.troubleshoot_version": "   - 버전/커밋이 존재하는지 확인하세요",
    "update.troubleshoot_docs": "   - 업데이트 문제에 관한 Copier 문서를 참조하세요",
    # ── ingress 명령 ──────────────────────────────────────────────────
    "ingress.title": "Aegis Stack - Ingress TLS 활성화",
    "ingress.project": "프로젝트: {path}",
    "ingress.not_found": "Ingress 컴포넌트를 찾을 수 없습니다. 먼저 추가합니다...",
    "ingress.add_confirm": "Ingress 컴포넌트를 추가하시겠습니까?",
    "ingress.add_failed": "Ingress 컴포넌트 추가 실패: {error}",
    "ingress.added": "Ingress 컴포넌트가 추가되었습니다.",
    "ingress.tls_already": "이 프로젝트에는 TLS가 이미 활성화됨.",
    "ingress.domain_label": "   도메인: {domain}",
    "ingress.acme_email": "   ACME 이메일: {email}",
    "ingress.domain_prompt": (
        "도메인 이름 (예: example.com, IP 기반 라우팅의 경우 비워두세요)"
    ),
    "ingress.email_reuse": "ACME에 기존 이메일 사용: {email}",
    "ingress.email_prompt": "Let's Encrypt 알림용 이메일",
    "ingress.email_required": (
        "오류: TLS에는 --email이 필요합니다 (Let's Encrypt에 필요)"
    ),
    "ingress.tls_config": "TLS 설정:",
    "ingress.domain_none": "   도메인: (없음 - IP/PathPrefix 라우팅)",
    "ingress.tls_confirm": "이 설정으로 TLS를 활성화하시겠습니까?",
    "ingress.enabling": "TLS 활성화 중...",
    "ingress.updated_file": "   업데이트됨: {file}",
    "ingress.created_file": "   생성됨: {file}",
    "ingress.success": "TLS가 활성화 완료!",
    "ingress.available_at": "   앱 접근 주소: https://{domain}",
    "ingress.https_configured": "   Let's Encrypt로 HTTPS가 설정되었습니다",
    "ingress.next_steps": "다음 단계:",
    "ingress.next_deploy": "   1. 배포: aegis deploy",
    "ingress.next_ports": "   2. 서버에서 80번, 443번 포트가 열려 있는지 확인하세요",
    "ingress.next_dns": ("   3. {domain}의 DNS A 레코드를 서버 IP로 지정하세요"),
    "ingress.next_certs": "   첫 요청 시 인증서가 자동으로 발급됩니다",
    # ── deploy 명령 ───────────────────────────────────────────────────
    "deploy.no_config": (
        "배포 설정을 찾을 수 없습니다. 먼저 'aegis deploy-init'을 실행하세요."
    ),
    "deploy.init_saved": "배포 설정이 {file}에 저장되었습니다",
    "deploy.init_host": "   호스트: {host}",
    "deploy.init_user": "   사용자: {user}",
    "deploy.init_path": "   경로: {path}",
    "deploy.init_docker_context": "   Docker 컨텍스트: {context}",
    "deploy.prompt_host": "서버 IP 또는 호스트명",
    "deploy.init_gitignore": (
        "참고: 배포 설정 커밋을 방지하려면 .aegis/를 .gitignore에 추가하세요"
    ),
    "deploy.setup_title": "{target}에 서버를 설정하는 중...",
    "deploy.checking_ssh": "SSH 연결을 확인하는 중...",
    "deploy.adding_host_key": "서버를 known_hosts에 추가하는 중...",
    "deploy.ssh_keyscan_failed": "SSH 호스트 키 스캔 실패: {error}",
    "deploy.ssh_failed": "SSH 연결 실패: {error}",
    "deploy.copying_script": "설정 스크립트를 서버로 복사하는 중...",
    "deploy.copy_failed": "설정 스크립트 복사 실패",
    "deploy.running_setup": "서버 설정을 실행하는 중 (몇 분 걸릴 수 있습니다)...",
    "deploy.setup_failed": "서버 설정 실패",
    "deploy.setup_script_missing": "서버 설정 스크립트를 찾을 수 없습니다: {path}",
    "deploy.setup_script_hint": (
        "프로젝트가 ingress 컴포넌트와 함께 생성되었는지 확인하세요."
    ),
    "deploy.setup_complete": "서버 설정이 완료되었습니다!",
    "deploy.setup_verify": "설치 확인:",
    "deploy.setup_verify_docker": "  Docker: {version}",
    "deploy.setup_verify_compose": "  Docker Compose: {version}",
    "deploy.setup_verify_uv": "  uv: {version}",
    "deploy.setup_verify_app_dir": "  앱 디렉토리: {path}",
    "deploy.setup_next": "다음: 'aegis deploy'를 실행하여 애플리케이션을 배포하세요",
    "deploy.deploying": "{host}에 배포하는 중...",
    "deploy.creating_backup": "백업 {timestamp} 생성 중...",
    "deploy.backup_failed": "백업 생성 실패: {error}",
    "deploy.backup_db": "PostgreSQL 데이터베이스 백업 중...",
    "deploy.backup_db_failed": (
        "경고: 데이터베이스 백업 실패, 백업 없이 계속 진행합니다"
    ),
    "deploy.backup_created": "백업 생성됨: {timestamp}",
    "deploy.backup_pruned": "오래된 백업 삭제됨: {name}",
    "deploy.no_existing": "기존 배포를 찾을 수 없어 백업을 건너뜁니다",
    "deploy.syncing": "서버로 파일을 동기화하는 중...",
    "deploy.mkdir_failed": "원격 디렉토리 '{path}' 생성 실패",
    "deploy.sync_failed": "파일 동기화 실패",
    "deploy.copying_env": "{file}을(를) 서버에 .env로 복사하는 중...",
    "deploy.env_copy_failed": ".env 파일 복사 실패",
    "deploy.stopping": "기존 서비스를 중지하는 중...",
    "deploy.building": "서버에서 서비스를 빌드하고 시작하는 중...",
    "deploy.start_failed": "서비스 시작 실패",
    "deploy.auto_rollback": "이전 버전으로 자동 롤백하는 중...",
    "deploy.health_waiting": "컨테이너가 안정화될 때까지 대기 중...",
    "deploy.health_attempt": "헬스 체크 시도 {n}/{total}...",
    "deploy.health_passed": "헬스 체크 통과",
    "deploy.health_retry": "헬스 체크 실패, {interval}초 후 재시도...",
    "deploy.health_all_failed": "모든 헬스 체크 시도가 실패했습니다",
    "deploy.rolled_back": "백업 {timestamp}(으)로 롤백되었습니다",
    "deploy.rollback_failed": "롤백 실패! 수동 조치가 필요합니다.",
    "deploy.health_failed_hint": (
        "배포는 완료되었지만 헬스 체크에 실패했습니다. 로그를 확인하세요: aegis deploy-logs"
    ),
    "deploy.complete": "배포가 완료되었습니다!",
    "deploy.app_running": "   애플리케이션 실행 중: http://{host}",
    "deploy.overseer": "   Overseer 대시보드: http://{host}/dashboard/",
    "deploy.view_logs": "   로그 확인: aegis deploy-logs",
    "deploy.check_status": "   상태 확인: aegis deploy-status",
    "deploy.backup_complete": "백업이 완료되었습니다!",
    "deploy.creating_backup_on": "{host}에서 백업을 생성하는 중...",
    "deploy.no_backups": "백업이 없습니다.",
    "deploy.backups_header": "{host}의 백업 ({count}개):",
    "deploy.col_timestamp": "타임스탬프",
    "deploy.col_size": "크기",
    "deploy.col_database": "데이터베이스",
    "deploy.rollback_hint": ("롤백 명령: aegis deploy-rollback --backup <timestamp>"),
    "deploy.no_backups_available": "사용 가능한 백업이 없습니다.",
    "deploy.rolling_back": "{host}에서 백업 {backup}(으)로 롤백하는 중...",
    "deploy.rollback_not_found": "백업을 찾을 수 없습니다: {timestamp}",
    "deploy.rollback_stopping": "서비스를 중지하는 중...",
    "deploy.rollback_restoring": "백업 {timestamp}에서 파일을 복원하는 중...",
    "deploy.rollback_restore_failed": "파일 복원 실패: {error}",
    "deploy.rollback_db": "데이터베이스를 복원하는 중...",
    "deploy.rollback_pg_wait": "PostgreSQL이 준비될 때까지 대기 중...",
    "deploy.rollback_pg_timeout": (
        "PostgreSQL이 준비되지 않았습니다. 복원을 시도합니다"
    ),
    "deploy.rollback_db_failed": "경고: 데이터베이스 복원 실패",
    "deploy.rollback_starting": "서비스를 시작하는 중...",
    "deploy.rollback_start_failed": "롤백 후 서비스 시작 실패",
    "deploy.rollback_complete": "롤백이 완료되었습니다!",
    "deploy.rollback_failed_final": "롤백에 실패했습니다!",
    "deploy.status_header": "{host}의 서비스 상태:",
    "deploy.stop_stopping": "서비스를 중지하는 중...",
    "deploy.stop_success": "서비스가 중지되었습니다",
    "deploy.stop_failed": "서비스 중지 실패",
    "deploy.restart_restarting": "서비스를 재시작하는 중...",
    "deploy.restart_success": "서비스가 재시작되었습니다",
    "deploy.restart_failed": "서비스 재시작 실패",
}
