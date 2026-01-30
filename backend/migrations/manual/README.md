# Manual SQL Migrations

수동으로 실행하는 SQL 스크립트 모음입니다.

## 실행 방법

### PostgreSQL psql 사용

```bash
# 1. PostgreSQL 접속
psql -U postgres -d shorts_producer

# 2. SQL 파일 실행
\i backend/migrations/manual/001_make_storyboard_id_required.sql
```

### psycopg2 사용 (Python)

```python
import psycopg2
from pathlib import Path

conn = psycopg2.connect(
    host="localhost",
    database="shorts_producer",
    user="postgres",
    password="your_password"
)

sql_file = Path("backend/migrations/manual/001_make_storyboard_id_required.sql")
with conn.cursor() as cur:
    cur.execute(sql_file.read_text())
    conn.commit()
```

### DBeaver / pgAdmin

1. SQL 파일 내용 복사
2. Query Editor에 붙여넣기
3. 실행 (F5)

---

## Migration 이력

| 파일 | 날짜 | 설명 |
|------|------|------|
| 001_make_storyboard_id_required.sql | 2026-01-30 | activity_logs.storyboard_id를 NOT NULL로 변경 |
