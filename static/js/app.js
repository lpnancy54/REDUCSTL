/**
 * STL Reducer SaaS - Application JavaScript
 * Gère l'upload de fichiers multiples, la visualisation 3D et l'interaction utilisateur
 */

// État de l'application
const appState = {
    files: [], // Liste des fichiers {id, name, status, originalInfo, reducedInfo}
    currentFileIndex: 0,
    reductionRate: 50,
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

        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xf5f7fa);

        this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 10000);
        this.camera.position.set(100, 100, 100);

        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        this.container.appendChild(this.renderer.domElement);

        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.screenSpacePanning = true;

        this.setupLighting();

        const gridHelper = new THREE.GridHelper(200, 20, 0xcccccc, 0xe0e0e0);
        this.scene.add(gridHelper);

        window.addEventListener('resize', () => this.onResize());
        this.animate();
    }

    setupLighting() {
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
        this.scene.add(ambientLight);

        const mainLight = new THREE.DirectionalLight(0xffffff, 0.8);
        mainLight.position.set(50, 100, 50);
        mainLight.castShadow = true;
        this.scene.add(mainLight);

        const fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
        fillLight.position.set(-50, 50, -50);
        this.scene.add(fillLight);

        const backLight = new THREE.DirectionalLight(0xffffff, 0.2);
        backLight.position.set(0, -50, -100);
        this.scene.add(backLight);
    }

    loadMesh(data) {
        if (this.mesh) {
            this.scene.remove(this.mesh);
            this.mesh.geometry.dispose();
            this.mesh.material.dispose();
        }

        const geometry = new THREE.BufferGeometry();
        const vertices = new Float32Array(data.vertices);
        geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));

        const indices = new Uint32Array(data.triangles);
        geometry.setIndex(new THREE.BufferAttribute(indices, 1));

        if (data.normals && data.normals.length > 0) {
            const normals = new Float32Array(data.normals);
            geometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3));
        } else {
            geometry.computeVertexNormals();
        }

        const material = new THREE.MeshStandardMaterial({
            color: 0x6366f1,
            metalness: 0.1,
            roughness: 0.5,
            flatShading: false,
            side: THREE.DoubleSide
        });

        this.mesh = new THREE.Mesh(geometry, material);
        this.mesh.castShadow = true;
        this.mesh.receiveShadow = true;
        this.scene.add(this.mesh);

        this.centerAndScaleMesh();
    }

    centerAndScaleMesh() {
        if (!this.mesh) return;

        this.mesh.geometry.computeBoundingBox();
        const boundingBox = this.mesh.geometry.boundingBox;

        const center = new THREE.Vector3();
        boundingBox.getCenter(center);
        this.mesh.geometry.translate(-center.x, -center.y, -center.z);

        const size = new THREE.Vector3();
        boundingBox.getSize(size);
        const maxDim = Math.max(size.x, size.y, size.z);

        const scale = 80 / maxDim;
        this.mesh.scale.setScalar(scale);

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

// Mise à jour de la liste des fichiers dans l'interface
function updateFileList() {
    const fileList = document.getElementById('fileList');

    if (appState.files.length === 0) {
        fileList.innerHTML = '<p class="no-files">Aucun fichier</p>';
        return;
    }

    fileList.innerHTML = appState.files.map((file, index) => `
        <div class="file-item ${file.status} ${index === appState.currentFileIndex ? 'active' : ''}"
             data-index="${index}" onclick="selectFile(${index})">
            <div class="file-item-info">
                <span class="file-item-name">${file.name}</span>
                <span class="file-item-triangles">${file.originalInfo ? formatNumber(file.originalInfo.triangles) + ' triangles' : ''}</span>
            </div>
            <div class="file-item-status">
                ${getStatusIcon(file.status)}
            </div>
            <button class="file-item-remove" onclick="event.stopPropagation(); removeFile(${index})" title="Supprimer">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        </div>
    `).join('');
}

function getStatusIcon(status) {
    switch(status) {
        case 'pending':
            return '<span class="status-badge pending">En attente</span>';
        case 'processing':
            return '<span class="status-badge processing"><span class="spinner-small"></span></span>';
        case 'completed':
            return '<span class="status-badge completed"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20,6 9,17 4,12"></polyline></svg></span>';
        case 'error':
            return '<span class="status-badge error"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg></span>';
        default:
            return '';
    }
}

// Sélection d'un fichier dans la liste
async function selectFile(index) {
    if (index < 0 || index >= appState.files.length) return;

    appState.currentFileIndex = index;
    const file = appState.files[index];

    updateFileList();
    updateFileInfo(file);

    // Charge la visualisation 3D
    if (file.id) {
        await loadMeshViewer('original', file.id);
        if (file.status === 'completed') {
            await loadMeshViewer('reduced', file.id);
            document.getElementById('reducedPlaceholder')?.remove();
        } else {
            resetReducedViewer();
        }
    }
}

function updateFileInfo(file) {
    document.getElementById('fileName').textContent = file.name;

    if (file.originalInfo) {
        document.getElementById('originalVertices').textContent = formatNumber(file.originalInfo.vertices);
        document.getElementById('originalTriangles').textContent = formatNumber(file.originalInfo.triangles);
        document.getElementById('originalDimensions').textContent =
            `${file.originalInfo.dimensions.x.toFixed(1)} x ${file.originalInfo.dimensions.y.toFixed(1)} x ${file.originalInfo.dimensions.z.toFixed(1)} mm`;

        updateEstimatedTriangles(file.originalInfo.triangles);
    }

    // Afficher/masquer les résultats
    if (file.status === 'completed' && file.reducedInfo) {
        document.getElementById('beforeTriangles').textContent = formatNumber(file.originalInfo.triangles);
        document.getElementById('afterTriangles').textContent = formatNumber(file.reducedInfo.triangles);
        const reduction = (1 - file.reducedInfo.triangles / file.originalInfo.triangles) * 100;
        document.getElementById('reductionPercentage').textContent = reduction.toFixed(1);
        document.getElementById('resultSection').classList.remove('hidden');
    } else {
        document.getElementById('resultSection').classList.add('hidden');
    }
}

function resetReducedViewer() {
    const reducedViewer = document.getElementById('reducedViewer');
    if (appState.viewers.reduced) {
        appState.viewers.reduced.dispose();
        appState.viewers.reduced = null;
    }
    reducedViewer.innerHTML = `
        <div class="viewer-placeholder" id="reducedPlaceholder">
            <p>Configurez les paramètres et lancez la réduction</p>
        </div>
    `;
}

// Suppression d'un fichier
async function removeFile(index) {
    const file = appState.files[index];

    // Supprime sur le serveur
    if (file.id) {
        try {
            await fetch(`/api/file/${file.id}`, { method: 'DELETE' });
        } catch (e) {
            console.log('Erreur suppression:', e);
        }
    }

    appState.files.splice(index, 1);

    if (appState.files.length === 0) {
        resetForNewFile();
    } else {
        if (appState.currentFileIndex >= appState.files.length) {
            appState.currentFileIndex = appState.files.length - 1;
        }
        updateFileList();
        selectFile(appState.currentFileIndex);
    }
}

// Gestion de l'upload de plusieurs fichiers
async function handleFilesUpload(files) {
    const stlFiles = Array.from(files).filter(f => f.name.toLowerCase().endsWith('.stl'));

    if (stlFiles.length === 0) {
        alert('Veuillez sélectionner des fichiers STL valides.');
        return;
    }

    showLoading(`Téléchargement de ${stlFiles.length} fichier(s)...`);

    // Affiche la section de traitement
    document.getElementById('uploadSection').classList.add('hidden');
    document.getElementById('processingSection').classList.remove('hidden');

    for (let i = 0; i < stlFiles.length; i++) {
        const file = stlFiles[i];
        showLoading(`Téléchargement ${i + 1}/${stlFiles.length}: ${file.name}`);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Erreur lors du téléchargement');
            }

            appState.files.push({
                id: data.file_id,
                name: data.filename,
                status: 'pending',
                originalInfo: data.info,
                reducedInfo: null
            });

        } catch (error) {
            console.error('Erreur upload:', error);
            appState.files.push({
                id: null,
                name: file.name,
                status: 'error',
                originalInfo: null,
                reducedInfo: null,
                error: error.message
            });
        }
    }

    hideLoading();
    updateFileList();

    // Sélectionne le premier fichier
    if (appState.files.length > 0) {
        selectFile(0);
    }
}

