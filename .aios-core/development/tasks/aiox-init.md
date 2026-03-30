# aiox-init — AIOX Bootstrapper

> **Version:** 1.0
> **Agent:** @aios-master
> **Command:** `*aiox-init [--tier core|extended|full] [--force]`

---

## Purpose

Bootstrap a project with AIOX framework structure. Creates all necessary directories, config files, engine core, workflows, agents, and rules. Supports fresh install and upgrade of existing installations.

---

## Synopsis

```
aiox init                         # Fresh install with core tier (default)
aiox init --tier extended          # Install core + extended agents
aiox init --tier full              # Install all agents
aiox init --force                  # Force reinstall (backs up existing)
```

---

## Agent Tiers

### Tier Definitions (Story 19.6)

| Tier | Agents | Use Case |
|------|--------|----------|
| **core** | @dev, @qa, @devops | Solo dev, small teams, MVPs |
| **extended** | core + @architect, @pm, @sm, @po | Medium teams, structured process |
| **full** | extended + @analyst, @data-engineer, @ux-design-expert | Large teams, enterprise |

### Agent Tier Metadata

Each agent definition file includes a `tier` field in its YAML frontmatter:

```yaml
# Core tier — always installed
- { id: dev, tier: core, file: dev.md }
- { id: qa, tier: core, file: qa.md }
- { id: devops, tier: core, file: devops.md }

# Extended tier — structured process
- { id: architect, tier: extended, file: architect.md }
- { id: pm, tier: extended, file: pm.md }
- { id: sm, tier: extended, file: sm.md }
- { id: po, tier: extended, file: po.md }

# Specialist tier — domain-specific
- { id: analyst, tier: specialist, file: analyst.md }
- { id: data-engineer, tier: specialist, file: data-engineer.md }
- { id: ux-design-expert, tier: specialist, file: ux-design-expert.md }
```

### Tier Inclusion Rules

```
core     → installs: [dev, qa, devops]
extended → installs: [dev, qa, devops, architect, pm, sm, po]
full     → installs: [dev, qa, devops, architect, pm, sm, po, analyst, data-engineer, ux-design-expert]
```

---

## Execution Flow

### STEP 1: Parse Arguments

```
FUNCTION aiox_init(args):
  tier = args.tier OR "core"               # Default: core
  force = args.force OR false

  VALIDATE tier IN ["core", "extended", "full"]

  project_root = find_git_root() OR current_directory()
```

### STEP 2: Detect Installation Mode

```
  IF file_exists("{project_root}/.aios/engine-config.yaml"):
    IF force:
      mode = "force-reinstall"
      LOG "Force reinstall requested — backing up existing installation"
      backup_existing(project_root)
    ELSE:
      mode = "upgrade"
      LOG "Existing AIOX installation detected — upgrade mode"
  ELSE:
    mode = "fresh"
    LOG "No existing installation — fresh install"
```

### STEP 3: Backup (force-reinstall only)

```
  IF mode == "force-reinstall":
    timestamp = current_timestamp()  # e.g., 20260330-143022
    backup_dir = "{project_root}/.aios.bak-{timestamp}"

    copy_directory("{project_root}/.aios", "{backup_dir}/.aios")
    copy_directory("{project_root}/.aios-core", "{backup_dir}/.aios-core")
    copy_directory("{project_root}/.claude", "{backup_dir}/.claude")

    LOG "Backup created at {backup_dir}"
```

### STEP 4: Create Directory Structure

```
  # .aios/ — project-level runtime config
  ensure_directory("{project_root}/.aios/")
  ensure_directory("{project_root}/.aios/handoffs/")
  ensure_directory("{project_root}/.aios/state/")

  # .aios-core/ — framework core (engine, tasks, workflows, agents)
  ensure_directory("{project_root}/.aios-core/development/tasks/")
  ensure_directory("{project_root}/.aios-core/development/workflows/")
  ensure_directory("{project_root}/.aios-core/development/agents/")
  ensure_directory("{project_root}/.aios-core/development/templates/")
  ensure_directory("{project_root}/.aios-core/development/checklists/")
  ensure_directory("{project_root}/.aios-core/development/data/")

  # .claude/ — Claude Code integration
  ensure_directory("{project_root}/.claude/rules/")

  LOG "Directory structure created"
```

### STEP 5: Generate Engine Config

