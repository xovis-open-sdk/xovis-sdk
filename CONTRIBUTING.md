# Contributing to xovis-sdk

Thank you for your interest in contributing to the Xovis SDK! To maintain the high-performance and architectural integrity of this project, we have established the following guidelines.

## 🏗️ Architectural Philosophy: The Quadrifurcation

The SDK is strictly divided into four distinct planes. **Never mix the design patterns of these planes:**

1.  **The Data Plane (`src/xovis/datapush/`)**: High-frequency ingestion. Use pure `asyncio`, no Pydantic validation in the hot path.
2.  **The Control Plane (`src/xovis/api/`)**: REST API wrappers. Enforce strict Pydantic CRUD and robust error handling.
3.  **The State Plane (`src/xovis/fleet/`)**: Topology-aware fleet management and caching.
4.  **The Skill Plane (`src/xovis/skills/`)**: AI-powered toolkit and MCP integrations.

## ✍️ Coding Standards

-   **Google-Style Docstrings**: Every module, class, and public method MUST have a comprehensive Google-style docstring.
-   **Type Hinting**: Use strict type hinting across the entire codebase.
-   **Zero-Inline-Comments**: Code should be self-documenting. Use docstrings for architectural intent, not inline chatter.
-   **Pydantic V2**: Use Pydantic V2 models for all API payloads and configurations.

## 🧪 Testing Requirements

-   All new features must include tests.
-   **Tier 1 (Smoke)**: Fast, non-destructive tests.
-   **Tier 2 (CRUD)**: Stateful operations. Use `try...finally` for hard teardown.
-   **Tier 3 (Data)**: Telemetry pipeline validation.
- Tests must be idempotent and respect hardware pacing delays.

## 🧪 Testing with Mocks (CI Safety)

Since physical Xovis hardware is not available in the CI environment, the SDK uses a **Mocked Device Layer** triggered automatically when hardware environment variables are missing.

- **Local Development**: Set `XOVIS_TEST_HOST`, `XOVIS_TEST_USER`, and `XOVIS_TEST_PASS` to run tests against real hardware.
- **CI / Isolated Testing**: Omit these variables to use the `unittest.mock` based surrogate defined in `tests/conftest.py`.
- **Stateless Tests**: Prefer using `respx` for fine-grained HTTP lifecycle validation as demonstrated in `tests/api/device/test_cp_datapush_stateless.py`.

## 🚀 Pull Request Process

1.  **Branching**: Create a feature branch from `main`.
2.  **Linting**: Run `ruff check .` and `ruff format .` before submitting.
3.  **Documentation**: Verify docstring coverage using `xovis-cli check-docs`.
4.  **Security**: Ensure no sensitive data (MAC addresses, API keys) is included in tests or code.
5.  **Review**: All PRs require at least one approval from a code owner.

## 🛡️ Safety Guardrails

When developing, leverage the `XovisSafetyGuardrail`. Destructive operations (factory reset, network changes) are marked as `CRITICAL` and require human-in-the-loop confirmation.

### 5. Proper & DRY Standards
To ensure the SDK maintains professional standards and isn't "dissed" by senior developers, we enforce strict code quality rules:

*   **DRY (Don't Repeat Yourself)**: Shared logic (e.g., ID resolution) MUST be refactored into base classes (like `HubResourceManager`) or utility modules.
*   **Static Typing**: All public APIs MUST have type hints. Use `mypy` for verification.
*   **Linting**: Use `ruff` for ultra-fast linting and import sorting.
*   **Security**: Use `bandit` to catch common security pitfalls.
*   **Documentation**: Every public class and method MUST have a Google-style docstring.

#### Quality Audit Tool
Run the unified quality audit before submitting any PR:
```bash
python scripts/check_quality.py
```
This script aggregates results from Ruff, MyPy, Pylint (DRY check), Bandit, and the internal Docstring Audit.

---
*By contributing to this project, you agree that your contributions will be licensed under the project's license.*
