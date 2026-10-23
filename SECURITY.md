# Security Policy & Threat Model

## 1. Threat Model Overview

`ai-ops-eval-harness` is designed to operate in high-security environments where autonomous agents interact with operational data, proprietary financial ledgers, and external dispatch systems.

### Primary Threat Vectors & Mitigations

| Threat Vector | Potential Impact | Architectural Mitigation |
|---|---|---|
| **Prompt Injection & Marker Corruption** | Agent bypasses constraints or hallucinates outputs | `assert_prompt_context_integrity` validates markers; `assert_decoupled_json_contract` rejects raw text leaks |
| **Silent Ingestion Data Starvation** | AI agent generates reports on empty/incomplete metrics | `assert_no_coercion_starvation` and `audit_temporal_completeness` fail closed on missing records |
| **Financial Ledger Tampering** | Hidden balance variances go undetected | `reconcile_channel_ledgers` enforces multi-channel arithmetic with IEEE 754 float tolerance |
| **External Side-Effect Blast Radius** | Evaluation runs dispatch actual customer messages or webhooks | `BlastShield` context manager captures dispatch calls without network transmission |
| **Sensitive IP & Credential Leakage** | Tokens, passwords, or customer identifiers committed to git | Pre-commit hook and CI run `scripts/check_blacklist.sh` against clean-room regex patterns |
| **Container Privilege Escalation** | Compromised container gains host access | Multi-stage Dockerfile drops root privileges, creates non-root `appuser`, and removes package managers |

---

## 2. Clean-Room Static Leak Scanning

Every commit and CI run executes `scripts/check_blacklist.sh`, which performs a regex scan over all tracked repository files, rejecting:
- API credentials and tokens
- Specific internal system names and endpoints
- Sensitive customer identifier formats
- Unsanitized development tooling scripts in `scripts/dev/`

---

## 3. Container Security & Dogfooding

Container images are audited via `scripts/audit_image.sh` to enforce:
1. No prohibited files (`.env`, `.key`, `.pem`, `sessions.json`).
2. Trivy vulnerability scanning for `HIGH` and `CRITICAL` CVEs.
3. Minimal attack surface with non-root runtime user.

---

## 4. Reporting Security Vulnerabilities

If you identify a security vulnerability in this repository, please do not file a public issue. Send disclosure details via email to the repository maintainer.
