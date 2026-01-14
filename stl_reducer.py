#!/usr/bin/env python3
"""
STL Mesh Reducer - Application GUI pour réduire le pourcentage de mesh sur des fichiers STL.
Utilise Open3D pour la simplification par décimation quadrique.
"""

import os
import open3d as o3d
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, BooleanVar, Checkbutton
from tkinter.simpledialog import Dialog
from tkinterdnd2 import DND_FILES, TkinterDnD
import threading
from PIL import Image, ImageTk


def nettoyer_mesh(mesh):
    """Nettoie le mesh en supprimant les triangles dégénérés, doublons, etc."""
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_duplicated_vertices()
    mesh.remove_non_manifold_edges()
    mesh.remove_unreferenced_vertices()
    mesh.compute_vertex_normals()
    return mesh


class ReductionDialog(Dialog):
    """Boîte de dialogue pour configurer le taux de réduction."""

    def __init__(self, parent, fichiers):
        self.result = None
        self.fichiers = fichiers
        self.mode_sauvegarde = tk.StringVar(value="nouveau_nom")
        super().__init__(parent)

    def body(self, master):
        self.wm_title("Réduction des fichiers STL")
        self.wm_transient(self.master)
        self.grab_set()
        self.focus_force()
        self.lift()

        # Afficher le nombre de fichiers sélectionnés
        nb_fichiers = len(self.fichiers)
        tk.Label(master, text=f"{nb_fichiers} fichier(s) sélectionné(s)", font=("Arial", 10, "bold")).pack(pady=5)

        tk.Label(master, text="Taux de réduction (10% à 90%)").pack(pady=5)
        self.scale = tk.Scale(master, from_=10, to=90, orient=tk.HORIZONTAL, length=300)
        self.scale.set(50)
        self.scale.pack()

        # Options de sauvegarde
        tk.Label(master, text="Mode de sauvegarde :", font=("Arial", 10, "bold")).pack(pady=(15, 5))

        frame_options = tk.Frame(master)
        frame_options.pack(pady=5, anchor="w", padx=20)

        tk.Radiobutton(
            frame_options,
            text="Nouveau nom (fichier_reduit_XX%.stl) dans le répertoire source",
            variable=self.mode_sauvegarde,
            value="nouveau_nom"
        ).pack(anchor="w")

        tk.Radiobutton(
            frame_options,
            text="Écraser les fichiers originaux (même nom, même emplacement)",
            variable=self.mode_sauvegarde,
            value="ecraser"
        ).pack(anchor="w")

        tk.Radiobutton(
            frame_options,
            text="Choisir un dossier de destination",
            variable=self.mode_sauvegarde,
            value="choisir_dossier"
        ).pack(anchor="w")

        return self.scale

    def apply(self):
        self.result = (self.scale.get() / 100, self.mode_sauvegarde.get())


