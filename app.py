#!/usr/bin/env python3
"""
STL Mesh Reducer - Version Web (SaaS)
Application Flask pour réduire le pourcentage de mesh sur des fichiers STL.
"""

import os
import uuid
import zipfile
from flask import Flask, render_template, request, send_file, jsonify, after_this_request
from werkzeug.utils import secure_filename
import open3d as o3d
import tempfile
import shutil

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB max
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

ALLOWED_EXTENSIONS = {'stl'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def nettoyer_mesh(mesh):
    """Nettoie le mesh en supprimant les triangles dégénérés, doublons, etc."""
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_duplicated_vertices()
    mesh.remove_non_manifold_edges()
    mesh.remove_unreferenced_vertices()
    mesh.compute_vertex_normals()
    return mesh


def reduire_stl(input_path, output_path, taux):
    """Réduit un fichier STL avec le taux spécifié."""
    mesh = o3d.io.read_triangle_mesh(input_path)
    if not mesh.has_vertices() or not mesh.has_triangles():
        raise ValueError("Le fichier STL est vide ou invalide")

    mesh = nettoyer_mesh(mesh)
    triangles_origine = len(mesh.triangles)
    cible = max(int(triangles_origine * taux), 100)
    mesh_simplifie = mesh.simplify_quadric_decimation(cible)
    mesh_simplifie = nettoyer_mesh(mesh_simplifie)

    o3d.io.write_triangle_mesh(output_path, mesh_simplifie)

    return {
        'triangles_origine': triangles_origine,
        'triangles_final': len(mesh_simplifie.triangles),
        'reduction_reelle': round((1 - len(mesh_simplifie.triangles) / triangles_origine) * 100, 1)
    }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files[]' not in request.files:
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400

    files = request.files.getlist('files[]')
    taux = int(request.form.get('taux', 50)) / 100

    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400

    # Créer un dossier temporaire pour cette session
    session_id = str(uuid.uuid4())
    session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    os.makedirs(session_folder, exist_ok=True)

    resultats = []
    fichiers_traites = []

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            input_path = os.path.join(session_folder, filename)
            file.save(input_path)

            # Nom du fichier de sortie
            base, ext = os.path.splitext(filename)
            output_filename = f"{base}_reduit_{int(taux * 100)}pc{ext}"
            output_path = os.path.join(session_folder, output_filename)

            try:
                stats = reduire_stl(input_path, output_path, taux)
                resultats.append({
                    'fichier': filename,
                    'fichier_sortie': output_filename,
                    'succes': True,
                    **stats
                })
                fichiers_traites.append(output_path)
                # Supprimer le fichier original
                os.remove(input_path)
            except Exception as e:
                resultats.append({
                    'fichier': filename,
                    'succes': False,
                    'erreur': str(e)
                })
                if os.path.exists(input_path):
                    os.remove(input_path)

    if not fichiers_traites:
        shutil.rmtree(session_folder, ignore_errors=True)
        return jsonify({'error': 'Aucun fichier n\'a pu être traité', 'details': resultats}), 400

    # Si un seul fichier, retourner directement
    if len(fichiers_traites) == 1:
        return jsonify({
            'succes': True,
            'session_id': session_id,
            'fichiers': resultats,
            'download_url': f'/download/{session_id}/{os.path.basename(fichiers_traites[0])}'
        })

    # Si plusieurs fichiers, créer un ZIP
    zip_filename = f"stl_reduits_{int(taux * 100)}pc.zip"
    zip_path = os.path.join(session_folder, zip_filename)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for filepath in fichiers_traites:
            zipf.write(filepath, os.path.basename(filepath))

    return jsonify({
        'succes': True,
        'session_id': session_id,
        'fichiers': resultats,
        'download_url': f'/download/{session_id}/{zip_filename}',
        'is_zip': True
    })


@app.route('/download/<session_id>/<filename>')
def download_file(session_id, filename):
    session_folder = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(session_id))
    file_path = os.path.join(session_folder, secure_filename(filename))

    if not os.path.exists(file_path):
        return jsonify({'error': 'Fichier non trouvé'}), 404

    @after_this_request
    def cleanup(response):
        # Nettoyer le dossier de session après téléchargement
        try:
            shutil.rmtree(session_folder, ignore_errors=True)
        except Exception:
            pass
        return response

    return send_file(
        file_path,
        as_attachment=True,
        download_name=filename
    )


if __name__ == '__main__':
    print("=" * 50)
    print("STL Mesh Reducer - Version Web")
    print("Ouvrez http://localhost:8003 dans votre navigateur")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=8003)
