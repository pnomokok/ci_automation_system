# CI Otomasyon Sistemi — Claude Session Rehberi

## Proje Özeti

**Ders:** CENG314 Yazılım Mühendisliği  
**Proje:** GitHub push'larında otomatik derleme/test çalıştıran CI sistemi  
**Bizim Rolümüz:** Kişi 1 — Irmak · CI Orchestrator & API  
**GitHub Repo:** https://github.com/pnomokok/ci_automation_system.git  
**Yerel Konum:** `C:\Users\suyil\Desktop\CI\ci_automation_system\`

---

## Sistemin 4 Modülü (Genel Bakış)

| Modül | Sahip | Klasör | Teknoloji |
|---|---|---|---|
| **CI Orchestrator** | **Kişi 1 - Irmak (BİZ)** | `orchestrator/` | FastAPI, PostgreSQL, SQLAlchemy, Alembic, Redis, JWT |
| Runner | Kişi 2 - Aleyna | `runner/` | Python, Docker SDK, Redis |
| Repository Manager | Kişi 3 - Zeynep Sude | `repo-manager/` | FastAPI, GitPython, HMAC-SHA256 |
| Web Dashboard | Kişi 4 - Rabia | `dashboard/` | React, Axios, TailwindCSS |

**Kritik:** Orchestrator API tüm ekibe bağımlılık noktası — biz önce bitirmeliyiz.

---

## Bizim Modülümüz: CI Orchestrator

### Klasör Yapısı (hedef)

```
orchestrator/
├── app/
│   ├── main.py                  # FastAPI app, lifespan, CORS
│   ├── api/
│   │   ├── pipelines.py         # Pipeline CRUD endpoint'leri
│   │   ├── repositories.py      # Repo kayıt endpoint'leri
│   │   ├── auth.py              # Login / refresh
│   │   └── internal/
│   │       ├── steps.py         # Runner → PATCH step durumu, POST log
│   │       └── pipelines.py     # Runner → PATCH pipeline durumu
│   ├── services/
│   │   ├── pipeline_service.py  # İş mantığı, durum makinesi
│   │   ├── step_service.py
│   │   └── log_service.py
│   ├── repositories/
│   │   ├── pipeline_repo.py     # SQLAlchemy sorgular
│   │   ├── step_repo.py
│   │   ├── log_repo.py
│   │   └── repository_repo.py
│   ├── schemas/
│   │   ├── pipeline.py          # Pydantic istek/yanıt modelleri
│   │   ├── step.py
│   │   ├── log.py
│   │   └── auth.py
│   ├── models/
│   │   ├── pipeline.py          # SQLAlchemy ORM tabloları
│   │   ├── step.py
│   │   ├── log.py
│   │   ├── repository.py
│   │   └── user.py
│   └── core/
│       ├── config.py            # Ortam değişkenleri (Settings)
│       ├── security.py          # JWT encode/decode
│       ├── database.py          # SQLAlchemy engine, session
│       ├── redis.py             # Redis bağlantısı
│       └── deps.py              # FastAPI bağımlılıkları (get_db, get_current_user)
├── migrations/                  # Alembic migration dosyaları
├── tests/                       # Birim testler (%70 coverage hedefi)
├── Dockerfile
└── requirements.txt
```

### Veritabanı Tabloları

**pipelines:** id(uuid), repo_id, repo_url, branch, commit_hash, commit_msg, commit_author, trigger_type, status, started_at, finished_at, duration_sec, created_at  
**steps:** id(uuid), pipeline_id, name(install|build|test), order, status, started_at, finished_at, duration_sec, exit_code  
**logs:** id(uuid), step_id, line_number, stream(stdout|stderr), timestamp, content  
**repositories:** id(uuid), url, default_branch, webhook_secret, created_at  
**users:** id(uuid), username, hashed_password, created_at

### Durum Makinesi

```
Pipeline: QUEUED → RUNNING → SUCCESS
                           → FAILED
                           → STOPPED  (POST /pipelines/{id}/stop ile)

Step:     PENDING → RUNNING → SUCCESS
                            → FAILED
```

---

## Interface Contract v1.0 (tam endpoint listesi)

Base URL: `http://localhost:8000`  Prefix: `/api/v1`

### Authentication (JWT Bearer)
```
POST /api/v1/auth/login    → {access_token, token_type, expires_in}
POST /api/v1/auth/refresh
```

### Pipeline Endpoint'leri (Authorization: Bearer <token>)
```
GET  /api/v1/pipelines?page=1&page_size=20&status=&repo_id=
     → {items:[{id,repo_id,repo_url,branch,commit_hash,trigger_type,status,started_at,finished_at,duration_sec}], total, page, page_size}

POST /api/v1/pipelines
     body: {repo_url, branch}
     → 201 {id, status:"QUEUED", trigger_type:"manual", branch, created_at}

GET  /api/v1/pipelines/{id}
     → {id,repo_id,repo_url,branch,commit_hash,commit_msg,commit_author,trigger_type,status,started_at,finished_at,duration_sec,
        steps:[{id,name,order,status,started_at,finished_at,duration_sec,exit_code}]}

POST /api/v1/pipelines/{id}/stop
     → 200 {pipeline_id, status:"STOPPED"}

GET  /api/v1/pipelines/{id}/logs?step_name=&page=1&page_size=100&stream=
     → {pipeline_id, items:[{step_id,step_name,line_number,stream,timestamp,content}], total, page, page_size}

GET  /api/v1/pipelines/{id}/report
     → {pipeline_id, status, total_tests, passed, failed, skipped, duration_sec}
```

