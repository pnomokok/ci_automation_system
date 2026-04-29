# Repository Manager

Bu modul, CI otomasyon sistemi icinde GitHub `push` webhook olaylarini alir,
istek imzasini dogrular, branch bilgisini filtreler, commit verisini ayiklar
ve Orchestrator icin pipeline tetikleme verisini hazirlar.

## Dokumana gore temel sorumluluklar

- `POST /webhook` endpointi ile GitHub webhook istegini almak
- `X-Hub-Signature-256` basligini HMAC-SHA256 ile dogrulamak
- Gecersiz imzada `401`, bozuk istekte `400` donmek
- Push payload icinden branch, commit hash, commit mesaji ve yazar bilgisini ayiklamak
- Izinli branch kontrolu yapmak
- Orchestrator'a pipeline tetikleme verisi uretmek
- Gerekirse manuel tetiklemeyi desteklemek

## Klasor yapisi

```text
repo-manager/
  ci-config.yaml
  INTEGRATION.md
  integration/
    mock_orchestrator.py
    trigger_request.json
    webhook_payload.json
  app/
    __init__.py
    API/
      __init__.py
      webhook.py
      trigger.py
    webhook_receiver.py
    signature_validator.py
    git_client.py
    branch_filter.py
    commit_parser.py
    trigger_handler.py
  tests/
    test_branch_filter.py
    test_commit_parser.py
    test_signature_validator.py
    test_webhook_receiver.py
  requirements.txt
  Dockerfile
  .env.example
```

## Ortam degiskenleri

- `GITHUB_WEBHOOK_SECRET`: GitHub webhook secret degeri
- `ORCHESTRATOR_URL`: Orchestrator temel adresi. Varsayilan: `http://localhost:8000`
- `WORKSPACE_ROOT`: Repo kopyalarinin tutulacagi kok klasor. Varsayilan: `/shared/workspaces`

## `ci-config.yaml`

Repo Manager branch kurallarini ve calisma ayarlarini repo kokundeki
`ci-config.yaml` dosyasindan okuyabilir. Desteklenen temel alanlar:

```yaml
branches:
  - main
  - develop
image: python:3.11
stages:
  - name: install
    commands:
      - pip install -r requirements.txt
  - name: test
    commands:
      - pytest
env:
  APP_ENV: test
timeout_sec: 600
```

Bu dosya yoksa varsayilanlar kullanilir:

- `branches`: `main`, `develop`
- `image`: `python:3.11`
- `stages`: bos liste
- `env`: bos sozluk
- `timeout_sec`: `600`

Repo kokunde ornek bir [ci-config.yaml](C:\Users\Lenovo\Desktop\ci_automation_system\repo-manager\ci-config.yaml)
dosyasi bulunur. Bunu test reposunda ihtiyaca gore duzenleyebilirsin.

## Endpointler

### `POST /webhook`

Beklenen basliklar:

- `X-GitHub-Event: push`
- `X-Hub-Signature-256: sha256=...`
- `Content-Type: application/json`

Beklenen sonuc:

- Webhook dogrulanir
- Push bilgisi ayrisir
- Branch uygun ise pipeline tetikleme verisi hazirlanir
- Hazirlanan veri Orchestrator'a iletilir
- Sistem `queued` durumu ile cevap verir ve `repo_url`, `branch`,
  `commit_hash`, `commit_msg`, `workspace`, `ci_config` alanlarini doner
- Orchestrator erisilemiyorsa `502` doner

### `POST /trigger`

Manuel tetikleme icin kullanilir. Dokumandaki akisla uyumlu olacak sekilde
Orchestrator bu endpoint'e `repo_url` ve `branch` gonderir. Repo Manager ilgili
repo klasorunu hazirlar, pipeline istegini Orchestrator'a iletir ve asagidaki
alanlari dondurur:

- `repo_url`
- `branch`
- `commit_hash`
- `commit_msg`
- `workspace`
- `ci_config`
- Repo hazirlanamazsa `500`, Orchestrator erisilemiyorsa `502` doner

## Calistirma

```bash
uvicorn app.webhook_receiver:app --reload --host 0.0.0.0 --port 8081
```

## Test

```bash
pytest
```

## Entegrasyon hazirligi

Yerel entegrasyon testi icin [INTEGRATION.md](C:\Users\Lenovo\Desktop\ci_automation_system\repo-manager\INTEGRATION.md)
dosyasini kullanabilirsin. Bu dosyada:

- mock Orchestrator calistirma
- ornek trigger istegi
- ornek webhook payload'i
- imza uretme adimlari

hazir durumda bulunur.
