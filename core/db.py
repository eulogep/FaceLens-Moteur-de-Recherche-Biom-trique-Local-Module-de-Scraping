import sqlite3
import json
import os
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from core.config import settings
from core.vector_index import VectorIndexManager

class DatabaseManager:
    def __init__(self, db_path: str = settings.DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Faces table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_path TEXT NOT NULL,
                source_url TEXT,
                person_name TEXT,
                source_type TEXT DEFAULT 'local',
                tags TEXT DEFAULT '',
                image_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            # Scrape jobs table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS scrape_jobs (
                job_id TEXT PRIMARY KEY,
                target_url TEXT NOT NULL,
                status TEXT NOT NULL,
                total_images INTEGER DEFAULT 0,
                faces_indexed INTEGER DEFAULT 0,
                duplicates_skipped INTEGER DEFAULT 0,
                errors_by_domain_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            # Excluded domains table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS excluded_domains (
                domain TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.commit()

    def count_faces(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM faces")
            return cursor.fetchone()[0]

    def get_face(self, face_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM faces WHERE id = ?", (face_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_faces_by_ids(self, face_ids: List[int]) -> List[Dict[str, Any]]:
        if not face_ids:
            return []
        placeholders = ",".join(["?"] * len(face_ids))
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM faces WHERE id IN ({placeholders})", face_ids)
            rows = cursor.fetchall()
            # Maintain input ordering
            rows_by_id = {row["id"]: dict(row) for row in rows}
            return [rows_by_id[fid] for fid in face_ids if fid in rows_by_id]

    def enroll_face_atomic(
        self,
        index_manager: VectorIndexManager,
        vector: np.ndarray,
        image_path: str,
        source_url: Optional[str] = None,
        person_name: Optional[str] = None,
        source_type: str = "local",
        tags: str = "",
        image_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Atomic enrollment:
        1. Write metadata to SQLite to obtain SQLite autoincrement ID.
        2. Insert vector into FAISS index using add_with_ids(vector, [sqlite_id]).
        3. Save FAISS index.
        4. Rollback (delete SQLite row) if FAISS insertion fails.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            INSERT INTO faces (image_path, source_url, person_name, source_type, tags, image_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (image_path, source_url, person_name, source_type, tags, image_hash))
            face_id = cursor.lastrowid
            conn.commit()
        except Exception as e:
            conn.rollback()
            conn.close()
            raise RuntimeError(f"Failed SQLite face insertion: {e}") from e

        try:
            index_manager.add_vector(vector, face_id)
            index_manager.save()
        except Exception as e:
            # Rollback SQLite insertion if FAISS indexing fails
            cursor.execute("DELETE FROM faces WHERE id = ?", (face_id,))
            conn.commit()
            conn.close()
            raise RuntimeError(f"FAISS vector addition failed; rolled back SQLite face #{face_id}: {e}") from e
        finally:
            if conn:
                conn.close()

        # Integrity Check
        self.verify_integrity(index_manager)

        return self.get_face(face_id)

    def delete_face_atomic(self, index_manager: VectorIndexManager, face_id: int) -> bool:
        """
        Atomic deletion:
        1. Remove vector from FAISS index first.
        2. Delete face record from SQLite database.
        3. Save FAISS index.
        """
        face = self.get_face(face_id)
        if not face:
            return False

        # FAISS removal first
        removed_count = index_manager.remove_ids([face_id])
        index_manager.save()

        # SQLite deletion second
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM faces WHERE id = ?", (face_id,))
            conn.commit()

        # Integrity Check
        self.verify_integrity(index_manager)
        return True

    def delete_domain_atomic(self, index_manager: VectorIndexManager, domain: str) -> int:
        """
        Excludes a domain and deletes all associated faces atomically.
        """
        # Add to excluded domains
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO excluded_domains (domain) VALUES (?)", (domain,))
            # Find matching faces
            cursor.execute("SELECT id FROM faces WHERE source_url LIKE ?", (f"%{domain}%",))
            face_ids = [row["id"] for row in cursor.fetchall()]
            conn.commit()

        deleted_count = 0
        for fid in face_ids:
            if self.delete_face_atomic(index_manager, fid):
                deleted_count += 1

        self.verify_integrity(index_manager)
        return deleted_count

    def is_domain_excluded(self, domain: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM excluded_domains WHERE domain = ?", (domain,))
            return cursor.fetchone() is not None

    def get_excluded_domains(self) -> List[str]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT domain FROM excluded_domains")
            return [row["domain"] for row in cursor.fetchall()]

    def verify_integrity(self, index_manager: VectorIndexManager) -> bool:
        """
        Verifies that SQLite and FAISS contain exactly the same face IDs.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM faces ORDER BY id")
            sqlite_ids = {int(row["id"]) for row in cursor.fetchall()}

        faiss_ids = set(index_manager.get_ids())
        if sqlite_ids != faiss_ids:
            missing_in_faiss = sorted(sqlite_ids - faiss_ids)
            missing_in_sqlite = sorted(faiss_ids - sqlite_ids)
            raise AssertionError(
                "Atomic integrity breach! "
                f"missing_in_faiss={missing_in_faiss}; "
                f"missing_in_sqlite={missing_in_sqlite}"
            )
        return True

    # Scrape Job Management
    def create_scrape_job(self, job_id: str, target_url: str) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO scrape_jobs (job_id, target_url, status, total_images, faces_indexed, duplicates_skipped, errors_by_domain_json)
            VALUES (?, ?, 'pending', 0, 0, 0, '{}')
            """, (job_id, target_url))
            conn.commit()

    def update_scrape_job(
        self,
        job_id: str,
        status: str,
        total_images: int = 0,
        faces_indexed: int = 0,
        duplicates_skipped: int = 0,
        errors_by_domain: Dict[str, str] = None
    ) -> None:
        errors_json = json.dumps(errors_by_domain or {})
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE scrape_jobs
            SET status = ?, total_images = ?, faces_indexed = ?, duplicates_skipped = ?, errors_by_domain_json = ?, updated_at = CURRENT_TIMESTAMP
            WHERE job_id = ?
            """, (status, total_images, faces_indexed, duplicates_skipped, errors_json, job_id))
            conn.commit()

    def get_scrape_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scrape_jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None
            job = dict(row)
            job["errors_by_domain"] = json.loads(job.get("errors_by_domain_json") or "{}")
            return job

    def get_scrape_stats(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM scrape_jobs")
            total_jobs = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM faces WHERE source_type != 'local'")
            scraped_faces = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT domain) FROM excluded_domains")
            excluded_count = cursor.fetchone()[0]

            cursor.execute("SELECT source_type, COUNT(*) as count FROM faces GROUP BY source_type")
            by_source_type = {row["source_type"]: row["count"] for row in cursor.fetchall()}

            return {
                "total_jobs": total_jobs,
                "scraped_faces": scraped_faces,
                "excluded_domains_count": excluded_count,
                "faces_by_source_type": by_source_type,
                "total_indexed_faces": self.count_faces()
            }
