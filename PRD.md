# PRODUCT REQUIREMENTS DOCUMENT
## NEXUS CORE (Satria Bahari AI Agency Orchestrator)

**Founder & Owner:** MUHAMMAD MUFTI ZAKA
**Versi:** v1.0 (Core Loop)
**Status:** Living Document

### SECTION 1: Problem Statement
**Masalah:** 
Membangun dan mengelola agensi software (Micro-SaaS) secara manual memakan waktu, rentan human error, dan margin kepotong biaya operasional. Founder (Muhammad Mufti Zaka) bekerja solo dari HP dan butuh sistem otomasi penuh.
**Solusi:** 
Sebuah backend orchestrator ("Nexus Core") yang menjalankan 19 AI Agent terstruktur dalam 6 divisi (Marketing, CS, Finance, Engineering, QA, Technical) untuk menangani siklus hidup proyek klien dari intake, costing, coding, audit, hingga billing, dengan approval akhir via Telegram.
**Data Pendukung (Asumsi Awal):**
- 1 Founder tidak mungkin handle 5 klien paralel secara manual tanpa burnout.
- Biaya LLM API bisa membengkak 10x lipat jika tidak ada "Circuit Breaker" dan pembagian tugas (Arsitek vs Kuli).

### SECTION 2: Goals
| ID | Tujuan | Metrik Kesuksesan |
|---|---|---|
| G1 | Otomasi Siklus Proyek | 1 proyek standar selesai dari Intake ke Deployment < 24 jam tanpa intervensi Founder (kecuali approval). |
| G2 | Proteksi Margin | Margin bersih proyek tetap > 70% setelah biaya API LLM dan Infra. |
| G3 | Zero Hallucination | 0 insiden di mana AI Agent menjanjikan fitur di luar kapabilitas atau memberi diskon di luar batas. |
| G4 | Mobile Operability | 100% approval (Deploy, Diskon, Bayar) bisa dilakukan Founder dari HP via Telegram. |

### SECTION 3: Target Users / Personas
| Persona | Deskripsi | Kebutuhan Utama |
|---|---|---|
| **Muhammad Mufti Zaka (Founder)** | Solo operator, kerja dari HP, otoritas tertinggi. | Dashboard simpel, notifikasi Telegram, kill-switch, laporan margin. |
| **Klien UMKM** | Pemilik bisnis non-teknis. | Solusi kasir/stok yang jujur, harga transparan, bahasa manusia (bukan robot). |
| **AI Agents (Internal)** | 19 Karyawan AI (Budi, Sari, Pak Harto, dll). | System prompt yang jelas, batas wewenang (JSON contracts), akses tools. |

### SECTION 4: User Stories
| ID | Pri | User Story |
|---|---|---|
| US-1 | P1 | Sebagai Founder, saya ingin menerima notifikasi Telegram berisi rincian HPP dan Harga Jual dari Pak Harto (Finance) agar saya bisa approve margin. |
| US-2 | P1 | Sebagai Sari (CS), saya ingin menanyakan requirement klien tanpa menggunakan bahasa "AI Slop" agar klien percaya ini dibantu manusia. |
| US-3 | P1 | Sebagai Mas Eko (Engineering Manager), saya ingin menerima JSON ProjectSpec dari CS agar saya bisa menyuruh Agus (Frontend) dan Bambang (Backend) bekerja. |
| US-4 | P1 | Sebagai Bang Jago (QA), saya ingin menolak kode dari Coder jika ditemukan celah keamanan, dan memaksanya mengulang (loop max 3x). |
| US-5 | P1 | Sebagai Sistem, saya ingin menghentikan proses (Circuit Breaker) jika API LLM gagal 3x berturut-turut agar token tidak terbakar sia-sia. |

### SECTION 5: Functional Requirements
| ID | Kebutuhan Sistem | Pri |
|---|---|---|
| FR-1 | **State Machine:** Sistem harus melacak status proyek: LEAD -> DISCOVERY -> QUOTED -> SIGNED -> BUILDING -> AUDITING -> DEPLOYED -> SUBSCRIPTION. | P1 |
| FR-2 | **Telegram Bot Integration:** Endpoint webhook untuk mengirim Approval Card ke Founder dan menerima callback (Approve/Reject). | P1 |
| FR-3 | **JSON Handoff Protocol:** Komunikasi antar divisi HANYA boleh lewat pertukaran JSON tervalidasi (Pydantic). | P1 |
| FR-4 | **Corporate Memory:** Database harus menyimpan `lessons_learned` pasca-proyek untuk disuntikkan ke prompt agen di masa depan. | P2 |
| FR-5 | **Mock-First External APIs:** Integrasi ke Tripay, Cloudflare, dan Vercel harus memiliki mode `MOCK` yang mengembalikan data dummy untuk testing. | P1 |

### SECTION 6: Non-Functional Requirements
| ID | Kebutuhan | Pri |
|---|---|---|
| NFR-1 | **Anti-Slop Text Generation:** Semua output teks ke klien (dari CS/Marketing) WAJIB lulus validasi `ANTI_SLOP_RULES.md`. | P1 |
| NFR-2 | **Token Circuit Breaker:** Jika 1 task memakan token > batas budget ($2), task di-pause dan Founder dinotifikasi. | P1 |
| NFR-3 | **Keamanan Secret:** API Keys tidak boleh hardcode di repo, wajib pakai Environment Variables. | P1 |

### SECTION 7: Scope (In/Out)
**In Scope v1.0:**
- Backend FastAPI (Python) sebagai Core Router.
- Database SQLite/Supabase untuk State & Memory.
- Integrasi Telegram Bot untuk Approval Founder.
- Mock API untuk Payment, Domain, dan Deployment.
**Out of Scope v1.0:**
- Trading Bot / EA MQL5 / Hedge Fund (DILARANG KERAS).
- Frontend Dashboard Web (Fokus ke Telegram UI dulu).
- Native Mobile App untuk Klien.