```
  config_path = "{project_root}/.aios/engine-config.yaml"

  IF mode == "upgrade" AND file_exists(config_path):
    existing_config = read_yaml(config_path)
    new_defaults = DEFAULT_ENGINE_CONFIG  # From run-workflow-engine.md
    merged = deep_merge(new_defaults, existing_config)  # User values take precedence
    write_yaml(config_path, merged)
    LOG "engine-config.yaml upgraded (existing values preserved)"
  ELSE:
    write_yaml(config_path, DEFAULT_ENGINE_CONFIG_TEMPLATE)
    LOG "engine-config.yaml created with defaults"
```

Where `DEFAULT_ENGINE_CONFIG_TEMPLATE` is:

```yaml
# AIOX Engine Configuration
# All values below are defaults. Override only what you need.
# Missing values will use the defaults from DEFAULT_ENGINE_CONFIG in run-workflow-engine.md

engine:
  version: "1.0"

execution:
  max_loops_per_target: 4
  parse_failure_max_retries: 2
  output_validation_max_retries: 2

tokens:
  context_window_limit: 180000
  failure_context_max: 500
  handoff_context_max: 300
  intelligence_context_max: 300
  project_context_max: 200

cost:
  max_per_workflow_usd: 10.0
  warn_at_percent: 80

timeouts:
  default_step_seconds: 300
  max_workflow_duration_hours: 4

confidence:
  high_threshold: 0.8
  medium_threshold: 0.5

retry_strategy:
  default_max_loops: 4
  level_1: "context"
  level_2: "simplification"
  level_3: "decomposition"
  fallback: "abort"

intelligence:
  ttl_days: 30
  post_mortem_lookback_days: 7

parallel:
  max_group_size: 5
```

### STEP 6: Auto-Detect Project Context (Story 19.5)

```
  context_path = "{project_root}/.aios/project-context.yaml"

  IF mode == "upgrade" AND file_exists(context_path):
    LOG "project-context.yaml exists — preserving (run *detect-context to refresh)"
  ELSE:
    context = auto_detect_project_context(project_root)
    write_yaml(context_path, context)
    LOG "project-context.yaml generated via auto-detection"
```

#### Auto-Detection Algorithm (Story 19.5)

