import base64
import re
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image as PILImage, UnidentifiedImageError
from pydantic import BaseModel

from services.storage import get_storage

router = APIRouter()

# Kept as fallback base for path validation and local listing.
ASSETS_BASE = Path("/tmp/templates")

ALLOWED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/svg+xml",
}

MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

# Strict safe filename — no path traversal
_SAFE_FILENAME_RE = re.compile(r"^[\w\-. ]+\.(png|jpg|jpeg|webp|svg)$", re.IGNORECASE)

# MIME types for image assets (used to build data URIs in list_assets)
_ASSET_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}


def _validate_template_id(template_id: str) -> None:
    """Validate template_id to prevent path traversal."""
    if not re.match(r"^[\w\-]{1,64}$", template_id):
        raise HTTPException(status_code=400, detail="template_id inválido.")


def _get_assets_dir(template_id: str) -> Path:
    """Return (and create) the assets directory for a template.

    Validates template_id to prevent path traversal.
    """
    _validate_template_id(template_id)
    assets_dir = ASSETS_BASE / template_id / "assets"
    resolved = assets_dir.resolve()
    base_resolved = ASSETS_BASE.resolve()
    if not str(resolved).startswith(str(base_resolved)):
        raise HTTPException(status_code=400, detail="template_id fora do escopo permitido.")
    assets_dir.mkdir(parents=True, exist_ok=True)
    return assets_dir


def _validate_filename(filename: str) -> str:
    if not _SAFE_FILENAME_RE.match(filename):
        raise HTTPException(
            status_code=400,
            detail="Nome de arquivo inválido. Use apenas letras, números, hífens, pontos e espaços.",
        )
    return filename


class AssetResponse(BaseModel):
    filename: str
    path: str
    size: int
    dimensions: dict  # {"width": int, "height": int}


class AssetInfo(BaseModel):
    filename: str
    path: str
    size: int
    thumbnailUrl: str
    dataUri: str


@router.post("/templates/{template_id}/assets", response_model=AssetResponse)
async def upload_asset(template_id: str, file: UploadFile = File(...)):
    """Upload an image asset and store it via StorageGateway."""
    _validate_template_id(template_id)
    storage = get_storage()

    # Validate MIME type
    content_type = file.content_type or ""
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de arquivo não suportado: {content_type}. São aceitos: PNG, JPG, WEBP, SVG.",
        )

    # Validate filename
    original_name = file.filename or "image"
    _validate_filename(original_name)

    # Read content
    content = await file.read()

    # Validate size
    if len(content) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Arquivo muito grande: {len(content) / (1024*1024):.1f} MB. Máximo permitido: 5 MB.",
        )

    # Get dimensions
    width, height = 0, 0
    if content_type != "image/svg+xml":
        try:
            import io
            img = PILImage.open(io.BytesIO(content))
            width, height = img.size
        except UnidentifiedImageError:
            raise HTTPException(status_code=400, detail="Arquivo de imagem inválido ou corrompido.")

    # Upload via storage gateway (template_id used as "job_id" namespace)
    storage_path = await storage.upload_asset(template_id, original_name, content)

    return AssetResponse(
        filename=original_name,
        path=storage_path,
        size=len(content),
        dimensions={"width": width, "height": height},
    )


@router.delete("/templates/{template_id}/assets/{filename}")
async def delete_asset(template_id: str, filename: str):
    """Delete an asset file from the template's assets/ folder."""
    _validate_filename(filename)
    assets_dir = _get_assets_dir(template_id)
    dest = assets_dir / filename

    # Double-check path
    if not str(dest.resolve()).startswith(str(assets_dir.resolve())):
        raise HTTPException(status_code=400, detail="Caminho de arquivo inválido.")

    if not dest.exists():
        raise HTTPException(status_code=404, detail=f"Asset '{filename}' não encontrado.")

    dest.unlink()
    return JSONResponse(content={"detail": f"Asset '{filename}' removido com sucesso."})


@router.get("/templates/{template_id}/assets", response_model=List[AssetInfo])
async def list_assets(template_id: str):
    """List all assets in the template's assets/ folder."""
    assets_dir = _get_assets_dir(template_id)
    storage = get_storage()

    result: List[AssetInfo] = []
    for f in sorted(assets_dir.iterdir()):
        if f.is_file() and _SAFE_FILENAME_RE.match(f.name):
            # Generate URL via storage gateway
            url = await storage.get_signed_url(
                "templates", f"templates/{template_id}/assets/{f.name}"
            )
            # Embed asset as base64 data URI so the gallery can set src without
            # depending on a server-accessible URL (iframe srcdoc has no base URL)
            content = f.read_bytes()
            mime = _ASSET_MIME.get(f.suffix.lower(), "image/png")
            data_uri = f"data:{mime};base64,{base64.b64encode(content).decode('ascii')}"
            result.append(
                AssetInfo(
                    filename=f.name,
                    path=f"assets/{f.name}",
                    size=f.stat().st_size,
                    thumbnailUrl=url,
                    dataUri=data_uri,
                )
            )
    return result
