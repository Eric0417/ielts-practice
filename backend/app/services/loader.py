"""
Content loader — scans the content/ directory for meta.json files
and upserts them into the questions table on startup.

Directory structure expected:
    content/
      reading/
        passage-01/
          meta.json      # required
          passage.pdf    # optional
          passage.md     # optional
      listening/
        section-01/
          meta.json      # required
          audio.mp3      # optional
      writing/
        task1-01/
          meta.json      # required
"""
import json
from pathlib import Path
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models import Question

# Resolve content/ directory relative to the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONTENT_DIR = PROJECT_ROOT / "content"


def load_single_meta(meta_path: Path) -> dict | None:
    """Read and validate a single meta.json file.

    Returns:
        Parsed dict if valid, None if the file is missing or malformed.
    """
    if not meta_path.is_file():
        return None

    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"[loader] WARNING: Could not parse {meta_path}: {exc}")
        return None

    # Validate required fields
    required = ["id", "type", "title"]
    missing = [k for k in required if k not in data]
    if missing:
        print(f"[loader] WARNING: {meta_path} is missing fields: {missing}")
        return None

    # Validate type enum
    if data["type"] not in ("reading", "listening", "writing"):
        print(f"[loader] WARNING: {meta_path} has unknown type: {data['type']}")
        return None

    return data


def load_all_content() -> int:
    """Scan content/ for meta.json files and upsert into the questions table.

    Called once at application startup. Individual files can fail without
    taking down the whole application — warnings are printed to stdout.

    Returns:
        Number of questions loaded/updated.
    """
    if not CONTENT_DIR.is_dir():
        print(f"[loader] Content directory not found: {CONTENT_DIR}")
        print("[loader] Create content/ with subdirectories for reading/, listening/, writing/")
        return 0

    db: Session = SessionLocal()
    loaded = 0

    try:
        for meta_path in sorted(CONTENT_DIR.rglob("meta.json")):
            data = load_single_meta(meta_path)
            if data is None:
                continue

            qid = data["id"]

            # Upsert: update if exists, insert if new
            existing = db.query(Question).filter(Question.id == qid).first()
            if existing:
                existing.type = data["type"]
                existing.title = data["title"]
                existing.payload = data
                print(f"[loader] Updated: {qid}")
            else:
                db.add(Question(
                    id=qid,
                    type=data["type"],
                    title=data["title"],
                    payload=data,
                ))
                print(f"[loader] Inserted: {qid}")

            loaded += 1

        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"[loader] ERROR during content load: {exc}")
        raise
    finally:
        db.close()

    print(f"[loader] Content sync complete: {loaded} questions loaded")
    return loaded
