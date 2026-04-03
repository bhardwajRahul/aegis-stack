"""Spanish locale — Definiciones de mensajes en español."""

MESSAGES: dict[str, str] = {
    # ── Validation ─────────────────────────────────────────────────────
    "validation.invalid_name": (
        "Nombre de proyecto inválido. Solo se permiten letras, números, "
        "guiones y guiones bajos."
    ),
    "validation.reserved_name": "'{name}' es un nombre reservado.",
    "validation.name_too_long": (
        "Nombre de proyecto demasiado largo. Máximo 50 caracteres."
    ),
    "validation.invalid_python": (
        "Versión de Python inválida '{version}'. Debe ser una de: {supported}"
    ),
    "validation.unknown_service": "Servicio desconocido: {name}",
    "validation.unknown_services": "Servicios desconocidos: {names}",
    "validation.unknown_component": "Componente desconocido: {name}",
    # ── Init command ───────────────────────────────────────────────────
    "init.title": "Inicialización de proyecto Aegis Stack",
    "init.location": "Ubicación:",
    "init.template_version": "Versión de plantilla:",
    "init.dir_exists": "El directorio '{path}' ya existe",
    "init.dir_exists_hint": "Usa --force para sobrescribir o elige otro nombre",
    "init.overwriting": "Sobrescribiendo directorio existente: {path}",
    "init.services_require": "Servicios requieren componentes: {components}",
    "init.compat_errors": "Errores de compatibilidad servicio-componente:",
    "init.suggestion_add": (
        "Sugerencia: Agrega componentes faltantes --components {components}"
    ),
    "init.suggestion_remove": (
        "O quita --components para que los servicios agreguen dependencias automáticamente."
    ),
    "init.suggestion_interactive": (
        "También puedes usar modo interactivo para agregar dependencias de servicios automáticamente."
    ),
    "init.auto_detected_scheduler": (
        "Auto-detectado: Scheduler con persistencia {backend}"
    ),
    "init.auto_added_deps": "Dependencias agregadas automáticamente: {deps}",
    "init.auto_added_by_services": "Agregado automáticamente por servicios:",
    "init.required_by": "requerido por {services}",
    "init.config_title": "Configuración del proyecto",
    "init.config_name": "Nombre:",
    "init.config_core": "Core:",
    "init.config_infra": "Infraestructura:",
    "init.config_services": "Servicios:",
    "init.component_files": "Archivos de componentes:",
    "init.entrypoints": "Puntos de entrada:",
    "init.worker_queues": "Colas de Worker:",
    "init.dependencies": "Dependencias a instalar:",
    "init.confirm_create": "¿Crear este proyecto?",
    "init.cancelled": "Creación de proyecto cancelada",
    "init.removing_dir": "Eliminando directorio existente: {path}",
    "init.creating": "Creando proyecto: {name}",
    "init.error": "Error al crear proyecto: {error}",
    # ── Interactive: section headers ───────────────────────────────────
    "interactive.component_selection": "Selección de componentes",
    "interactive.service_selection": "Selección de servicios",
    "interactive.core_included": (
        "Componentes core ({components}) incluidos automáticamente"
    ),
    "interactive.infra_header": "Componentes de infraestructura:",
    "interactive.services_intro": (
        "Los servicios proporcionan lógica de negocio para tu aplicación."
    ),
    # ── Component descriptions ──────────────────────────────────────────
    "component.backend": "Servidor backend FastAPI",
    "component.frontend": "Interfaz frontend Flet",
    "component.redis": "Redis cache y broker de mensajes",
    "component.worker": "Procesamiento de tareas en segundo plano (arq, Dramatiq o TaskIQ)",
    "component.scheduler": "Infraestructura de ejecución de tareas programadas",
    "component.database": "Base de datos con SQLModel ORM (SQLite o PostgreSQL)",
    "component.ingress": "Traefik reverse proxy y balanceador de carga",
    "component.observability": "Logfire observabilidad, trazas y métricas",
    # ── Service descriptions ────────────────────────────────────────────
    "service.auth": "Autenticación y autorización de usuarios con tokens JWT",
    "service.ai": "Servicio de chatbot IA con soporte multi-framework",
    "service.comms": "Servicio de comunicaciones con email, SMS y voz",
    # ── Interactive: component prompts ─────────────────────────────────
    "interactive.add_prompt": "¿Agregar {description}?",
    "interactive.add_with_redis": "¿Agregar {description}? (agregará Redis automáticamente)",
    "interactive.worker_configured": "Worker con backend {backend} configurado",
    # ── Interactive: scheduler ─────────────────────────────────────────
    "interactive.scheduler_persistence": "Persistencia de Scheduler:",
    "interactive.persist_prompt": (
        "¿Persistir tareas programadas? "
        "(Habilita historial de tareas, recuperación tras reinicios)"
    ),
    "interactive.scheduler_db_configured": "Scheduler + base de datos {engine} configurado",
    "interactive.bonus_backup": "Extra: Agregando tarea de respaldo de base de datos",
    "interactive.backup_desc": (
        "Tarea de respaldo diario de base de datos incluida (se ejecuta a las 2 AM)"
    ),
    # ── Interactive: database engine ───────────────────────────────────
    "interactive.db_engine_label": "Motor de base de datos {context}:",
    "interactive.db_select": "Selecciona motor de base de datos:",
    "interactive.db_sqlite": "SQLite - Simple, basado en archivo (ideal para desarrollo)",
    "interactive.db_postgres": (
        "PostgreSQL - Listo para producción, soporte multi-contenedor"
    ),
    "interactive.db_reuse": "Usando base de datos previamente seleccionada: {engine}",
    # ── Interactive: worker backend ────────────────────────────────────
    "interactive.worker_label": "Backend de Worker:",
    "interactive.worker_select": "Selecciona backend de worker:",
    "interactive.worker_arq": "arq - Async, ligero (predeterminado)",
    "interactive.worker_dramatiq": (
        "Dramatiq - Basado en procesos, ideal para trabajo CPU-bound"
    ),
    "interactive.worker_taskiq": (
        "TaskIQ - Async, estilo framework con brokers por cola"
    ),
    # ── Interactive: auth ──────────────────────────────────────────────
    "interactive.auth_header": "Servicios de autenticación:",
    "interactive.auth_level_label": "Nivel de autenticación:",
    "interactive.auth_select": "¿Qué tipo de autenticación?",
    "interactive.auth_basic": "Básico - Login con email/contraseña",
    "interactive.auth_rbac": "Con Roles - + control de acceso basado en roles (experimental)",
    "interactive.auth_org": "Con Organizaciones - + soporte multi-tenant (experimental)",
    "interactive.auth_selected": "Nivel de auth seleccionado: {level}",
    "interactive.auth_db_required": "Base de datos requerida:",
    "interactive.auth_db_reason": (
        "Autenticación requiere base de datos para almacenar usuarios"
    ),
    "interactive.auth_db_details": "(cuentas de usuario, sesiones, tokens JWT)",
    "interactive.auth_db_already": "Componente de base de datos ya seleccionado",
    "interactive.auth_db_confirm": "¿Continuar y agregar componente de base de datos?",
    "interactive.auth_cancelled": "Servicio de autenticación cancelado",
    "interactive.auth_db_configured": "Autenticación + Base de datos configurado",
    # ── Interactive: AI service ────────────────────────────────────────
    "interactive.ai_header": "Servicios de IA y Machine Learning:",
    "interactive.ai_framework_label": "Selección de framework IA:",
    "interactive.ai_framework_intro": "Elige tu framework de IA:",
    "interactive.ai_pydanticai": (
        "PydanticAI - Framework IA type-safe y Pythónico (recomendado)"
    ),
    "interactive.ai_langchain": (
        "LangChain - Framework popular con integraciones extensivas"
    ),
    "interactive.ai_use_pydanticai": "¿Usar PydanticAI? (recomendado)",
    "interactive.ai_selected_framework": "Framework seleccionado: {framework}",
    "interactive.ai_tracking_context": "Seguimiento de uso de IA",
    "interactive.ai_tracking_label": "Seguimiento de uso de LLM:",
    "interactive.ai_tracking_prompt": (
        "¿Habilitar seguimiento de uso? (conteo de tokens, costos, historial de conversaciones)"
    ),
    "interactive.ai_sync_label": "Sincronización de catálogo LLM:",
    "interactive.ai_sync_desc": (
        "Sincronizar obtiene datos actualizados de modelos desde APIs de OpenRouter/LiteLLM"
    ),
    "interactive.ai_sync_time": ("Requiere acceso a red y toma ~30-60 segundos"),
    "interactive.ai_sync_prompt": "¿Sincronizar catálogo LLM durante la generación del proyecto?",
    "interactive.ai_sync_will": "Catálogo LLM se sincronizará tras la generación del proyecto",
    "interactive.ai_sync_skipped": (
        "Sincronización LLM omitida - datos de fixture estáticos disponibles"
    ),
    "interactive.ai_provider_label": "Selección de proveedor IA:",
    "interactive.ai_provider_intro": (
        "Elige proveedores de IA a incluir (selección múltiple permitida)"
    ),
    "interactive.ai_provider_options": "Opciones de proveedor:",
    "interactive.ai_provider_recommended": "(Recomendado)",
    "interactive.ai_provider.openai": "OpenAI - Modelos GPT (Pago)",
    "interactive.ai_provider.anthropic": "Anthropic - Modelos Claude (Pago)",
    "interactive.ai_provider.google": "Google - Modelos Gemini (Nivel gratuito)",
    "interactive.ai_provider.groq": "Groq - Inferencia rápida (Nivel gratuito)",
    "interactive.ai_provider.mistral": "Mistral - Modelos abiertos (Mayormente pago)",
    "interactive.ai_provider.cohere": "Cohere - Enfoque empresarial (Gratuito limitado)",
    "interactive.ai_provider.ollama": "Ollama - Inferencia local (Gratuito)",
    "interactive.ai_no_providers": (
        "Sin proveedores seleccionados, agregando valores predeterminados..."
    ),
    "interactive.ai_selected_providers": "Proveedores seleccionados: {providers}",
    "interactive.ai_deps_optimized": ("Dependencias optimizadas según tu selección"),
    "interactive.ai_ollama_label": "Modo de despliegue de Ollama:",
    "interactive.ai_ollama_intro": "¿Cómo quieres ejecutar Ollama?",
    "interactive.ai_ollama_host": (
        "Host - Conectar a Ollama en tu máquina (Mac/Windows)"
    ),
    "interactive.ai_ollama_docker": (
        "Docker - Ejecutar Ollama en contenedor Docker (Linux/Deploy)"
    ),
    "interactive.ai_ollama_host_prompt": (
        "¿Conectar a Ollama del host? (recomendado para Mac/Windows)"
    ),
    "interactive.ai_ollama_host_ok": (
        "Ollama se conectará a host.docker.internal:11434"
    ),
    "interactive.ai_ollama_host_hint": "Asegúrate de que Ollama esté corriendo: ollama serve",
    "interactive.ai_ollama_docker_ok": (
        "Servicio Ollama se agregará a docker-compose.yml"
    ),
    "interactive.ai_ollama_docker_hint": (
        "Nota: El primer inicio puede tardar en descargar modelos"
    ),
    "interactive.ai_rag_label": "RAG (Retrieval-Augmented Generation):",
    "interactive.ai_rag_warning": (
        "Advertencia: RAG requiere Python <3.14 (limitación de chromadb/onnxruntime)"
    ),
    "interactive.ai_rag_compat_note": (
        "Habilitar RAG generará un proyecto que requiere Python 3.11-3.13"
    ),
    "interactive.ai_rag_compat_prompt": (
        "¿Habilitar RAG a pesar de incompatibilidad con Python 3.14?"
    ),
    "interactive.ai_rag_prompt": (
        "¿Habilitar RAG para indexación de documentos y búsqueda semántica?"
    ),
    "interactive.ai_rag_enabled": "RAG habilitado con almacén vectorial ChromaDB",
    "interactive.ai_voice_label": "Voz (Text-to-Speech y Speech-to-Text):",
    "interactive.ai_voice_prompt": (
        "¿Habilitar capacidades de voz? (TTS y STT para interacciones por voz)"
    ),
    "interactive.ai_voice_enabled": "Voz habilitada con soporte TTS y STT",
    "interactive.ai_db_already": "Base de datos ya seleccionada - seguimiento de uso habilitado",
    "interactive.ai_db_added": "Base de datos ({backend}) agregada para seguimiento de uso",
    "interactive.ai_configured": "Servicio de IA configurado",
    # ── Shared: validation ──────────────────────────────────────────────
    "shared.not_copier_project": "Proyecto en {path} no fue generado con Copier.",
    "shared.copier_only": (
        "El comando 'aegis {command}' solo funciona con proyectos generados por Copier."
    ),
    "shared.regenerate_hint": (
        "Para agregar componentes, regenera el proyecto con los nuevos componentes incluidos."
    ),
    "shared.git_not_initialized": "Proyecto no está en un repositorio git",
    "shared.git_required": "Actualizaciones de Copier requieren git para seguimiento de cambios",
    "shared.git_init_hint": (
        "Proyectos creados con 'aegis init' deberían tener git inicializado automáticamente"
    ),
    "shared.git_manual_init": (
        "Si creaste este proyecto manualmente, ejecuta: "
        "git init && git add . && git commit -m 'Initial commit'"
    ),
    "shared.empty_component": "Nombre de componente vacío no permitido",
    "shared.empty_service": "Nombre de servicio vacío no permitido",
    # ── Shared: next steps / review ──────────────────────────────────
    "shared.next_steps": "Próximos pasos:",
    "shared.next_make_check": "   1. Ejecuta 'make check' para verificar la actualización",
    "shared.next_test": "   2. Prueba tu aplicación",
    "shared.next_commit": "   3. Confirma los cambios con: git add . && git commit",
    "shared.review_header": "Revisa los cambios:",
    "shared.review_docker": "   git diff docker-compose.yml",
    "shared.review_pyproject": "   git diff pyproject.toml",
    "shared.operation_cancelled": "Operación cancelada",
    "shared.interactive_ignores_args": (
        "Advertencia: la opción --interactive ignora argumentos de componentes"
    ),
    "shared.no_components_selected": "Sin componentes seleccionados",
    "shared.no_services_selected": "Sin servicios seleccionados",
    # ── Add command ──────────────────────────────────────────────────
    "add.title": "Aegis Stack - Agregar componentes",
    "add.project": "Proyecto: {path}",
    "add.error_no_args": (
        "Error: argumento de componentes requerido (o usa --interactive)"
    ),
    "add.usage_hint": "Uso: aegis add scheduler,worker",
    "add.interactive_hint": "O: aegis add --interactive",
    "add.auto_added_deps": "Dependencias agregadas automáticamente: {deps}",
    "add.validation_failed": "Validación de componentes fallida: {error}",
    "add.load_config_failed": "No se pudo cargar configuración del proyecto: {error}",
    "add.already_enabled": "Ya habilitado: {components}",
    "add.all_enabled": "¡Todos los componentes solicitados ya están habilitados!",
    "add.components_to_add": "Componentes a agregar:",
    "add.scheduler_backend": "Backend de scheduler: {backend}",
    "add.confirm": "¿Agregar estos componentes?",
    "add.updating": "Actualizando proyecto...",
    "add.adding": "Agregando {component}...",
    "add.added_files": "{count} archivos agregados",
    "add.skipped_files": "{count} archivos existentes omitidos",
    "add.success": "¡Componentes agregados!",
    "add.failed_component": "Error al agregar {component}: {error}",
    "add.failed": "Error al agregar componentes: {error}",
    "add.invalid_format": "Formato de componente inválido: {error}",
    "add.bracket_override": (
        "Sintaxis de corchetes 'scheduler[{engine}]' sobrescribe --backend {backend}"
    ),
    "add.invalid_scheduler_backend": "Backend de scheduler inválido: '{backend}'",
    "add.valid_backends": "Opciones válidas: {options}",
    "add.postgres_coming": "Nota: Soporte para PostgreSQL disponible en versión futura",
    "add.auto_added_db": "Componente de base de datos agregado automáticamente para persistencia de scheduler",
    # ── Remove command ────────────────────────────────────────────────
    "remove.title": "Aegis Stack - Eliminar componentes",
    "remove.project": "Proyecto: {path}",
    "remove.error_no_args": (
        "Error: argumento de componentes requerido (o usa --interactive)"
    ),
    "remove.usage_hint": "Uso: aegis remove scheduler,worker",
    "remove.interactive_hint": "O: aegis remove --interactive",
    "remove.no_selected": "Sin componentes seleccionados para eliminar",
    "remove.validation_failed": "Validación de componentes fallida: {error}",
    "remove.load_config_failed": "No se pudo cargar configuración del proyecto: {error}",
    "remove.cannot_remove_core": "No se puede eliminar componente core: {component}",
    "remove.not_enabled": "No habilitado: {components}",
    "remove.nothing_to_remove": "¡No hay componentes que eliminar!",
    "remove.auto_remove_redis": (
        "Eliminando redis automáticamente (sin funcionalidad independiente, solo usado por worker)"
    ),
    "remove.scheduler_persistence_warn": "IMPORTANTE: Advertencia de persistencia de Scheduler",
    "remove.scheduler_persistence_detail": (
        "Tu scheduler usa SQLite para persistencia de tareas."
    ),
    "remove.scheduler_db_remains": (
        "El archivo de base de datos en data/scheduler.db permanecerá."
    ),
    "remove.scheduler_keep_hint": (
        "Para conservar historial de tareas: Deja el componente de base de datos"
    ),
    "remove.scheduler_remove_hint": (
        "Para eliminar todos los datos: Elimina también el componente de base de datos"
    ),
    "remove.components_to_remove": "Componentes a eliminar:",
    "remove.warning_delete": (
        "ADVERTENCIA: ¡Esto ELIMINARÁ archivos de componentes de tu proyecto!"
    ),
    "remove.commit_hint": "Asegúrate de haber confirmado tus cambios en git.",
    "remove.confirm": "¿Eliminar estos componentes?",
    "remove.removing_all": "Eliminando componentes...",
    "remove.removing": "Eliminando {component}...",
    "remove.removed_files": "{count} archivos eliminados",
    "remove.failed_component": "Error al eliminar {component}: {error}",
    "remove.success": "¡Componentes eliminados!",
    "remove.failed": "Error al eliminar componentes: {error}",
    # ── Manual updater ─────────────────────────────────────────────────
    "updater.processing_files": "Procesando {count} archivos de componentes...",
    "updater.updating_shared": "Actualizando archivos de plantilla compartidos...",
    "updater.running_postgen": "Ejecutando tareas post-generación...",
    "updater.deps_synced": "Dependencias sincronizadas (uv sync)",
    "updater.code_formatted": "Código formateado (make fix)",
    # ── Project map ──────────────────────────────────────────────────
    "projectmap.new": "NUEVO",
    # ── Post-generation: setup tasks ──────────────────────────────────
    "postgen.setup_start": "Configurando entorno de proyecto...",
    "postgen.deps_installing": "Instalando dependencias con uv...",
    "postgen.deps_success": "Dependencias instaladas",
    "postgen.deps_failed": "Generación de proyecto fallida: instalación de dependencias falló",
    "postgen.deps_failed_detail": (
        "Los archivos del proyecto generado permanecen, pero el proyecto no es utilizable."
    ),
    "postgen.deps_failed_hint": (
        "Corrige el problema de dependencias (verifica compatibilidad de versión de Python) e intenta de nuevo."
    ),
    "postgen.deps_warn_failed": "Advertencia: Instalación de dependencias falló",
    "postgen.deps_manual": "Ejecuta 'uv sync' manualmente tras crear el proyecto",
    "postgen.deps_timeout": (
        "Advertencia: Tiempo de espera en instalación de dependencias - ejecuta 'uv sync' manualmente"
    ),
    "postgen.deps_uv_missing": "Advertencia: uv no encontrado en PATH",
    "postgen.deps_uv_install": "Instala uv primero: https://github.com/astral-sh/uv",
    "postgen.deps_warn_error": "Advertencia: Instalación de dependencias falló: {error}",
    "postgen.env_setup": "Configurando entorno...",
    "postgen.env_created": "Archivo de entorno creado desde .env.example",
    "postgen.env_exists": "Archivo de entorno ya existe",
    "postgen.env_missing": "Advertencia: Archivo .env.example no encontrado",
    "postgen.env_error": "Advertencia: Configuración de entorno falló: {error}",
    "postgen.env_manual": "Copia .env.example a .env manualmente",
    # ── Post-generation: database/migrations ────────────────────────────
    "postgen.db_setup": "Configurando esquema de base de datos...",
    "postgen.db_success": "Tablas de base de datos creadas",
    "postgen.db_alembic_missing": "Advertencia: Archivo de configuración de Alembic no encontrado en {path}",
    "postgen.db_alembic_hint": (
        "Omitiendo migración de base de datos. Asegúrate de que el archivo de configuración exista "
        "y ejecuta 'alembic upgrade head' manualmente."
    ),
    "postgen.db_failed": "Advertencia: Configuración de migración de base de datos falló",
    "postgen.db_manual": "Ejecuta 'alembic upgrade head' manualmente tras crear el proyecto",
    "postgen.db_timeout": (
        "Advertencia: Tiempo de espera en migración - ejecuta 'alembic upgrade head' manualmente"
    ),
    "postgen.db_error": "Advertencia: Configuración de migración falló: {error}",
    # ── Post-generation: LLM fixtures/sync ────────────────────────────
    "postgen.llm_seeding": "Cargando fixtures de LLM...",
    "postgen.llm_seed_success": "Fixtures de LLM cargados",
    "postgen.llm_seed_failed": "Advertencia: Carga de fixtures de LLM falló",
    "postgen.llm_seed_manual": (
        "Puedes cargar fixtures manualmente ejecutando el cargador de fixtures"
    ),
    "postgen.llm_seed_timeout": "Advertencia: Tiempo de espera en carga de fixtures de LLM",
    "postgen.llm_seed_error": "Advertencia: Carga de fixtures de LLM falló: {error}",
    "postgen.llm_syncing": "Sincronizando catálogo LLM desde APIs externas...",
    "postgen.llm_sync_success": "Catálogo LLM sincronizado",
    "postgen.llm_sync_failed": "Advertencia: Sincronización de catálogo LLM falló",
    "postgen.llm_sync_manual": (
        "Ejecuta '{slug} llm sync' manualmente para poblar el catálogo"
    ),
    "postgen.llm_sync_timeout": "Advertencia: Tiempo de espera en sincronización de catálogo LLM",
    "postgen.llm_sync_error": "Advertencia: Sincronización de catálogo LLM falló: {error}",
    # ── Post-generation: formatting ───────────────────────────────────
    "postgen.format_timeout": (
        "Advertencia: Tiempo de espera en formateo - ejecuta 'make fix' manualmente"
    ),
    "postgen.format_error": "Advertencia: Auto-formateo omitido: {error}",
    "postgen.format_error_manual": "Ejecuta 'make fix' manualmente para formatear código",
    "postgen.format_start": "Auto-formateando código generado...",
    "postgen.format_success": "Formateo de código completado",
    "postgen.format_partial": (
        "Algunos problemas de formateo detectados, pero proyecto creado"
    ),
    "postgen.format_manual": "Ejecuta 'make fix' manualmente para resolver problemas restantes",
    "postgen.format_hint": "Ejecuta 'make fix' para formatear código",
    "postgen.llm_sync_skipped": "Sincronización de catálogo LLM omitida",
    "postgen.llm_fixtures_outdated": "Datos de fixture estáticos cargados (pueden estar desactualizados)",
    "postgen.llm_sync_hint": "Ejecuta '{slug} llm sync' después para obtener datos actualizados",
    "postgen.llm_fixtures_fallback": (
        "Datos de fixture estáticos disponibles pero pueden estar desactualizados"
    ),
    "postgen.ready": "¡Proyecto listo para ejecutar!",
    "postgen.next_steps": "Próximos pasos:",
    "postgen.next_cd": "   cd {path}",
    "postgen.next_serve": "   make serve",
    "postgen.next_dashboard": "   Abrir Overseer: http://localhost:8000/dashboard/",
    # ── Post-generation: project map ──────────────────────────────────
    "projectmap.title": "Estructura del proyecto:",
    "projectmap.components": "Componentes",
    "projectmap.services": "Lógica de negocio",
    "projectmap.models": "Modelos de base de datos",
    "projectmap.cli": "Comandos CLI",
    "projectmap.entrypoints": "Puntos de ejecución",
    "projectmap.tests": "Suite de pruebas",
    "projectmap.migrations": "Migraciones",
    "projectmap.auth": "Autenticación",
    "projectmap.ai": "Conversaciones IA",
    "projectmap.comms": "Comunicaciones",
    "projectmap.docs": "Documentación",
    # ── Post-generation: footer ───────────────────────────────────────
    "postgen.docs_link": "Docs: https://lbedner.github.io/aegis-stack",
    "postgen.star_prompt": (
        "Si Aegis Stack te facilitó la vida, considera dejar una estrella:"
    ),
    # ── Add-service command ────────────────────────────────────────────
    "add_service.title": "Aegis Stack - Agregar servicios",
    "add_service.project": "Proyecto: {path}",
    "add_service.error_no_args": (
        "Error: argumento de servicios requerido (o usa --interactive)"
    ),
    "add_service.usage_hint": "Uso: aegis add-service auth,ai",
    "add_service.interactive_hint": "O: aegis add-service --interactive",
    "add_service.interactive_ignores_args": (
        "Advertencia: la opción --interactive ignora argumentos de servicios"
    ),
    "add_service.no_selected": "Sin servicios seleccionados",
    "add_service.already_enabled": "Ya habilitado: {services}",
    "add_service.all_enabled": "¡Todos los servicios solicitados ya están habilitados!",
    "add_service.validation_failed": "Validación de servicios fallida: {error}",
    "add_service.load_config_failed": "No se pudo cargar configuración del proyecto: {error}",
    "add_service.services_to_add": "Servicios a agregar:",
    "add_service.required_components": "Componentes requeridos (se agregarán automáticamente):",
    "add_service.already_have_components": (
        "Ya tiene componentes requeridos: {components}"
    ),
    "add_service.confirm": "¿Agregar estos servicios?",
    "add_service.adding_component": "Agregando componente requerido: {component}...",
    "add_service.failed_component": "Error al agregar componente {component}: {error}",
    "add_service.added_files": "{count} archivos agregados",
    "add_service.skipped_files": "{count} archivos existentes omitidos",
    "add_service.adding_service": "Agregando servicio: {service}...",
    "add_service.failed_service": "Error al agregar servicio {service}: {error}",
    "add_service.resolve_failed": "Error al resolver dependencias de servicio: {error}",
    "add_service.bootstrap_alembic": "Inicializando infraestructura alembic...",
    "add_service.created_file": "Creado: {file}",
    "add_service.generated_migration": "Migración generada: {name}",
    "add_service.applying_migrations": "Aplicando migraciones de base de datos...",
    "add_service.migration_failed": (
        "Advertencia: Migración automática falló. Ejecuta 'make migrate' manualmente."
    ),
    "add_service.success": "¡Servicios agregados!",
    "add_service.failed": "Error al agregar servicios: {error}",
    "add_service.auth_setup": "Configuración de Auth:",
    "add_service.auth_create_users": "   1. Crear usuarios de prueba: {cmd}",
    "add_service.auth_view_routes": "   2. Ver rutas de auth: {url}",
    "add_service.ai_setup": "Configuración de IA:",
    "add_service.ai_set_provider": (
        "   1. Configura {env_var} en .env (openai, anthropic, google, groq)"
    ),
    "add_service.ai_set_api_key": "   2. Configura la API key del proveedor ({env_var}, etc.)",
    "add_service.ai_test_cli": "   3. Prueba con CLI: {cmd}",
    # ── Remove-service command ─────────────────────────────────────────
    "remove_service.title": "Aegis Stack - Eliminar servicios",
    "remove_service.project": "Proyecto: {path}",
    "remove_service.error_no_args": (
        "Error: argumento de servicios requerido (o usa --interactive)"
    ),
    "remove_service.usage_hint": "Uso: aegis remove-service auth,ai",
    "remove_service.interactive_hint": "O: aegis remove-service --interactive",
    "remove_service.interactive_ignores_args": (
        "Advertencia: la opción --interactive ignora argumentos de servicios"
    ),
    "remove_service.no_selected": "Sin servicios seleccionados para eliminar",
    "remove_service.not_enabled": "No habilitado: {services}",
    "remove_service.nothing_to_remove": "¡No hay servicios que eliminar!",
    "remove_service.validation_failed": "Validación de servicios fallida: {error}",
    "remove_service.load_config_failed": (
        "No se pudo cargar configuración del proyecto: {error}"
    ),
    "remove_service.services_to_remove": "Servicios a eliminar:",
    "remove_service.auth_warning": "IMPORTANTE: Advertencia de servicio Auth",
    "remove_service.auth_delete_intro": "Eliminar servicio auth borrará:",
    "remove_service.auth_delete_endpoints": "Endpoints API de autenticación de usuarios",
    "remove_service.auth_delete_models": "Modelo de usuario y servicios de autenticación",
    "remove_service.auth_delete_jwt": "Código de manejo de tokens JWT",
    "remove_service.auth_db_note": (
        "Nota: Tablas de base de datos y migraciones alembic NO se eliminan."
    ),
    "remove_service.warning_delete": (
        "ADVERTENCIA: ¡Esto ELIMINARÁ archivos de servicios de tu proyecto!"
    ),
    "remove_service.confirm": "¿Eliminar estos servicios?",
    "remove_service.removing": "Eliminando servicio: {service}...",
    "remove_service.failed_service": "Error al eliminar servicio {service}: {error}",
    "remove_service.removed_files": "{count} archivos eliminados",
    "remove_service.success": "¡Servicios eliminados!",
    "remove_service.failed": "Error al eliminar servicios: {error}",
    "remove_service.deps_not_removed": (
        "Nota: Dependencias de servicios (base de datos, etc.) NO fueron eliminadas."
    ),
    "remove_service.deps_remove_hint": (
        "Usa 'aegis remove <componente>' para eliminar componentes por separado."
    ),
    # ── Version command ────────────────────────────────────────────────
    "version.info": "Aegis Stack CLI v{version}",
    # ── Components command ─────────────────────────────────────────────
    "components.core_title": "COMPONENTES CORE",
    "components.backend_desc": (
        "  backend      - Servidor backend FastAPI (siempre incluido)"
    ),
    "components.frontend_desc": (
        "  frontend     - Interfaz frontend Flet (siempre incluido)"
    ),
    "components.infra_title": "COMPONENTES DE INFRAESTRUCTURA",
    "components.requires": "Requiere: {deps}",
    "components.recommends": "Recomienda: {deps}",
    "components.usage_hint": (
        "Usa 'aegis init NOMBRE_PROYECTO --components redis,worker' para seleccionar componentes"
    ),
    # ── Services command ───────────────────────────────────────────────
    "services.title": "SERVICIOS DISPONIBLES",
    "services.type_auth": "Servicios de autenticación",
    "services.type_payment": "Servicios de pago",
    "services.type_ai": "Servicios de IA y Machine Learning",
    "services.type_notification": "Servicios de notificaciones",
    "services.type_analytics": "Servicios de analítica",
    "services.type_storage": "Servicios de almacenamiento",
    "services.requires_components": "Requiere componentes: {deps}",
    "services.recommends_components": "Recomienda componentes: {deps}",
    "services.requires_services": "Requiere servicios: {deps}",
    "services.none_available": "  Sin servicios disponibles aún.",
    "services.usage_hint": (
        "Usa 'aegis init NOMBRE_PROYECTO --services auth' para agregar servicios"
    ),
    # ── Update command ─────────────────────────────────────────────────
    "update.title": "Aegis Stack - Actualizar plantilla",
    "update.not_copier": "Proyecto en {path} no fue generado con Copier.",
    "update.copier_only": (
        "El comando 'aegis update' solo funciona con proyectos generados por Copier."
    ),
    "update.need_regen": "Proyectos generados antes de v0.2.0 necesitan ser regenerados.",
    "update.project": "Proyecto: {path}",
    "update.commit_or_stash": (
        "Confirma o guarda tus cambios antes de ejecutar 'aegis update'."
    ),
    "update.clean_required": (
        "Copier requiere un árbol git limpio para fusionar cambios de forma segura."
    ),
    "update.git_clean": "Árbol git limpio",
    "update.dirty_tree": "Árbol git tiene cambios sin confirmar",
    "update.changelog_breaking": "Cambios incompatibles:",
    "update.changelog_features": "Nuevas funcionalidades:",
    "update.changelog_fixes": "Correcciones:",
    "update.changelog_other": "Otros cambios:",
    "update.current_commit": "   Actual: {commit}...",
    "update.target_commit": "   Destino: {commit}...",
    "update.unknown_version": "Advertencia: No se puede determinar versión actual de plantilla",
    "update.untagged_commit": (
        "Proyecto puede haber sido generado desde un commit sin etiqueta"
    ),
    "update.custom_template": "Usando plantilla personalizada ({source}): {path}",
    "update.version_info": "Información de versión:",
    "update.current_cli": "   CLI actual:        {version}",
    "update.current_template": "   Plantilla actual:  {version}",
    "update.current_template_commit": "   Plantilla actual:  {commit}... (commit)",
    "update.current_template_unknown": "   Plantilla actual:  desconocida",
    "update.target_template": "   Plantilla destino: {version}",
    "update.already_at_version": "Proyecto ya está en la versión solicitada",
    "update.already_at_commit": "Proyecto ya está en el commit destino",
    "update.downgrade_blocked": "Degradación no soportada",
    "update.downgrade_reason": (
        "Copier no soporta degradación a versiones anteriores de plantilla."
    ),
    "update.changelog": "Registro de cambios:",
    "update.dry_run": "MODO DE PRUEBA - No se aplicarán cambios",
    "update.dry_run_hint": "Para aplicar esta actualización, ejecuta:",
    "update.confirm": "¿Aplicar esta actualización?",
    "update.cancelled": "Actualización cancelada",
    "update.creating_backup": "Creando punto de respaldo...",
    "update.backup_created": "   Respaldo creado: {tag}",
    "update.backup_failed": "No se pudo crear punto de respaldo",
    "update.updating": "Actualizando proyecto...",
    "update.updating_to": "Actualizando a versión de plantilla {version}",
    "update.moved_files": "   {count} archivos nuevos movidos desde directorio anidado",
    "update.synced_files": "   {count} cambios de plantilla sincronizados",
    "update.merge_conflicts": (
        "   {count} archivo(s) tienen conflictos de fusión (busca <<<<<<< para resolver):"
    ),
    "update.running_postgen": "Ejecutando tareas post-generación...",
    "update.version_updated": "   __aegis_version__ actualizado a {version}",
    "update.success": "¡Actualización completada!",
    "update.partial_success": (
        "Actualización completada con algunos fallos en tareas post-generación"
    ),
    "update.partial_detail": "   Algunas tareas de configuración fallaron. Ver detalles arriba.",
    "update.next_steps": "Próximos pasos:",
    "update.next_review": "   1. Revisa cambios: git diff",
    "update.next_conflicts": "   2. Verifica conflictos (archivos *.rej)",
    "update.next_test": "   3. Ejecuta pruebas: make check",
    "update.next_commit": "   4. Confirma cambios: git add . && git commit",
    "update.failed": "Actualización falló: {error}",
    "update.rollback_prompt": "¿Revertir al estado anterior?",
    "update.manual_rollback": "Reversión manual: git reset --hard {tag}",
    "update.troubleshooting": "Solución de problemas:",
    "update.troubleshoot_clean": "   - Asegúrate de tener un árbol git limpio",
    "update.troubleshoot_version": "   - Verifica que la versión/commit exista",
    "update.troubleshoot_docs": "   - Revisa documentación de Copier para problemas de actualización",
    # ── Ingress command ────────────────────────────────────────────────
    "ingress.title": "Aegis Stack - Habilitar Ingress TLS",
    "ingress.project": "Proyecto: {path}",
    "ingress.not_found": "Componente ingress no encontrado. Agregándolo primero...",
    "ingress.add_confirm": "¿Agregar componente ingress?",
    "ingress.add_failed": "Error al agregar componente ingress: {error}",
    "ingress.added": "Componente ingress agregado.",
    "ingress.tls_already": "TLS ya está habilitado en este proyecto.",
    "ingress.domain_label": "   Dominio: {domain}",
    "ingress.acme_email": "   Email ACME: {email}",
    "ingress.domain_prompt": (
        "Nombre de dominio (ej: example.com, o vacío para enrutamiento por IP)"
    ),
    "ingress.email_reuse": "Usando email existente para ACME: {email}",
    "ingress.email_prompt": "Email para notificaciones de Let's Encrypt",
    "ingress.email_required": (
        "Error: --email requerido para TLS (necesario para Let's Encrypt)"
    ),
    "ingress.tls_config": "Configuración TLS:",
    "ingress.domain_none": "   Dominio: (ninguno - enrutamiento por IP/PathPrefix)",
    "ingress.tls_confirm": "¿Habilitar TLS con esta configuración?",
    "ingress.enabling": "Habilitando TLS...",
    "ingress.updated_file": "   Actualizado: {file}",
    "ingress.created_file": "   Creado: {file}",
    "ingress.success": "¡TLS habilitado!",
    "ingress.available_at": "   Tu app estará disponible en: https://{domain}",
    "ingress.https_configured": "   HTTPS configurado con Let's Encrypt",
    "ingress.next_steps": "Próximos pasos:",
    "ingress.next_deploy": "   1. Despliega con: aegis deploy",
    "ingress.next_ports": "   2. Asegúrate de que los puertos 80 y 443 estén abiertos en tu servidor",
    "ingress.next_dns": (
        "   3. Apunta el registro DNS A de {domain} a la IP de tu servidor"
    ),
    "ingress.next_certs": "   Certificados se aprovisionarán automáticamente en la primera solicitud",
    # ── Deploy commands ────────────────────────────────────────────────
    "deploy.no_config": (
        "Sin configuración de despliegue. Ejecuta 'aegis deploy-init' primero."
    ),
    "deploy.init_saved": "Configuración de despliegue guardada en {file}",
    "deploy.init_host": "   Host: {host}",
    "deploy.init_user": "   Usuario: {user}",
    "deploy.init_path": "   Ruta: {path}",
    "deploy.init_docker_context": "   Docker Context: {context}",
    "deploy.prompt_host": "IP o hostname del servidor",
    "deploy.init_gitignore": (
        "Nota: Considera agregar .aegis/ a .gitignore para evitar confirmar config de despliegue"
    ),
    "deploy.setup_title": "Configurando servidor en {target}...",
    "deploy.checking_ssh": "Verificando conectividad SSH...",
    "deploy.adding_host_key": "Agregando servidor a known_hosts...",
    "deploy.ssh_keyscan_failed": "Error al escanear clave SSH del host: {error}",
    "deploy.ssh_failed": "Conexión SSH falló: {error}",
    "deploy.copying_script": "Copiando script de configuración al servidor...",
    "deploy.copy_failed": "Error al copiar script de configuración",
    "deploy.running_setup": "Ejecutando configuración del servidor (puede tardar unos minutos)...",
    "deploy.setup_failed": "Configuración del servidor falló",
    "deploy.setup_script_missing": "Script de configuración del servidor no encontrado: {path}",
    "deploy.setup_script_hint": (
        "Asegúrate de que tu proyecto fue creado con el componente ingress."
    ),
    "deploy.setup_complete": "¡Configuración del servidor completada!",
    "deploy.setup_verify": "Verificando instalación:",
    "deploy.setup_verify_docker": "  Docker: {version}",
    "deploy.setup_verify_compose": "  Docker Compose: {version}",
    "deploy.setup_verify_uv": "  uv: {version}",
    "deploy.setup_verify_app_dir": "  Directorio de app: {path}",
    "deploy.setup_next": "Siguiente: Ejecuta 'aegis deploy' para desplegar tu aplicación",
    "deploy.deploying": "Desplegando en {host}...",
    "deploy.creating_backup": "Creando respaldo {timestamp}...",
    "deploy.backup_failed": "Error al crear respaldo: {error}",
    "deploy.backup_db": "Respaldando base de datos PostgreSQL...",
    "deploy.backup_db_failed": (
        "Advertencia: Respaldo de base de datos falló, continuando sin él"
    ),
    "deploy.backup_created": "Respaldo creado: {timestamp}",
    "deploy.backup_pruned": "Respaldo antiguo eliminado: {name}",
    "deploy.no_existing": "Sin despliegue existente, omitiendo respaldo",
    "deploy.syncing": "Sincronizando archivos al servidor...",
    "deploy.mkdir_failed": "Error al crear directorio remoto '{path}'",
    "deploy.sync_failed": "Error al sincronizar archivos",
    "deploy.copying_env": "Copiando {file} al servidor como .env...",
    "deploy.env_copy_failed": "Error al copiar archivo .env",
    "deploy.stopping": "Deteniendo servicios existentes...",
    "deploy.building": "Construyendo e iniciando servicios en servidor...",
    "deploy.start_failed": "Error al iniciar servicios",
    "deploy.auto_rollback": "Revirtiendo automáticamente a versión anterior...",
    "deploy.health_waiting": "Esperando estabilización de contenedores...",
    "deploy.health_attempt": "Verificación de salud intento {n}/{total}...",
    "deploy.health_passed": "Verificación de salud aprobada",
    "deploy.health_retry": "Verificación de salud falló, reintentando en {interval}s...",
    "deploy.health_all_failed": "Todas las verificaciones de salud fallaron",
    "deploy.rolled_back": "Revertido a respaldo {timestamp}",
    "deploy.rollback_failed": "¡Reversión falló! Intervención manual requerida.",
    "deploy.health_failed_hint": (
        "Despliegue completado pero verificación de salud falló. Revisa logs con: aegis deploy-logs"
    ),
    "deploy.complete": "¡Despliegue completado!",
    "deploy.app_running": "   Aplicación corriendo en: http://{host}",
    "deploy.overseer": "   Dashboard Overseer: http://{host}/dashboard/",
    "deploy.view_logs": "   Ver logs: aegis deploy-logs",
    "deploy.check_status": "   Verificar estado: aegis deploy-status",
    "deploy.backup_complete": "¡Respaldo completado!",
    "deploy.creating_backup_on": "Creando respaldo en {host}...",
    "deploy.no_backups": "Sin respaldos encontrados.",
    "deploy.backups_header": "Respaldos en {host} ({count} total):",
    "deploy.col_timestamp": "Fecha/Hora",
    "deploy.col_size": "Tamaño",
    "deploy.col_database": "Base de datos",
    "deploy.rollback_hint": (
        "Revertir con: aegis deploy-rollback --backup <timestamp>"
    ),
    "deploy.no_backups_available": "Sin respaldos disponibles.",
    "deploy.rolling_back": "Revirtiendo a respaldo {backup} en {host}...",
    "deploy.rollback_not_found": "Respaldo no encontrado: {timestamp}",
    "deploy.rollback_stopping": "Deteniendo servicios...",
    "deploy.rollback_restoring": "Restaurando archivos desde respaldo {timestamp}...",
    "deploy.rollback_restore_failed": "Error al restaurar archivos: {error}",
    "deploy.rollback_db": "Restaurando base de datos...",
    "deploy.rollback_pg_wait": "Esperando que PostgreSQL esté listo...",
    "deploy.rollback_pg_timeout": (
        "PostgreSQL no quedó listo, intentando restauración de todas formas"
    ),
    "deploy.rollback_db_failed": "Advertencia: Restauración de base de datos falló",
    "deploy.rollback_starting": "Iniciando servicios...",
    "deploy.rollback_start_failed": "Error al iniciar servicios tras reversión",
    "deploy.rollback_complete": "¡Reversión completada!",
    "deploy.rollback_failed_final": "¡Reversión falló!",
    "deploy.status_header": "Estado de servicios en {host}:",
    "deploy.stop_stopping": "Deteniendo servicios...",
    "deploy.stop_success": "Servicios detenidos",
    "deploy.stop_failed": "Error al detener servicios",
    "deploy.restart_restarting": "Reiniciando servicios...",
    "deploy.restart_success": "Servicios reiniciados",
    "deploy.restart_failed": "Error al reiniciar servicios",
}
