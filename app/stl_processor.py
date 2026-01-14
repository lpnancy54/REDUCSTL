"""
Module de traitement des fichiers STL.
Utilise Open3D pour la simplification par décimation quadrique.
"""

import os
import tempfile
from typing import Tuple, Dict, Any
import numpy as np

try:
    import open3d as o3d
    OPEN3D_AVAILABLE = True
except ImportError:
    OPEN3D_AVAILABLE = False

try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False


def nettoyer_mesh(mesh):
    """Nettoie le mesh en supprimant les triangles dégénérés, doublons, etc."""
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_duplicated_vertices()
    mesh.remove_non_manifold_edges()
    mesh.remove_unreferenced_vertices()
    mesh.compute_vertex_normals()
    return mesh


def get_mesh_info(mesh) -> Dict[str, Any]:
    """Récupère les informations du mesh."""
    vertices = np.asarray(mesh.vertices)
    triangles = np.asarray(mesh.triangles)

    # Calcul du bounding box
    if len(vertices) > 0:
        min_bound = vertices.min(axis=0)
        max_bound = vertices.max(axis=0)
        dimensions = max_bound - min_bound
    else:
        dimensions = [0, 0, 0]

    return {
        "vertices": len(vertices),
        "triangles": len(triangles),
        "dimensions": {
            "x": float(dimensions[0]),
            "y": float(dimensions[1]),
            "z": float(dimensions[2])
        }
    }


def process_stl_file(
    input_path: str,
    reduction_rate: float,
    output_path: str = None
) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    """
    Traite un fichier STL avec le taux de réduction spécifié.

    Args:
        input_path: Chemin vers le fichier STL d'entrée
        reduction_rate: Taux de réduction (0.1 à 0.9)
        output_path: Chemin de sortie (optionnel)

    Returns:
        Tuple contenant (chemin_sortie, info_original, info_reduit)
    """
    if not OPEN3D_AVAILABLE:
        raise ImportError("Open3D n'est pas installé. Veuillez installer open3d.")

    # Lecture du mesh
    mesh = o3d.io.read_triangle_mesh(input_path)

    if not mesh.has_vertices() or not mesh.has_triangles():
        raise ValueError("Le fichier STL est vide ou invalide.")

    # Informations originales
    original_info = get_mesh_info(mesh)

    # Nettoyage du mesh
    mesh = nettoyer_mesh(mesh)

    # Calcul du nombre de triangles cible
    target_triangles = max(int(len(mesh.triangles) * reduction_rate), 100)

    # Simplification par décimation quadrique
    mesh_simplified = mesh.simplify_quadric_decimation(target_triangles)
    mesh_simplified = nettoyer_mesh(mesh_simplified)

    # Informations après réduction
    reduced_info = get_mesh_info(mesh_simplified)

    # Génération du chemin de sortie si non spécifié
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_reduced_{int(reduction_rate * 100)}pc{ext}"

    # Écriture du fichier de sortie
    o3d.io.write_triangle_mesh(output_path, mesh_simplified)

    return output_path, original_info, reduced_info


def stl_to_glb(stl_path: str, glb_path: str = None) -> str:
    """
    Convertit un fichier STL en GLB pour la visualisation web.

    Args:
        stl_path: Chemin vers le fichier STL
        glb_path: Chemin de sortie GLB (optionnel)

    Returns:
        Chemin vers le fichier GLB
    """
    if not TRIMESH_AVAILABLE:
        raise ImportError("Trimesh n'est pas installé. Veuillez installer trimesh.")

    mesh = trimesh.load(stl_path)

    if glb_path is None:
        base, _ = os.path.splitext(stl_path)
        glb_path = f"{base}.glb"

    mesh.export(glb_path, file_type='glb')

    return glb_path


def get_stl_vertices_and_faces(stl_path: str) -> Dict[str, Any]:
    """
    Récupère les vertices et faces d'un fichier STL pour la visualisation.

    Args:
        stl_path: Chemin vers le fichier STL

    Returns:
        Dict contenant vertices, faces et normales
    """
    if OPEN3D_AVAILABLE:
        mesh = o3d.io.read_triangle_mesh(stl_path)
        mesh.compute_vertex_normals()

        vertices = np.asarray(mesh.vertices).flatten().tolist()
        triangles = np.asarray(mesh.triangles).flatten().tolist()
        normals = np.asarray(mesh.vertex_normals).flatten().tolist()

        return {
            "vertices": vertices,
            "triangles": triangles,
            "normals": normals
        }
    elif TRIMESH_AVAILABLE:
        mesh = trimesh.load(stl_path)

        vertices = mesh.vertices.flatten().tolist()
        triangles = mesh.faces.flatten().tolist()
        normals = mesh.vertex_normals.flatten().tolist()

        return {
            "vertices": vertices,
            "triangles": triangles,
            "normals": normals
        }
    else:
        raise ImportError("Ni Open3D ni Trimesh n'est installé.")