class STLReducerApp:
    """Application principale pour la réduction de fichiers STL."""

    def __init__(self, master):
        self.master = master
        master.title("Réducteur STL - Drag & Drop + Sélecteur")
        master.geometry("540x370")
        master.drop_target_register(DND_FILES)
        master.dnd_bind('<<Drop>>', self.on_drop)

        # Chargement du logo (optionnel)
        try:
            image_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "logo odf.png")
            if os.path.exists(image_path):
                img = Image.open(image_path)
                img = img.resize((150, 150), Image.LANCZOS)
                self.logo = ImageTk.PhotoImage(img)
                logo_label = tk.Label(master, image=self.logo)
                logo_label.image = self.logo
                logo_label.pack(pady=5)
        except Exception as e:
            print("Erreur lors du chargement du logo :", e)

        self.label_var = tk.StringVar(value="Glissez vos fichiers STL ici ou utilisez le bouton.")
        tk.Label(master, textvariable=self.label_var, font=("Arial", 12)).pack(pady=5)

        self.progress = ttk.Progressbar(master, length=400, mode="determinate")
        self.progress.pack(pady=10)

        self.bouton = tk.Button(master, text="Choisir fichiers STL", command=self.choisir_fichiers)
        self.bouton.pack(pady=5)

        self.quit = tk.Button(master, text="Quitter", command=master.quit)
        self.quit.pack(pady=5)

    def choisir_fichiers(self):
        """Ouvre le dialogue de sélection de fichiers."""
        fichiers = filedialog.askopenfilenames(filetypes=[("Fichiers STL", "*.stl")])
        if fichiers:
            self.demander_taux_et_traiter(fichiers)

    def on_drop(self, event):
        """Gère le drag & drop de fichiers."""
        fichiers = self.master.tk.splitlist(event.data)
        fichiers = [f for f in fichiers if f.lower().endswith(".stl")]
        if fichiers:
            self.demander_taux_et_traiter(fichiers)

    def demander_taux_et_traiter(self, fichiers):
        """Affiche le dialogue de configuration et lance le traitement."""
        dlg = ReductionDialog(self.master, fichiers)
        result = dlg.result
        if result is None:
            return

        taux, mode_sauvegarde = result
        dossier_destination = None

        if mode_sauvegarde == "ecraser":
            confirm = messagebox.askyesno(
                "Confirmation d'écrasement",
                f"Êtes-vous sûr de vouloir écraser les {len(fichiers)} fichier(s) original(aux) ?\n\n"
                "Cette action est irréversible !"
            )
            if not confirm:
                mode_sauvegarde = "nouveau_nom"

        elif mode_sauvegarde == "choisir_dossier":
            # Proposer le répertoire du premier fichier par défaut
            repertoire_initial = os.path.dirname(fichiers[0]) if fichiers else ""
            dossier_destination = filedialog.askdirectory(
                title="Choisir le dossier de destination",
                initialdir=repertoire_initial
            )
            if not dossier_destination:
                return  # L'utilisateur a annulé

        threading.Thread(
            target=self.traiter_fichiers,
            args=(fichiers, taux, mode_sauvegarde, dossier_destination),
            daemon=True
        ).start()

    def traiter_fichiers(self, fichiers, taux, mode_sauvegarde, dossier_destination=None):
        """Traite les fichiers STL avec le taux de réduction spécifié."""
        total = len(fichiers)
        fichiers_traites = 0
        fichiers_erreur = []

        for i, fichier in enumerate(fichiers):
            nom = os.path.basename(fichier)
            self.label_var.set(f"Traitement de : {nom} ({i + 1}/{total})")
            self.master.update_idletasks()

            try:
                mesh = o3d.io.read_triangle_mesh(fichier)
                if not mesh.has_vertices() or not mesh.has_triangles():
                    fichiers_erreur.append(f"{nom} (mesh vide)")
                    continue
                mesh = nettoyer_mesh(mesh)
                cible = max(int(len(mesh.triangles) * taux), 100)
                mesh_simplifie = mesh.simplify_quadric_decimation(cible)
                mesh_simplifie = nettoyer_mesh(mesh_simplifie)

                # Déterminer le chemin de sortie selon le mode
                repertoire_source = os.path.dirname(fichier)
                nom_fichier = os.path.basename(fichier)
                base_nom, ext = os.path.splitext(nom_fichier)

                if mode_sauvegarde == "ecraser":
                    # Écraser le fichier original (même nom, même emplacement)
                    sortie = fichier
                    original_mtime = os.path.getmtime(fichier)
                elif mode_sauvegarde == "choisir_dossier" and dossier_destination:
                    # Sauvegarder dans le dossier choisi avec un nouveau nom
                    sortie = os.path.join(dossier_destination, f"{base_nom}_reduit_{int(taux * 100)}pc{ext}")
                else:
                    # Mode par défaut: nouveau nom dans le répertoire source
                    sortie = os.path.join(repertoire_source, f"{base_nom}_reduit_{int(taux * 100)}pc{ext}")

                o3d.io.write_triangle_mesh(sortie, mesh_simplifie)

                if mode_sauvegarde == "ecraser":
                    os.utime(sortie, (original_mtime, original_mtime))

                fichiers_traites += 1

            except Exception as e:
                print(f"Erreur sur {fichier} : {e}")
                fichiers_erreur.append(f"{nom} ({str(e)})")
                continue

            self.progress["value"] = ((i + 1) / total) * 100
            self.master.update_idletasks()

        self.label_var.set("Réduction terminée. Glissez ou choisissez d'autres fichiers pour recommencer.")
        self.progress["value"] = 0

        # Message de fin avec détails
        if fichiers_erreur:
            message = f"{fichiers_traites}/{total} fichier(s) traité(s) avec succès.\n\nErreurs:\n"
            message += "\n".join(f"- {err}" for err in fichiers_erreur)
            messagebox.showwarning("Traitement terminé avec erreurs", message)
        else:
            messagebox.showinfo("Succès", f"Tous les {total} fichier(s) ont été traités avec succès.")


if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = STLReducerApp(root)
    root.mainloop()
