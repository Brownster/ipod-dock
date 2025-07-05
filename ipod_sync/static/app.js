let currentTab = 'music';
let tracks = [];
let selectedTracks = new Set();
let uploadQueue = [];

function authHeaders() {
    const key = localStorage.getItem('ipodApiKey');
    return key ? { 'X-API-Key': key } : {};
}

function authFetch(url, options = {}) {
    options.headers = { ...(options.headers || {}), ...authHeaders() };
    return fetch(url, options);
}

async function initializeApp() {
    setupEventListeners();
    updateUploadPrompt();
    try {
        await loadTracks();
        await updateStats();
        await checkDeviceStatus();
        setInterval(checkDeviceStatus, 30000);
    } catch (err) {
        console.error('Initialization failed', err);
    }
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
    } else if (currentTab === 'podcasts') {
        uploadText.innerHTML = '<strong>Drop podcast files here</strong><br>or click to browse';
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
        if (currentTab === 'podcasts') {
            endpoint += '/podcast';
        } else if (file.name.endsWith('.m4b')) {
            endpoint += '/audiobook';
        } else {
            endpoint += '/music';
        }
        formData.append('file', file);
        await authFetch(endpoint, { method: 'POST', body: formData });
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
    document.querySelectorAll('.nav-link').forEach(t => t.classList.remove('active'));
    element.classList.add('active');
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('show', 'active'));
    const pane = document.getElementById(`${tab}-pane`);
    if (pane) pane.classList.add('show', 'active');

    const tracksArea = document.getElementById('tracks-area');
    if (tab === 'audiobooks') {
        tracksArea.style.display = 'none';
    } else {
        tracksArea.style.display = 'block';
    }

    // Show/hide playlist controls based on tab
    const playlistControls = document.getElementById('playlist-controls');
    if (playlistControls) {
        if (tab === 'music' || tab === 'playlists') {
            playlistControls.style.display = 'block';
        } else {
            playlistControls.style.display = 'none';
        }
    }

    updateUploadPrompt();
    loadTracks();
}

async function loadTracks() {
    const res = await authFetch('/tracks');
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
    } else if (currentTab === 'podcasts') {
        filteredTracks = tracks.filter(t => t.type === 'podcast');
    } else {
        filteredTracks = tracks.filter(t => t.type !== 'audiobook' && t.type !== 'podcast');
    }
    grid.innerHTML = filteredTracks.length === 0 ?
        '<div style="text-align: center; color: #666; padding: 40px;">No tracks found</div>' :
        filteredTracks.map(track => `
            <div class="track-item ${track.type || ''}">
                <input type="checkbox" class="select-box" onchange="toggleTrack('${track.id}', this)" ${selectedTracks.has(String(track.id)) ? 'checked' : ''}>
                <div class="track-info">
                    <div class="track-title">${track.title || ''}</div>
                    <div class="track-meta">
                        <span>${track.artist || ''} • ${track.album || ''}</span>
                        <span>${track.duration || ''}</span>
                    </div>
                </div>
                <div class="track-actions">
                    <button class="btn btn-small" onclick="playTrack('${track.id}')">▶️</button>
                    <button class="btn btn-small btn-secondary" onclick="removeTrack('${track.id}')">🗑️</button>
                </div>
            </div>
        `).join('');
}

async function loadQueue() {
    const res = await authFetch('/queue');
    const items = await res.json();
    const grid = document.getElementById('track-grid');
    grid.innerHTML = items.length === 0 ?
        '<div style="text-align: center; color: #666; padding: 40px;">No files in queue</div>' :
        items.map(file => `
            <div class="track-item">
                <div class="track-info">
                    <div class="track-title">${file.name}</div>
                    <div class="track-meta">
                        <span>Size: ${(file.size / 1024 / 1024).toFixed(1)} MB</span>
                        <span>Pending upload</span>
                    </div>
                </div>
            </div>
        `).join('');
}

