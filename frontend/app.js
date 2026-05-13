// API base URL
const API_BASE = window.location.origin;

const STATUS_LABELS = {
    'APPLIED':    'Applied',
    'INTERVIEW':  'Interview',
    'REJECTION':  'Rejected',
    'OFFER':      'Offer',
    'GHOSTED':    'Ghosted',
    'JOB_ALERT':  'Job Alert',
    'OTHER':      'Other',
};

// State
let allApplications = [];
let currentFilter = '';
const PAGE_SIZE = 10;
let currentPage = 1;

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    // Check if setup is complete
    await checkSetupStatus();
    
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
    document.getElementById('reset-btn').addEventListener('click', resetData);
    document.getElementById('logout-btn').addEventListener('click', logout);
});

// Check setup status and redirect to onboarding if needed
async function checkSetupStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/setup-status`);
        const status = await response.json();
        
        if (status.needs_onboarding) {
            window.location.href = '/onboarding';
        }
    } catch (error) {
        console.error('Error checking setup status:', error);
    }
}

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
        document.getElementById('job-alert-count').textContent = data.status_breakdown.job_alert || 0;
        
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
        currentPage = 1;
        renderApplications();
        
    } catch (error) {
        console.error('Error loading applications:', error);
        document.getElementById('applications-list').innerHTML = 
            '<div class="loading" style="color: #c07070;">Error loading applications</div>';
    }
}

// Render applications
function renderApplications() {
    const container = document.getElementById('applications-list');
    
    if (allApplications.length === 0) {
        container.innerHTML = '<div class="loading">No applications found. Click "Sync Emails" to get started!</div>';
        document.getElementById('pagination').innerHTML = '';
        return;
    }

    const totalPages = Math.ceil(allApplications.length / PAGE_SIZE);
    currentPage = Math.min(currentPage, totalPages);
    const start = (currentPage - 1) * PAGE_SIZE;
    const page = allApplications.slice(start, start + PAGE_SIZE);
    
    container.innerHTML = page.map(app => {
        const rawBody = normalizeBody(app.last_email_body || '')
            || 'No email body stored — resync to capture new emails.';
        const sender = escapeHtml(app.last_email_from || 'Unknown sender');
        const dateFormatted = app.last_email_date
            ? new Date(app.last_email_date).toLocaleString()
            : 'Unknown date';

        return `
        <div class="application-card" data-id="${app.id}">
            <div class="app-main" onclick="toggleExpand(this)">
                <div class="app-title">
                    <h3>${escapeHtml(app.role)}</h3>
                    <div class="app-company">${escapeHtml(app.company)}</div>
                </div>
                <span class="app-status status-${app.status}">${STATUS_LABELS[app.status] || app.status}</span>
                <span class="confidence-pill">${Math.round(app.confidence * 100)}%</span>
                <div class="app-date">${formatDate(app.last_email_date || app.created_at)}</div>
                <span class="app-expand-icon">&#9660;</span>
            </div>
            <div class="app-expanded">
                <div class="email-meta">
                    <span class="email-meta-label">From</span>
                    <span class="email-meta-value">${sender}</span>
                    <span class="email-meta-label">Date</span>
                    <span class="email-meta-value">${dateFormatted}</span>
                    <span class="email-meta-label">Subject</span>
                    <span class="email-meta-value email-subject">${escapeHtml(app.last_email_subject || 'No subject')}</span>
                </div>
                <div class="email-body">${escapeHtml(rawBody)}</div>
            </div>
        </div>`;
    }).join('');

    renderPagination(totalPages);
}

function renderPagination(totalPages) {
    const el = document.getElementById('pagination');
    if (totalPages <= 1) { el.innerHTML = ''; return; }

    const items = [];
    items.push(`<button class="page-btn" onclick="goToPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>&#8592;</button>`);

    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || Math.abs(i - currentPage) <= 1) {
            items.push(`<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`);
        } else if (Math.abs(i - currentPage) === 2) {
            items.push(`<span class="page-ellipsis">…</span>`);
        }
    }

    items.push(`<button class="page-btn" onclick="goToPage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>&#8594;</button>`);
    el.innerHTML = items.join('');
}

function goToPage(page) {
    const totalPages = Math.ceil(allApplications.length / PAGE_SIZE);
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    renderApplications();
    document.querySelector('.applications-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function toggleExpand(header) {
    const card = header.closest('.application-card');
    const expanded = card.querySelector('.app-expanded');
    const icon = card.querySelector('.app-expand-icon');
    expanded.classList.toggle('show');
    icon.classList.toggle('open');
}

function stripHtml(html) {
    const el = document.createElement('div');
    el.innerHTML = html;
    return el.textContent || el.innerText || '';
}

function normalizeBody(text) {
    // Strip any residual HTML tags
    const plain = stripHtml(text);
    // Trim each line, then collapse runs of 3+ blank lines to one blank line
    const lines = plain.split('\n').map(l => l.trimEnd());
    const out = [];
    let blankRun = 0;
    for (const line of lines) {
        if (line.trim() === '') {
            blankRun++;
            if (blankRun <= 1) out.push('');
        } else {
            blankRun = 0;
            out.push(line);
        }
    }
    return out.join('\n').trim();
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

async function resetData() {
    if (!confirm('Delete ALL tracked applications and email logs? This cannot be undone.')) return;
    const statusDiv = document.getElementById('sync-status');
    try {
        const res = await fetch(`${API_BASE}/api/reset-data`, { method: 'POST' });
        const data = await res.json();
        statusDiv.className = 'success';
        statusDiv.textContent = `Cleared ${data.deleted_applications} applications and ${data.deleted_logs} email logs. Sync again to rebuild.`;
        statusDiv.classList.remove('hidden');
        loadStats();
        loadApplications();
    } catch (e) {
        statusDiv.className = 'error';
        statusDiv.textContent = `Reset failed: ${e.message}`;
        statusDiv.classList.remove('hidden');
    }
}

async function logout() {
    if (!confirm('Disconnect Gmail? You will need to re-authorise on the next page load.')) return;
    await fetch(`${API_BASE}/api/logout`, { method: 'POST' });
    window.location.href = '/onboarding';
}