### Repository Endpoint'leri (JWT gerekli)
```
GET    /api/v1/repositories
POST   /api/v1/repositories
       body: {url, default_branch, webhook_secret}
       → 201 {id, url, default_branch, created_at}
DELETE /api/v1/repositories/{id}
```

### Internal Endpoint'ler (JWT YOK — sadece Runner çağırır)
```
PATCH /api/v1/internal/steps/{step_id}
      body: {status, exit_code, started_at, finished_at}
      → 200 {step_id, status}

POST  /api/v1/internal/steps/{step_id}/logs
      body: {lines:[{line_number,stream,timestamp,content}]}
      → 201 {saved: N}

PATCH /api/v1/internal/pipelines/{pipeline_id}
      body: {status, finished_at}
      → 200 {pipeline_id, status}
```

### Standart Hata Formatı
```json
{"error": {"code": "PIPELINE_NOT_FOUND|INVALID_INPUT|UNAUTHORIZED|...", "message": "...", "detail": "..."}}
```
HTTP kodları: 400→INVALID_INPUT, 401→UNAUTHORIZED, 403→FORBIDDEN, 404→PIPELINE_NOT_FOUND, 409→ALREADY_RUNNING, 422→VALIDATION_ERROR, 500→INTERNAL_ERROR

### Redis Kuyruğu
Kuyruk adı: `pipeline_jobs`  
Orchestrator push'lar, Runner okur:
```json
{
  "pipeline_id": "uuid",
  "repo_url": "https://...",
  "branch": "main",
  "commit_hash": "abc123",
  "workspace": "/shared/workspaces/<pipeline_id>",
  "steps": ["install","build","test"],
  "step_ids": {"install":"uuid-1","build":"uuid-2","test":"uuid-3"},
  "timeout_sec": 600
}
```

---

## Repo Manager'dan Gelen İstek Formatı (biz alıyoruz)

Repo Manager, webhook geldiğinde bize şunu gönderir:
```
POST /api/v1/pipelines
{
  "repo_url": "...",
  "branch": "main",
  "commit_hash": "...",
  "commit_msg": "...",
  "commit_author": "...",
  "trigger_type": "webhook"
}
```

---

## Ortak Veri Tipleri

- **Tüm tarihler:** ISO 8601 UTC milisaniye — `"2026-04-26T10:00:06.123Z"`
- **Tüm ID'ler:** UUID v4 — `"550e8400-e29b-41d4-a716-446655440000"`
- **/api/v1/internal/...** → JWT YOK (aynı Docker ağı içinde servis-servis)
- **/api/v1/...** → JWT zorunlu (Dashboard ve dış dünya)
- **/webhook** → HMAC-SHA256 (Repo Manager yönetir, bizi ilgilendirmez)

---

## Git Kuralları

**Branch:** `feature/orchestrator-<özellik>` → `develop` → `main`  
**Commit:** `feat(orchestrator): ...` / `fix(orchestrator): ...` / `test(orchestrator): ...`  
**PR:** develop'a merge için en az 1 code review, CI testler geçmeli  
**Kural:** Yalnızca `orchestrator/` klasörüne yazıyoruz. `docker-compose.yml` ve `.env.example` değişikliklerinde ekiple koordinasyon.

---

## Görev Listesi (Implementasyon Rehberi'nden)

- [x] FastAPI uygulama iskeletini kur (main.py, router yapısı)
- [x] PostgreSQL veritabanı şemasını oluştur (pipelines, steps, logs, repositories, users tabloları)
- [x] Alembic migration dosyalarını yaz
- [x] SQLAlchemy ORM modellerini tanımla
- [x] Pipeline CRUD API endpoint'lerini geliştir (GET/POST /pipelines, GET /pipelines/{id})
- [x] Pipeline durum makinesini geliştir (QUEUED→RUNNING→SUCCESS/FAILED/STOPPED)
- [x] Pipeline durdurma endpoint'ini geliştir (POST /pipelines/{id}/stop)
- [x] Log görüntüleme endpoint'ini geliştir (GET /pipelines/{id}/logs)
- [x] Test raporu endpoint'ini geliştir (GET /pipelines/{id}/report)
- [x] Redis kuyruğu entegrasyonu (pipeline'ları kuyruğa ekleme, eşzamanlılık limiti)
- [x] Runner'dan gelen adım sonuçlarını alan internal endpoint'leri geliştir
- [x] JWT tabanlı kimlik doğrulama sistemini kur
- [x] OpenAPI/Swagger dokümantasyonunun otomatik oluşturulduğunu doğrula
- [x] Orchestrator için birim testleri yaz (%75 coverage — hedef %70 aşıldı, 38 test)
- [x] docker-compose.yml'de orchestrator servisini tanımla

## Kalan İş

~~Tüm görevler tamamlandı.~~

> Son güncelleme: 2026-04-28 — Orchestrator modülü %100 teslime hazır
