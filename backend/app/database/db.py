import sqlite3
import os
from typing import List, Optional, Dict, Any
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "jobs.db")

def get_db_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        external_id TEXT,
        source TEXT NOT NULL,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        location TEXT NOT NULL,
        city TEXT,
        state TEXT DEFAULT 'RS',
        work_model TEXT DEFAULT 'Não Informado',
        category TEXT DEFAULT 'outro',
        role_matched TEXT,
        description TEXT,
        salary TEXT DEFAULT 'A combinar / Não informado',
        url TEXT NOT NULL,
        match_score INTEGER DEFAULT 50,
        status TEXT DEFAULT 'nova',
        notes TEXT DEFAULT '',
        is_favorite INTEGER DEFAULT 0,
        published_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        dedup_hash TEXT UNIQUE
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scrape_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        source TEXT NOT NULL,
        jobs_found INTEGER DEFAULT 0,
        new_jobs INTEGER DEFAULT 0,
        status TEXT NOT NULL,
        error_message TEXT
    );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_city ON jobs(city);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_category ON jobs(category);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_dedup_hash ON jobs(dedup_hash);")
    
    conn.commit()
    conn.close()

def compute_dedup_hash(title: str, company: str, location: str, url: str) -> str:
    import hashlib
    norm_title = "".join(e for e in title.lower() if e.isalnum())
    norm_company = "".join(e for e in company.lower() if e.isalnum())
    norm_location = "".join(e for e in location.lower() if e.isalnum())
    raw = f"{norm_title}|{norm_company}|{norm_location}"
    if not norm_company or norm_company == "empresaconfidencial":
        raw += f"|{url}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def insert_job(job_data: Dict[str, Any]) -> Optional[int]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    dedup_hash = job_data.get("dedup_hash") or compute_dedup_hash(
        job_data["title"],
        job_data.get("company", ""),
        job_data.get("location", ""),
        job_data["url"]
    )
    
    now = datetime.now().isoformat()
    try:
        cursor.execute("""
        INSERT INTO jobs (
            external_id, source, title, company, location, city, state,
            work_model, category, role_matched, description, salary, url,
            match_score, status, notes, is_favorite, published_at,
            created_at, updated_at, dedup_hash
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """, (
            job_data.get("external_id"),
            job_data["source"],
            job_data["title"],
            job_data.get("company", "Empresa não informada"),
            job_data.get("location", ""),
            job_data.get("city"),
            job_data.get("state", "RS"),
            job_data.get("work_model", "Não Informado"),
            job_data.get("category", "outro"),
            job_data.get("role_matched"),
            job_data.get("description", ""),
            job_data.get("salary", "A combinar / Não informado"),
            job_data["url"],
            job_data.get("match_score", 50),
            job_data.get("status", "nova"),
            job_data.get("notes", ""),
            1 if job_data.get("is_favorite") else 0,
            job_data.get("published_at") or "Recente",
            now,
            now,
            dedup_hash
        ))
        conn.commit()
        inserted_id = cursor.lastrowid
        return inserted_id
    except sqlite3.IntegrityError:
        return None
    except Exception as e:
        return None
    finally:
        conn.close()

def get_jobs(
    category: Optional[str] = None,
    city: Optional[str] = None,
    status: Optional[str] = None,
    work_model: Optional[str] = None,
    search: Optional[str] = None,
    only_favorites: bool = False,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM jobs WHERE 1=1"
    params = []
    
    if category and category != "todas":
        query += " AND category = ?"
        params.append(category)
        
    if city and city != "todas":
        query += " AND (city LIKE ? OR location LIKE ?)"
        params.append(f"%{city}%")
        params.append(f"%{city}%")
        
    if status and status != "todas":
        query += " AND status = ?"
        params.append(status)
        
    if work_model and work_model != "todos":
        query += " AND work_model = ?"
        params.append(work_model)
        
    if only_favorites:
        query += " AND is_favorite = 1"
        
    if search:
        search_term = f"%{search}%"
        query += " AND (title LIKE ? OR company LIKE ? OR description LIKE ? OR role_matched LIKE ? OR source LIKE ?)"
        params.extend([search_term, search_term, search_term, search_term, search_term])
        
    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    jobs = [dict(row) for row in rows]
    conn.close()
    return jobs

def get_job_by_id(job_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_job(job_id: int, updates: Dict[str, Any]) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    fields = []
    values = []
    for k, v in updates.items():
        if k in ("status", "notes", "is_favorite", "category", "salary"):
            fields.append(f"{k} = ?")
            values.append(1 if isinstance(v, bool) and v else 0 if isinstance(v, bool) else v)
            
    if not fields:
        conn.close()
        return False
        
    fields.append("updated_at = ?")
    values.append(datetime.now().isoformat())
    values.append(job_id)
    
    query = f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(query, values)
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated

def delete_job(job_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted

def get_stats() -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = cursor.fetchone()[0]
    
    cursor.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status")
    by_status = dict(cursor.fetchall())
    
    cursor.execute("SELECT category, COUNT(*) FROM jobs GROUP BY category")
    by_category = dict(cursor.fetchall())
    
    cursor.execute("SELECT city, COUNT(*) FROM jobs WHERE city IS NOT NULL GROUP BY city")
    by_city = dict(cursor.fetchall())
    
    cursor.execute("SELECT source, COUNT(*) FROM jobs GROUP BY source")
    by_source = dict(cursor.fetchall())
    
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE date(created_at) = date('now')")
    today_jobs = cursor.fetchone()[0]

    conn.close()
    return {
        "total_jobs": total_jobs,
        "today_jobs": today_jobs,
        "by_status": by_status,
        "by_category": by_category,
        "by_city": by_city,
        "by_source": by_source
    }

def log_scrape(source: str, jobs_found: int, new_jobs: int, status: str, error_message: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO scrape_logs (timestamp, source, jobs_found, new_jobs, status, error_message)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        source,
        jobs_found,
        new_jobs,
        status,
        error_message
    ))
    conn.commit()
    conn.close()
