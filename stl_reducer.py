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

    def __init__(self, parent):
        self.result = None
        self.ecraser_var = BooleanVar()
        super().__init__(parent)

    def body(self, master):
        self.wm_title("Réduction du fichier STL")
        self.wm_transient(self.master)
        self.grab_set()
        self.focus_force()
        self.lift()

        tk.Label(master, text="Taux de réduction (10% à 90%)").pack(pady=5)
        self.scale = tk.Scale(master, from_=10, to=90, orient=tk.HORIZONTAL, length=300)
        self.scale.set(50)
        self.scale.pack()

        self.chk = Checkbutton(master, text="Écraser le fichier d'origine", variable=self.ecraser_var)
        self.chk.pack(pady=10)

        return self.scale

    def apply(self):
        self.result = (self.scale.get() / 100, self.ecraser_var.get())


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
        dlg = ReductionDialog(self.master)
        result = dlg.result
        if result is None:
            return

        taux, ecraser = result
        if ecraser:
            confirm = messagebox.askyesno(
                "Confirmation",
                "Êtes-vous sûr de vouloir écraser les fichiers originaux ?"
            )
            if not confirm:
                ecraser = False

        threading.Thread(
            target=self.traiter_fichiers,
            args=(fichiers, taux, ecraser),
            daemon=True
        ).start()

    def traiter_fichiers(self, fichiers, taux, ecraser):
        """Traite les fichiers STL avec le taux de réduction spécifié."""
        total = len(fichiers)
        for i, fichier in enumerate(fichiers):
            nom = os.path.basename(fichier)
            self.label_var.set(f"Traitement de : {nom}")
            self.master.update_idletasks()

            try:
                mesh = o3d.io.read_triangle_mesh(fichier)
                if not mesh.has_vertices() or not mesh.has_triangles():
                    continue
                mesh = nettoyer_mesh(mesh)
                cible = max(int(len(mesh.triangles) * taux), 100)
                mesh_simplifie = mesh.simplify_quadric_decimation(cible)
                mesh_simplifie = nettoyer_mesh(mesh_simplifie)

                if ecraser:
                    sortie = fichier
                    original_mtime = os.path.getmtime(fichier)
                else:
                    base, _ = os.path.splitext(fichier)
                    sortie = f"{base}_reduit_{int(taux * 100)}pc.stl"

                o3d.io.write_triangle_mesh(sortie, mesh_simplifie)

                if ecraser:
                    os.utime(sortie, (original_mtime, original_mtime))

            except Exception as e:
                print(f"Erreur sur {fichier} : {e}")
                continue

            self.progress["value"] = ((i + 1) / total) * 100
            self.master.update_idletasks()

        self.label_var.set("Réduction terminée. Glissez ou choisissez d'autres fichiers pour recommencer.")
        self.progress["value"] = 0
        messagebox.showinfo("Succès", "Tous les fichiers ont été traités.")


if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = STLReducerApp(root)
    root.mainloop()