// Charge le mesh dans un viewer
async function loadMeshViewer(type, fileId) {
    const viewerId = type === 'original' ? 'originalViewer' : 'reducedViewer';
    const statsId = type === 'original' ? 'originalViewerStats' : 'reducedViewerStats';

    try {
        const response = await fetch(`/api/mesh/${fileId}/${type}`);

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Erreur lors du chargement du mesh');
        }

        const data = await response.json();

        if (appState.viewers[type]) {
            appState.viewers[type].dispose();
        }

        const placeholder = document.getElementById('reducedPlaceholder');
        if (placeholder && type === 'reduced') {
            placeholder.remove();
        }

        appState.viewers[type] = new STLViewer(viewerId);
        appState.viewers[type].loadMesh(data.data);

        const triangleCount = data.data.triangles.length / 3;
        document.getElementById(statsId).textContent = `${formatNumber(triangleCount)} triangles`;

    } catch (error) {
        console.error(`Erreur de chargement (${type}):`, error);
    }
}

// Mise à jour des triangles estimés
function updateEstimatedTriangles(originalTriangles) {
    const slider = document.getElementById('reductionSlider');
    const reductionRate = slider.value / 100;
    const triangles = originalTriangles || appState.files[appState.currentFileIndex]?.originalInfo?.triangles || 0;
    const estimated = Math.max(Math.round(triangles * reductionRate), 100);
    document.getElementById('estimatedTriangles').textContent = formatNumber(estimated);
}

