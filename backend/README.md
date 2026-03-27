# Exam Recognition Backend

FastAPI + MySQL backend for Word/PDF exam recognition.

## 1) Database

```sql
mysql -uroot -proot < sql/schema.sql
```

Default DB URL:

```text
mysql+pymysql://root:root@127.0.0.1:3306/exam_recognition?charset=utf8mb4
```

## 2) Install

```bash
cd backend
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3) Run

Windows:

```powershell
.\scripts\run_windows.ps1
```

Linux:

```bash
chmod +x ./scripts/run_linux.sh
./scripts/run_linux.sh
```

Service URL: `http://127.0.0.1:8001`
Swagger: `http://127.0.0.1:8001/docs`

## 4) API Overview

- `POST /api/v1/recognitions/upload`
- `GET /api/v1/recognitions/tasks/{taskId}`
- `GET /api/v1/recognitions/tasks/{taskId}/result`
- `GET /api/v1/recognitions/tasks/{taskId}/details`
- `POST /api/v1/rule-profiles`
- `GET /api/v1/rule-profiles`
- `PUT /api/v1/rule-profiles/{id}`
