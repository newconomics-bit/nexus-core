# SOP DIVISI ENGINEERING — Build, Quality, Deploy RakitDigital

## 1. TUJUAN
Mengembangkan Micro-SaaS UMKM (Kasir, Stok, Laporan) dengan kualitas production-ready, zero critical security findings, dan proses yang auditable.

## 2. LINGKUP
- **Agen**: Mas Eko (Engineering Manager), Agus (Frontend), Bambang (Backend), Dedi (Database), Bang Jago (QA & Security Auditor), Pak Arif (CTO - oversight).
- **Alur**: ProjectSpec → Breakdown Task → Build (Agus/Bambang/Dedi) → Visual/SAST/DAST/DB Audit → Rework Loop (max 3x) → Approved → Deploy.

## 3. PROSEDUR

### 3.1 Build Process (Deterministik)
1. **Breakdown Task** (Mas Eko):
   - Input: ProjectSpec dari Sari (CS) dengan `features[]`.
   - Output: Max 3 task per fitur: 1 FRONTEND, 1 BACKEND, 1 DATABASE.
   - Assign task_id, title deskriptif, kind enum.
   - DILARANG menambah task di luar 3 kind per fitur.

2. **Execute Task** (Agus/Bambang/Dedi):
   - Terima task dari Mas Eko via DB handoff.
   - Generate code via LLM Gateway (mock mode = dummy code template).
   - Simpan artefak ke DB via BuildArtifact (filename: .tsx/.py/.sql).
   - **DILARANG** commit ke file system/shell.
   - Update task status: PENDING → DONE / FAILED.

3. **Run Build Loop** (Mas Eko):
   - Loop semua task PENDING.
   - Max 3 attempts per task.
   - Jika 1 task gagal 3x → task FAILED, project BLOCKED, **STOP** (jangan lanjut task lain).
   - Semua task DONE → BuildSubmission READY_FOR_AUDIT + project state AUDITING.

### 3.2 Quality Gates (Wajib Lolos)
| Gate | Scanner | Threshold | Blokir Ke |
|------|---------|-----------|-----------|
| Visual Quality (Frontend) | `audit_frontend()` | 0 CRITICAL / 0 HIGH | AUDITING |
| SAST (Backend/DB) | SAST scanner | 0 CRITICAL / 0 HIGH | AUDITING |
| DAST (Runtime) | DAST scanner | 0 CRITICAL / 0 HIGH | AUDITING |
| DB Audit | DB_AUDIT scanner | 0 HIGH violation | AUDITING |
| OSINT | OSINT scanner | 0 CRITICAL (bind 0.0.0.0) | AUDITING |

### 3.3 Rework Loop (Max 3 Cycles)
- Audit FAILED (ada CRITICAL/HIGH) → Bang Jago buat `rework_task` untuk agen yang sama.
- Agen memperbaiki → submit ulang → audit ulang.
- **Max 3 cycles**. Cycle ke-3 tetap FAILED → ESCALATED → project BLOCKED + ApprovalRequest `QA_ESCALATION` ke Founder.
- Bang Jago **DILARANG** mengubah isi artefak (read-only). Perbaikan dilakukan Engineering.

### 3.4 Code Review (Pak Arif / Bang Jago)
- PR < 100 lines: Pak Arif approve.
- PR ≥ 100 lines: **WAJIB approval Founder**.
- Bang Jago: read-only audit, tidak merge PR.

### 3.5 Deployment Approval
- State harus APPROVED (post-QA).
- Om Tono generate deployment request (Hosted Subdomain vs Custom Domain).
- **WAJIB approval Founder** via Telegram `DEPLOY_PRODUCTION`.
- Execute deployment hanya jika Founder APPROVE → state DEPLOYED + activate subscription billing.

## 4. ESKALASI
| Situasi | Eskalasi Ke | SLA |
|---------|-------------|-----|
| Tech debt tinggi / bug kritis | Pak Arif (CTO) | < 4 jam |
| QA Audit 3x gagal (BLOCKED) | Bang Jago → Pak Arif → Founder | < 1 jam |
| Tech stack change (DB, framework, deploy) | Pak Arif → Founder | < 4 jam |
| Security finding CRITICAL | Bang Jago → Om Tono → Founder | < 15 menit |
| Circuit breaker token cap near ($1.60) | Mas Eko → Budi (alert) → Founder | Real-time |
| Mas Eko mentorship needed | Pak Arif | Mingguan (1x sync) |

## 5. METRICS / KPI
| Metric | Target | Measurement |
|--------|--------|-------------|
| Build Success Rate | > 95% | Task DONE / Total Task |
| Zero Critical Security Findings | 100% | Bang Jago audit report |
| Rework Cycle ≤ 2 | > 80% projects | Audit cycles before PASS |
| Deploy Success Rate | 100% | DEPLOYED state achieved |
| PR Review Turnaround | < 24 jam | PR created → approved |
| Technical Debt Tracked | 100% | Corporate memory entries |
| Code Quality (Type-hint, docstring) | 100% | SAST/DAST clean |