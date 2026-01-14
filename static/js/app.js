/**
 * STL Reducer SaaS - Application JavaScript
 * Gère l'upload de fichiers, la visualisation 3D et l'interaction utilisateur
 */

// État de l'application
const appState = {
    fileId: null,
    fileName: null,
    originalTriangles: 0,
    originalVertices: 0,
    reducedTriangles: 0,
    viewers: {
        original: null,
        reduced: null
    }
};

// Classe pour gérer la visualisation 3D avec Three.js
class STLViewer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.mesh = null;
        this.animationId = null;

        this.init();
    }

    init() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;

        // Scène
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xf5f7fa);

        // Caméra
        this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 10000);
        this.camera.position.set(100, 100, 100);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        this.container.appendChild(this.renderer.domElement);

        // Contrôles orbitaux
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.screenSpacePanning = true;

        // Éclairage
        this.setupLighting();

        // Grille d'aide
        const gridHelper = new THREE.GridHelper(200, 20, 0xcccccc, 0xe0e0e0);
        this.scene.add(gridHelper);

        // Gestion du redimensionnement
        window.addEventListener('resize', () => this.onResize());

        // Démarrage de l'animation
        this.animate();
    }

    setupLighting() {
        // Lumière ambiante
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
        this.scene.add(ambientLight);

        // Lumière directionnelle principale
        const mainLight = new THREE.DirectionalLight(0xffffff, 0.8);
        mainLight.position.set(50, 100, 50);
        mainLight.castShadow = true;
        this.scene.add(mainLight);

        // Lumière de remplissage
        const fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
        fillLight.position.set(-50, 50, -50);
        this.scene.add(fillLight);

        // Lumière arrière
        const backLight = new THREE.DirectionalLight(0xffffff, 0.2);
        backLight.position.set(0, -50, -100);
        this.scene.add(backLight);
    }

    loadMesh(data) {
        // Supprime le mesh existant
        if (this.mesh) {
            this.scene.remove(this.mesh);
            this.mesh.geometry.dispose();
            this.mesh.material.dispose();
        }

        // Création de la géométrie
        const geometry = new THREE.BufferGeometry();

        // Vertices
        const vertices = new Float32Array(data.vertices);
        geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));

        // Indices (triangles)
        const indices = new Uint32Array(data.triangles);
        geometry.setIndex(new THREE.BufferAttribute(indices, 1));

        // Normales
        if (data.normals && data.normals.length > 0) {
            const normals = new Float32Array(data.normals);
            geometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3));
        } else {
            geometry.computeVertexNormals();
        }

        // Matériau
        const material = new THREE.MeshStandardMaterial({
            color: 0x6366f1,
            metalness: 0.1,
            roughness: 0.5,
            flatShading: false,
            side: THREE.DoubleSide
        });

        // Création du mesh
        this.mesh = new THREE.Mesh(geometry, material);
        this.mesh.castShadow = true;
        this.mesh.receiveShadow = true;
        this.scene.add(this.mesh);

        // Centrage et mise à l'échelle
        this.centerAndScaleMesh();
    }

    centerAndScaleMesh() {
        if (!this.mesh) return;

        // Calcul du bounding box
        this.mesh.geometry.computeBoundingBox();
        const boundingBox = this.mesh.geometry.boundingBox;

        // Centre le mesh
        const center = new THREE.Vector3();
        boundingBox.getCenter(center);
        this.mesh.geometry.translate(-center.x, -center.y, -center.z);

        // Calcul de la taille
        const size = new THREE.Vector3();
        boundingBox.getSize(size);
        const maxDim = Math.max(size.x, size.y, size.z);

        // Mise à l'échelle pour que le mesh soit visible
        const scale = 80 / maxDim;
        this.mesh.scale.setScalar(scale);

        // Positionne la caméra
        this.camera.position.set(100, 80, 100);
        this.controls.target.set(0, 0, 0);
        this.controls.update();
    }

    animate() {
        this.animationId = requestAnimationFrame(() => this.animate());
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }

    onResize() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    dispose() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        if (this.mesh) {
            this.scene.remove(this.mesh);
            this.mesh.geometry.dispose();
            this.mesh.material.dispose();
        }
        this.renderer.dispose();
        this.container.innerHTML = '';
    }
}

// Fonctions utilitaires
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
}

function showLoading(message = 'Chargement...') {
    document.getElementById('loadingText').textContent = message;
    document.getElementById('loadingOverlay').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.add('hidden');
}

function showProgress(percent, message) {
    const container = document.getElementById('progressContainer');
    const fill = document.getElementById('progressFill');
    const text = document.getElementById('progressText');

    container.classList.remove('hidden');
    fill.style.width = `${percent}%`;
    text.textContent = message;
}

function hideProgress() {
    document.getElementById('progressContainer').classList.add('hidden');
}

// Gestion de l'upload
async function handleFileUpload(file) {
    if (!file.name.toLowerCase().endsWith('.stl')) {
        alert('Veuillez sélectionner un fichier STL valide.');
        return;
    }

    showLoading('Téléchargement du fichier...');

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Erreur lors du téléchargement');
        }

        // Mise à jour de l'état
        appState.fileId = data.file_id;
        appState.fileName = data.filename;
        appState.originalTriangles = data.info.triangles;
        appState.originalVertices = data.info.vertices;

        // Mise à jour de l'interface
        document.getElementById('fileName').textContent = data.filename;
        document.getElementById('originalVertices').textContent = formatNumber(data.info.vertices);
        document.getElementById('originalTriangles').textContent = formatNumber(data.info.triangles);
        document.getElementById('originalDimensions').textContent =
            `${data.info.dimensions.x.toFixed(1)} x ${data.info.dimensions.y.toFixed(1)} x ${data.info.dimensions.z.toFixed(1)} mm`;

        // Affiche la section de traitement
        document.getElementById('uploadSection').classList.add('hidden');
        document.getElementById('processingSection').classList.remove('hidden');

        // Charge la visualisation 3D
        await loadMeshViewer('original');
        updateEstimatedTriangles();

        hideLoading();

    } catch (error) {
        hideLoading();
        console.error('Erreur:', error);
        alert(`Erreur: ${error.message}`);
    }
}

