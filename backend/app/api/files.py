from __future__ import annotations

from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.files.extractors import extract_file_content
from app.settings import settings

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".csv", ".txt", ".md", ".json", ".png", ".jpg", ".jpeg", ".webp"}


def _ensure_org(org_id: str, db: Session) -> None:
    db.execute(
        text("insert into organizations (org_id, name) values (:org_id, :name) on conflict (org_id) do nothing"),
        {"org_id": org_id, "name": ""},
    )


@router.post("/v1/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    org_id: str = Query(..., min_length=1, max_length=64),
    uploaded_by: str = Query(default="user"),
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> dict:
    effective_org = (x_org_id or org_id).strip()
    filename = (file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="Missing file name")

    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    content = await file.read()
    if len(content) > int(settings.upload_max_size_mb) * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large. Max {settings.upload_max_size_mb}MB")

    file_id = str(uuid.uuid4())
    upload_root = Path(settings.upload_dir).resolve()
    org_dir = upload_root / effective_org
    org_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{file_id}{suffix}"
    stored_path = org_dir / stored_name
    stored_path.write_bytes(content)

    extracted_text = ""
    try:
        extracted_text = extract_file_content(stored_path, file.content_type or "", filename)
    except Exception:
        extracted_text = ""

    _ensure_org(effective_org, db)
    row = db.execute(
        text(
            """
            insert into uploaded_files
              (file_id, org_id, filename, file_path, file_type, file_size, extracted_text, uploaded_by, uploaded_at, is_active)
            values
              (cast(:file_id as uuid), :org_id, :filename, :file_path, :file_type, :file_size, :extracted_text, :uploaded_by, now(), true)
            returning file_id, org_id, filename, file_type, file_size, uploaded_at;
            """
        ),
        {
            "file_id": file_id,
            "org_id": effective_org,
            "filename": filename,
            "file_path": str(stored_path),
            "file_type": file.content_type or suffix.replace(".", ""),
            "file_size": len(content),
            "extracted_text": extracted_text[:100_000],
            "uploaded_by": uploaded_by,
        },
    ).mappings().first()
    db.commit()
    return {
        "file_id": str(row["file_id"]),
        "org_id": str(row["org_id"]),
        "filename": str(row["filename"]),
        "file_type": str(row["file_type"]),
        "file_size": int(row["file_size"] or 0),
        "uploaded_at": row["uploaded_at"],
    }


@router.get("/v1/files/{file_id}")
def get_file(file_id: str, db: Session = Depends(get_db), x_org_id: str | None = Header(default=None, alias="X-Org-Id")) -> dict:
    org_id = (x_org_id or "org_test").strip()
    row = db.execute(
        text(
            """
            select file_id, org_id, filename, file_type, file_size, uploaded_by, uploaded_at, is_active
            from uploaded_files
            where file_id = cast(:file_id as uuid) and org_id = :org_id and is_active = true
            limit 1;
            """
        ),
        {"file_id": file_id, "org_id": org_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    return dict(row)


@router.delete("/v1/files/{file_id}")
def delete_file(file_id: str, db: Session = Depends(get_db), x_org_id: str | None = Header(default=None, alias="X-Org-Id")) -> dict:
    org_id = (x_org_id or "org_test").strip()
    row = db.execute(
        text(
            """
            update uploaded_files
            set is_active = false
            where file_id = cast(:file_id as uuid) and org_id = :org_id and is_active = true
            returning file_path;
            """
        ),
        {"file_id": file_id, "org_id": org_id},
    ).mappings().first()
    db.commit()
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        Path(str(row["file_path"])).unlink(missing_ok=True)
    except Exception:
        pass
    return {"ok": True, "file_id": file_id}


@router.get("/v1/organizations/{org_id}/files")
def list_files(org_id: str, db: Session = Depends(get_db), include_inactive: bool = False) -> list[dict]:
    sql = """
      select file_id, org_id, filename, file_type, file_size, uploaded_by, uploaded_at, is_active
      from uploaded_files
      where org_id = :org_id
    """
    if not include_inactive:
        sql += " and is_active = true"
    sql += " order by uploaded_at desc;"
    rows = db.execute(text(sql), {"org_id": org_id}).mappings().all()
    return [dict(item) for item in rows]
