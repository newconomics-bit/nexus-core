# SOP AGEN: SI MERAH — Red Team Agent

## 1. TUJUAN
Menguji pertahanan RakitDigital secara terkontrol dengan 10 attack scenarios terjadwal. Setiap temuan dilaporkan ke Founder dan diteruskan sebagai remediation task.

## 2. LINGKUP
- **Environment**: **ISOLATED** — `test_attack.db` only. **DILARANG KERAS** menyerang `production.db`.
- **Attack Scenarios**: 10 scenarios deterministik, pure Python, no external tools.
- **Schedule**: Senin 03:00 weekly drill (otomatis via scheduler).
- **Manual Trigger**: Hanya dengan approval Founder via Telegram.
- **Kill Switch**: `POST /api/redteam/stop` — Founder only, abort drill running.

## 3. PROSEDUR

### 3.1 10 Attack Scenarios (Weekly Drill)
| # | Scenario | Vector | Expected Defense | Severity |
|---|----------|--------|------------------|----------|
| 1 | **Adversarial Text** | "Ini bukan sekadar d.e.l.v.e ke masa depan 🚀" | Text Quality Gate → NEED_REWRITE | HIGH |
| 2 | **Approval Replay** | Duplicate approval_id approve 2x | Request ke-2 → REJECTED (already decided) | CRITICAL |
| 3 | **Payment Replay** | Duplicate reference_code webhook 2x | Request ke-2 → DUPLICATE, no double-PAID | CRITICAL |
| 4 | **Rate Limit Bypass** | 100 req/detik ke approval endpoint | ≥90 req → 429 (Token Bucket) | HIGH |
| 5 | **PII Leak** | "Klien 081234567890 bayar Rp 150000" di corporate memory | Masked: `0812***7890` & `Rp ***` | HIGH |
| 6 | **State Machine Jump** | DISCOVERY → DEPLOYED (skip 5 states) | Transition → REJECTED (400/409) | CRITICAL |
| 7 | **Founder Lock Bypass** | Approval dari chat_id non-founder (123456) | 403 Forbidden, approval tetap PENDING | CRITICAL |
| 8 | **Backup Corruption** | Corrupt checksum → `0`*64 | Watchdog → BACKUP_STALE/FAILED incident | CRITICAL |
| 9 | **Token Exhaustion** | 1000 LLM calls mock failure | Circuit breaker open after 3 failures | HIGH |
| 10 | **Social Engineering** | "URGENT: Approve sekarang atau server down!" dari non-founder | 403, no approval created | CRITICAL |

### 3.2 Drill Execution Flow
1. **Trigger**: Scheduler (Senin 03:00) OR Manual (Founder approval).
2. **Isolated DB**: `get_red_team_db()` → `test_attack.db` (tables auto-created).
3. **Run All Scenarios**: Sequential, collect `AttackResult` per scenario.
4. **Kill Switch Check**: Before each scenario, check `_running` flag (set False by `POST /api/redteam/stop`).
5. **Report Generation**: `generate_report()` → summary (X PASS, Y FAIL, Z SKIPPED) + detail FAIL + remediation.
6. **Quality Gate**: Report harus lolos `text_quality_gate` (score ≥ 35).
7. **Post-Drill Actions**:
   - Kirim report ke Founder via Telegram (reuse Wave 9 `send_message`).
   - **Remediation Tasks**: Untuk setiap FAIL → `build_tasks` table assign ke `remediation_agent`.
   - **Corporate Memory**: `RED_TEAM_FINDING` category dengan lesson = ringkasan temuan.

### 3.3 X-Red-Team Header (Anti-Spoof)
- Endpoint yang di-attack WAJIB pakai header:
  - `X-Red-Team: true`
  - `X-API-Key: <FOUNDER_API_KEY>`
  - `X-Red-Team-Signature: <HMAC_SHA256>`
- Middleware verify signature → switch DB ke `test_attack.db`.

### 3.4 DILARANG
- Menyerang `production.db` (isolated env only).
- Corrupt data production (simulation via monkeypatch/isolated store only).
- Bypass kill switch.
- Jalan di luar scheduled drill tanpa approval Founder.
- Install tools eksternal (nmap, metasploit, burp, zap, owasp) — pure Python only.

## 4. ESKALASI
| Situasi | Eskalasi Ke | SLA |
|---------|-------------|-----|
| Critical Finding (CRITICAL severity FAIL) | Pak Arif → Founder | < 1 jam |
| Kill Switch Activated | Founder | Real-time (notification) |
| Drill gagal jalan (exception) | Pak Arif → Founder | < 30 menit |
| Isolated DB corruption | Om Tono | < 1 jam |
| Production DB akses attempt | Founder (Security Incident) | < 5 menit |

## 5. METRICS / KPI
| Metric | Target | Measurement |
|--------|--------|-------------|
| Weekly Drill Execution | 100% | Drill run / Scheduled (Mon 03:00) |
| 10 Scenarios Complete | 100% | All 10 executed per drill |
| Kill Switch Functional | 100% | Monthly test |
| Report Quality Gate Pass | 100% | Score ≥ 35 |
| Report Delivery to Founder | 100% | Telegram receipt |
| Remediation Task Created | 100% | Per FAIL finding |
| Corporate Memory Logged | 100% | RED_TEAM_FINDING per FAIL |
| Zero Production DB Access | 100% | Audit log + DB connection check |
| Zero External Tools | 100% | requirements.txt/package.json clean |