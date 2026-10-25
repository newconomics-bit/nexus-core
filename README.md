# RakitDigital
*Autonomous Custom Software Factory for Indonesian UMKM*

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)]()
[![Version](https://img.shields.io/badge/version-1.0.0-orange)]()

## Tentang

RakitDigital adalah perusahaan perangkat lunak otonom pertama untuk UMKM Indonesia. Kami mengubah chat WhatsApp klien menjadi software custom yang ter-deploy dalam hitungan jam — bukan bulan. Dengan 21 AI Agent yang bekerja sepenuh waktu, kami menawarkan software berkualitas enterprise dengan margin 75%+ dan waktu deploy yang tak tertandingi.

Platform kami dirancang untuk bisnis kecil dan menengah yang membutuhkan solusi digital: kasir, manajemen stok, laporan harian, dan aplikasi custom lainnya — tanpa ribetnya mengelola tim pengembang atau biaya infrastruktur yang mahal.

## Arsitektur

```text
     [ Klien UMKM ] --(WhatsApp)--> [ Sari, Wati, Dewi ]
                                          |
                                     [ FastAPI Core + DB ] <--(Telegram)--> [ Founder / Budi ]
                                          |
                                     [ Mas Eko, Agus, Bambang ] --> [ Deployed Web App ]
```

Alur kerja kami menggunakan **JSON Handoff Only**: setiap agen menulis hasil ke database, dan Core Router memicu agen berikutnya. Tidak ada panggilan fungsi langsung antar agen — memastikan audit trail yang lengkap dan auditable.

## Fitur Utama

- **QRIS Dinamis**: Pembayaran QRIS terintegrasi dengan verifikasi otomatis dan idempotensi.
- **AI Intake (Sari)**: Mengubah chat klien menjadi ProjectSpec yang valid dalam hitungan detik.
- **Auto-Contract (Bu Ratna)**: Generate kontrak hukum dari template, tracking tanda tangan, dan reminder otomatis.
- **Red Team Security (Si Merah)**: 10 skenario serangan mingguan di isolated environment untuk menguji pertahanan.
- **Quality Gate (Bang Jago)**: Text, Visual, SAST, DAST, dan DB audit sebelum setiap output dikirim ke klien.
- **Billing & Dunning (Wati)**: SOP penagihan otomatis (H+3, H+7, H+14, H+30) tanpa skip.
- **Customer Success (Dewi)**: Onboarding, health score, dan churn prevention.
- **Marketing (Rina & Lina)**: Kampanye, positioning, dan lead generation etis.
- **Disaster Recovery (Om Tono)**: Backup harian 02:00, DR drill quarterly, dan watchdog real-time.

## Tech Stack

- **Backend**: Python 3.10+, FastAPI (Async)
- **Frontend**: React, Tailwind CSS
- **Database**: SQLite (dev), Supabase (production)
- **Validation**: Pydantic
- **LLM**: OpenRouter (Claude, DeepSeek, Qwen)
- **Deployment**: Vercel (frontend), Supabase (backend/DB)

## Filosofi

Kami beroperasi berdasarkan **7 Legenda Mindset** sebagai DNA perusahaan:
- **Warren Buffett**: Margin of Safety > 60%, fokus recurring revenue.
- **Jeff Bezos**: Hapus friction, putar flywheel, Day 1 mentality.
- **George Soros**: Cari asumsi yang salah, uji sistem dengan reflexivity.
- **Timothy Ronald**: Jual leverage (sistem), bukan waktu.
- **Chairul Tanjung**: Kecepatan eksekusi > kesempurnaan teoritis, Cash is King.
- **Prajogo Pangestu**: Resiliensi jangka panjang, vertical integration.
- **Hermanto Tanoko**: Obsesi pada detail, zero tolerance for slop.

Maskot kami adalah **Bang Lele** — simbol ketangguhan dan kemampuan bertahan di semua kondisi.

## Cara Menjalankan (Untuk Developer Internal)

```bash
# Clone repository
git clone https://github.com/newconomics-bit/nexus-core.git
cd nexus-core

# Install dependencies
pip install -r requirements.txt

# Jalankan development server
uvicorn main:app --reload
```

Server akan berjalan di `http://localhost:8000`. Dokumentasi API tersedia di `/docs`.

## Footer

Dibangun dengan ☕ dan 🐟 oleh Muhammad Mufti Zaka.