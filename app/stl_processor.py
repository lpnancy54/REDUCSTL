"""
Module de traitement des fichiers STL.
Utilise Trimesh (par défaut) ou Open3D pour la simplification de mesh.
"""

import os
from typing import Tuple, Dict, Any
import numpy as np

# Trimesh est la bibliothèque par défaut (compatible avec toutes les versions de Python)
try:
    import trimesh
    from trimesh import simplify
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False

# Open3D est optionnel (nécessite Python 3.8-3.11)
try:
    import open3d as o3d
    OPEN3D_AVAILABLE = True
except ImportError:
    OPEN3D_AVAILABLE = False


def get_mesh_info_trimesh(mesh) -> Dict[str, Any]:
    """Récupère les informations du mesh (Trimesh)."""
    vertices = mesh.vertices
    faces = mesh.faces

    if len(vertices) > 0:
        dimensions = mesh.bounds[1] - mesh.bounds[0]
    else:
        dimensions = [0, 0, 0]

    return {
        "vertices": len(vertices),
        "triangles": len(faces),
        "dimensions": {
            "x": float(dimensions[0]),
            "y": float(dimensions[1]),
            "z": float(dimensions[2])
        }
    }


def get_mesh_info_open3d(mesh) -> Dict[str, Any]:
    """Récupère les informations du mesh (Open3D)."""
    vertices = np.asarray(mesh.vertices)
    triangles = np.asarray(mesh.triangles)

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


def nettoyer_mesh_open3d(mesh):
    """Nettoie le mesh Open3D."""
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_duplicated_vertices()
    mesh.remove_non_manifold_edges()
    mesh.remove_unreferenced_vertices()
    mesh.compute_vertex_normals()
    return mesh


def process_stl_file_trimesh(
    input_path: str,
    reduction_rate: float,
    output_path: str = None
) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    """
    Traite un fichier STL avec Trimesh.
    """
    # Lecture du mesh
    mesh = trimesh.load(input_path)

    if not hasattr(mesh, 'vertices') or len(mesh.vertices) == 0:
        raise ValueError("Le fichier STL est vide ou invalide.")

    # Informations originales
    original_info = get_mesh_info_trimesh(mesh)

    # Calcul du nombre de faces cible
    target_faces = max(int(len(mesh.faces) * reduction_rate), 100)

    # Simplification avec quadric decimation
    # Trimesh utilise simplify_quadric_decimation
    mesh_simplified = mesh.simplify_quadric_decimation(target_faces)

    # Informations après réduction
    reduced_info = get_mesh_info_trimesh(mesh_simplified)

    # Génération du chemin de sortie si non spécifié
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_reduced_{int(reduction_rate * 100)}pc{ext}"

    # Écriture du fichier de sortie
    mesh_simplified.export(output_path, file_type='stl')

    return output_path, original_info, reduced_info


def process_stl_file_open3d(
    input_path: str,
    reduction_rate: float,
    output_path: str = None
) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    """
    Traite un fichier STL avec Open3D.
    """
    # Lecture du mesh
    mesh = o3d.io.read_triangle_mesh(input_path)

    if not mesh.has_vertices() or not mesh.has_triangles():
        raise ValueError("Le fichier STL est vide ou invalide.")

    # Informations originales
    original_info = get_mesh_info_open3d(mesh)

    # Nettoyage du mesh
    mesh = nettoyer_mesh_open3d(mesh)

    # Calcul du nombre de triangles cible
    target_triangles = max(int(len(mesh.triangles) * reduction_rate), 100)

    # Simplification par décimation quadrique
    mesh_simplified = mesh.simplify_quadric_decimation(target_triangles)
    mesh_simplified = nettoyer_mesh_open3d(mesh_simplified)

    # Informations après réduction
    reduced_info = get_mesh_info_open3d(mesh_simplified)

    # Génération du chemin de sortie si non spécifié
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_reduced_{int(reduction_rate * 100)}pc{ext}"

    # Écriture du fichier de sortie
    o3d.io.write_triangle_mesh(output_path, mesh_simplified)

    return output_path, original_info, reduced_info


def process_stl_file(
    input_path: str,
    reduction_rate: float,
    output_path: str = None
) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    """
    Traite un fichier STL avec le taux de réduction spécifié.
    Utilise Trimesh par défaut, Open3D si disponible et préféré.

    Args:
        input_path: Chemin vers le fichier STL d'entrée
        reduction_rate: Taux de réduction (0.1 à 0.9)
        output_path: Chemin de sortie (optionnel)

    Returns:
        Tuple contenant (chemin_sortie, info_original, info_reduit)
    """
    # Utilise Trimesh par défaut (plus compatible)
    if TRIMESH_AVAILABLE:
        return process_stl_file_trimesh(input_path, reduction_rate, output_path)
    elif OPEN3D_AVAILABLE:
        return process_stl_file_open3d(input_path, reduction_rate, output_path)
    else:
        raise ImportError(
            "Aucune bibliothèque de traitement 3D n'est installée. "
            "Veuillez installer trimesh: pip install trimesh"
        )


def get_stl_vertices_and_faces(stl_path: str) -> Dict[str, Any]:
    """
    Récupère les vertices et faces d'un fichier STL pour la visualisation.

    Args:
        stl_path: Chemin vers le fichier STL

    Returns:
        Dict contenant vertices, faces et normales
    """
    if TRIMESH_AVAILABLE:
        mesh = trimesh.load(stl_path)

        vertices = mesh.vertices.flatten().tolist()
        triangles = mesh.faces.flatten().tolist()
        normals = mesh.vertex_normals.flatten().tolist()

        return {
            "vertices": vertices,
            "triangles": triangles,
            "normals": normals
        }
    elif OPEN3D_AVAILABLE:
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
    else:
        raise ImportError("Ni Trimesh ni Open3D n'est installé.")


def get_mesh_info(file_path: str) -> Dict[str, Any]:
    """
    Récupère les informations d'un fichier STL.

    Args:
        file_path: Chemin vers le fichier STL

    Returns:
        Dict contenant vertices, triangles et dimensions
    """
    if TRIMESH_AVAILABLE:
        mesh = trimesh.load(file_path)
        return get_mesh_info_trimesh(mesh)
    elif OPEN3D_AVAILABLE:
        mesh = o3d.io.read_triangle_mesh(file_path)
        return get_mesh_info_open3d(mesh)
    else:
        raise ImportError("Ni Trimesh ni Open3D n'est installé.")
