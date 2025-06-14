let currentTab = 'music';
let tracks = [];
let selectedTracks = new Set();
let uploadQueue = [];

async function initializeApp() {
    await loadTracks();
    await updateStats();
    setupEventListeners();
    updateUploadPrompt();
}

function setupEventListeners() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const searchInput = document.getElementById('search-input');

    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);
    fileInput.addEventListener('change', handleFileSelect);
    searchInput.addEventListener('input', handleSearch);
}

function updateUploadPrompt() {
    const uploadText = document.getElementById('upload-message');
    if (!uploadText) return;
    if (currentTab === 'audiobooks') {
        uploadText.innerHTML = '<strong>Drop audiobook files here</strong><br>or click to browse';
    } else if (currentTab === 'music') {
        uploadText.innerHTML = '<strong>Drop music files here</strong><br>or click to browse';
    } else {
        uploadText.innerHTML = '<strong>Drop files here</strong><br>or click to browse';
    }
}

function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
}

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    handleFiles(files);
}

async function handleFiles(files) {
    const progressBar = document.getElementById('progress-bar');
    const progressFill = document.getElementById('progress-fill');
    progressBar.style.display = 'block';
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        let endpoint = '/upload';
        if (file.name.endsWith('.m4b')) {
            endpoint += '/audiobook';
        } else {
            endpoint += '/music';
        }
        formData.append('file', file);
        await fetch(endpoint, { method: 'POST', body: formData });
        progressFill.style.width = ((i + 1) / files.length) * 100 + '%';
    }
    progressBar.style.display = 'none';
    progressFill.style.width = '0%';
    showNotification('Upload completed successfully!', 'success');
    await updateStats();
    if (currentTab === 'queue') loadTracks();
}

function switchTab(tab, element) {
    currentTab = tab;
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    element.classList.add('active');
    updateUploadPrompt();
    loadTracks();
}

async function loadTracks() {
    const res = await fetch('/tracks');
    tracks = await res.json();
    const grid = document.getElementById('track-grid');
    let filteredTracks = tracks;
    if (currentTab === 'queue') {
        await loadQueue();
        return;
    } else if (currentTab === 'playlists') {
        await loadPlaylists();
        return;
    } else if (currentTab === 'audiobooks') {
        filteredTracks = tracks.filter(t => t.type === 'audiobook');
    } else {
        filteredTracks = tracks.filter(t => t.type !== 'audiobook');
    }
    grid.innerHTML = filteredTracks.length === 0 ?
        '<div style="text-align: center; color: #666; padding: 40px;">No tracks found</div>' :
        filteredTracks.map(track => `
            <div class="track-item ${track.type || ''}">
                <input type="checkbox" class="select-box" onchange="toggleTrack('${track.id}', this)" ${selectedTracks.has(String(track.id)) ? 'checked' : ''}>
                <div class="track-title">${track.title || ''}</div>
                <div class="track-meta">
                    <span>${track.artist || ''} • ${track.album || ''}</span>
                    <span>${track.duration || ''}</span>
                </div>
                <div class="track-actions">
                    <button class="btn btn-small" onclick="playTrack('${track.id}')">▶️ Play</button>
                    <button class="btn btn-small btn-secondary" onclick="removeTrack('${track.id}')">🗑️ Remove</button>
                </div>
            </div>
        `).join('');
}

async function loadQueue() {
    const res = await fetch('/queue');
    const items = await res.json();
    const grid = document.getElementById('track-grid');
    grid.innerHTML = items.length === 0 ?
        '<div style="text-align: center; color: #666; padding: 40px;">No files in queue</div>' :
        items.map(file => `
            <div class="track-item">
                <div class="track-title">${file.name}</div>
                <div class="track-meta">
                    <span>Size: ${(file.size / 1024 / 1024).toFixed(1)} MB</span>
                    <span>Pending upload</span>
                </div>
            </div>
        `).join('');
}

async function loadPlaylists() {
    const res = await fetch('/playlists');
    const pls = await res.json();
    const grid = document.getElementById('track-grid');
    grid.innerHTML = pls.length === 0 ?
        '<div style="text-align: center; color: #666; padding: 40px;">No playlists</div>' :
        pls.map(pl => `
            <div class="track-item">
                <div class="track-title">${pl.name}</div>
                <div class="track-meta">
                    <span>${pl.tracks.length} tracks</span>
                </div>
            </div>
        `).join('');
}

function toggleTrack(id, cb) {
    if (cb.checked) {
        selectedTracks.add(String(id));
    } else {
        selectedTracks.delete(String(id));
    }
}

function openPlaylistDialog() {
    if (selectedTracks.size === 0) {
        showNotification('Select tracks first', 'error');
        return;
    }
    const name = prompt('Playlist name');
    if (!name) return;
    createPlaylist(name, Array.from(selectedTracks));
}

async function createPlaylist(name, ids) {
    await fetch('/playlists', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, tracks: ids })
    });
    selectedTracks.clear();
    if (currentTab === 'playlists') loadTracks();
    showNotification('Playlist created', 'success');
}

function handleSearch() {
    const query = document.getElementById('search-input').value.toLowerCase();
    const filteredTracks = tracks.filter(track =>
        (track.title || '').toLowerCase().includes(query) ||
        (track.artist || '').toLowerCase().includes(query) ||
        (track.album || '').toLowerCase().includes(query)
    );
    const grid = document.getElementById('track-grid');
    grid.innerHTML = filteredTracks.map(track => `
        <div class="track-item ${track.type || ''}">
            <input type="checkbox" class="select-box" onchange="toggleTrack('${track.id}', this)" ${selectedTracks.has(String(track.id)) ? 'checked' : ''}>
            <div class="track-title">${track.title || ''}</div>
            <div class="track-meta">
                <span>${track.artist || ''} • ${track.album || ''}</span>
                <span>${track.duration || ''}</span>
            </div>
            <div class="track-actions">
                <button class="btn btn-small" onclick="playTrack('${track.id}')">▶️ Play</button>
                <button class="btn btn-small btn-secondary" onclick="removeTrack('${track.id}')">🗑️ Remove</button>
            </div>
        </div>
    `).join('');
}

async function updateStats() {
    const res = await fetch('/stats');
    const stats = await res.json();
    document.getElementById('music-count').textContent = stats.music;
    document.getElementById('audiobook-count').textContent = stats.audiobooks;
    document.getElementById('storage-used').textContent = stats.storage_used + '%';
    document.getElementById('sync-queue').textContent = stats.queue;
}

async function syncNow() {
    const statusIndicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');

    statusIndicator.className = 'status-indicator status-syncing';
    statusText.textContent = 'Syncing...';
    await fetch('/sync', { method: 'POST' });
    await updateStats();
    statusIndicator.className = 'status-indicator status-connected';
    statusText.textContent = 'iPod Connected';
    document.getElementById('last-sync').textContent = new Date().toLocaleTimeString();
    showNotification('Sync completed successfully!', 'success');
}

async function clearQueue() {
    await fetch('/queue/clear', { method: 'POST' });
    showNotification('Queue cleared', 'success');
    await updateStats();
    if (currentTab === 'queue') loadTracks();
}

function playTrack(id) {
    showNotification('Play functionality is not implemented', 'error');
}

async function removeTrack(id) {
    await fetch('/tracks/' + id, { method: 'DELETE' });
    showNotification('Track removed', 'success');
    await loadTracks();
    await updateStats();
}

function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    const notificationText = document.getElementById('notification-text');
    notificationText.textContent = message;
    notification.className = `notification ${type} show`;
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

document.addEventListener('DOMContentLoaded', initializeApp);
