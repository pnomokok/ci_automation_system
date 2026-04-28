# Orchestrator Modülü — Geliştirici Rehberi

**Sahip:** Kişi 1 - Irmak  
**Teknoloji:** Python 3.11+, FastAPI, PostgreSQL, SQLAlchemy, Alembic, Pydantic, Redis, JWT  
**Port:** 8000  
**Üst seviye bağlam için:** `../CLAUDE.md` dosyasını oku.

---

## Klasör Yapısı

```
orchestrator/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── pipelines.py
│   │   ├── repositories.py
│   │   ├── auth.py
│   │   └── internal/
│   │       ├── __init__.py
│   │       ├── steps.py
│   │       └── pipelines.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── pipeline_service.py
│   │   ├── step_service.py
│   │   └── log_service.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── pipeline_repo.py
│   │   ├── step_repo.py
│   │   ├── log_repo.py
│   │   └── repository_repo.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── pipeline.py
│   │   ├── step.py
│   │   ├── log.py
│   │   └── auth.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── pipeline.py
│   │   ├── step.py
│   │   ├── log.py
│   │   ├── repository.py
│   │   └── user.py
│   └── core/
│       ├── __init__.py
│       ├── config.py
│       ├── security.py
│       ├── database.py
│       ├── redis.py
│       └── deps.py
├── migrations/
│   ├── env.py
│   └── versions/
├── tests/
│   ├── conftest.py
│   ├── test_pipelines.py
│   ├── test_auth.py
│   └── test_internal.py
├── Dockerfile
└── requirements.txt
```

---

## Ortam Değişkenleri (.env)

```env
DATABASE_URL=postgresql+asyncpg://ci_user:ci_pass@postgres:5432/ci_db
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=<güçlü-rastgele-anahtar>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
ORCHESTRATOR_HOST=http://orchestrator:8000
MAX_CONCURRENT_PIPELINES=3
```

---

## SQLAlchemy Modelleri (Özet Şema)

### pipelines
| Sütun | Tip | Not |
|---|---|---|
| id | UUID | PK, default uuid4 |
| repo_id | UUID | FK repositories.id |
| repo_url | String | |
| branch | String | |
| commit_hash | String | nullable |
| commit_msg | String | nullable |
| commit_author | String | nullable |
| trigger_type | Enum | webhook / manual |
| status | Enum | QUEUED/RUNNING/SUCCESS/FAILED/STOPPED |
| started_at | DateTime | nullable |
| finished_at | DateTime | nullable |
| duration_sec | Integer | nullable |
| created_at | DateTime | default utcnow |

### steps
| Sütun | Tip | Not |
|---|---|---|
| id | UUID | PK |
| pipeline_id | UUID | FK pipelines.id |
| name | Enum | install / build / test |
| order | Integer | 1, 2, 3 |
| status | Enum | PENDING/RUNNING/SUCCESS/FAILED |
| started_at | DateTime | nullable |
| finished_at | DateTime | nullable |
| duration_sec | Integer | nullable |
| exit_code | Integer | nullable |

### logs
| Sütun | Tip | Not |
|---|---|---|
| id | UUID | PK |
| step_id | UUID | FK steps.id |
| line_number | Integer | |
| stream | Enum | stdout / stderr |
| timestamp | DateTime | milisaniye hassas |
| content | Text | |

### repositories
| Sütun | Tip | Not |
|---|---|---|
| id | UUID | PK |
| url | String | unique |
| default_branch | String | |
| webhook_secret | String | |
| created_at | DateTime | |

### users
| Sütun | Tip | Not |
|---|---|---|
| id | UUID | PK |
| username | String | unique |
| hashed_password | String | bcrypt |
| created_at | DateTime | |

---

## Pipeline Durum Makinesi

```
Oluşturulunca     → QUEUED
Runner alınca     → RUNNING
Tüm adım başarılı → SUCCESS
Herhangi adım fail → FAILED (kalan adımlar çalıştırılmaz)
POST /stop çağrılınca → STOPPED (container kill sinyali Redis'e yaz)
```

