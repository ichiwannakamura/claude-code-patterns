# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a best practices repository for Claude Code configuration, demonstrating patterns for skills, subagents, hooks, and commands. It serves as a reference implementation rather than an application codebase.

## Key Components

### Weather System (Example Workflow)
A demonstration of the **Command → Agent → Skills** architecture pattern:
- `/weather-orchestrator` command (`.claude/commands/weather-orchestrator.md`): Entry point that invokes the weather agent
- `weather` agent (`.claude/agents/weather.md`): Executes workflow using preloaded skills
- `weather-fetcher` skill (`.claude/skills/weather-fetcher/SKILL.md`): Instructions for fetching temperature from wttr.in API
- `weather-transformer` skill (`.claude/skills/weather-transformer/SKILL.md`): Instructions for applying transformation rules from `weather-orchestration/input.md`, writes results to `weather-orchestration/output.md`

The agent has skills preloaded via the `skills` field, providing domain knowledge for sequential execution. See `weather-orchestration/weather-orchestration-architecture.md` for the complete flow diagram.

### Skill Definition Structure
Skills in `.claude/skills/<name>/SKILL.md` use YAML frontmatter:
- `name`: Display name and `/slash-command` (defaults to directory name)
- `description`: When to invoke (recommended for auto-discovery)
- `argument-hint`: Autocomplete hint (e.g., `[issue-number]`)
- `disable-model-invocation`: Set `true` to prevent automatic invocation
- `user-invocable`: Set `false` to hide from `/` menu (background knowledge only)
- `allowed-tools`: Tools allowed without permission prompts when skill is active
- `model`: Model to use when skill is active
- `context`: Set to `fork` to run in isolated subagent context
- `agent`: Subagent type for `context: fork` (default: `general-purpose`)
- `hooks`: Lifecycle hooks scoped to this skill

### Presentation System
Any request to update, modify, or fix the presentation (`presentation/index.html`) must be handled by the `presentation-curator` agent (`.claude/agents/presentation-curator.md`). Always delegate presentation work to this agent via the Task tool — never edit the presentation directly.

The agent is **self-evolving**: after every execution, it updates its own skills to stay in sync with the presentation. It has three preloaded skills:
- `vibe-to-agentic-framework`: The conceptual framework ("Vibe Coding → Agentic Engineering"), weight rationale, and journey narrative. Updated after every slide change.
- `presentation-structure`: Slide format, weight system, navigation, section ranges. Updated when slides are added/removed/reordered.
- `presentation-styling`: CSS classes, component patterns, syntax highlighting. Updated when new styling patterns are introduced.

### Hooks System
Cross-platform sound notification system in `.claude/hooks/`:
- `scripts/hooks.py`: Main handler for Claude Code hook events
- `config/hooks-config.json`: Shared team configuration
- `config/hooks-config.local.json`: Personal overrides (git-ignored)
- `sounds/`: Audio files organized by hook event (generated via ElevenLabs TTS)

Hook events configured in `.claude/settings.json`: PreToolUse, PostToolUse, UserPromptSubmit, Notification, Stop, SubagentStart, SubagentStop, PreCompact, SessionStart, SessionEnd, Setup, PermissionRequest, TeammateIdle, TaskCompleted, ConfigChange.

Special handling: git commits trigger `pretooluse-git-committing` sound.

## Critical Patterns

### Subagent Orchestration
Subagents **cannot** invoke other subagents via bash commands. Use the Task tool:

Task(subagent_type="agent-name", description="...", prompt="...", model="haiku")

Be explicit about tool usage in subagent definitions. Avoid vague terms like "launch" that could be misinterpreted as bash commands.

