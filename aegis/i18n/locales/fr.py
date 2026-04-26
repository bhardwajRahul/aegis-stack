"""French locale — Définitions des messages en français."""

MESSAGES: dict[str, str] = {
    # ── Validation ─────────────────────────────────────────────────────
    "validation.invalid_name": (
        "Nom de projet invalide. Seuls les lettres, chiffres, tirets "
        "et underscores sont autorisés."
    ),
    "validation.reserved_name": "« {name} » est un nom réservé.",
    "validation.name_too_long": ("Nom de projet trop long. Maximum 50 caractères."),
    "validation.invalid_python": (
        "Version Python invalide « {version} ». Doit être l'une de : {supported}"
    ),
    "validation.unknown_service": "Service inconnu : {name}",
    "validation.unknown_services": "Services inconnus : {names}",
    "validation.unknown_component": "Composant inconnu : {name}",
    # ── Init command ───────────────────────────────────────────────────
    "init.title": "Initialisation du projet Aegis Stack",
    "init.location": "Emplacement :",
    "init.template_version": "Version du modèle :",
    "init.dir_exists": "Le répertoire « {path} » existe déjà",
    "init.dir_exists_hint": "Utilisez --force pour écraser ou choisissez un autre nom",
    "init.overwriting": "Écrasement du répertoire existant : {path}",
    "init.services_require": "Les services nécessitent les composants : {components}",
    "init.compat_errors": "Erreurs de compatibilité service-composant :",
    "init.suggestion_add": (
        "Suggestion : ajoutez les composants manquants --components {components}"
    ),
    "init.suggestion_remove": (
        "Ou retirez --components pour laisser les services ajouter leurs dépendances automatiquement."
    ),
    "init.suggestion_interactive": (
        "Vous pouvez aussi utiliser le mode interactif pour ajouter les dépendances automatiquement."
    ),
    "init.auto_detected_scheduler": (
        "Détecté automatiquement : Scheduler avec persistance {backend}"
    ),
    "init.auto_added_deps": "Dépendances ajoutées automatiquement : {deps}",
    "init.auto_added_by_services": "Ajouté automatiquement par les services :",
    "init.required_by": "requis par {services}",
    "init.config_title": "Configuration du projet",
    "init.config_name": "Nom :",
    "init.config_core": "Base :",
    "init.config_infra": "Infrastructure :",
    "init.config_services": "Services :",
    "init.component_files": "Fichiers des composants :",
    "init.entrypoints": "Points d'entrée :",
    "init.worker_queues": "Files d'attente du worker :",
    "init.dependencies": "Dépendances à installer :",
    "init.confirm_create": "Créer ce projet ?",
    "init.cancelled": "Création du projet annulée",
    "init.removing_dir": "Suppression du répertoire existant : {path}",
    "init.creating": "Création du projet : {name}",
    "init.error": "Erreur lors de la création du projet : {error}",
    # ── Interactive: section headers ───────────────────────────────────
    "interactive.component_selection": "Sélection des composants",
    "interactive.service_selection": "Sélection des services",
    "interactive.core_included": (
        "Composants de base ({components}) inclus automatiquement"
    ),
    "interactive.infra_header": "Composants d'infrastructure :",
    "interactive.services_intro": (
        "Les services fournissent la logique métier de votre application."
    ),
    # ── Component descriptions ──────────────────────────────────────────
    "component.backend": "Serveur backend FastAPI",
    "component.frontend": "Interface frontend Flet",
    "component.redis": "Cache Redis et courtier de messages",
    "component.worker": "Traitement de tâches en arrière-plan (arq, Dramatiq ou TaskIQ)",
    "component.scheduler": "Infrastructure de planification de tâches",
    "component.database": "Base de données avec ORM SQLModel (SQLite ou PostgreSQL)",
    "component.ingress": "Reverse proxy et répartiteur de charge Traefik",
    "component.observability": "Observabilité, traçage et métriques Logfire",
    # ── Service descriptions ────────────────────────────────────────────
    "service.auth": "Authentification et autorisation avec jetons JWT",
    "service.ai": "Service de chatbot IA avec support multi-framework",
    "service.comms": "Service de communications : e-mail, SMS et voix",
    # ── Interactive: component prompts ─────────────────────────────────
    "interactive.add_prompt": "Ajouter {description} ?",
    "interactive.add_with_redis": "Ajouter {description} ? (Redis sera ajouté automatiquement)",
    "interactive.worker_configured": "Worker configuré avec le backend {backend}",
    # ── Interactive: scheduler ─────────────────────────────────────────
    "interactive.scheduler_persistence": "Persistance du scheduler :",
    "interactive.persist_prompt": (
        "Voulez-vous persister les tâches planifiées ? "
        "(Active l'historique et la reprise après redémarrage)"
    ),
    "interactive.scheduler_db_configured": "Scheduler + base de données {engine} configurés",
    "interactive.bonus_backup": "Bonus : ajout d'une tâche de sauvegarde de la base de données",
    "interactive.backup_desc": (
        "Sauvegarde quotidienne de la base de données incluse (exécution à 2h du matin)"
    ),
    # ── Interactive: database engine ───────────────────────────────────
    "interactive.db_engine_label": "Moteur de base de données {context} :",
    "interactive.db_select": "Sélectionnez le moteur de base de données :",
    "interactive.db_sqlite": "SQLite - Simple, fichier local (adapté au développement)",
    "interactive.db_postgres": ("PostgreSQL - Production, support multi-conteneur"),
    "interactive.db_reuse": "Base de données déjà sélectionnée : {engine}",
    # ── Interactive: worker backend ────────────────────────────────────
    "interactive.worker_label": "Backend du worker :",
    "interactive.worker_select": "Sélectionnez le backend du worker :",
    "interactive.worker_arq": "arq - Async, léger (par défaut)",
    "interactive.worker_dramatiq": (
        "Dramatiq - Multi-processus, idéal pour le calcul intensif"
    ),
    "interactive.worker_taskiq": (
        "TaskIQ - Async, style framework avec brokers par file"
    ),
    # ── Interactive: auth ──────────────────────────────────────────────
    "interactive.auth_header": "Services d'authentification :",
    "interactive.auth_level_label": "Niveau d'authentification :",
    "interactive.auth_select": "Quel type d'authentification ?",
    "interactive.auth_basic": "Basique - Connexion e-mail/mot de passe",
    "interactive.auth_rbac": "Avec rôles - + contrôle d'accès par rôle (expérimental)",
    "interactive.auth_org": "Avec organisations - + support multi-tenant (expérimental)",
    "interactive.auth_selected": "Niveau d'authentification sélectionné : {level}",
    "interactive.auth_db_required": "Base de données requise :",
    "interactive.auth_db_reason": (
        "L'authentification nécessite une base de données pour le stockage des utilisateurs"
    ),
    "interactive.auth_db_details": "(comptes utilisateurs, sessions, jetons JWT)",
    "interactive.auth_db_already": "Composant base de données déjà sélectionné",
    "interactive.auth_db_confirm": "Continuer et ajouter le composant base de données ?",
    "interactive.auth_cancelled": "Service d'authentification annulé",
    "interactive.auth_db_configured": "Authentification + base de données configurées",
    # ── Interactive: AI service ────────────────────────────────────────
    "interactive.ai_header": "Services IA et Machine Learning :",
    "interactive.ai_framework_label": "Sélection du framework IA :",
    "interactive.ai_framework_intro": "Choisissez votre framework IA :",
    "interactive.ai_pydanticai": (
        "PydanticAI - Framework IA typé et Pythonic (recommandé)"
    ),
    "interactive.ai_langchain": (
        "LangChain - Framework populaire avec intégrations étendues"
    ),
    "interactive.ai_use_pydanticai": "Utiliser PydanticAI ? (recommandé)",
    "interactive.ai_selected_framework": "Framework sélectionné : {framework}",
    "interactive.ai_tracking_context": "Suivi de l'utilisation IA",
    "interactive.ai_tracking_label": "Suivi d'utilisation LLM :",
    "interactive.ai_tracking_prompt": (
        "Activer le suivi d'utilisation ? (comptage de tokens, coûts, historique des conversations)"
    ),
    "interactive.ai_sync_label": "Synchronisation du catalogue LLM :",
    "interactive.ai_sync_desc": (
        "La synchronisation récupère les dernières données depuis les API OpenRouter/LiteLLM"
    ),
    "interactive.ai_sync_time": (
        "Nécessite un accès réseau et prend environ 30 à 60 secondes"
    ),
    "interactive.ai_sync_prompt": "Synchroniser le catalogue LLM pendant la génération du projet ?",
    "interactive.ai_sync_will": "Le catalogue LLM sera synchronisé après la génération du projet",
    "interactive.ai_sync_skipped": (
        "Synchronisation LLM ignorée - des données de fixtures statiques seront disponibles"
    ),
    "interactive.ai_provider_label": "Sélection du fournisseur IA :",
    "interactive.ai_provider_intro": (
        "Choisissez les fournisseurs IA à inclure (sélection multiple possible)"
    ),
    "interactive.ai_provider_options": "Options de fournisseurs :",
    "interactive.ai_provider_recommended": "(Recommandé)",
    "interactive.ai_provider.openai": "OpenAI - Modèles GPT (Payant)",
    "interactive.ai_provider.anthropic": "Anthropic - Modèles Claude (Payant)",
    "interactive.ai_provider.google": "Google - Modèles Gemini (Offre gratuite)",
    "interactive.ai_provider.groq": "Groq - Inférence rapide (Offre gratuite)",
    "interactive.ai_provider.mistral": "Mistral - Modèles ouverts (Majoritairement payant)",
    "interactive.ai_provider.cohere": "Cohere - Orienté entreprise (Gratuit limité)",
    "interactive.ai_provider.ollama": "Ollama - Inférence locale (Gratuit)",
    "interactive.ai_no_providers": (
        "Aucun fournisseur sélectionné, ajout des valeurs par défaut recommandées..."
    ),
    "interactive.ai_selected_providers": "Fournisseurs sélectionnés : {providers}",
    "interactive.ai_deps_optimized": (
        "Les dépendances seront optimisées selon votre sélection"
    ),
    "interactive.ai_ollama_label": "Mode de déploiement Ollama :",
    "interactive.ai_ollama_intro": "Comment voulez-vous exécuter Ollama ?",
    "interactive.ai_ollama_host": (
        "Hôte - Connexion à Ollama sur votre machine (Mac/Windows)"
    ),
    "interactive.ai_ollama_docker": (
        "Docker - Exécuter Ollama dans un conteneur Docker (Linux/Déploiement)"
    ),
    "interactive.ai_ollama_host_prompt": (
        "Se connecter à Ollama sur l'hôte ? (recommandé pour Mac/Windows)"
    ),
    "interactive.ai_ollama_host_ok": (
        "Ollama se connectera à host.docker.internal:11434"
    ),
    "interactive.ai_ollama_host_hint": "Assurez-vous qu'Ollama est en cours d'exécution : ollama serve",
    "interactive.ai_ollama_docker_ok": (
        "Le service Ollama sera ajouté à docker-compose.yml"
    ),
    "interactive.ai_ollama_docker_hint": (
        "Note : le premier démarrage peut prendre du temps pour télécharger les modèles"
    ),
    "interactive.ai_rag_label": "RAG (Retrieval-Augmented Generation) :",
    "interactive.ai_rag_warning": (
        "Attention : RAG nécessite Python <3.14 (limitation chromadb/onnxruntime)"
    ),
    "interactive.ai_rag_compat_note": (
        "Activer RAG générera un projet nécessitant Python 3.11-3.13"
    ),
    "interactive.ai_rag_compat_prompt": (
        "Activer RAG malgré l'incompatibilité avec Python 3.14 ?"
    ),
    "interactive.ai_rag_prompt": (
        "Activer RAG pour l'indexation de documents et la recherche sémantique ?"
    ),
    "interactive.ai_rag_enabled": "RAG activé avec le vector store ChromaDB",
    "interactive.ai_voice_label": "Voix (Text-to-Speech et Speech-to-Text) :",
    "interactive.ai_voice_prompt": (
        "Activer les fonctionnalités vocales ? (TTS et STT pour les interactions vocales)"
    ),
    "interactive.ai_voice_enabled": "Voix activée avec support TTS et STT",
    "interactive.ai_db_already": "Base de données déjà sélectionnée - suivi d'utilisation activé",
    "interactive.ai_db_added": "Base de données ({backend}) ajoutée pour le suivi d'utilisation",
    "interactive.ai_configured": "Service IA configuré",
    # ── Shared: validation ──────────────────────────────────────────────
    "shared.not_copier_project": "Le projet dans {path} n'a pas été généré avec Copier.",
    "shared.copier_only": (
        "La commande « aegis {command} » ne fonctionne qu'avec les projets générés par Copier."
    ),
    "shared.regenerate_hint": (
        "Pour ajouter des composants, regénérez le projet avec les nouveaux composants inclus."
    ),
    "shared.git_not_initialized": "Le projet n'est pas dans un dépôt git",
    "shared.git_required": "Les mises à jour Copier nécessitent git pour le suivi des modifications",
    "shared.git_init_hint": (
        "Les projets créés avec « aegis init » devraient avoir git initialisé automatiquement"
    ),
    "shared.git_manual_init": (
        "Si vous avez créé ce projet manuellement, exécutez : "
        "git init && git add . && git commit -m 'Initial commit'"
    ),
    "shared.empty_component": "Un nom de composant vide n'est pas autorisé",
    "shared.empty_service": "Un nom de service vide n'est pas autorisé",
    # ── Shared: next steps / review ──────────────────────────────────
    "shared.next_steps": "Prochaines étapes :",
    "shared.next_make_check": "   1. Exécutez « make check » pour vérifier la mise à jour",
    "shared.next_test": "   2. Testez votre application",
    "shared.next_commit": "   3. Validez les modifications avec : git add . && git commit",
    "shared.review_header": "Examiner les modifications :",
    "shared.review_docker": "   git diff docker-compose.yml",
    "shared.review_pyproject": "   git diff pyproject.toml",
    "shared.operation_cancelled": "Opération annulée",
    "shared.interactive_ignores_args": (
        "Attention : le flag --interactive ignore les arguments de composants"
    ),
    "shared.no_components_selected": "Aucun composant sélectionné",
    "shared.no_services_selected": "Aucun service sélectionné",
    # ── Add command ──────────────────────────────────────────────────
    "add.title": "Aegis Stack - Ajout de composants",
    "add.project": "Projet : {path}",
    "add.error_no_args": (
        "Erreur : l'argument components est requis (ou utilisez --interactive)"
    ),
    "add.usage_hint": "Utilisation : aegis add scheduler,worker",
    "add.interactive_hint": "Ou : aegis add --interactive",
    "add.auto_added_deps": "Dépendances ajoutées automatiquement : {deps}",
    "add.validation_failed": "Validation des composants échouée : {error}",
    "add.load_config_failed": "Impossible de charger la configuration du projet : {error}",
    "add.already_enabled": "Déjà activé : {components}",
    "add.all_enabled": "Tous les composants demandés sont déjà activés !",
    "add.components_to_add": "Composants à ajouter :",
    "add.scheduler_backend": "Backend du scheduler : {backend}",
    "add.confirm": "Ajouter ces composants ?",
    "add.updating": "Mise à jour du projet...",
    "add.adding": "Ajout de {component}...",
    "add.added_files": "{count} fichiers ajoutés",
    "add.skipped_files": "{count} fichiers existants ignorés",
    "add.success": "Composants ajoutés !",
    "add.failed_component": "Échec de l'ajout de {component} : {error}",
    "add.failed": "Échec de l'ajout des composants : {error}",
    "add.invalid_format": "Format de composant invalide : {error}",
    "add.bracket_override": (
        "La syntaxe entre crochets « scheduler[{engine}] » remplace --backend {backend}"
    ),
    "add.invalid_scheduler_backend": "Backend de scheduler invalide : « {backend} »",
    "add.valid_backends": "Options valides : {options}",
    "add.postgres_coming": "Note : le support PostgreSQL arrive dans une prochaine version",
    "add.auto_added_db": "Composant base de données ajouté automatiquement pour la persistance du scheduler",
    # ── Remove command ────────────────────────────────────────────────
    "remove.title": "Aegis Stack - Suppression de composants",
    "remove.project": "Projet : {path}",
    "remove.error_no_args": (
        "Erreur : l'argument components est requis (ou utilisez --interactive)"
    ),
    "remove.usage_hint": "Utilisation : aegis remove scheduler,worker",
    "remove.interactive_hint": "Ou : aegis remove --interactive",
    "remove.no_selected": "Aucun composant sélectionné pour la suppression",
    "remove.validation_failed": "Validation des composants échouée : {error}",
    "remove.load_config_failed": "Impossible de charger la configuration du projet : {error}",
    "remove.cannot_remove_core": "Impossible de supprimer le composant de base : {component}",
    "remove.not_enabled": "Non activé : {components}",
    "remove.nothing_to_remove": "Aucun composant à supprimer !",
    "remove.auto_remove_redis": (
        "Suppression automatique de Redis (pas de fonctionnalité autonome, utilisé uniquement par le worker)"
    ),
    "remove.scheduler_persistence_warn": "IMPORTANT : avertissement de persistance du scheduler",
    "remove.scheduler_persistence_detail": (
        "Votre scheduler utilise SQLite pour la persistance des tâches."
    ),
    "remove.scheduler_db_remains": (
        "Le fichier de base de données data/scheduler.db sera conservé."
    ),
    "remove.scheduler_keep_hint": (
        "Pour conserver l'historique : laissez le composant base de données"
    ),
    "remove.scheduler_remove_hint": (
        "Pour tout supprimer : supprimez aussi le composant base de données"
    ),
    "remove.components_to_remove": "Composants à supprimer :",
    "remove.warning_delete": (
        "ATTENTION : les fichiers des composants seront SUPPRIMÉS de votre projet !"
    ),
    "remove.commit_hint": "Assurez-vous d'avoir validé vos modifications dans git.",
    "remove.confirm": "Supprimer ces composants ?",
    "remove.removing_all": "Suppression des composants...",
    "remove.removing": "Suppression de {component}...",
    "remove.removed_files": "{count} fichiers supprimés",
    "remove.failed_component": "Échec de la suppression de {component} : {error}",
    "remove.success": "Composants supprimés !",
    "remove.failed": "Échec de la suppression des composants : {error}",
    # ── Manual updater ─────────────────────────────────────────────────
    "updater.processing_files": "Traitement de {count} fichiers de composants...",
    "updater.updating_shared": "Mise à jour des fichiers de modèle partagés...",
    "updater.running_postgen": "Exécution des tâches post-génération...",
    "updater.deps_synced": "Dépendances synchronisées (uv sync)",
    "updater.code_formatted": "Code formaté (make fix)",
    # ── Project map ──────────────────────────────────────────────────
    "projectmap.new": "NOUVEAU",
    # ── Post-generation: setup tasks ──────────────────────────────────
    "postgen.setup_start": "Configuration de l'environnement du projet...",
    "postgen.deps_installing": "Installation des dépendances avec uv...",
    "postgen.deps_success": "Dépendances installées",
    "postgen.deps_failed": "Échec de la génération du projet : l'installation des dépendances a échoué",
    "postgen.deps_failed_detail": (
        "Les fichiers du projet sont en place, mais le projet n'est pas utilisable."
    ),
    "postgen.deps_failed_hint": (
        "Corrigez le problème de dépendances (vérifiez la compatibilité Python) et réessayez."
    ),
    "postgen.deps_warn_failed": "Attention : l'installation des dépendances a échoué",
    "postgen.deps_manual": "Exécutez « uv sync » manuellement après la création du projet",
    "postgen.deps_timeout": (
        "Attention : délai d'installation des dépendances dépassé - exécutez « uv sync » manuellement"
    ),
    "postgen.deps_uv_missing": "Attention : uv introuvable dans le PATH",
    "postgen.deps_uv_install": "Installez d'abord uv : https://github.com/astral-sh/uv",
    "postgen.deps_warn_error": "Attention : l'installation des dépendances a échoué : {error}",
    "postgen.env_setup": "Configuration de l'environnement...",
    "postgen.env_created": "Fichier d'environnement créé depuis .env.example",
    "postgen.env_exists": "Le fichier d'environnement existe déjà",
    "postgen.env_missing": "Attention : fichier .env.example introuvable",
    "postgen.env_error": "Attention : la configuration de l'environnement a échoué : {error}",
    "postgen.env_manual": "Copiez .env.example vers .env manuellement",
    # ── Post-generation: database/migrations ────────────────────────────
    "postgen.db_setup": "Configuration du schéma de la base de données...",
    "postgen.db_success": "Tables de la base de données créées",
    "postgen.db_alembic_missing": "Attention : fichier de configuration Alembic introuvable à {path}",
    "postgen.db_alembic_hint": (
        "Migration de la base de données ignorée. Vérifiez que le fichier de configuration "
        "existe et exécutez « alembic upgrade head » manuellement."
    ),
    "postgen.db_failed": "Attention : la configuration des migrations a échoué",
    "postgen.db_manual": "Exécutez « alembic upgrade head » manuellement après la création du projet",
    "postgen.db_timeout": (
        "Attention : délai de configuration des migrations dépassé - exécutez « alembic upgrade head » manuellement"
    ),
    "postgen.db_error": "Attention : la configuration des migrations a échoué : {error}",
    # ── Post-generation: LLM fixtures/sync ────────────────────────────
    "postgen.llm_seeding": "Chargement des fixtures LLM...",
    "postgen.llm_seed_success": "Fixtures LLM chargées",
    "postgen.llm_seed_failed": "Attention : le chargement des fixtures LLM a échoué",
    "postgen.llm_seed_manual": (
        "Vous pouvez charger les fixtures manuellement en exécutant le chargeur de fixtures"
    ),
    "postgen.llm_seed_timeout": "Attention : délai de chargement des fixtures LLM dépassé",
    "postgen.llm_seed_error": "Attention : le chargement des fixtures LLM a échoué : {error}",
    "postgen.llm_syncing": "Synchronisation du catalogue LLM depuis les API externes...",
    "postgen.llm_sync_success": "Catalogue LLM synchronisé",
    "postgen.llm_sync_failed": "Attention : la synchronisation du catalogue LLM a échoué",
    "postgen.llm_sync_manual": (
        "Exécutez « {slug} llm sync » manuellement pour alimenter le catalogue"
    ),
    "postgen.llm_sync_timeout": "Attention : délai de synchronisation du catalogue LLM dépassé",
    "postgen.llm_sync_error": "Attention : la synchronisation du catalogue LLM a échoué : {error}",
    # ── Post-generation: formatting ───────────────────────────────────
    "postgen.format_timeout": (
        "Attention : délai de formatage dépassé - exécutez « make fix » manuellement"
    ),
    "postgen.format_error": "Attention : formatage automatique ignoré : {error}",
    "postgen.format_error_manual": "Exécutez « make fix » manuellement pour formater le code",
    "postgen.format_start": "Formatage automatique du code généré...",
    "postgen.format_success": "Formatage du code terminé",
    "postgen.format_partial": (
        "Quelques problèmes de formatage détectés, mais le projet créé"
    ),
    "postgen.format_manual": "Exécutez « make fix » manuellement pour résoudre les problèmes restants",
    "postgen.format_hint": "Exécutez « make fix » pour formater le code",
    "postgen.llm_sync_skipped": "Synchronisation du catalogue LLM ignorée",
    "postgen.llm_fixtures_outdated": "Données de fixtures statiques chargées (potentiellement obsolètes)",
    "postgen.llm_sync_hint": "Exécutez « {slug} llm sync » plus tard pour obtenir les dernières données",
    "postgen.llm_fixtures_fallback": (
        "Les données de fixtures statiques sont disponibles mais potentiellement obsolètes"
    ),
    "postgen.ready": "Projet prêt à être lancé !",
    "postgen.next_steps": "Prochaines étapes :",
    "postgen.next_cd": "   cd {path}",
    "postgen.next_serve": "   make serve",
    "postgen.next_dashboard": "   Ouvrir Overseer : http://localhost:8000/dashboard/",
    # ── Post-generation: project map ──────────────────────────────────
    "projectmap.title": "Structure du projet :",
    "projectmap.components": "Composants",
    "projectmap.services": "Logique métier",
    "projectmap.models": "Modèles de base de données",
    "projectmap.cli": "Commandes CLI",
    "projectmap.entrypoints": "Points d'exécution",
    "projectmap.tests": "Suite de tests",
    "projectmap.migrations": "Migrations",
    "projectmap.auth": "Authentification",
    "projectmap.ai": "Conversations IA",
    "projectmap.comms": "Communications",
    "projectmap.docs": "Documentation",
    # ── Post-generation: footer ───────────────────────────────────────
    "postgen.docs_link": "Docs : https://lbedner.github.io/aegis-stack",
    "postgen.star_prompt": (
        "Si Aegis Stack vous a simplifié la vie, pensez à laisser une étoile :"
    ),
    # ── Add-service command ────────────────────────────────────────────
    "add_service.title": "Aegis Stack - Ajout de services",
    "add_service.project": "Projet : {path}",
    "add_service.error_no_args": (
        "Erreur : l'argument services est requis (ou utilisez --interactive)"
    ),
    "add_service.usage_hint": "Utilisation : aegis add-service auth,ai",
    "add_service.interactive_hint": "Ou : aegis add-service --interactive",
    "add_service.interactive_ignores_args": (
        "Attention : le flag --interactive ignore les arguments de services"
    ),
    "add_service.no_selected": "Aucun service sélectionné",
    "add_service.already_enabled": "Déjà activé : {services}",
    "add_service.all_enabled": "Tous les services demandés sont déjà activés !",
    "add_service.validation_failed": "Validation des services échouée : {error}",
    "add_service.load_config_failed": "Impossible de charger la configuration du projet : {error}",
    "add_service.services_to_add": "Services à ajouter :",
    "add_service.required_components": "Composants requis (seront ajoutés automatiquement) :",
    "add_service.already_have_components": (
        "Composants requis déjà présents : {components}"
    ),
    "add_service.confirm": "Ajouter ces services ?",
    "add_service.adding_component": "Ajout du composant requis : {component}...",
    "add_service.failed_component": "Échec de l'ajout du composant {component} : {error}",
    "add_service.added_files": "{count} fichiers ajoutés",
    "add_service.skipped_files": "{count} fichiers existants ignorés",
    "add_service.adding_service": "Ajout du service : {service}...",
    "add_service.failed_service": "Échec de l'ajout du service {service} : {error}",
    "add_service.resolve_failed": "Échec de la résolution des dépendances de services : {error}",
    "add_service.bootstrap_alembic": "Initialisation de l'infrastructure Alembic...",
    "add_service.created_file": "Créé : {file}",
    "add_service.generated_migration": "Migration générée : {name}",
    "add_service.applying_migrations": "Application des migrations de base de données...",
    "add_service.migration_failed": (
        "Attention : la migration automatique a échoué. Exécutez « make migrate » manuellement."
    ),
    "add_service.success": "Services ajoutés !",
    "add_service.failed": "Échec de l'ajout des services : {error}",
    "add_service.auth_setup": "Configuration du service Auth :",
    "add_service.auth_create_users": "   1. Créer des utilisateurs de test : {cmd}",
    "add_service.auth_view_routes": "   2. Voir les routes d'authentification : {url}",
    "add_service.ai_setup": "Configuration du service IA :",
    "add_service.ai_set_provider": (
        "   1. Définir {env_var} dans .env (openai, anthropic, google, groq)"
    ),
    "add_service.ai_set_api_key": "   2. Définir la clé API du fournisseur ({env_var}, etc.)",
    "add_service.ai_test_cli": "   3. Tester avec le CLI : {cmd}",
    # ── Remove-service command ─────────────────────────────────────────
    "remove_service.title": "Aegis Stack - Suppression de services",
    "remove_service.project": "Projet : {path}",
    "remove_service.error_no_args": (
        "Erreur : l'argument services est requis (ou utilisez --interactive)"
    ),
    "remove_service.usage_hint": "Utilisation : aegis remove-service auth,ai",
    "remove_service.interactive_hint": "Ou : aegis remove-service --interactive",
    "remove_service.interactive_ignores_args": (
        "Attention : le flag --interactive ignore les arguments de services"
    ),
    "remove_service.no_selected": "Aucun service sélectionné pour la suppression",
    "remove_service.not_enabled": "Non activé : {services}",
    "remove_service.nothing_to_remove": "Aucun service à supprimer !",
    "remove_service.validation_failed": "Validation des services échouée : {error}",
    "remove_service.load_config_failed": (
        "Impossible de charger la configuration du projet : {error}"
    ),
    "remove_service.services_to_remove": "Services à supprimer :",
    "remove_service.auth_warning": "IMPORTANT : avertissement concernant le service Auth",
    "remove_service.auth_delete_intro": "La suppression du service Auth entraînera la suppression de :",
    "remove_service.auth_delete_endpoints": "Points d'accès API d'authentification",
    "remove_service.auth_delete_models": "Modèle utilisateur et services d'authentification",
    "remove_service.auth_delete_jwt": "Code de gestion des jetons JWT",
    "remove_service.auth_db_note": (
        "Note : les tables de base de données et les migrations Alembic ne sont PAS supprimées."
    ),
    "remove_service.warning_delete": (
        "ATTENTION : les fichiers de services seront SUPPRIMÉS de votre projet !"
    ),
    "remove_service.confirm": "Supprimer ces services ?",
    "remove_service.removing": "Suppression du service : {service}...",
    "remove_service.failed_service": "Échec de la suppression du service {service} : {error}",
    "remove_service.removed_files": "{count} fichiers supprimés",
    "remove_service.success": "Services supprimés !",
    "remove_service.failed": "Échec de la suppression des services : {error}",
    "remove_service.deps_not_removed": (
        "Note : les dépendances de services (base de données, etc.) n'ont PAS été supprimées."
    ),
    "remove_service.deps_remove_hint": (
        "Utilisez « aegis remove <composant> » pour supprimer les composants séparément."
    ),
    # ── Version command ────────────────────────────────────────────────
    "version.info": "Aegis Stack CLI v{version}",
    # ── Components command ─────────────────────────────────────────────
    "components.core_title": "COMPOSANTS DE BASE",
    "components.backend_desc": (
        "  backend      - Serveur backend FastAPI (toujours inclus)"
    ),
    "components.frontend_desc": (
        "  frontend     - Interface frontend Flet (toujours inclus)"
    ),
    "components.infra_title": "COMPOSANTS D'INFRASTRUCTURE",
    "components.requires": "Requis : {deps}",
    "components.recommends": "Recommandé : {deps}",
    "components.usage_hint": (
        "Utilisez « aegis init NOM_PROJET --components redis,worker » pour sélectionner les composants"
    ),
    # ── Services command ───────────────────────────────────────────────
    "services.title": "SERVICES DISPONIBLES",
    "services.type_auth": "Services d'authentification",
    "services.type_payment": "Services de paiement",
    "services.type_ai": "Services IA et Machine Learning",
    "services.type_notification": "Services de notification",
    "services.type_analytics": "Services d'analyse",
    "services.type_storage": "Services de stockage",
    "services.requires_components": "Composants requis : {deps}",
    "services.recommends_components": "Composants recommandés : {deps}",
    "services.requires_services": "Services requis : {deps}",
    "services.none_available": "  Aucun service disponible pour le moment.",
    "services.usage_hint": (
        "Utilisez « aegis init NOM_PROJET --services auth » pour ajouter des services"
    ),
    # ── Update command ─────────────────────────────────────────────────
    "update.title": "Aegis Stack - Mise à jour du modèle",
    "update.not_copier": "Le projet dans {path} n'a pas été généré avec Copier.",
    "update.copier_only": (
        "La commande « aegis update » ne fonctionne qu'avec les projets générés par Copier."
    ),
    "update.need_regen": "Les projets générés avant la v0.2.0 doivent être regénérés.",
    "update.project": "Projet : {path}",
    "update.commit_or_stash": (
        "Validez ou remisez vos modifications avant d'exécuter « aegis update »."
    ),
    "update.clean_required": (
        "Copier nécessite un arbre git propre pour fusionner les modifications en toute sécurité."
    ),
    "update.git_clean": "Arbre git propre",
    "update.dirty_tree": "L'arbre git contient des modifications non validées",
    "update.changelog_breaking": "Changements incompatibles :",
    "update.changelog_features": "Nouvelles fonctionnalités :",
    "update.changelog_fixes": "Corrections de bugs :",
    "update.changelog_other": "Autres modifications :",
    "update.current_commit": "   Actuel : {commit}...",
    "update.target_commit": "   Cible :  {commit}...",
    "update.unknown_version": "Attention : impossible de déterminer la version actuelle du modèle",
    "update.untagged_commit": (
        "Le projet a peut-être été généré depuis un commit non tagué"
    ),
    "update.custom_template": "Utilisation d'un modèle personnalisé ({source}) : {path}",
    "update.version_info": "Informations de version :",
    "update.current_cli": "   CLI actuel :      {version}",
    "update.current_template": "   Modèle actuel :   {version}",
    "update.current_template_commit": "   Modèle actuel :   {commit}... (commit)",
    "update.current_template_unknown": "   Modèle actuel :   inconnu",
    "update.target_template": "   Modèle cible :    {version}",
    "update.already_at_version": "Le projet est déjà à la version demandée",
    "update.already_at_commit": "Le projet est déjà au commit cible",
    "update.downgrade_blocked": "Rétrogradation non supportée",
    "update.downgrade_reason": (
        "Copier ne supporte pas la rétrogradation vers des versions antérieures du modèle."
    ),
    "update.changelog": "Journal des modifications :",
    "update.dry_run": "MODE SIMULATION - Aucune modification ne sera appliquée",
    "update.dry_run_hint": "Pour appliquer cette mise à jour, exécutez :",
    "update.confirm": "Appliquer cette mise à jour ?",
    "update.cancelled": "Mise à jour annulée",
    "update.creating_backup": "Création d'un point de sauvegarde...",
    "update.backup_created": "   Sauvegarde créée : {tag}",
    "update.backup_failed": "Impossible de créer le point de sauvegarde",
    "update.updating": "Mise à jour du projet...",
    "update.updating_to": "Mise à jour vers la version {version} du modèle",
    "update.moved_files": "   {count} nouveaux fichiers déplacés depuis le répertoire imbriqué",
    "update.synced_files": "   {count} modifications de modèle synchronisées",
    "update.merge_conflicts": (
        "   {count} fichier(s) avec des conflits de fusion (cherchez <<<<<<< pour résoudre) :"
    ),
    "update.running_postgen": "Exécution des tâches post-génération...",
    "update.version_updated": "   __aegis_version__ mis à jour vers {version}",
    "update.success": "Mise à jour terminée !",
    "update.partial_success": (
        "Mise à jour terminée avec des échecs de tâches post-génération"
    ),
    "update.partial_detail": "   Certaines tâches de configuration ont échoué. Voir les détails ci-dessus.",
    "update.next_steps": "Prochaines étapes :",
    "update.next_review": "   1. Examiner les modifications : git diff",
    "update.next_conflicts": "   2. Vérifier les conflits (fichiers *.rej)",
    "update.next_test": "   3. Exécuter les tests : make check",
    "update.next_commit": "   4. Valider les modifications : git add . && git commit",
    "update.failed": "Mise à jour échouée : {error}",
    "update.rollback_prompt": "Revenir à l'état précédent ?",
    "update.manual_rollback": "Rollback manuel : git reset --hard {tag}",
    "update.troubleshooting": "Dépannage :",
    "update.troubleshoot_clean": "   - Assurez-vous d'avoir un arbre git propre",
    "update.troubleshoot_version": "   - Vérifiez que la version/le commit existe",
    "update.troubleshoot_docs": "   - Consultez la documentation Copier pour les problèmes de mise à jour",
    # ── Ingress command ────────────────────────────────────────────────
    "ingress.title": "Aegis Stack - Activation du TLS Ingress",
    "ingress.project": "Projet : {path}",
    "ingress.not_found": "Composant ingress introuvable. Ajout en cours...",
    "ingress.add_confirm": "Ajouter le composant ingress ?",
    "ingress.add_failed": "Échec de l'ajout du composant ingress : {error}",
    "ingress.added": "Composant ingress ajouté.",
    "ingress.tls_already": "TLS est déjà activé sur ce projet.",
    "ingress.domain_label": "   Domaine : {domain}",
    "ingress.acme_email": "   E-mail ACME : {email}",
    "ingress.domain_prompt": (
        "Nom de domaine (ex. : example.com, ou vide pour le routage par IP)"
    ),
    "ingress.email_reuse": "Utilisation de l'e-mail existant pour ACME : {email}",
    "ingress.email_prompt": "E-mail pour les notifications Let's Encrypt",
    "ingress.email_required": (
        "Erreur : --email est requis pour TLS (nécessaire pour Let's Encrypt)"
    ),
    "ingress.tls_config": "Configuration TLS :",
    "ingress.domain_none": "   Domaine : (aucun - routage par IP/PathPrefix)",
    "ingress.tls_confirm": "Activer TLS avec cette configuration ?",
    "ingress.enabling": "Activation du TLS...",
    "ingress.updated_file": "   Mis à jour : {file}",
    "ingress.created_file": "   Créé : {file}",
    "ingress.success": "TLS activé !",
    "ingress.available_at": "   Votre application sera disponible à : https://{domain}",
    "ingress.https_configured": "   HTTPS est maintenant configuré avec Let's Encrypt",
    "ingress.next_steps": "Prochaines étapes :",
    "ingress.next_deploy": "   1. Déployer avec : aegis deploy",
    "ingress.next_ports": "   2. Assurez-vous que les ports 80 et 443 sont ouverts sur votre serveur",
    "ingress.next_dns": (
        "   3. Pointez votre enregistrement DNS A pour {domain} vers l'IP de votre serveur"
    ),
    "ingress.next_certs": "   Les certificats seront provisionnés automatiquement à la première requête",
    # ── Deploy commands ────────────────────────────────────────────────
    "deploy.no_config": (
        "Aucune configuration de déploiement trouvée. Exécutez « aegis deploy-init » d'abord."
    ),
    "deploy.init_saved": "Configuration de déploiement enregistrée dans {file}",
    "deploy.init_host": "   Hôte : {host}",
    "deploy.init_user": "   Utilisateur : {user}",
    "deploy.init_path": "   Chemin : {path}",
    "deploy.init_docker_context": "   Contexte Docker : {context}",
    "deploy.prompt_host": "IP ou nom d'hôte du serveur",
    "deploy.init_gitignore": (
        "Note : pensez à ajouter .aegis/ dans .gitignore pour ne pas versionner la configuration de déploiement"
    ),
    "deploy.setup_title": "Configuration du serveur {target}...",
    "deploy.checking_ssh": "Vérification de la connectivité SSH...",
    "deploy.adding_host_key": "Ajout du serveur aux known_hosts...",
    "deploy.ssh_keyscan_failed": "Échec du scan de la clé SSH de l'hôte : {error}",
    "deploy.ssh_failed": "Connexion SSH échouée : {error}",
    "deploy.copying_script": "Copie du script de configuration vers le serveur...",
    "deploy.copy_failed": "Échec de la copie du script de configuration",
    "deploy.running_setup": "Exécution de la configuration du serveur (peut prendre quelques minutes)...",
    "deploy.setup_failed": "Configuration du serveur échouée",
    "deploy.setup_script_missing": "Script de configuration du serveur introuvable : {path}",
    "deploy.setup_script_hint": (
        "Assurez-vous que votre projet créé avec le composant ingress."
    ),
    "deploy.setup_complete": "Configuration du serveur terminée !",
    "deploy.setup_verify": "Vérification de l'installation :",
    "deploy.setup_verify_docker": "  Docker : {version}",
    "deploy.setup_verify_compose": "  Docker Compose : {version}",
    "deploy.setup_verify_uv": "  uv : {version}",
    "deploy.setup_verify_app_dir": "  Répertoire de l'application : {path}",
    "deploy.setup_next": "Ensuite : exécutez « aegis deploy » pour déployer votre application",
    "deploy.deploying": "Déploiement vers {host}...",
    "deploy.creating_backup": "Création de la sauvegarde {timestamp}...",
    "deploy.backup_failed": "Échec de la création de la sauvegarde : {error}",
    "deploy.backup_db": "Sauvegarde de la base de données PostgreSQL...",
    "deploy.backup_db_failed": (
        "Attention : la sauvegarde de la base de données a échoué, poursuite sans sauvegarde"
    ),
    "deploy.backup_created": "Sauvegarde créée : {timestamp}",
    "deploy.backup_pruned": "Ancienne sauvegarde supprimée : {name}",
    "deploy.no_existing": "Aucun déploiement existant trouvé, sauvegarde ignorée",
    "deploy.syncing": "Synchronisation des fichiers vers le serveur...",
    "deploy.mkdir_failed": "Impossible de créer le répertoire distant « {path} »",
    "deploy.sync_failed": "Échec de la synchronisation des fichiers",
    "deploy.copying_env": "Copie de {file} vers le serveur en tant que .env...",
    "deploy.env_copy_failed": "Échec de la copie du fichier .env",
    "deploy.stopping": "Arrêt des services existants...",
    "deploy.building": "Construction et démarrage des services sur le serveur...",
    "deploy.start_failed": "Échec du démarrage des services",
    "deploy.auto_rollback": "Rollback automatique vers la version précédente...",
    "deploy.health_waiting": "Attente de la stabilisation des conteneurs...",
    "deploy.health_attempt": "Vérification de santé {n}/{total}...",
    "deploy.health_passed": "Vérification de santé réussie",
    "deploy.health_retry": "Vérification de santé échouée, nouvelle tentative dans {interval}s...",
    "deploy.health_all_failed": "Toutes les vérifications de santé ont échoué",
    "deploy.rolled_back": "Rollback vers la sauvegarde {timestamp} effectué",
    "deploy.rollback_failed": "Rollback échoué ! Intervention manuelle requise.",
    "deploy.health_failed_hint": (
        "Déploiement terminé mais la vérification de santé a échoué. Consultez les logs avec : aegis deploy-logs"
    ),
    "deploy.complete": "Déploiement terminé !",
    "deploy.app_running": "   Application accessible à : http://{host}",
    "deploy.overseer": "   Tableau de bord Overseer : http://{host}/dashboard/",
    "deploy.view_logs": "   Voir les logs : aegis deploy-logs",
    "deploy.check_status": "   Vérifier le statut : aegis deploy-status",
    "deploy.backup_complete": "Sauvegarde terminée !",
    "deploy.creating_backup_on": "Création de la sauvegarde sur {host}...",
    "deploy.no_backups": "Aucune sauvegarde trouvée.",
    "deploy.backups_header": "Sauvegardes sur {host} ({count} au total) :",
    "deploy.col_timestamp": "Horodatage",
    "deploy.col_size": "Taille",
    "deploy.col_database": "Base de données",
    "deploy.rollback_hint": (
        "Rollback avec : aegis deploy-rollback --backup <horodatage>"
    ),
    "deploy.no_backups_available": "Aucune sauvegarde disponible.",
    "deploy.rolling_back": "Rollback vers la sauvegarde {backup} sur {host}...",
    "deploy.rollback_not_found": "Sauvegarde introuvable : {timestamp}",
    "deploy.rollback_stopping": "Arrêt des services...",
    "deploy.rollback_restoring": "Restauration des fichiers depuis la sauvegarde {timestamp}...",
    "deploy.rollback_restore_failed": "Échec de la restauration des fichiers : {error}",
    "deploy.rollback_db": "Restauration de la base de données...",
    "deploy.rollback_pg_wait": "Attente de la disponibilité de PostgreSQL...",
    "deploy.rollback_pg_timeout": (
        "PostgreSQL n'est pas devenu disponible, tentative de restauration malgré tout"
    ),
    "deploy.rollback_db_failed": "Attention : la restauration de la base de données a échoué",
    "deploy.rollback_starting": "Démarrage des services...",
    "deploy.rollback_start_failed": "Échec du démarrage des services après le rollback",
    "deploy.rollback_complete": "Rollback terminé !",
    "deploy.rollback_failed_final": "Rollback échoué !",
    "deploy.status_header": "Statut des services sur {host} :",
    "deploy.stop_stopping": "Arrêt des services...",
    "deploy.stop_success": "Services arrêtés",
    "deploy.stop_failed": "Échec de l'arrêt des services",
    "deploy.restart_restarting": "Redémarrage des services...",
    "deploy.restart_success": "Services redémarrés",
    "deploy.restart_failed": "Échec du redémarrage des services",
}
