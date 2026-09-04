import sqlite3
import os
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA_DIR = os.path.join(ROOT_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "jobs.db")
DEFAULT_JSON_PATH = os.path.join(DATA_DIR, "jobs.json")

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
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_external_id ON jobs(external_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_url ON jobs(url);")
    
    conn.commit()
    conn.close()

def normalize_url(url: str) -> str:
    if not url:
        return ""
    u = url.strip().split('#')[0].split('?')[0].rstrip('/')
    if u.startswith("http://"):
        u = "https://" + u[7:]
    return u

def compute_dedup_hash(title: str, company: str, location: str, url: str) -> str:
    import hashlib
    norm_title = "".join(e for e in (title or "").lower() if e.isalnum())
    norm_company = "".join(e for e in (company or "").lower() if e.isalnum())
    norm_location = "".join(e for e in (location or "").lower() if e.isalnum())
    norm_url = normalize_url(url)
    raw = f"{norm_title}|{norm_company}|{norm_location}"
    if not norm_company or norm_company in ("empresaconfidencial", "confidencial"):
        raw += f"|{norm_url}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def find_existing_job(cursor: sqlite3.Cursor, external_id: Optional[str], url: str, dedup_hash: str) -> Optional[sqlite3.Row]:
    """
    Localiza uma vaga já listada usando múltiplos critérios:
    1. external_id (ex: tb_9090994 no Trabalha Brasil)
    2. URL limpa normalizada
    3. Hash de conteúdo (título + empresa + localização)
    """
    if external_id:
        cursor.execute("SELECT * FROM jobs WHERE external_id = ?", (external_id,))
        row = cursor.fetchone()
        if row:
            return row

    norm_u = normalize_url(url)
    if norm_u:
        cursor.execute("SELECT * FROM jobs WHERE url = ? OR url = ? OR url LIKE ?", (url, norm_u, f"{norm_u}%"))
        row = cursor.fetchone()
        if row:
            return row

    if dedup_hash:
        cursor.execute("SELECT * FROM jobs WHERE dedup_hash = ?", (dedup_hash,))
        row = cursor.fetchone()
        if row:
            return row

    return None

def sync_jobs_from_json(json_path: Optional[str] = None) -> int:
    """
    Sincroniza o banco SQLite com as vagas já listadas em data/jobs.json.
    Garante que vagas já existentes mantenham seus IDs originais, datas de criação originais,
    status e notas, evitando que apareçam como novas repetidamente após execuções do GitHub Actions.
    Retorna o número de vagas restauradas/sincronizadas.
    """
    target_path = json_path or DEFAULT_JSON_PATH
    if not os.path.exists(target_path):
        alt_path = os.path.join(ROOT_DIR, "backend", "data", "jobs.json")
        if os.path.exists(alt_path):
            target_path = alt_path
        else:
            return 0

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        logger.error(f"[DB Sync] Erro ao ler {target_path}: {e}")
        return 0

    jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    if not jobs:
        return 0

    conn = get_db_connection()
    cursor = conn.cursor()
    restored = 0

    for j in jobs:
        ext_id = j.get("external_id")
        url = j.get("url", "")
        dedup_hash = j.get("dedup_hash") or compute_dedup_hash(
            j.get("title", ""),
            j.get("company", ""),
            j.get("location", ""),
            url
        )

        existing = find_existing_job(cursor, ext_id, url, dedup_hash)
        if existing:
            # Preserva a data de criação mais antiga
            orig_created = existing["created_at"]
            json_created = j.get("created_at")
            if json_created and json_created < orig_created:
                cursor.execute("UPDATE jobs SET created_at = ? WHERE id = ?", (json_created, existing["id"]))
            continue

        now = datetime.now().isoformat()
        try:
            cursor.execute("""
            INSERT INTO jobs (
                id, external_id, source, title, company, location, city, state,
                work_model, category, role_matched, description, salary, url,
                match_score, status, notes, is_favorite, published_at,
                created_at, updated_at, dedup_hash
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """, (
                j.get("id"),
                ext_id,
                j.get("source", "Portal"),
                j.get("title", "Vaga"),
                j.get("company", "Empresa não informada"),
                j.get("location", ""),
                j.get("city"),
                j.get("state", "RS"),
                j.get("work_model", "Não Informado"),
                j.get("category", "outro"),
                j.get("role_matched"),
                j.get("description", ""),
                j.get("salary", "A combinar / Não informado"),
                url,
                j.get("match_score", 50),
                j.get("status", "nova"),
                j.get("notes", ""),
                1 if j.get("is_favorite") else 0,
                j.get("published_at") or "Recente",
                j.get("created_at") or now,
                j.get("updated_at") or now,
                dedup_hash
            ))
            restored += 1
        except Exception as err:
            logger.debug(f"[DB Sync] Pulando inserção de vaga: {err}")

    conn.commit()
    conn.close()
    if restored > 0:
        logger.info(f"[DB Sync] {restored} vagas sincronizadas com sucesso a partir de {target_path}")
    return restored

def insert_job(job_data: Dict[str, Any]) -> Optional[int]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    external_id = job_data.get("external_id")
    url = job_data.get("url", "")
    dedup_hash = job_data.get("dedup_hash") or compute_dedup_hash(
        job_data.get("title", ""),
        job_data.get("company", ""),
        job_data.get("location", ""),
        url
    )
    
    # Verificar se já existe por external_id, url ou dedup_hash
    existing = find_existing_job(cursor, external_id, url, dedup_hash)
    if existing:
        conn.close()
        return None
    
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
            external_id,
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
            url,
            job_data.get("match_score", 50),
            job_data.get("status", "nova"),
            job_data.get("notes", ""),
            1 if job_data.get("is_favorite") else 0,
            job_data.get("published_at") or "Recente",
            job_data.get("created_at") or now,
            job_data.get("updated_at") or now,
            dedup_hash
        ))
        conn.commit()
        inserted_id = cursor.lastrowid
        return inserted_id
    except sqlite3.IntegrityError:
        return None
    except Exception as e:
        logger.error(f"[DB] Erro ao inserir vaga: {e}")
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
