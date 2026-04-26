"""Japanese locale — 日本語メッセージ定義."""

MESSAGES: dict[str, str] = {
    # ── バリデーション ─────────────────────────────────────────────────
    "validation.invalid_name": (
        "プロジェクト名が不正です。英字・数字・ハイフン・アンダースコアのみ使用可能です。"
    ),
    "validation.reserved_name": "「{name}」は予約名のため使用できません。",
    "validation.name_too_long": "プロジェクト名が長すぎます。最大50文字です。",
    "validation.invalid_python": (
        "Python バージョン「{version}」は不正です。対応バージョン：{supported}"
    ),
    "validation.unknown_service": "不明なサービス：{name}",
    "validation.unknown_services": "不明なサービス：{names}",
    "validation.unknown_component": "不明なコンポーネント：{name}",
    # ── init コマンド ──────────────────────────────────────────────────
    "init.title": "Aegis Stack プロジェクト初期化",
    "init.location": "パス：",
    "init.template_version": "テンプレートバージョン：",
    "init.dir_exists": "ディレクトリ「{path}」は既に存在します",
    "init.dir_exists_hint": "--force で上書きするか、別の名前を指定してください",
    "init.overwriting": "既存ディレクトリを上書き中：{path}",
    "init.services_require": "サービスに必要なコンポーネント：{components}",
    "init.compat_errors": "サービスとコンポーネントの互換性エラー：",
    "init.suggestion_add": "提案：不足コンポーネントを追加 --components {components}",
    "init.suggestion_remove": (
        "または --components を外してサービスの依存を自動追加させてください。"
    ),
    "init.suggestion_interactive": (
        "対話モードを使えば、依存関係を自動で解決できます。"
    ),
    "init.auto_detected_scheduler": ("自動検出：スケジューラは {backend} で永続化"),
    "init.auto_added_deps": "依存を自動追加：{deps}",
    "init.auto_added_by_services": "サービスにより自動追加：",
    "init.required_by": "（{services} が必要とするコンポーネント）",
    "init.config_title": "プロジェクト設定",
    "init.config_name": "名前：",
    "init.config_core": "コア：",
    "init.config_infra": "インフラ：",
    "init.config_services": "サービス：",
    "init.component_files": "コンポーネントファイル：",
    "init.entrypoints": "エントリーポイント：",
    "init.worker_queues": "ワーカーキュー：",
    "init.dependencies": "インストール予定の依存パッケージ：",
    "init.confirm_create": "このプロジェクトを作成しますか？",
    "init.cancelled": "プロジェクト作成をキャンセルしました",
    "init.removing_dir": "既存ディレクトリを削除中：{path}",
    "init.creating": "プロジェクトを作成中：{name}",
    "init.error": "プロジェクト作成エラー：{error}",
    # ── 対話モード：セクション見出し ───────────────────────────────────
    "interactive.component_selection": "コンポーネント選択",
    "interactive.service_selection": "サービス選択",
    "interactive.core_included": (
        "コアコンポーネント（{components}）は自動的に含まれます"
    ),
    "interactive.infra_header": "インフラコンポーネント：",
    "interactive.services_intro": (
        "サービスはアプリケーションにビジネスロジック機能を提供します。"
    ),
    # ── コンポーネント説明 ──────────────────────────────────────────────
    "component.backend": "FastAPI バックエンドサーバー",
    "component.frontend": "Flet フロントエンドインターフェース",
    "component.redis": "Redis キャッシュ＆メッセージブローカー",
    "component.worker": "バックグラウンドタスク処理（arq・Dramatiq・TaskIQ）",
    "component.scheduler": "定期タスク実行基盤",
    "component.database": "SQLModel ORM 付きデータベース（SQLite / PostgreSQL）",
    "component.ingress": "Traefik リバースプロキシ＆ロードバランサー",
    "component.observability": "Logfire による監視・トレース・メトリクス",
    # ── サービス説明 ────────────────────────────────────────────────────
    "service.auth": "JWT トークンによるユーザー認証・認可",
    "service.ai": "マルチフレームワーク対応 AI チャットボットサービス",
    "service.comms": "メール・SMS・音声のコミュニケーションサービス",
    # ── 対話モード：コンポーネントプロンプト ────────────────────────────
    "interactive.add_prompt": "{description} を追加しますか？",
    "interactive.add_with_redis": "{description} を追加しますか？（Redis も自動追加）",
    "interactive.worker_configured": "ワーカー（{backend} バックエンド）を設定済み",
    # ── 対話モード：スケジューラ ────────────────────────────────────────
    "interactive.scheduler_persistence": "スケジューラの永続化：",
    "interactive.persist_prompt": (
        "ジョブを永続化しますか？（ジョブ履歴の保存、再起動後の復旧が可能になります）"
    ),
    "interactive.scheduler_db_configured": "スケジューラ + {engine} データベース設定済み",
    "interactive.bonus_backup": "ボーナス：データベースバックアップジョブを追加",
    "interactive.backup_desc": (
        "毎日 2:00 AM にデータベースをバックアップするジョブを含みます"
    ),
    # ── 対話モード：データベースエンジン ────────────────────────────────
    "interactive.db_engine_label": "{context} データベースエンジン：",
    "interactive.db_select": "データベースエンジンを選択：",
    "interactive.db_sqlite": "SQLite — シンプルなファイルベース（開発向け）",
    "interactive.db_postgres": ("PostgreSQL — 本番対応、マルチコンテナ対応"),
    "interactive.db_reuse": "既に選択済みのデータベースを使用：{engine}",
    # ── 対話モード：ワーカーバックエンド ────────────────────────────────
    "interactive.worker_label": "ワーカーバックエンド：",
    "interactive.worker_select": "ワーカーバックエンドを選択：",
    "interactive.worker_arq": "arq — 非同期・軽量（デフォルト）",
    "interactive.worker_dramatiq": (
        "Dramatiq — プロセスベース、CPU 負荷の高い処理に最適"
    ),
    "interactive.worker_taskiq": (
        "TaskIQ — 非同期、フレームワーク型でキュー別ブローカー対応"
    ),
    # ── 対話モード：認証 ───────────────────────────────────────────────
    "interactive.auth_header": "認証サービス：",
    "interactive.auth_level_label": "認証レベル：",
    "interactive.auth_select": "認証の種類を選択してください：",
    "interactive.auth_basic": "ベーシック — メール＆パスワードログイン",
    "interactive.auth_rbac": "ロール付き — ＋ロールベースアクセス制御（実験的）",
    "interactive.auth_org": "組織付き — ＋マルチテナント対応（実験的）",
    "interactive.auth_selected": "認証レベルを選択：{level}",
    "interactive.auth_db_required": "データベースが必要：",
    "interactive.auth_db_reason": (
        "認証にはユーザー情報を保存するデータベースが必要です"
    ),
    "interactive.auth_db_details": "（ユーザーアカウント、セッション、JWT トークン）",
    "interactive.auth_db_already": "データベースコンポーネントは選択済みです",
    "interactive.auth_db_confirm": "データベースコンポーネントを追加しますか？",
    "interactive.auth_cancelled": "認証サービスをキャンセルしました",
    "interactive.auth_db_configured": "認証 + データベース設定済み",
    # ── 対話モード：AI サービス ─────────────────────────────────────────
    "interactive.ai_header": "AI ＆機械学習サービス：",
    "interactive.ai_framework_label": "AI フレームワーク選択：",
    "interactive.ai_framework_intro": "AI フレームワークを選んでください：",
    "interactive.ai_pydanticai": (
        "PydanticAI — 型安全で Python らしい AI フレームワーク（推奨）"
    ),
    "interactive.ai_langchain": (
        "LangChain — 豊富なインテグレーションを備えた人気フレームワーク"
    ),
    "interactive.ai_use_pydanticai": "PydanticAI を使用しますか？（推奨）",
    "interactive.ai_selected_framework": "選択されたフレームワーク：{framework}",
    "interactive.ai_tracking_context": "AI 利用状況トラッキング",
    "interactive.ai_tracking_label": "LLM 利用状況トラッキング：",
    "interactive.ai_tracking_prompt": (
        "利用状況トラッキングを有効にしますか？（トークン数、コスト、会話履歴）"
    ),
    "interactive.ai_sync_label": "LLM カタログ同期：",
    "interactive.ai_sync_desc": (
        "同期すると OpenRouter/LiteLLM API から最新モデル情報を取得します"
    ),
    "interactive.ai_sync_time": ("ネットワーク接続が必要で、約30〜60秒かかります"),
    "interactive.ai_sync_prompt": "プロジェクト生成時に LLM カタログを同期しますか？",
    "interactive.ai_sync_will": "プロジェクト生成後に LLM カタログを同期します",
    "interactive.ai_sync_skipped": (
        "LLM 同期をスキップ — 静的フィクスチャデータが使用されます"
    ),
    "interactive.ai_provider_label": "AI プロバイダー選択：",
    "interactive.ai_provider_intro": (
        "利用する AI プロバイダーを選択してください（複数選択可）"
    ),
    "interactive.ai_provider_options": "プロバイダー一覧：",
    "interactive.ai_provider_recommended": "（推奨）",
    "interactive.ai_provider.openai": "OpenAI — GPT モデル（有料）",
    "interactive.ai_provider.anthropic": "Anthropic — Claude モデル（有料）",
    "interactive.ai_provider.google": "Google — Gemini モデル（無料枠あり）",
    "interactive.ai_provider.groq": "Groq — 高速推論（無料枠あり）",
    "interactive.ai_provider.mistral": "Mistral — オープンモデル（ほぼ有料）",
    "interactive.ai_provider.cohere": "Cohere — エンタープライズ向け（無料枠あり）",
    "interactive.ai_provider.ollama": "Ollama — ローカル推論（無料）",
    "interactive.ai_no_providers": (
        "プロバイダーが未選択のため、推奨デフォルトを追加します..."
    ),
    "interactive.ai_selected_providers": "選択されたプロバイダー：{providers}",
    "interactive.ai_deps_optimized": ("選択内容に合わせて依存パッケージを最適化します"),
    "interactive.ai_ollama_label": "Ollama デプロイモード：",
    "interactive.ai_ollama_intro": "Ollama の実行方法を選んでください：",
    "interactive.ai_ollama_host": (
        "ホスト — ローカルの Ollama に接続（Mac/Windows 向け）"
    ),
    "interactive.ai_ollama_docker": (
        "Docker — Docker コンテナで Ollama を実行（Linux/デプロイ向け）"
    ),
    "interactive.ai_ollama_host_prompt": (
        "ホストの Ollama に接続しますか？（Mac/Windows 推奨）"
    ),
    "interactive.ai_ollama_host_ok": (
        "Ollama は host.docker.internal:11434 に接続します"
    ),
    "interactive.ai_ollama_host_hint": "Ollama が起動していることを確認：ollama serve",
    "interactive.ai_ollama_docker_ok": (
        "Ollama サービスが docker-compose.yml に追加されます"
    ),
    "interactive.ai_ollama_docker_hint": (
        "注意：初回起動時はモデルのダウンロードに時間がかかります"
    ),
    "interactive.ai_rag_label": "RAG（検索拡張生成）：",
    "interactive.ai_rag_warning": (
        "警告：RAG は Python <3.14 が必要です（chromadb/onnxruntime の制限）"
    ),
    "interactive.ai_rag_compat_note": (
        "RAG を有効にすると Python 3.11〜3.13 が必要なプロジェクトが生成されます"
    ),
    "interactive.ai_rag_compat_prompt": (
        "Python 3.14 非互換ですが RAG を有効にしますか？"
    ),
    "interactive.ai_rag_prompt": (
        "ドキュメントインデックスとセマンティック検索の RAG を有効にしますか？"
    ),
    "interactive.ai_rag_enabled": "RAG 有効化済み（ChromaDB ベクトルストア使用）",
    "interactive.ai_voice_label": "音声（テキスト読み上げ＆音声認識）：",
    "interactive.ai_voice_prompt": (
        "音声機能を有効にしますか？（TTS / STT による音声対話）"
    ),
    "interactive.ai_voice_enabled": "音声機能有効化済み（TTS / STT 対応）",
    "interactive.ai_db_already": "データベース選択済み — 利用状況トラッキング有効",
    "interactive.ai_db_added": "データベース（{backend}）を追加（利用状況トラッキング用）",
    "interactive.ai_configured": "AI サービス設定完了",
    # ── 共通：バリデーション ────────────────────────────────────────────
    "shared.not_copier_project": "プロジェクト {path} は Copier で生成されていません。",
    "shared.copier_only": (
        "'aegis {command}' コマンドは Copier 生成プロジェクトでのみ使用できます。"
    ),
    "shared.regenerate_hint": (
        "コンポーネントを追加するには、新しいコンポーネントを含めてプロジェクトを再生成してください。"
    ),
    "shared.git_not_initialized": "プロジェクトは git リポジトリ内にありません",
    "shared.git_required": "Copier の更新には変更追跡のため git が必要です",
    "shared.git_init_hint": (
        "'aegis init' で作成されたプロジェクトは自動で git 初期化されるはずです"
    ),
    "shared.git_manual_init": (
        "手動で作成した場合は次を実行してください："
        "git init && git add . && git commit -m 'Initial commit'"
    ),
    "shared.empty_component": "コンポーネント名を空にすることはできません",
    "shared.empty_service": "サービス名を空にすることはできません",
    # ── 共通：次のステップ／レビュー ──────────────────────────────────
    "shared.next_steps": "次のステップ：",
    "shared.next_make_check": "   1. 'make check' で更新を検証",
    "shared.next_test": "   2. アプリケーションをテスト",
    "shared.next_commit": "   3. 変更をコミット：git add . && git commit",
    "shared.review_header": "変更を確認：",
    "shared.review_docker": "   git diff docker-compose.yml",
    "shared.review_pyproject": "   git diff pyproject.toml",
    "shared.operation_cancelled": "操作をキャンセルしました",
    "shared.interactive_ignores_args": (
        "警告：--interactive フラグはコンポーネント引数を無視します"
    ),
    "shared.no_components_selected": "コンポーネントが選択されていません",
    "shared.no_services_selected": "サービスが選択されていません",
    # ── add コマンド ───────────────────────────────────────────────────
    "add.title": "Aegis Stack — コンポーネント追加",
    "add.project": "プロジェクト：{path}",
    "add.error_no_args": (
        "エラー：コンポーネント引数が必要です（または --interactive を使用）"
    ),
    "add.usage_hint": "使い方：aegis add scheduler,worker",
    "add.interactive_hint": "または：aegis add --interactive",
    "add.auto_added_deps": "依存を自動追加：{deps}",
    "add.validation_failed": "コンポーネントバリデーション失敗：{error}",
    "add.load_config_failed": "プロジェクト設定の読み込み失敗：{error}",
    "add.already_enabled": "有効化済み：{components}",
    "add.all_enabled": "要求されたコンポーネントはすべて有効化済みです！",
    "add.components_to_add": "追加するコンポーネント：",
    "add.scheduler_backend": "スケジューラバックエンド：{backend}",
    "add.confirm": "これらのコンポーネントを追加しますか？",
    "add.updating": "プロジェクトを更新中...",
    "add.adding": "{component} を追加中...",
    "add.added_files": "{count} ファイル追加",
    "add.skipped_files": "{count} ファイルスキップ（既存）",
    "add.success": "コンポーネント追加完了！",
    "add.failed_component": "{component} の追加失敗：{error}",
    "add.failed": "コンポーネント追加失敗：{error}",
    "add.invalid_format": "不正なコンポーネント形式：{error}",
    "add.bracket_override": (
        "ブラケット構文 'scheduler[{engine}]' は --backend {backend} を上書きします"
    ),
    "add.invalid_scheduler_backend": "不正なスケジューラバックエンド：'{backend}'",
    "add.valid_backends": "有効なオプション：{options}",
    "add.postgres_coming": "注意：PostgreSQL 対応は今後のリリースで追加予定です",
    "add.auto_added_db": "スケジューラ永続化のためデータベースコンポーネントを自動追加",
    # ── remove コマンド ────────────────────────────────────────────────
    "remove.title": "Aegis Stack — コンポーネント削除",
    "remove.project": "プロジェクト：{path}",
    "remove.error_no_args": (
        "エラー：コンポーネント引数が必要です（または --interactive を使用）"
    ),
    "remove.usage_hint": "使い方：aegis remove scheduler,worker",
    "remove.interactive_hint": "または：aegis remove --interactive",
    "remove.no_selected": "削除対象のコンポーネントが選択されていません",
    "remove.validation_failed": "コンポーネントバリデーション失敗：{error}",
    "remove.load_config_failed": "プロジェクト設定の読み込み失敗：{error}",
    "remove.cannot_remove_core": "コアコンポーネントは削除できません：{component}",
    "remove.not_enabled": "未有効：{components}",
    "remove.nothing_to_remove": "削除対象のコンポーネントがありません！",
    "remove.auto_remove_redis": (
        "Redis を自動削除（単独機能なし、ワーカー専用のため）"
    ),
    "remove.scheduler_persistence_warn": "重要：スケジューラ永続化に関する警告",
    "remove.scheduler_persistence_detail": (
        "スケジューラは SQLite でジョブを永続化しています。"
    ),
    "remove.scheduler_db_remains": (
        "data/scheduler.db のデータベースファイルは残ります。"
    ),
    "remove.scheduler_keep_hint": (
        "ジョブ履歴を保持：データベースコンポーネントはそのままにしてください"
    ),
    "remove.scheduler_remove_hint": (
        "すべてのデータを削除：データベースコンポーネントも一緒に削除してください"
    ),
    "remove.components_to_remove": "削除するコンポーネント：",
    "remove.warning_delete": (
        "警告：コンポーネントのファイルがプロジェクトから削除されます！"
    ),
    "remove.commit_hint": "変更を git にコミット済みか確認してください。",
    "remove.confirm": "これらのコンポーネントを削除しますか？",
    "remove.removing_all": "コンポーネントを削除中...",
    "remove.removing": "{component} を削除中...",
    "remove.removed_files": "{count} ファイル削除",
    "remove.failed_component": "{component} の削除失敗：{error}",
    "remove.success": "コンポーネント削除完了！",
    "remove.failed": "コンポーネント削除失敗：{error}",
    # ── 手動アップデーター ──────────────────────────────────────────────
    "updater.processing_files": "{count} コンポーネントファイルを処理中...",
    "updater.updating_shared": "共通テンプレートファイルを更新中...",
    "updater.running_postgen": "生成後タスクを実行中...",
    "updater.deps_synced": "依存パッケージ同期完了（uv sync）",
    "updater.code_formatted": "コード整形完了（make fix）",
    # ── プロジェクトマップ ──────────────────────────────────────────────
    "projectmap.new": "新規",
    # ── 生成後：セットアップ ───────────────────────────────────────────
    "postgen.setup_start": "プロジェクト環境をセットアップ中...",
    "postgen.deps_installing": "uv で依存パッケージをインストール中...",
    "postgen.deps_success": "依存パッケージのインストール完了",
    "postgen.deps_failed": "プロジェクト生成失敗：依存パッケージのインストールに失敗",
    "postgen.deps_failed_detail": (
        "生成されたファイルはそのまま残りますが、プロジェクトは使用できない状態です。"
    ),
    "postgen.deps_failed_hint": (
        "依存の問題（Python バージョンの互換性を確認）を修正して再試行してください。"
    ),
    "postgen.deps_warn_failed": "警告：依存パッケージのインストールに失敗",
    "postgen.deps_manual": "プロジェクト作成後に手動で 'uv sync' を実行してください",
    "postgen.deps_timeout": (
        "警告：依存インストールがタイムアウト — 手動で 'uv sync' を実行してください"
    ),
    "postgen.deps_uv_missing": "警告：PATH に uv が見つかりません",
    "postgen.deps_uv_install": "先に uv をインストール：https://github.com/astral-sh/uv",
    "postgen.deps_warn_error": "警告：依存パッケージのインストール失敗：{error}",
    "postgen.env_setup": "環境設定をセットアップ中...",
    "postgen.env_created": ".env.example から環境ファイルを作成",
    "postgen.env_exists": "環境ファイルは既に存在します",
    "postgen.env_missing": "警告：.env.example ファイルが見つかりません",
    "postgen.env_error": "警告：環境セットアップ失敗：{error}",
    "postgen.env_manual": ".env.example を .env に手動でコピーしてください",
    # ── 生成後：データベース／マイグレーション ──────────────────────────
    "postgen.db_setup": "データベーススキーマをセットアップ中...",
    "postgen.db_success": "データベーステーブルの作成完了",
    "postgen.db_alembic_missing": "警告：Alembic 設定ファイルが見つかりません：{path}",
    "postgen.db_alembic_hint": (
        "データベースマイグレーションをスキップします。"
        "設定ファイルを確認し、手動で 'alembic upgrade head' を実行してください。"
    ),
    "postgen.db_failed": "警告：データベースマイグレーションのセットアップに失敗",
    "postgen.db_manual": "プロジェクト作成後に手動で 'alembic upgrade head' を実行してください",
    "postgen.db_timeout": (
        "警告：マイグレーションがタイムアウト — 手動で 'alembic upgrade head' を実行してください"
    ),
    "postgen.db_error": "警告：マイグレーションセットアップ失敗：{error}",
    # ── 生成後：LLM フィクスチャ／同期 ─────────────────────────────────
    "postgen.llm_seeding": "LLM フィクスチャをシード中...",
    "postgen.llm_seed_success": "LLM フィクスチャのシード完了",
    "postgen.llm_seed_failed": "警告：LLM フィクスチャのシードに失敗",
    "postgen.llm_seed_manual": ("フィクスチャローダーを実行して手動でシードできます"),
    "postgen.llm_seed_timeout": "警告：LLM フィクスチャシードがタイムアウト",
    "postgen.llm_seed_error": "警告：LLM フィクスチャシード失敗：{error}",
    "postgen.llm_syncing": "外部 API から LLM カタログを同期中...",
    "postgen.llm_sync_success": "LLM カタログの同期完了",
    "postgen.llm_sync_failed": "警告：LLM カタログの同期に失敗",
    "postgen.llm_sync_manual": (
        "手動で '{slug} llm sync' を実行してカタログを更新してください"
    ),
    "postgen.llm_sync_timeout": "警告：LLM カタログ同期がタイムアウト",
    "postgen.llm_sync_error": "警告：LLM カタログ同期失敗：{error}",
    # ── 生成後：フォーマット ───────────────────────────────────────────
    "postgen.format_timeout": (
        "警告：フォーマットがタイムアウト — 手動で 'make fix' を実行してください"
    ),
    "postgen.format_error": "警告：自動フォーマットをスキップ：{error}",
    "postgen.format_error_manual": "手動で 'make fix' を実行してコードを整形してください",
    "postgen.format_start": "生成コードを自動フォーマット中...",
    "postgen.format_success": "コードフォーマット完了",
    "postgen.format_partial": (
        "一部フォーマットの問題がありますが、プロジェクトは作成しました"
    ),
    "postgen.format_manual": "残りの問題は手動で 'make fix' を実行して解決してください",
    "postgen.format_hint": "準備ができたら 'make fix' でコードを整形してください",
    "postgen.llm_sync_skipped": "LLM カタログ同期をスキップ",
    "postgen.llm_fixtures_outdated": "静的フィクスチャデータを読み込み（古い可能性あり）",
    "postgen.llm_sync_hint": "後で '{slug} llm sync' を実行して最新データを取得してください",
    "postgen.llm_fixtures_fallback": (
        "静的フィクスチャデータは利用可能ですが、古い可能性があります"
    ),
    "postgen.ready": "プロジェクトの準備完了！",
    "postgen.next_steps": "次のステップ：",
    "postgen.next_cd": "   cd {path}",
    "postgen.next_serve": "   make serve",
    "postgen.next_dashboard": "   Overseer を開く：http://localhost:8000/dashboard/",
    # ── 生成後：プロジェクトマップ ─────────────────────────────────────
    "projectmap.title": "プロジェクト構成：",
    "projectmap.components": "コンポーネント",
    "projectmap.services": "ビジネスロジック",
    "projectmap.models": "データベースモデル",
    "projectmap.cli": "CLI コマンド",
    "projectmap.entrypoints": "実行ターゲット",
    "projectmap.tests": "テストスイート",
    "projectmap.migrations": "マイグレーション",
    "projectmap.auth": "認証",
    "projectmap.ai": "AI チャット",
    "projectmap.comms": "コミュニケーション",
    "projectmap.docs": "ドキュメント",
    # ── 生成後：フッター ───────────────────────────────────────────────
    "postgen.docs_link": "ドキュメント：https://lbedner.github.io/aegis-stack",
    "postgen.star_prompt": ("Aegis Stack が役に立ったら、ぜひスターをお願いします："),
    # ── add-service コマンド ───────────────────────────────────────────
    "add_service.title": "Aegis Stack — サービス追加",
    "add_service.project": "プロジェクト：{path}",
    "add_service.error_no_args": (
        "エラー：サービス引数が必要です（または --interactive を使用）"
    ),
    "add_service.usage_hint": "使い方：aegis add-service auth,ai",
    "add_service.interactive_hint": "または：aegis add-service --interactive",
    "add_service.interactive_ignores_args": (
        "警告：--interactive フラグはサービス引数を無視します"
    ),
    "add_service.no_selected": "サービスが選択されていません",
    "add_service.already_enabled": "有効化済み：{services}",
    "add_service.all_enabled": "要求されたサービスはすべて有効化済みです！",
    "add_service.validation_failed": "サービスバリデーション失敗：{error}",
    "add_service.load_config_failed": "プロジェクト設定の読み込み失敗：{error}",
    "add_service.services_to_add": "追加するサービス：",
    "add_service.required_components": "必要なコンポーネント（自動追加）：",
    "add_service.already_have_components": (
        "必要なコンポーネントは設定済み：{components}"
    ),
    "add_service.confirm": "これらのサービスを追加しますか？",
    "add_service.adding_component": "必要なコンポーネントを追加中：{component}...",
    "add_service.failed_component": "コンポーネント {component} の追加失敗：{error}",
    "add_service.added_files": "{count} ファイル追加",
    "add_service.skipped_files": "{count} ファイルスキップ（既存）",
    "add_service.adding_service": "サービスを追加中：{service}...",
    "add_service.failed_service": "サービス {service} の追加失敗：{error}",
    "add_service.resolve_failed": "サービス依存の解決に失敗：{error}",
    "add_service.bootstrap_alembic": "Alembic 基盤をブートストラップ中...",
    "add_service.created_file": "作成：{file}",
    "add_service.generated_migration": "マイグレーション生成：{name}",
    "add_service.applying_migrations": "データベースマイグレーションを適用中...",
    "add_service.migration_failed": (
        "警告：自動マイグレーション失敗。手動で 'make migrate' を実行してください。"
    ),
    "add_service.success": "サービス追加完了！",
    "add_service.failed": "サービス追加失敗：{error}",
    "add_service.auth_setup": "Auth サービスのセットアップ：",
    "add_service.auth_create_users": "   1. テストユーザーを作成：{cmd}",
    "add_service.auth_view_routes": "   2. 認証ルートを確認：{url}",
    "add_service.ai_setup": "AI サービスのセットアップ：",
    "add_service.ai_set_provider": (
        "   1. .env に {env_var} を設定（openai, anthropic, google, groq）"
    ),
    "add_service.ai_set_api_key": "   2. プロバイダーの API キーを設定（{env_var} など）",
    "add_service.ai_test_cli": "   3. CLI でテスト：{cmd}",
    # ── remove-service コマンド ────────────────────────────────────────
    "remove_service.title": "Aegis Stack — サービス削除",
    "remove_service.project": "プロジェクト：{path}",
    "remove_service.error_no_args": (
        "エラー：サービス引数が必要です（または --interactive を使用）"
    ),
    "remove_service.usage_hint": "使い方：aegis remove-service auth,ai",
    "remove_service.interactive_hint": "または：aegis remove-service --interactive",
    "remove_service.interactive_ignores_args": (
        "警告：--interactive フラグはサービス引数を無視します"
    ),
    "remove_service.no_selected": "削除対象のサービスが選択されていません",
    "remove_service.not_enabled": "未有効：{services}",
    "remove_service.nothing_to_remove": "削除対象のサービスがありません！",
    "remove_service.validation_failed": "サービスバリデーション失敗：{error}",
    "remove_service.load_config_failed": ("プロジェクト設定の読み込み失敗：{error}"),
    "remove_service.services_to_remove": "削除するサービス：",
    "remove_service.auth_warning": "重要：Auth サービスに関する警告",
    "remove_service.auth_delete_intro": "Auth サービスを削除すると以下が削除されます：",
    "remove_service.auth_delete_endpoints": "ユーザー認証 API エンドポイント",
    "remove_service.auth_delete_models": "ユーザーモデルと認証サービス",
    "remove_service.auth_delete_jwt": "JWT トークン処理コード",
    "remove_service.auth_db_note": (
        "注意：データベーステーブルと Alembic マイグレーションは削除されません。"
    ),
    "remove_service.warning_delete": (
        "警告：サービスのファイルがプロジェクトから削除されます！"
    ),
    "remove_service.confirm": "これらのサービスを削除しますか？",
    "remove_service.removing": "サービスを削除中：{service}...",
    "remove_service.failed_service": "サービス {service} の削除失敗：{error}",
    "remove_service.removed_files": "{count} ファイル削除",
    "remove_service.success": "サービス削除完了！",
    "remove_service.failed": "サービス削除失敗：{error}",
    "remove_service.deps_not_removed": (
        "注意：サービスの依存（データベースなど）は削除されていません。"
    ),
    "remove_service.deps_remove_hint": (
        "'aegis remove <component>' でコンポーネントを個別に削除してください。"
    ),
    # ── version コマンド ──────────────────────────────────────────────
    "version.info": "Aegis Stack CLI v{version}",
    # ── components コマンド ───────────────────────────────────────────
    "components.core_title": "コアコンポーネント",
    "components.backend_desc": (
        "  backend      - FastAPI バックエンドサーバー（常に含まれます）"
    ),
    "components.frontend_desc": (
        "  frontend     - Flet フロントエンドインターフェース（常に含まれます）"
    ),
    "components.infra_title": "インフラコンポーネント",
    "components.requires": "必須：{deps}",
    "components.recommends": "推奨：{deps}",
    "components.usage_hint": (
        "'aegis init PROJECT_NAME --components redis,worker' でコンポーネントを選択"
    ),
    # ── services コマンド ──────────────────────────────────────────────
    "services.title": "利用可能なサービス",
    "services.type_auth": "認証サービス",
    "services.type_payment": "決済サービス",
    "services.type_ai": "AI ＆機械学習サービス",
    "services.type_notification": "通知サービス",
    "services.type_analytics": "分析サービス",
    "services.type_storage": "ストレージサービス",
    "services.requires_components": "必須コンポーネント：{deps}",
    "services.recommends_components": "推奨コンポーネント：{deps}",
    "services.requires_services": "必須サービス：{deps}",
    "services.none_available": "  利用可能なサービスはまだありません。",
    "services.usage_hint": (
        "'aegis init PROJECT_NAME --services auth' でサービスを追加"
    ),
    # ── update コマンド ───────────────────────────────────────────────
    "update.title": "Aegis Stack — テンプレート更新",
    "update.not_copier": "プロジェクト {path} は Copier で生成されていません。",
    "update.copier_only": (
        "'aegis update' コマンドは Copier 生成プロジェクトでのみ使用できます。"
    ),
    "update.need_regen": "v0.2.0 以前に生成されたプロジェクトは再生成が必要です。",
    "update.project": "プロジェクト：{path}",
    "update.commit_or_stash": (
        "'aegis update' 実行前に変更をコミットまたはスタッシュしてください。"
    ),
    "update.clean_required": (
        "Copier は安全にマージするためクリーンな git ツリーが必要です。"
    ),
    "update.git_clean": "git ツリーはクリーンです",
    "update.dirty_tree": "git ツリーに未コミットの変更があります",
    "update.changelog_breaking": "破壊的変更：",
    "update.changelog_features": "新機能：",
    "update.changelog_fixes": "バグ修正：",
    "update.changelog_other": "その他の変更：",
    "update.current_commit": "   現在：{commit}...",
    "update.target_commit": "   目標：{commit}...",
    "update.unknown_version": "警告：現在のテンプレートバージョンを特定できません",
    "update.untagged_commit": (
        "プロジェクトはタグなしコミットから生成された可能性があります"
    ),
    "update.custom_template": "カスタムテンプレート使用（{source}）：{path}",
    "update.version_info": "バージョン情報：",
    "update.current_cli": "   現在の CLI：      {version}",
    "update.current_template": "   現在のテンプレート：{version}",
    "update.current_template_commit": "   現在のテンプレート：{commit}...（コミット）",
    "update.current_template_unknown": "   現在のテンプレート：不明",
    "update.target_template": "   目標テンプレート：  {version}",
    "update.already_at_version": "プロジェクトは既に指定バージョンです",
    "update.already_at_commit": "プロジェクトは既に目標コミットです",
    "update.downgrade_blocked": "ダウングレード非対応",
    "update.downgrade_reason": (
        "Copier は古いテンプレートバージョンへのダウングレードに対応していません。"
    ),
    "update.changelog": "変更履歴：",
    "update.dry_run": "ドライランモード — 変更は適用されません",
    "update.dry_run_hint": "更新を適用するには次を実行：",
    "update.confirm": "この更新を適用しますか？",
    "update.cancelled": "更新をキャンセルしました",
    "update.creating_backup": "バックアップポイントを作成中...",
    "update.backup_created": "   バックアップ作成：{tag}",
    "update.backup_failed": "バックアップポイントを作成できませんでした",
    "update.updating": "プロジェクトを更新中...",
    "update.updating_to": "テンプレートバージョン {version} に更新中",
    "update.moved_files": "   ネストされたディレクトリから {count} ファイルを移動",
    "update.synced_files": "   {count} テンプレート変更を同期",
    "update.merge_conflicts": (
        "   {count} ファイルにマージコンフリクトがあります（<<<<<<< を検索して解決）："
    ),
    "update.running_postgen": "生成後タスクを実行中...",
    "update.version_updated": "   __aegis_version__ を {version} に更新",
    "update.success": "更新完了！",
    "update.partial_success": ("更新完了（一部の生成後タスクが失敗）"),
    "update.partial_detail": "   一部のセットアップタスクが失敗しました。上記の詳細を確認してください。",
    "update.next_steps": "次のステップ：",
    "update.next_review": "   1. 変更を確認：git diff",
    "update.next_conflicts": "   2. コンフリクトを確認（*.rej ファイル）",
    "update.next_test": "   3. テストを実行：make check",
    "update.next_commit": "   4. 変更をコミット：git add . && git commit",
    "update.failed": "更新失敗：{error}",
    "update.rollback_prompt": "以前の状態にロールバックしますか？",
    "update.manual_rollback": "手動ロールバック：git reset --hard {tag}",
    "update.troubleshooting": "トラブルシューティング：",
    "update.troubleshoot_clean": "   - git ツリーがクリーンか確認してください",
    "update.troubleshoot_version": "   - バージョン/コミットが存在するか確認してください",
    "update.troubleshoot_docs": "   - 更新の問題については Copier ドキュメントを参照してください",
    # ── ingress コマンド ───────────────────────────────────────────────
    "ingress.title": "Aegis Stack — Ingress TLS 有効化",
    "ingress.project": "プロジェクト：{path}",
    "ingress.not_found": "Ingress コンポーネントが見つかりません。先に追加します...",
    "ingress.add_confirm": "Ingress コンポーネントを追加しますか？",
    "ingress.add_failed": "Ingress コンポーネントの追加失敗：{error}",
    "ingress.added": "Ingress コンポーネント追加完了。",
    "ingress.tls_already": "このプロジェクトでは TLS は既に有効です。",
    "ingress.domain_label": "   ドメイン：{domain}",
    "ingress.acme_email": "   ACME メール：{email}",
    "ingress.domain_prompt": (
        "ドメイン名（例：example.com、IP ベースルーティングの場合は空欄）"
    ),
    "ingress.email_reuse": "既存のメールを ACME に使用：{email}",
    "ingress.email_prompt": "Let's Encrypt 通知用メールアドレス",
    "ingress.email_required": (
        "エラー：TLS には --email が必要です（Let's Encrypt に必要）"
    ),
    "ingress.tls_config": "TLS 設定：",
    "ingress.domain_none": "   ドメイン：（なし — IP/PathPrefix ルーティング）",
    "ingress.tls_confirm": "この設定で TLS を有効にしますか？",
    "ingress.enabling": "TLS を有効化中...",
    "ingress.updated_file": "   更新：{file}",
    "ingress.created_file": "   作成：{file}",
    "ingress.success": "TLS 有効化完了！",
    "ingress.available_at": "   アプリの URL：https://{domain}",
    "ingress.https_configured": "   Let's Encrypt で HTTPS が設定しました",
    "ingress.next_steps": "次のステップ：",
    "ingress.next_deploy": "   1. デプロイ：aegis deploy",
    "ingress.next_ports": "   2. サーバーのポート 80 と 443 を開放してください",
    "ingress.next_dns": (
        "   3. {domain} の DNS A レコードをサーバー IP に向けてください"
    ),
    "ingress.next_certs": "   証明書は初回リクエスト時に自動プロビジョニングされます",
    # ── deploy コマンド ────────────────────────────────────────────────
    "deploy.no_config": (
        "デプロイ設定が見つかりません。先に 'aegis deploy-init' を実行してください。"
    ),
    "deploy.init_saved": "デプロイ設定を保存：{file}",
    "deploy.init_host": "   ホスト：{host}",
    "deploy.init_user": "   ユーザー：{user}",
    "deploy.init_path": "   パス：{path}",
    "deploy.init_docker_context": "   Docker コンテキスト：{context}",
    "deploy.prompt_host": "サーバーの IP またはホスト名",
    "deploy.init_gitignore": (
        "注意：デプロイ設定のコミットを避けるため .aegis/ を .gitignore に追加検討してください"
    ),
    "deploy.setup_title": "サーバー {target} をセットアップ中...",
    "deploy.checking_ssh": "SSH 接続を確認中...",
    "deploy.adding_host_key": "サーバーを known_hosts に追加中...",
    "deploy.ssh_keyscan_failed": "SSH ホストキーの取得失敗：{error}",
    "deploy.ssh_failed": "SSH 接続失敗：{error}",
    "deploy.copying_script": "セットアップスクリプトをサーバーにコピー中...",
    "deploy.copy_failed": "セットアップスクリプトのコピー失敗",
    "deploy.running_setup": "サーバーセットアップを実行中（数分かかる場合があります）...",
    "deploy.setup_failed": "サーバーセットアップ失敗",
    "deploy.setup_script_missing": "サーバーセットアップスクリプトが見つかりません：{path}",
    "deploy.setup_script_hint": (
        "プロジェクトが Ingress コンポーネント付きで作成されたか確認してください。"
    ),
    "deploy.setup_complete": "サーバーセットアップ完了！",
    "deploy.setup_verify": "インストール確認：",
    "deploy.setup_verify_docker": "  Docker：{version}",
    "deploy.setup_verify_compose": "  Docker Compose：{version}",
    "deploy.setup_verify_uv": "  uv：{version}",
    "deploy.setup_verify_app_dir": "  アプリディレクトリ：{path}",
    "deploy.setup_next": "次に 'aegis deploy' でアプリケーションをデプロイしてください",
    "deploy.deploying": "{host} にデプロイ中...",
    "deploy.creating_backup": "バックアップ {timestamp} を作成中...",
    "deploy.backup_failed": "バックアップ作成失敗：{error}",
    "deploy.backup_db": "PostgreSQL データベースをバックアップ中...",
    "deploy.backup_db_failed": (
        "警告：データベースバックアップ失敗、バックアップなしで続行"
    ),
    "deploy.backup_created": "バックアップ作成：{timestamp}",
    "deploy.backup_pruned": "古いバックアップを削除：{name}",
    "deploy.no_existing": "既存のデプロイが見つかりません、バックアップをスキップ",
    "deploy.syncing": "ファイルをサーバーに同期中...",
    "deploy.mkdir_failed": "リモートディレクトリ '{path}' の作成失敗",
    "deploy.sync_failed": "ファイル同期失敗",
    "deploy.copying_env": "{file} を .env としてサーバーにコピー中...",
    "deploy.env_copy_failed": ".env ファイルのコピー失敗",
    "deploy.stopping": "既存サービスを停止中...",
    "deploy.building": "サーバーでサービスをビルド＆起動中...",
    "deploy.start_failed": "サービスの起動失敗",
    "deploy.auto_rollback": "前のバージョンに自動ロールバック中...",
    "deploy.health_waiting": "コンテナの安定化を待機中...",
    "deploy.health_attempt": "ヘルスチェック {n}/{total} 回目...",
    "deploy.health_passed": "ヘルスチェック合格",
    "deploy.health_retry": "ヘルスチェック失敗、{interval} 秒後に再試行...",
    "deploy.health_all_failed": "すべてのヘルスチェックが失敗",
    "deploy.rolled_back": "バックアップ {timestamp} にロールバック完了",
    "deploy.rollback_failed": "ロールバック失敗！手動対応が必要です。",
    "deploy.health_failed_hint": (
        "デプロイ完了但しヘルスチェック失敗。ログを確認：aegis deploy-logs"
    ),
    "deploy.complete": "デプロイ完了！",
    "deploy.app_running": "   アプリケーション：http://{host}",
    "deploy.overseer": "   Overseer ダッシュボード：http://{host}/dashboard/",
    "deploy.view_logs": "   ログ確認：aegis deploy-logs",
    "deploy.check_status": "   ステータス確認：aegis deploy-status",
    "deploy.backup_complete": "バックアップ完了！",
    "deploy.creating_backup_on": "{host} でバックアップを作成中...",
    "deploy.no_backups": "バックアップが見つかりません。",
    "deploy.backups_header": "{host} のバックアップ（合計 {count} 件）：",
    "deploy.col_timestamp": "タイムスタンプ",
    "deploy.col_size": "サイズ",
    "deploy.col_database": "データベース",
    "deploy.rollback_hint": (
        "ロールバック：aegis deploy-rollback --backup <timestamp>"
    ),
    "deploy.no_backups_available": "利用可能なバックアップがありません。",
    "deploy.rolling_back": "{host} でバックアップ {backup} にロールバック中...",
    "deploy.rollback_not_found": "バックアップが見つかりません：{timestamp}",
    "deploy.rollback_stopping": "サービスを停止中...",
    "deploy.rollback_restoring": "バックアップ {timestamp} からファイルを復元中...",
    "deploy.rollback_restore_failed": "ファイル復元失敗：{error}",
    "deploy.rollback_db": "データベースを復元中...",
    "deploy.rollback_pg_wait": "PostgreSQL の準備完了を待機中...",
    "deploy.rollback_pg_timeout": (
        "PostgreSQL の準備が完了しませんでした、復元を試行します"
    ),
    "deploy.rollback_db_failed": "警告：データベース復元失敗",
    "deploy.rollback_starting": "サービスを起動中...",
    "deploy.rollback_start_failed": "ロールバック後のサービス起動失敗",
    "deploy.rollback_complete": "ロールバック完了！",
    "deploy.rollback_failed_final": "ロールバック失敗！",
    "deploy.status_header": "{host} のサービスステータス：",
    "deploy.stop_stopping": "サービスを停止中...",
    "deploy.stop_success": "サービス停止完了",
    "deploy.stop_failed": "サービス停止失敗",
    "deploy.restart_restarting": "サービスを再起動中...",
    "deploy.restart_success": "サービス再起動完了",
    "deploy.restart_failed": "サービス再起動失敗",
}