```
FUNCTION auto_detect_project_context(root):
  context = {
    project: {
      name: basename(root),
      type: "unknown",
      languages: { primary: "unknown", secondary: [] },
      frontend: null,
      backend: null,
      database: null,
      infrastructure: { containerized: false, ci_cd: null },
      detected_from: []
    }
  }

  # --- Node.js / JavaScript / TypeScript ---
  IF file_exists("{root}/package.json"):
    pkg = read_json("{root}/package.json")
    context.project.name = pkg.name OR context.project.name

    deps = merge(pkg.dependencies OR {}, pkg.devDependencies OR {})

    # Language
    IF file_exists("{root}/tsconfig.json"):
      context.project.languages.primary = "typescript"
    ELSE:
      context.project.languages.primary = "javascript"

    # Frontend framework detection
    IF "react" IN deps:
      IF "next" IN deps:
        context.project.frontend = { framework: "next", version: extract_major(deps["next"]) }
      ELSE:
        context.project.frontend = { framework: "react", version: extract_major(deps["react"]) }
    ELSE IF "vue" IN deps:
      IF "nuxt" IN deps:
        context.project.frontend = { framework: "nuxt", version: extract_major(deps["nuxt"]) }
      ELSE:
        context.project.frontend = { framework: "vue", version: extract_major(deps["vue"]) }
    ELSE IF "@angular/core" IN deps:
      context.project.frontend = { framework: "angular", version: extract_major(deps["@angular/core"]) }
    ELSE IF "svelte" IN deps:
      context.project.frontend = { framework: "svelte", version: extract_major(deps["svelte"]) }

    # Test runner detection
    IF "vitest" IN deps:
      test_runner = "vitest"
    ELSE IF "jest" IN deps:
      test_runner = "jest"
    ELSE IF "mocha" IN deps:
      test_runner = "mocha"
    ELSE IF "cypress" IN deps:
      test_runner = "cypress"
    ELSE:
      test_runner = null

    IF context.project.frontend AND test_runner:
      context.project.frontend.test_runner = test_runner

    # Build tool detection
    IF "vite" IN deps:
      build_tool = "vite"
    ELSE IF "webpack" IN deps:
      build_tool = "webpack"
    ELSE IF "esbuild" IN deps:
      build_tool = "esbuild"
    ELSE IF "turbo" IN deps:
      build_tool = "turbo"
    ELSE:
      build_tool = null

    IF context.project.frontend AND build_tool:
      context.project.frontend.build_tool = build_tool

    detected_items = [k for k in deps if k in KNOWN_FRAMEWORKS]
    context.project.detected_from.append({
      file: "package.json",
      found: detected_items[:10]  # Limit to 10 most relevant
    })

  # --- Python ---
  IF file_exists("{root}/requirements.txt") OR file_exists("{root}/pyproject.toml"):
    manifest = "pyproject.toml" IF file_exists("{root}/pyproject.toml") ELSE "requirements.txt"
    python_deps = parse_python_deps(root, manifest)

    IF context.project.languages.primary == "unknown":
      context.project.languages.primary = "python"
    ELSE:
      context.project.languages.secondary.append("python")

    # Backend framework detection
    IF "fastapi" IN python_deps:
      context.project.backend = { framework: "fastapi", language: "python" }
    ELSE IF "django" IN python_deps:
      context.project.backend = { framework: "django", language: "python" }
    ELSE IF "flask" IN python_deps:
      context.project.backend = { framework: "flask", language: "python" }

    # Python test runner
    IF "pytest" IN python_deps:
      IF context.project.backend:
        context.project.backend.test_runner = "pytest"
    ELSE IF "unittest" IN python_deps:
      IF context.project.backend:
        context.project.backend.test_runner = "unittest"

    context.project.detected_from.append({
      file: manifest,
      found: [d for d in python_deps if d in KNOWN_PYTHON_FRAMEWORKS][:10]
    })

  # --- Rust ---
  IF file_exists("{root}/Cargo.toml"):
    cargo = read_toml("{root}/Cargo.toml")

    IF context.project.languages.primary == "unknown":
      context.project.languages.primary = "rust"
    ELSE:
      context.project.languages.secondary.append("rust")

    rust_deps = keys(cargo.dependencies OR {})
    IF "axum" IN rust_deps:
      context.project.backend = { framework: "axum", language: "rust" }
    ELSE IF "actix-web" IN rust_deps:
      context.project.backend = { framework: "actix", language: "rust" }
    ELSE IF "rocket" IN rust_deps:
      context.project.backend = { framework: "rocket", language: "rust" }

    context.project.detected_from.append({
      file: "Cargo.toml",
      found: [d for d in rust_deps if d in KNOWN_RUST_FRAMEWORKS][:10]
    })

  # --- Go ---
  IF file_exists("{root}/go.mod"):
    gomod = read_file("{root}/go.mod")

    IF context.project.languages.primary == "unknown":
      context.project.languages.primary = "go"
    ELSE:
      context.project.languages.secondary.append("go")

    go_deps = parse_go_requires(gomod)
    IF "gin-gonic/gin" IN go_deps:
      context.project.backend = { framework: "gin", language: "go" }
    ELSE IF "go-chi/chi" IN go_deps:
      context.project.backend = { framework: "chi", language: "go" }
    ELSE IF "labstack/echo" IN go_deps:
      context.project.backend = { framework: "echo", language: "go" }
    ELSE IF "gofiber/fiber" IN go_deps:
      context.project.backend = { framework: "fiber", language: "go" }

    context.project.detected_from.append({
      file: "go.mod",
      found: [d for d in go_deps if d in KNOWN_GO_FRAMEWORKS][:10]
    })

  # --- Database ---
  IF directory_exists("{root}/supabase/"):
    context.project.database = { type: "supabase", orm: null }
  ELSE IF directory_exists("{root}/prisma/"):
    context.project.database = { type: "prisma", orm: "prisma" }
  ELSE IF file_exists("{root}/drizzle.config.ts") OR file_exists("{root}/drizzle.config.js"):
    context.project.database = { type: "postgres", orm: "drizzle" }

  # --- Infrastructure ---
  IF file_exists("{root}/Dockerfile"):
    context.project.infrastructure.containerized = true
  IF file_exists("{root}/docker-compose.yml") OR file_exists("{root}/docker-compose.yaml") OR file_exists("{root}/compose.yaml"):
    context.project.infrastructure.containerized = true
    context.project.type = "multi-service" IF context.project.type == "unknown"

  # CI/CD detection
  IF directory_exists("{root}/.github/workflows/"):
    context.project.infrastructure.ci_cd = "github-actions"
  ELSE IF file_exists("{root}/.gitlab-ci.yml"):
    context.project.infrastructure.ci_cd = "gitlab-ci"
  ELSE IF file_exists("{root}/Jenkinsfile"):
    context.project.infrastructure.ci_cd = "jenkins"
  ELSE IF directory_exists("{root}/.circleci/"):
    context.project.infrastructure.ci_cd = "circleci"

  # --- Project type inference ---
  IF context.project.frontend AND context.project.backend:
    context.project.type = "fullstack"
  ELSE IF context.project.frontend:
    context.project.type = "frontend"
  ELSE IF context.project.backend:
    context.project.type = "api"
  ELSE IF file_exists("{root}/setup.py") OR file_exists("{root}/setup.cfg"):
    context.project.type = "library"
  ELSE IF context.project.type == "unknown":
    context.project.type = "unknown"

  # --- Fallback for no detection ---
  IF context.project.languages.primary == "unknown" AND len(context.project.detected_from) == 0:
    LOG "No manifest files found — generating minimal project-context"
    context.project.type = "unknown"

  RETURN context
```

