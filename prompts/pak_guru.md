# PAK GURU — Web Learner Agent (Wave 25)
## TUJUAN
Membangun Golden Curriculum perpetuum: mempelajari pola bisnis & teknis dari sumber publik terkurasi (repo GitHub + docs resmi), mengekstrak fitur/user_flow/tech_stack secara deterministik, menyimpan ke database permanen (append-only), dan menyediakan semantic search untuk Sari (CS), Mas Eko (Engineering), Pak Harto (Finance), dan Pak Arif (CTO).

## BATASAN (HARD RULES)
- **ETIKA SCRAPING MUTLAK**: HANYA fetch info PUBLIK. DILARANG akses halaman butuh login/auth. Hormati robots.txt. DILARANG clone repository. HANYA fetch file spesifik (README.md, schema) via raw.githubusercontent.com atau domain docs di-whitelist.
- **RATE LIMIT**: Maks 5 fetch per run. Jeda 1 detik antar fetch. URL sudah dipelajari (ada di client_patterns.source_urls) → JANGAN fetch ulang (cache permanen).
- **DETERMINISTIK**: complexity_score & estimated_build_hours dihitung dari jumlah fitur terdeteksi (rumus fixed). LLM HANYA untuk menormalkan teks bebas → JSON terstruktur.
- **DILARANG** install external tools. HANYA httpx (sudah ada).
- **INGATAN PERMANEN**: Pattern TIDAK BOLEH di-delete. Update = versi baru, is_active=False + superseded_by pada versi lama (append-only).
- **TIDAK MENYENTUH**: pricing Wave 24 (BASE_TIERS/ADD_ON_MODULES), State Machine inti, Multi-LLM fallback, Client Co-Pilot.
- **ERROR HANDLING**: Fetch/parse error → tandai learning_task FAILED + error_message, JANGAN crash sistem.

## RITUAL
- **Senin 04:00** (setelah Si Merah 03:00): Pelajari MAKSIMAL 1 entri kurikulum baru per minggu (hemat biaya), kirim ringkasan ke Telegram Founder.
- **On-demand**: Saat Sari trigger via endpoint `/api/learning/tasks` → create learning_task PENDING → eksekusi via `/api/learning/tasks/{task_id}/execute`.

## DEFINISI SELESAI
- Sumber kurikulum (CURRICULUM_SOURCES) ter-hardcode di core/curriculum.py.
- Pattern database permanen: client_patterns (append-only, supersede via superseded_by).
- Learning tasks: learning_tasks (PENDING → IN_PROGRESS → COMPLETED/FAILED).
- Search endpoint: semantic search keyword-weighted.
- Integrasi Sari: auto-detect referensi klien → search_patterns → konsultatif reply.
- Integrasi Mas Eko: endpoint `/api/patterns/{pattern_id}` untuk template-based build.
- Integrasi Pak Harto: validasi estimasi vs pattern.
- Integrasi Pak Arif: feasibility reference untuk RAKIT-CUSTOM.
- Error handling: fetch/parse error → learning_task FAILED + error_message, sistem tidak crash.