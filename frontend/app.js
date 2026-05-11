// API base URL
const API_BASE = window.location.origin;

// State
let allApplications = [];
let currentFilter = '';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadApplications();
    
    // Event listeners
    document.getElementById('sync-btn').addEventListener('click', syncEmails);
    document.getElementById('refresh-btn').addEventListener('click', () => {
        loadStats();
        loadApplications();
    });
    document.getElementById('status-filter').addEventListener('change', (e) => {
        currentFilter = e.target.value;
        loadApplications();
    });
});

// Load statistics
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/api/stats`);
        const data = await response.json();
        
        document.getElementById('total-apps').textContent = data.total_applications;
        document.getElementById('applied-count').textContent = data.status_breakdown.applied || 0;
        document.getElementById('interview-count').textContent = data.status_breakdown.interview || 0;
        document.getElementById('offer-count').textContent = data.status_breakdown.offer || 0;
        document.getElementById('rejection-count').textContent = data.status_breakdown.rejection || 0;
        document.getElementById('ghosted-count').textContent = data.potentially_ghosted || 0;
        
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load applications
async function loadApplications() {
    try {
        const url = currentFilter 
            ? `${API_BASE}/api/applications?status=${currentFilter}`
            : `${API_BASE}/api/applications`;
        
        const response = await fetch(url);
        const data = await response.json();
        
        allApplications = data.applications;
        renderApplications(allApplications);
        
    } catch (error) {
        console.error('Error loading applications:', error);
        document.getElementById('applications-list').innerHTML = 
            '<div class="loading" style="color: #e74c3c;">Error loading applications</div>';
    }
}

// Render applications
function renderApplications(applications) {
    const container = document.getElementById('applications-list');
    
    if (applications.length === 0) {
        container.innerHTML = '<div class="loading">No applications found. Click "Sync Emails" to get started!</div>';
        return;
    }
    
    container.innerHTML = applications.map(app => `
        <div class="application-card">
            <div class="app-header">
                <div class="app-title">
                    <h3>${escapeHtml(app.role)}</h3>
                    <div class="app-company">${escapeHtml(app.company)}</div>
                </div>
                <span class="app-status status-${app.status}">${app.status}</span>
            </div>
            
            <div class="app-details">
                <div class="app-email">
                    📧 ${escapeHtml(app.last_email_subject || 'No subject')}
                </div>
                ${app.last_email_snippet ? `
                    <div class="app-snippet">
                        "${escapeHtml(app.last_email_snippet.substring(0, 150))}..."
                    </div>
                ` : ''}
            </div>
            
            <div class="app-meta">
                <span>📅 ${formatDate(app.last_email_date || app.created_at)}</span>
                <span class="app-confidence">
                    AI Confidence:
                    <div class="confidence-bar">
                        <div class="confidence-fill" style="width: ${app.confidence * 100}%"></div>
                    </div>
                    ${Math.round(app.confidence * 100)}%
                </span>
            </div>
        </div>
    `).join('');
}

// Sync emails
async function syncEmails() {
    const syncBtn = document.getElementById('sync-btn');
    const syncText = document.getElementById('sync-text');
    const syncLoader = document.getElementById('sync-loader');
    const statusDiv = document.getElementById('sync-status');
    
    // Disable button and show loader
    syncBtn.disabled = true;
    syncText.classList.add('hidden');
    syncLoader.classList.remove('hidden');
    
    try {
        const response = await fetch(`${API_BASE}/api/sync`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            statusDiv.className = 'success';
            statusDiv.textContent = `✅ Sync complete! Processed ${data.emails_processed} emails, ` +
                                   `${data.new_applications} new applications, ` +
                                   `${data.updated_applications} updated.`;
            statusDiv.classList.remove('hidden');
            
            // Reload data
            loadStats();
            loadApplications();
            
            // Hide status after 5 seconds
            setTimeout(() => {
                statusDiv.classList.add('hidden');
            }, 5000);
        } else {
            throw new Error('Sync failed');
        }
        
    } catch (error) {
        console.error('Sync error:', error);
        statusDiv.className = 'error';
        statusDiv.textContent = `❌ Sync failed: ${error.message}`;
        statusDiv.classList.remove('hidden');
    } finally {
        // Re-enable button
        syncBtn.disabled = false;
        syncText.classList.remove('hidden');
        syncLoader.classList.add('hidden');
    }
}

// Utility functions
function formatDate(dateStr) {
    if (!dateStr) return 'Unknown date';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    
    return date.toLocaleDateString();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
