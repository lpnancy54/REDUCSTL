"""
STL Reducer SaaS - Backend FastAPI.
Application web pour réduire les fichiers STL avec visualisation 3D.
"""

import os
import uuid
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .stl_processor import process_stl_file, get_mesh_info, get_stl_vertices_and_faces

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Durée de rétention des fichiers (en heures)
FILE_RETENTION_HOURS = 24

# Création de l'application FastAPI
app = FastAPI(
    title="STL Reducer SaaS",
    description="Application web pour réduire les fichiers STL avec visualisation 3D",
    version="1.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montage des fichiers statiques
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Configuration des templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Stockage en mémoire des tâches de traitement
processing_tasks = {}


def cleanup_old_files():
    """Nettoie les fichiers plus anciens que FILE_RETENTION_HOURS."""
    cutoff = datetime.now() - timedelta(hours=FILE_RETENTION_HOURS)
    for item in UPLOAD_DIR.iterdir():
        if item.is_dir():
            try:
                mtime = datetime.fromtimestamp(item.stat().st_mtime)
                if mtime < cutoff:
                    shutil.rmtree(item)
            except Exception:
                pass


@app.get("/")
async def home(request: Request):
    """Page d'accueil avec l'interface de l'application."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload un fichier STL et retourne ses informations.
    """
    # Vérification de l'extension
    if not file.filename.lower().endswith('.stl'):
        raise HTTPException(status_code=400, detail="Seuls les fichiers STL sont acceptés.")

    # Création d'un répertoire unique pour ce fichier
    file_id = str(uuid.uuid4())
    file_dir = UPLOAD_DIR / file_id
    file_dir.mkdir(exist_ok=True)

    # Sauvegarde du fichier
    original_filename = file.filename
    safe_filename = f"original_{original_filename}"
    file_path = file_dir / safe_filename

    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Récupération des informations du mesh
        try:
            import open3d as o3d
            mesh = o3d.io.read_triangle_mesh(str(file_path))
            mesh_info = get_mesh_info(mesh)
        except ImportError:
            # Fallback avec trimesh si open3d n'est pas disponible
            import trimesh
            mesh = trimesh.load(str(file_path))
            mesh_info = {
                "vertices": len(mesh.vertices),
                "triangles": len(mesh.faces),
                "dimensions": {
                    "x": float(mesh.bounds[1][0] - mesh.bounds[0][0]),
                    "y": float(mesh.bounds[1][1] - mesh.bounds[0][1]),
                    "z": float(mesh.bounds[1][2] - mesh.bounds[0][2])
                }
            }

        return JSONResponse({
            "success": True,
            "file_id": file_id,
            "filename": original_filename,
            "info": mesh_info
        })

    except Exception as e:
        # Nettoyage en cas d'erreur
        if file_dir.exists():
            shutil.rmtree(file_dir)
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement: {str(e)}")


@app.post("/api/reduce/{file_id}")
async def reduce_file(
    file_id: str,
    reduction_rate: float = Form(...),
    background_tasks: BackgroundTasks = None
):
    """
    Réduit un fichier STL avec le taux de réduction spécifié.
    """
    file_dir = UPLOAD_DIR / file_id

    if not file_dir.exists():
        raise HTTPException(status_code=404, detail="Fichier non trouvé.")

    # Validation du taux de réduction
    if not 0.1 <= reduction_rate <= 0.9:
        raise HTTPException(
            status_code=400,
            detail="Le taux de réduction doit être entre 10% et 90%."
        )

    # Recherche du fichier original
    original_file = None
    for f in file_dir.iterdir():
        if f.name.startswith("original_"):
            original_file = f
            break

    if original_file is None:
        raise HTTPException(status_code=404, detail="Fichier original non trouvé.")

    try:
        # Traitement du fichier
        output_filename = f"reduced_{int(reduction_rate * 100)}pc_{original_file.name.replace('original_', '')}"
        output_path = file_dir / output_filename

        _, original_info, reduced_info = process_stl_file(
            str(original_file),
            reduction_rate,
            str(output_path)
        )

        # Nettoyage en arrière-plan
        if background_tasks:
            background_tasks.add_task(cleanup_old_files)

        return JSONResponse({
            "success": True,
            "file_id": file_id,
            "reduced_filename": output_filename,
            "original_info": original_info,
            "reduced_info": reduced_info,
            "reduction_percentage": round(
                (1 - reduced_info["triangles"] / original_info["triangles"]) * 100, 2
            )
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la réduction: {str(e)}")


@app.get("/api/mesh/{file_id}/{mesh_type}")
async def get_mesh_data(file_id: str, mesh_type: str):
    """
    Récupère les données du mesh pour la visualisation 3D.
    mesh_type: 'original' ou 'reduced'
    """
    file_dir = UPLOAD_DIR / file_id

    if not file_dir.exists():
        raise HTTPException(status_code=404, detail="Fichier non trouvé.")

    # Recherche du fichier approprié
    target_file = None
    prefix = "original_" if mesh_type == "original" else "reduced_"

    for f in file_dir.iterdir():
        if f.name.startswith(prefix) and f.suffix.lower() == '.stl':
            target_file = f
            break

    if target_file is None:
        raise HTTPException(status_code=404, detail=f"Fichier {mesh_type} non trouvé.")

    try:
        mesh_data = get_stl_vertices_and_faces(str(target_file))
        return JSONResponse({
            "success": True,
            "data": mesh_data
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la lecture: {str(e)}")


@app.get("/api/download/{file_id}/{mesh_type}")
async def download_file(file_id: str, mesh_type: str):
    """
    Télécharge le fichier STL (original ou réduit).
    """
    file_dir = UPLOAD_DIR / file_id

    if not file_dir.exists():
        raise HTTPException(status_code=404, detail="Fichier non trouvé.")

    # Recherche du fichier approprié
    target_file = None
    prefix = "original_" if mesh_type == "original" else "reduced_"

    for f in file_dir.iterdir():
        if f.name.startswith(prefix) and f.suffix.lower() == '.stl':
            target_file = f
            break

    if target_file is None:
        raise HTTPException(status_code=404, detail=f"Fichier {mesh_type} non trouvé.")

    # Nom de fichier pour le téléchargement
    download_name = target_file.name.replace("original_", "").replace("reduced_", "reduced_")

    return FileResponse(
        path=str(target_file),
        filename=download_name,
        media_type="application/octet-stream"
    )


@app.delete("/api/file/{file_id}")
async def delete_file(file_id: str):
    """
    Supprime un fichier et son répertoire associé.
    """
    file_dir = UPLOAD_DIR / file_id

    if not file_dir.exists():
        raise HTTPException(status_code=404, detail="Fichier non trouvé.")

    try:
        shutil.rmtree(file_dir)
        return JSONResponse({"success": True, "message": "Fichier supprimé."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression: {str(e)}")


@app.get("/api/health")
async def health_check():
    """Vérification de l'état de l'application."""
    return JSONResponse({
        "status": "healthy",
        "version": "1.0.0"
    })


# Point d'entrée pour exécution directe
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