Stop sinyali: Orchestrator, `pipeline_stop:<pipeline_id>` anahtarını Redis'e yazar. Runner bu anahtarı polling ile kontrol eder.

---

## Redis Entegrasyonu

### Orchestrator → Runner (iş kuyruğu)
```python
# Kuyruk adı: "pipeline_jobs"
# Orchestrator push'lar, Runner BLPOP ile okur
await redis.rpush("pipeline_jobs", json.dumps({
    "pipeline_id": str(pipeline.id),
    "repo_url": pipeline.repo_url,
    "branch": pipeline.branch,
    "commit_hash": pipeline.commit_hash,
    "workspace": f"/shared/workspaces/{pipeline.id}",
    "steps": ["install", "build", "test"],
    "step_ids": {
        "install": str(steps[0].id),
        "build":   str(steps[1].id),
        "test":    str(steps[2].id),
    },
    "timeout_sec": 600
}))
```

### Stop sinyali
```python
# Orchestrator yazar
await redis.set(f"pipeline_stop:{pipeline_id}", "1", ex=3600)
# Runner kontrol eder
```

### Eşzamanlılık limiti
```python
# MAX_CONCURRENT_PIPELINES kadar pipeline aynı anda RUNNING olabilir
# Orchestrator, Redis'teki "running_count" sayacını yönetir
```

---

## JWT

```python
# Payload
{"sub": str(user.id), "username": user.username, "exp": datetime.utcnow() + timedelta(minutes=60)}

# Header
Authorization: Bearer <token>

# Internal endpoint'ler (/api/v1/internal/*) JWT kontrolü yapmaz
# Sadece aynı Docker ağından erişilebilir
```

---

## Önemli Tasarım Kararları

1. **Async-first:** SQLAlchemy `asyncpg` driver ile async kullan. `async_sessionmaker` kullan.
2. **Repository pattern:** Service katmanı doğrudan ORM kullanmaz; repository sınıfları üzerinden gider.
3. **Internal endpoint'ler ayrı router'da:** `/api/v1/internal` prefix'li endpoint'ler ayrı bir router'da, JWT middleware uygulanmaz.
4. **Pagination:** Tüm liste endpoint'leri `page` + `page_size` parametreli; page_size maks 100 (logs için 500).
5. **Stop mekanizması:** Container kill Orchestrator'ın değil Runner'ın işi; Orchestrator sadece Redis'e sinyal yazar.

---

## Test Stratejisi (%70 Coverage)

```
tests/
├── conftest.py          # TestClient, test DB (SQLite in-memory), override deps
├── test_auth.py         # Login, token refresh, invalid credentials
├── test_pipelines.py    # CRUD, durum geçişleri, stop, logs, report
├── test_repositories.py # Repo ekleme/listeleme/silme
└── test_internal.py     # Step güncelleme, log gönderme, pipeline güncelleme
```

---

## Geliştirme Sırası (önerilen)

1. `core/config.py`, `core/database.py`, `core/redis.py` — altyapı
2. `models/` — ORM modelleri
3. Alembic migration (initial)
4. `schemas/` — Pydantic modeller
5. `repositories/` — DB erişim katmanı
6. `core/security.py` + `api/auth.py` — JWT auth
7. `api/pipelines.py` + `services/pipeline_service.py` — pipeline CRUD
8. Redis kuyruk push'u
9. `api/internal/steps.py` + `api/internal/pipelines.py` — Runner callback'leri
10. `api/repositories.py`
11. Testler
12. Dockerfile + docker-compose.yml girişi

---

## Bağımlılık Matrisi

| Modül | Bizden Ne Bekliyor? |
|---|---|
| Runner (Aleyna) | PATCH /internal/steps/{id}, POST /internal/steps/{id}/logs, PATCH /internal/pipelines/{id} — bu 3 endpoint olmadan Runner test edemez |
| Repo Manager (Zeynep Sude) | POST /api/v1/pipelines — webhook tetiklemesi için |
| Dashboard (Rabia) | Tüm public endpoint'ler + JWT auth |

**Öncelik:** Internal endpoint'leri ve temel pipeline CRUD'u erkenden aç ki diğerleri mock olmadan test edebilsin.