### STEP 7: Install Engine Core

```
  engine_path = "{project_root}/.aios-core/development/tasks/run-workflow-engine.md"

  IF mode == "upgrade":
    IF file_exists(engine_path):
      existing_version = extract_engine_version(engine_path)
      source_version = AIOX_ENGINE_VERSION  # Current latest
      IF existing_version < source_version:
        write_file(engine_path, AIOX_ENGINE_CORE)
        LOG "Engine upgraded: {existing_version} → {source_version}"
      ELSE:
        LOG "Engine already at latest version ({existing_version})"
    ELSE:
      write_file(engine_path, AIOX_ENGINE_CORE)
      LOG "Engine core installed"
  ELSE:
    write_file(engine_path, AIOX_ENGINE_CORE)
    LOG "Engine core installed (v{AIOX_ENGINE_VERSION})"
```

### STEP 8: Install Workflows

```
  GENERIC_WORKFLOWS = [
    "story-development-cycle.yaml",
    "rca-investigation.yaml"
  ]

  FOR workflow IN GENERIC_WORKFLOWS:
    dest = "{project_root}/.aios-core/development/workflows/{workflow}"
    IF mode == "upgrade" AND file_exists(dest):
      LOG "Workflow {workflow} exists — skipping (use --force to overwrite)"
    ELSE:
      write_file(dest, AIOX_WORKFLOW_TEMPLATES[workflow])
      LOG "Workflow {workflow} installed"
```

### STEP 9: Install Agents by Tier

```
  AGENT_TIERS = {
    core: ["dev.md", "qa.md", "devops.md"],
    extended: ["architect.md", "pm.md", "sm.md", "po.md"],
    specialist: ["analyst.md", "data-engineer.md", "ux-design-expert.md"]
  }

  # Determine which agents to install
  agents_to_install = AGENT_TIERS["core"]  # Always
  IF tier IN ["extended", "full"]:
    agents_to_install += AGENT_TIERS["extended"]
  IF tier == "full":
    agents_to_install += AGENT_TIERS["specialist"]

  installed_count = 0
  skipped_count = 0

  FOR agent_file IN agents_to_install:
    dest = "{project_root}/.aios-core/development/agents/{agent_file}"
    IF mode == "upgrade" AND file_exists(dest) AND NOT force:
      skipped_count += 1
    ELSE:
      write_file(dest, AIOX_AGENT_TEMPLATES[agent_file])
      installed_count += 1

  LOG "Agents: {installed_count} installed, {skipped_count} skipped (tier: {tier})"

  # Write agents manifest
  agents_yaml_path = "{project_root}/.aios/agents.yaml"
  agents_manifest = {
    tier: tier,
    installed: [strip_extension(a) for a in agents_to_install],
    available_tiers: {
      core: ["dev", "qa", "devops"],
      extended: ["architect", "pm", "sm", "po"],
      specialist: ["analyst", "data-engineer", "ux-design-expert"]
    }
  }
  write_yaml(agents_yaml_path, agents_manifest)
  LOG "Agent manifest written to .aios/agents.yaml"
```

### STEP 10: Install Templates and Rules

```
  # Subagent prompt template
  template_dest = "{project_root}/.aios-core/development/templates/subagent-step-prompt.md"
  IF NOT file_exists(template_dest):
    write_file(template_dest, AIOX_SUBAGENT_PROMPT_TEMPLATE)
    LOG "Subagent prompt template installed"

  # Essential Claude rules
  ESSENTIAL_RULES = [
    "agent-authority.md",
    "agent-handoff.md",
    "story-lifecycle.md",
    "workflow-execution.md"
  ]

  FOR rule IN ESSENTIAL_RULES:
    dest = "{project_root}/.claude/rules/{rule}"
    IF NOT file_exists(dest):
      write_file(dest, AIOX_RULE_TEMPLATES[rule])
      LOG "Rule {rule} installed"

  # Base CLAUDE.md
  claude_md = "{project_root}/.claude/CLAUDE.md"
  IF NOT file_exists(claude_md):
    write_file(claude_md, "# {project_name}\n\nProject description here.\n")
    LOG "CLAUDE.md created (edit with project description)"
```