### Subagent Definition Structure
Subagents in `.claude/agents/*.md` use YAML frontmatter:
- `name`: Subagent identifier
- `description`: When to invoke (use "PROACTIVELY" for auto-invocation)
- `tools`: Comma-separated allowlist of tools (inherits all if omitted). Supports `Task(agent_type)` syntax
- `disallowedTools`: Tools to deny, removed from inherited or specified list
- `model`: Model alias: `haiku`, `sonnet`, `opus`, or `inherit` (default: `inherit`)
- `permissionMode`: Permission mode (e.g., `"acceptEdits"`, `"plan"`, `"bypassPermissions"`)
- `maxTurns`: Maximum agentic turns before the subagent stops
- `skills`: List of skill names to preload into agent context
- `mcpServers`: MCP servers for this subagent (server names or inline configs)
- `hooks`: Lifecycle hooks scoped to this subagent (`PreToolUse`, `PostToolUse`, `Stop`)
- `memory`: Persistent memory scope — `user`, `project`, or `local` (see `reports/claude-agent-memory.md`)
- `background`: Set to `true` to always run as a background task
- `isolation`: Set to `"worktree"` to run in a temporary git worktree
- `color`: CLI output color for visual distinction

### Configuration Hierarchy
1. `.claude/settings.local.json`: Personal settings (git-ignored)
2. `.claude/settings.json`: Team-shared settings
3. `hooks-config.local.json` overrides `hooks-config.json`

### Disable Hooks
Set `"disableAllHooks": true` in `.claude/settings.local.json`, or disable individual hooks in `hooks-config.json`.

## Workflow Best Practices

From experience with this repository:
- Keep CLAUDE.md under 150 lines for reliable adherence
- Use commands for workflows instead of standalone agents
- Create feature-specific subagents with skills (progressive disclosure) rather than general-purpose agents
- Perform manual `/compact` at ~50% context usage
- Start with plan mode for complex tasks
- Use human-gated todo list workflow for multi-step tasks
- Break subtasks small enough to complete in under 50% context

### Debugging Tips
- Use `/doctor` for diagnostics
- Run long-running terminal commands as background tasks for better log visibility
- Use browser automation MCPs (Claude in Chrome, Playwright, Chrome DevTools) for Claude to inspect console logs
- Provide screenshots when reporting visual issues

## Documentation & Reports

- `docs/AGENTS.md`: Subagent orchestration troubleshooting
- `docs/COMPARISION.md`: Commands vs Agents vs Skills invocation patterns
- `weather-orchestration/weather-orchestration-architecture.md`: Weather system flow diagram
- `reports/claude-in-chrome-v-chrome-devtools-mcp.md`: Browser automation MCP comparison
- `reports/claude-md-for-larger-mono-repos.md`: CLAUDE.md loading behavior in monorepos
- `reports/claude-skills-for-larger-mono-repos.md`: Skills discovery and loading behavior
- `reports/claude-agent-memory.md`: Agent memory frontmatter
- `reports/claude-advanced-tool-use.md`: Advanced tool use patterns

## AI Provider Routing (外部AIプロバイダー連携)

AI Bridge MCP サーバー (`mcp__ai-bridge__*`) を通じて、Gemini・OpenAI・Grok を**ユーザー選択式**で利用できる。Claudeが自動で外部AIを呼び出すことはしない。

### ルーティングルール
1. **提案のみ**: タスクに応じて外部AIが有用と判断した場合、`AskUserQuestion` でプロバイダー候補を提案する
2. **ユーザー承認必須**: ユーザーが明示的に選択・承認するまで外部APIは呼び出さない
3. **コスト意識**: 外部AI利用はClaudeの利用に加算される追加コストであることをユーザーに伝える

### プロバイダー適性ガイド
| プロバイダー | 得意分野 | ツール名 |
|---|---|---|
| **Gemini** | 最新情報の検索、Google エコシステム連携、長文コンテキスト | `mcp__ai-bridge__ai_ask(provider="gemini")` |
| **OpenAI** | コード生成、構造化出力、GPT固有の知識 | `mcp__ai-bridge__ai_ask(provider="openai")` |
| **Grok** | リアルタイム情報（※X/Twitterデータアクセスは不可） | `mcp__ai-bridge__ai_ask(provider="grok")` |

### 利用フロー
```
ユーザー要求 → Claude分析 → 外部AIが有用？
  ├─ No → Claudeが直接回答
  └─ Yes → AskUserQuestion で提案 → ユーザー承認 → 外部AI呼び出し → 結果統合
```

### 禁止事項
- ユーザー未承認での外部API呼び出し
- 機密情報（APIキー、個人情報）を外部AIプロンプトに含めること
- 外部AIの回答を検証なしにそのまま最終回答とすること

---

## 🛠️ Custom Instructions (AIへのカスタム指示)

