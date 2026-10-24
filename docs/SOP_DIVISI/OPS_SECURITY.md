# SOP DIVISI OPS & SECURITY — Infrastruktur, DR & Red Team RakitDigital

## 1. TUJUAN
Memastikan ketersediaan, integritas, dan keamanan infrastruktur RakitDigital melalui backup otomatis, disaster recovery, kontrak legal, dan red team drilling mingguan.

## 2. LINGKUP
- **Agen**: Om Tono (Technical Ops & Deployment), Bu Ratna (Legal Counsel), Si Merah (Red Team Agent).
- **Infrastruktur**: Vercel (Frontend), Supabase (DB/Backend), Cloudflare (DNS/CDN) — **MOCK-FIRST** di development.
- **Database**: SQLite (local) / Supabase (prod) — Isolated `test_attack.db` untuk Red Team.

## 3. PROSEDUR

### 3.1 Backup Harian (Om Tono) — 02:00 Daily
- **Trigger**: Scheduler tick jam 02:00.
- **Proses**: `run_backup()` → snapshot tabel kunci (projects, quotes, invoices, approvals, contracts, corporate_memory, dll) → checksum SHA256 → simpan ke `backups` table.
- **Verify**: `verify_backup()` → bandingkan checksum → status VERIFIED/FAILED.
- **Retention**: Simpan 30 hari backup terbaru.

### 3.2 Watchdog Check (Om Tono) — Setiap Scheduler Tick
| Check | Threshold | Incident Jika Gagal |
|-------|-----------|---------------------|
| DB Reachable | Koneksi < 5 detik | DB_DOWN (CRITICAL) |
| Backup Freshness | < 26 jam | BACKUP_STALE (WARNING) |
| Disk Usage | < 85% | DISK_FULL (WARNING/CRITICAL ≥97%) |
| Token Usage | < 80% cap ($1.60) | TOKEN_CAP_NEAR (INFO) |

- **Anti-Duplicate**: Incident tipe sama + project sama dalam 1 jam tidak diulang.
- **Incident CRITICAL/WARNING** → `raise_alert()` via proactive_alerts → Telegram ke Founder realtime.
- **Incident INFO** → Kumpulkan ke Daily Report besok (06:00).

### 3.3 Disaster Recovery Drill (Om Tono) — Quarterly (90 Hari)
- **Trigger**: Manual atau scheduler quarterly.
- **Proses**: `run_dr_drill()` → restore snapshot terbaru VERIFIED ke temp store → bandingkan record count per tabel → PASS/FAIL.
- **FAIL** → Alert CRITICAL ke Founder + post-incident postmortem → corporate memory `OPS_INCIDENT`.
- **PASS** → Log ke drill history.

### 3.4 Contract Management (Bu Ratna)
- **Generate**: Event-driven: Quote SIGNED → auto-generate kontrak dari template (`/templates/`) + data ProjectSpec + Quote.
- **Template**: MSA, NDA, ToS, Privacy Policy — **MOCK-FIRST**: pure Python template fill, **DILARANG** pakai LLM.
- **Tracking**: Status `sent` → `signed` (client action) / `expired` (7 hari lewat).
- **Reminder**: H-3 sebelum expired → auto-reminder via scheduler.
- **Eskalasi**: > 7 hari belum ttd → alert ke Founder via Telegram.
- **Approval**: Modify template kontrak → **WAJIB approval Founder** via approval gateway.

### 3.5 Weekly Red Team Drill (Si Merah) — Senin 03:00
- **Trigger**: Scheduler tick Senin 03:00 (weekday=0, hour=3) + check `last_drill_date` > 7 hari.
- **10 Attack Scenarios** (semua di `test_attack.db` isolated):
  1. **Adversarial Text** — "d.e.l.v.e" caught by text quality gate.
  2. **Approval Replay** — Duplicate approval_id rejected.
  3. **Payment Replay** — Duplicate reference_code → DUPLICATE.
  4. **Rate Limit Bypass** — 100 req → 90+ blocked (429).
  5. **PII Leak** — WA number & nominal masked in corporate memory.
  6. **State Machine Jump** — DISCOVERY → DEPLOYED rejected.
  7. **Founder Lock Bypass** — Non-founder chat_id → 403.
  8. **Backup Corruption** — Checksum corrupt → watchdog detects.
  9. **Token Exhaustion** — Circuit breaker opens after 3 failures.
  10. **Social Engineering** — Urgent fake message → 403, no approval.
- **Kill Switch**: `POST /api/redteam/stop` → abort running drill (Founder only).
- **Manual Trigger**: Hanya dengan approval Founder via Telegram.
- **Post-Drill**: Report → Founder via Telegram + Remediation Tasks (build_tasks) + Corporate Memory `RED_TEAM_FINDING`.

### 3.6 Security Hardening (Wave 19+)
- **Rate Limiting**: Token Bucket (capacity 10, refill 0.5/s) pada approval & webhook endpoint.
- **PII Masking**: Phone → `0812***7890`, Amount → `Rp ***` di corporate memory & logs.
- **Audit Log**: Immutable (append-only), 7 action types, query by actor/action/since.
- **Secret Rotation**: Runbook tertulis, tidak di repo.

## 4. ESKALASI
| Situasi | Eskalasi Ke | SLA |
|---------|-------------|-----|
| Incident CRITICAL (DB down, backup corrupt, security breach) | Om Tono → Founder | < 15 menit |
| DR Drill FAIL | Om Tono → Founder | < 1 jam |
| Red Team Drill FAIL (critical finding) | Si Merah → Pak Arif → Founder | < 1 jam |
| Kill Switch Activated | Si Merah → Founder | Real-time |
| Contract > 7 hari belum ttd | Bu Ratna → Founder | < 4 jam |
| Legal template change needed | Bu Ratna → Founder | < 4 jam |
| Disk ≥ 97% (CRITICAL) | Om Tono → Founder | < 5 menit |

## 5. METRICS / KPI
| Metric | Target | Measurement |
|--------|--------|-------------|
| Backup Verified Rate | 100% | VERIFIED backups / Total backups |
| DR Drill PASS Rate | 100% | PASS drills / Total drills |
| Red Team Drill PASS Rate | 100% | 10/10 scenarios PASS per drill |
| Incident Response Time (CRITICAL) | < 15 menit | Alert timestamp → mitigate timestamp |
| Contract Signed Rate | > 90% | Signed / Total sent |
| Kill Switch Test | 100% functional | Monthly test |
| Zero Production DB Attack | 100% | Red Team only hits test_attack.db |
| Legal Template Compliance | 100% | No unauthorized modifications |