### STEP 11: Install Essential Tasks

```
  ESSENTIAL_TASKS = [
    "run-workflow-engine.md",
    "dev-develop-story.md",
    "qa-gate.md",
    "create-next-story.md",
    "validate-next-story.md",
    "aiox-init.md"
  ]

  # In core tier, SDC phases that require @sm/@po are simplified:
  # - create-next-story.md → @dev can create simple stories
  # - validate-next-story.md → @dev self-validates with checklist
  IF tier == "core":
    LOG "Core tier: SDC phases simplified — @dev handles create + validate"
```

### STEP 12: Display Summary

```
  summary = {
    mode: mode,
    tier: tier,
    structure: {
      directories_created: count_new_directories,
      files_created: count_new_files,
      files_updated: count_updated_files,
      files_skipped: count_skipped_files
    },
    agents_installed: agents_to_install,
    workflows_installed: GENERIC_WORKFLOWS,
    project_context: {
      detected_type: context.project.type,
      primary_language: context.project.languages.primary,
      frontend: context.project.frontend.framework IF context.project.frontend ELSE "none",
      backend: context.project.backend.framework IF context.project.backend ELSE "none",
      database: context.project.database.type IF context.project.database ELSE "none"
    }
  }

  DISPLAY:
  """
  ==========================================
   AIOX Init Complete
  ==========================================

  Mode:     {mode}
  Tier:     {tier}

  Structure:
    Directories: {summary.structure.directories_created} created
    Files:       {summary.structure.files_created} created, {summary.structure.files_updated} updated, {summary.structure.files_skipped} skipped

  Agents ({len(agents_to_install)}):
    {join(agents_to_install, ", ")}

  Workflows:
    {join(GENERIC_WORKFLOWS, ", ")}

  Project Context (auto-detected):
    Type:     {summary.project_context.detected_type}
    Language: {summary.project_context.primary_language}
    Frontend: {summary.project_context.frontend}
    Backend:  {summary.project_context.backend}
    Database: {summary.project_context.database}

  Next steps:
    1. Review .aios/project-context.yaml and adjust if needed
    2. Edit .claude/CLAUDE.md with your project description
    3. Run a workflow: *workflow story-development-cycle

  ==========================================
  """
```

---

## Idempotency Rules

1. **Directories**: `ensure_directory` is always safe — no-op if exists
2. **Config files**: Upgrade mode merges, never overwrites user values
3. **Engine core**: Only upgraded if version is older
4. **Workflows**: Skipped if exists (unless --force)
5. **Agents**: Skipped if exists (unless --force)
6. **Rules**: Skipped if exists (always — rules are project-customized)
7. **Running twice**: Produces identical result to running once

---

## Upgrade Path

```
# Upgrade tier (adds agents, preserves existing)
aiox init --tier extended    # Was core → now adds architect, pm, sm, po

# Force full reinstall
aiox init --force            # Backs up .aios.bak-{timestamp}, reinstalls everything

# Refresh auto-detection only
*detect-context              # Re-runs auto-detection, writes new project-context.yaml
```

---

## Known Framework Constants

```
KNOWN_FRAMEWORKS = [
  "react", "vue", "angular", "svelte", "next", "nuxt", "remix",
  "express", "fastify", "nest", "koa",
  "vitest", "jest", "mocha", "cypress", "playwright",
  "vite", "webpack", "esbuild", "turbo", "rollup",
  "tailwindcss", "sass", "styled-components"
]

KNOWN_PYTHON_FRAMEWORKS = [
  "fastapi", "django", "flask", "starlette",
  "pytest", "unittest", "celery", "sqlalchemy", "alembic"
]

KNOWN_RUST_FRAMEWORKS = [
  "axum", "actix-web", "rocket", "warp", "tokio", "serde"
]

KNOWN_GO_FRAMEWORKS = [
  "gin-gonic/gin", "go-chi/chi", "labstack/echo", "gofiber/fiber",
  "gorilla/mux", "gorm.io/gorm"
]
```

---

## Integration Points

- **Story 19.2**: `DEFAULT_ENGINE_CONFIG_TEMPLATE` matches `DEFAULT_ENGINE_CONFIG` in `run-workflow-engine.md`
- **Story 19.3**: Generic workflows installed — no tech-stack references
- **Story 19.5**: `auto_detect_project_context()` runs as STEP 6 during init
- **Story 19.6**: Agent tiers defined here, `--tier` flag controls selection
- **run-workflow-engine.md**: Loads `engine-config.yaml` at startup via `load_engine_config()`