AIアシスタントはこのリポジトリでコードを記述・レビューする際、以下のルールに厳格に従うこと。

### 🛡️ セキュリティ・レビュープロセス (Red / Blue Team)
新しい機能（特に認証、DB操作、外部API通信、ユーザー入力の処理など）を実装した際、またはユーザーから「セキュリティチェックをお願い」と指示された場合は、必ず以下のステップでコードを評価し、修正してください。

#### 😈 ステップ1: Black Hacker (攻撃 / Offensive)
- **タスク:** 実装されたコードに対し、システムへの侵入経路や脆弱性を徹底的に探す。
- **視点:** SQLインジェクション、XSS、CSRF、認証バイパス、権限昇格、ディレクトリトラバーサル、機密情報の漏洩など、あらゆる攻撃ベクトルを想定する。
- **出力:** 「私が攻撃者なら、このコードの〇〇をこう突いてシステムを破壊・乗っ取る」という具体的な攻撃シナリオを容赦なく指摘する。

#### 👼 ステップ2: White Hacker (防御 / Defensive)
- **タスク:** Black Hackerが発見した脆弱性を完全に塞ぐための、具体的なコード修正案を実装する。
- **視点:** 単なる対症療法ではなく、根本的なセキュリティ強化（バリデーションの強化、サニタイズ、安全なライブラリの利用など）を提案・実装する。
- **出力:** セキュアに修正されたコードと、なぜその対策が有効なのかの解説。

#### 🔄 ステップ3: セキュリティ教訓の蓄積（自己進化）
- 上記プロセスで**発見された脆弱性と解決策のエッセンスを、必ずこのファイルの `## 🛑 過去の失敗と教訓` セクションにあなた自身で追記**してください。これにより、今後の開発で二度と同じ脆弱性を生み出さないようにします。

---

## 🛑 過去の失敗と教訓 (Lessons Learned)
AIはコードを書く前に必ずこのセクションを読み、同じミスを繰り返さないこと。新しい教訓を得た場合は、AI自身がここに追記すること。

### 2026-02-25: AI Bridge MCP サーバー セキュリティ強化

#### 1. APIキーのエラーメッセージ漏洩
- **発見**: OpenAI SDK 等のエラーメッセージにAPIキーが含まれることがある。`formatError()` や `logger.error()` でそのまま出力すると、ログやMCPレスポンスにキーが露出する。
- **対策**: `BaseProvider.sanitize()` を導入し、`sk-*`, `AIza*`, `xai-*`, `Bearer *` パターンを `[REDACTED]` に置換。全プロバイダーの `sendRequest` catch節で適用。
- **教訓**: 外部SDK由来のエラーは必ずサニタイズしてからログ出力・再throwすること。

#### 2. プロンプト長の未検証（DoS・コスト爆発）
- **発見**: ユーザー入力のプロンプトに文字数制限がなく、巨大な入力でAPIコストが爆発する可能性があった。
- **対策**: `BaseProvider.validatePromptLength()` で200,000文字上限を設定。全プロバイダーの `sendRequest` 冒頭で検証。
- **教訓**: 外部APIに送信するユーザー入力は、必ず長さ・サイズのバリデーションを入れること。

#### 3. OpenAI推論モデルのパラメータ非互換
- **発見**: o1/o1-mini/o3-mini 等の推論モデルに `temperature` や `max_tokens` を渡すと 400 Bad Request になる。
- **対策**: `isReasoningModel()` で `/^o[0-9]/` パターン判定し、推論モデルには `max_completion_tokens` を使用、`temperature` を省略。
- **教訓**: 同一プロバイダーでもモデルファミリーによってAPI仕様が異なる場合がある。モデル名による条件分岐を忘れないこと。

#### 4. `.mcp.json` 未作成によるサーバー未検出
- **発見**: MCP サーバーのコードは完成していたが、Claude Code にサーバーを登録する `.mcp.json` が存在せず、サーバーが起動されなかった。
- **対策**: プロジェクトルートに `.mcp.json` を作成し、`node dist/index.js` コマンドを登録。
- **教訓**: MCP サーバー開発時は、コード実装だけでなく `.mcp.json` による登録も必ずセットで行うこと。