// Charge le mesh dans un viewer
async function loadMeshViewer(type) {
    const viewerId = type === 'original' ? 'originalViewer' : 'reducedViewer';
    const statsId = type === 'original' ? 'originalViewerStats' : 'reducedViewerStats';

    try {
        const response = await fetch(`/api/mesh/${appState.fileId}/${type}`);

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Erreur lors du chargement du mesh');
        }

        const data = await response.json();

        // Crée ou réutilise le viewer
        if (appState.viewers[type]) {
            appState.viewers[type].dispose();
        }

        // Supprime le placeholder si présent
        const placeholder = document.getElementById('reducedPlaceholder');
        if (placeholder && type === 'reduced') {
            placeholder.remove();
        }

        appState.viewers[type] = new STLViewer(viewerId);
        appState.viewers[type].loadMesh(data.data);

        // Met à jour les stats du viewer
        const triangleCount = data.data.triangles.length / 3;
        document.getElementById(statsId).textContent = `${formatNumber(triangleCount)} triangles`;

    } catch (error) {
        console.error(`Erreur de chargement (${type}):`, error);
    }
}

// Mise à jour des triangles estimés
function updateEstimatedTriangles() {
    const slider = document.getElementById('reductionSlider');
    const reductionRate = slider.value / 100;
    const estimated = Math.max(Math.round(appState.originalTriangles * reductionRate), 100);
    document.getElementById('estimatedTriangles').textContent = formatNumber(estimated);
}

// Réduction du mesh
async function reduceMesh() {
    const slider = document.getElementById('reductionSlider');
    const reductionRate = slider.value / 100;

    showProgress(0, 'Démarrage de la réduction...');

    try {
        // Simulation de progression
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress = Math.min(progress + 5, 90);
            showProgress(progress, 'Traitement en cours...');
        }, 200);

        const formData = new FormData();
        formData.append('reduction_rate', reductionRate);

        const response = await fetch(`/api/reduce/${appState.fileId}`, {
            method: 'POST',
            body: formData
        });

        clearInterval(progressInterval);

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Erreur lors de la réduction');
        }

        showProgress(100, 'Finalisation...');

        // Mise à jour de l'état
        appState.reducedTriangles = data.reduced_info.triangles;

        // Charge le mesh réduit
        await loadMeshViewer('reduced');

        // Affiche les résultats
        document.getElementById('beforeTriangles').textContent = formatNumber(data.original_info.triangles);
        document.getElementById('afterTriangles').textContent = formatNumber(data.reduced_info.triangles);
        document.getElementById('reductionPercentage').textContent = data.reduction_percentage.toFixed(1);

        document.getElementById('resultSection').classList.remove('hidden');
        hideProgress();

    } catch (error) {
        hideProgress();
        console.error('Erreur:', error);
        alert(`Erreur: ${error.message}`);
    }
}

// Téléchargement du fichier réduit
function downloadReducedFile() {
    if (!appState.fileId) return;
    window.location.href = `/api/download/${appState.fileId}/reduced`;
}

// Réinitialisation pour un nouveau fichier
function resetForNewFile() {
    // Nettoie les viewers
    if (appState.viewers.original) {
        appState.viewers.original.dispose();
        appState.viewers.original = null;
    }
    if (appState.viewers.reduced) {
        appState.viewers.reduced.dispose();
        appState.viewers.reduced = null;
    }

    // Supprime le fichier sur le serveur
    if (appState.fileId) {
        fetch(`/api/file/${appState.fileId}`, { method: 'DELETE' })
            .catch(err => console.log('Nettoyage:', err));
    }

    // Réinitialise l'état
    appState.fileId = null;
    appState.fileName = null;
    appState.originalTriangles = 0;
    appState.originalVertices = 0;
    appState.reducedTriangles = 0;

    // Réinitialise l'interface
    document.getElementById('uploadSection').classList.remove('hidden');
    document.getElementById('processingSection').classList.add('hidden');
    document.getElementById('resultSection').classList.add('hidden');
    document.getElementById('reductionSlider').value = 50;
    document.getElementById('reductionValue').textContent = '50';

    // Recrée le placeholder pour le viewer réduit
    const reducedViewer = document.getElementById('reducedViewer');
    reducedViewer.innerHTML = `
        <div class="viewer-placeholder" id="reducedPlaceholder">
            <p>Configurez les paramètres et lancez la réduction</p>
        </div>
    `;
}

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const selectFileBtn = document.getElementById('selectFileBtn');
    const reductionSlider = document.getElementById('reductionSlider');
    const reductionValue = document.getElementById('reductionValue');
    const reduceBtn = document.getElementById('reduceBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const newFileBtn = document.getElementById('newFileBtn');

    // Événements de drag & drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });

    // Clic sur la zone de drop
    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    selectFileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });

    // Slider de réduction
    reductionSlider.addEventListener('input', (e) => {
        reductionValue.textContent = e.target.value;
        updateEstimatedTriangles();
    });

    // Bouton de réduction
    reduceBtn.addEventListener('click', reduceMesh);

    // Bouton de téléchargement
    downloadBtn.addEventListener('click', downloadReducedFile);

    // Bouton nouveau fichier
    newFileBtn.addEventListener('click', resetForNewFile);
});