async function loadPlaylists() {
    const res = await authFetch('/playlists');
    const pls = await res.json();
    const grid = document.getElementById('track-grid');
    grid.innerHTML = pls.length === 0 ?
        '<div style="text-align: center; color: #666; padding: 40px;">No playlists</div>' :
        pls.map(pl => `
            <div class="track-item">
                <div class="track-info">
                    <div class="track-title">${pl.name}</div>
                    <div class="track-meta">
                        <span>${pl.tracks.length} tracks</span>
                    </div>
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
    updateSelectionUI();
}

function updateSelectionUI() {
    const selectedCount = document.getElementById('selected-count');
    if (selectedCount) {
        selectedCount.textContent = selectedTracks.size;
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
    await authFetch('/playlists', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, tracks: ids })
    });
    selectedTracks.clear();
    updateSelectionUI();
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
            <div class="track-info">
                <div class="track-title">${track.title || ''}</div>
                <div class="track-meta">
                    <span>${track.artist || ''} • ${track.album || ''}</span>
                    <span>${track.duration || ''}</span>
                </div>
            </div>
            <div class="track-actions">
                <button class="btn btn-small" onclick="playTrack('${track.id}')">▶️</button>
                <button class="btn btn-small btn-secondary" onclick="removeTrack('${track.id}')">🗑️</button>
            </div>
        </div>
    `).join('');
}

async function updateStats() {
    const res = await authFetch('/stats');
    const stats = await res.json();
    document.getElementById('music-count').textContent = stats.music;
    document.getElementById('audiobook-count').textContent = stats.audiobooks;
    if (stats.podcasts !== undefined) {
        document.getElementById('podcast-count').textContent = stats.podcasts;
    }
    document.getElementById('storage-used').textContent = stats.storage_used + '%';
    document.getElementById('sync-queue').textContent = stats.queue;
}

async function checkDeviceStatus() {
    const statusIndicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    try {
        const res = await authFetch('/status');
        const data = await res.json();
        if (data.connected) {
            statusIndicator.className = 'status-indicator status-connected';
            statusText.textContent = 'iPod Connected';
        } else {
            statusIndicator.className = 'status-indicator status-disconnected';
            statusText.textContent = 'iPod Disconnected';
        }
    } catch (err) {
        console.error(err);
        statusIndicator.className = 'status-indicator status-error';
        statusText.textContent = 'Status Error';
    }
}

async function syncNow() {
    const statusIndicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');

    statusIndicator.className = 'status-indicator status-syncing';
    statusText.textContent = 'Syncing...';
    try {
        const res = await authFetch('/sync', { method: 'POST' });
        if (!res.ok) throw new Error('Sync failed');
        await updateStats();
        statusIndicator.className = 'status-indicator status-connected';
        statusText.textContent = 'iPod Connected';
        document.getElementById('last-sync').textContent = new Date().toLocaleTimeString();
        showNotification('Sync completed successfully!', 'success');
    } catch (err) {
        console.error(err);
        statusIndicator.className = 'status-indicator status-error';
        statusText.textContent = 'Sync failed';
        showNotification('Sync failed', 'error');
    }
}

async function clearQueue() {
    await authFetch('/queue/clear', { method: 'POST' });
    showNotification('Queue cleared', 'success');
    await updateStats();
    if (currentTab === 'queue') loadTracks();
}

async function fetchPodcasts() {
    const feedUrl = document.getElementById('podcast-feed-url').value.trim();
    if (!feedUrl) return;
    await authFetch('/podcasts/fetch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feed_url: feedUrl })
    });
    document.getElementById('podcast-feed-url').value = '';
    showNotification('Podcast download queued', 'success');
    await updateStats();
    if (currentTab === 'queue') loadTracks();
}

function playTrack(id) {
    sendControl('play');
}

async function removeTrack(id) {
    await authFetch('/tracks/' + id, { method: 'DELETE' });
    showNotification('Track removed', 'success');
    await loadTracks();
    await updateStats();
}

async function sendControl(cmd) {
    await authFetch('/control/' + cmd, { method: 'POST' });
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