// Réduction de tous les fichiers
async function reduceAllFiles() {
    const slider = document.getElementById('reductionSlider');
    const reductionRate = slider.value / 100;

    const pendingFiles = appState.files.filter(f => f.status === 'pending' && f.id);

    if (pendingFiles.length === 0) {
        alert('Aucun fichier en attente de traitement.');
        return;
    }

    for (let i = 0; i < appState.files.length; i++) {
        const file = appState.files[i];
        if (file.status !== 'pending' || !file.id) continue;

        file.status = 'processing';
        appState.currentFileIndex = i;
        updateFileList();

        showProgress((i / pendingFiles.length) * 100, `Traitement de ${file.name}...`);

        try {
            const formData = new FormData();
            formData.append('reduction_rate', reductionRate);

            const response = await fetch(`/api/reduce/${file.id}`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Erreur lors de la réduction');
            }

            file.status = 'completed';
            file.reducedInfo = data.reduced_info;

        } catch (error) {
            console.error('Erreur réduction:', error);
            file.status = 'error';
            file.error = error.message;
        }

        updateFileList();
    }

    hideProgress();

    // Affiche le fichier courant avec ses résultats
    selectFile(appState.currentFileIndex);

    // Vérifie si tous les fichiers sont traités
    const completedCount = appState.files.filter(f => f.status === 'completed').length;
    if (completedCount > 0) {
        alert(`Traitement terminé ! ${completedCount}/${appState.files.length} fichier(s) réduit(s).`);
    }
}

// Téléchargement du fichier réduit actuel
function downloadReducedFile() {
    const file = appState.files[appState.currentFileIndex];
    if (!file || !file.id || file.status !== 'completed') return;
    window.location.href = `/api/download/${file.id}/reduced`;
}

// Téléchargement de tous les fichiers réduits
async function downloadAllReducedFiles() {
    const completedFiles = appState.files.filter(f => f.status === 'completed' && f.id);

    if (completedFiles.length === 0) {
        alert('Aucun fichier réduit à télécharger.');
        return;
    }

    for (const file of completedFiles) {
        window.open(`/api/download/${file.id}/reduced`, '_blank');
        await new Promise(resolve => setTimeout(resolve, 500)); // Petit délai entre les téléchargements
    }
}

// Réinitialisation pour de nouveaux fichiers
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

    // Supprime les fichiers sur le serveur
    for (const file of appState.files) {
        if (file.id) {
            fetch(`/api/file/${file.id}`, { method: 'DELETE' })
                .catch(err => console.log('Nettoyage:', err));
        }
    }

    // Réinitialise l'état
    appState.files = [];
    appState.currentFileIndex = 0;

    // Réinitialise l'interface
    document.getElementById('uploadSection').classList.remove('hidden');
    document.getElementById('processingSection').classList.add('hidden');
    document.getElementById('resultSection').classList.add('hidden');
    document.getElementById('reductionSlider').value = 50;
    document.getElementById('reductionValue').textContent = '50';
    document.getElementById('fileInput').value = '';

    resetReducedViewer();
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

    // Support fichiers multiples
    fileInput.setAttribute('multiple', 'multiple');

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
            handleFilesUpload(files);
        }
    });

    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    selectFileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFilesUpload(e.target.files);
        }
    });

    reductionSlider.addEventListener('input', (e) => {
        reductionValue.textContent = e.target.value;
        updateEstimatedTriangles();
    });

    reduceBtn.addEventListener('click', reduceAllFiles);
    downloadBtn.addEventListener('click', downloadReducedFile);
    newFileBtn.addEventListener('click', resetForNewFile);

    // Bouton télécharger tout
    const downloadAllBtn = document.getElementById('downloadAllBtn');
    if (downloadAllBtn) {
        downloadAllBtn.addEventListener('click', downloadAllReducedFiles);
    }

    // Bouton ajouter plus de fichiers
    const addMoreFilesBtn = document.getElementById('addMoreFilesBtn');
    if (addMoreFilesBtn) {
        addMoreFilesBtn.addEventListener('click', () => {
            fileInput.click();
        });
    }
});
