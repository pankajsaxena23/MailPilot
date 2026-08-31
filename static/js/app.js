// State Management
let recipients = [];
let currentDraft = null;

// Prompt Templates
const TEMPLATES = {
    meeting: {
        subject: "Meeting Invitation: Q3 Project Review & Next Steps",
        tone: "Professional",
        instructions: "Propose a 30-minute sync this Thursday at 2:00 PM EST via Google Meet. Outline the agenda: project status, upcoming milestone deliverables, and Q&A."
    },
    followup: {
        subject: "Following up on our recent conversation",
        tone: "Friendly",
        instructions: "Kindly follow up on the proposal sent last week. Ask if they had a chance to review the details and if they have any questions."
    },
    cold_outreach: {
        subject: "Quick question regarding your team's workflow",
        tone: "Persuasive",
        instructions: "Introduce our solution briefly, highlight a key value proposition (saving 5+ hours weekly on email operations), and ask for a quick 10-minute intro chat next week."
    },
    interview: {
        subject: "Interview Invitation: Senior Software Engineer at MailPilot",
        tone: "Formal",
        instructions: "Invite the candidate for a 45-minute technical interview. Mention that the interview will cover system design and previous project experiences. Ask for their availability over the next 3 business days."
    },
    announcement: {
        subject: "Exciting Update: Introducing MailPilot AI",
        tone: "Enthusiastic",
        instructions: "Announce our major product release featuring instant Gemini AI email drafting, smart tone refinement, and automated deliverability tracking. Include a call to action to test the new features."
    },
    thankyou: {
        subject: "Thank you for your partnership and support",
        tone: "Friendly",
        instructions: "Express sincere gratitude for their recent collaboration on the project. Highlight the great results achieved together and express excitement for future initiatives."
    }
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    updateGreeting();

    // Setup navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            const target = e.currentTarget.dataset.target;
            navigate(target);
        });
    });

    // Load initial data
    loadDashboardStats();
    loadSettings();

    // Setup Enter key for quick recipient addition
    const newRecipientInput = document.getElementById('new-recipient');
    if (newRecipientInput) {
        newRecipientInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addRecipient();
            }
        });
    }

    const customRefineInput = document.getElementById('custom-refine-instruction');
    if (customRefineInput) {
        customRefineInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                refineWithCustomInstruction();
            }
        });
    }
});

function updateGreeting() {
    const greetingEl = document.getElementById('greeting-text');
    if (!greetingEl) return;
    greetingEl.textContent = 'Greetings';
}

function navigate(viewId) {
    document.querySelectorAll('.view-section').forEach(view => {
        view.classList.remove('active');
    });

    const targetView = document.getElementById(viewId);
    if (targetView) targetView.classList.add('active');

    // Update active nav link
    document.querySelectorAll('.nav-link').forEach(link => {
        if (link.dataset.target === viewId) {
            link.classList.add('active');
        } else if (viewId === 'email-editor' && link.dataset.target === 'create-email') {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });

    // View specific triggers
    if (viewId === 'dashboard') loadDashboardStats();
    if (viewId === 'history') loadHistory();
    if (viewId === 'recipients') loadRecipients();
    if (viewId === 'settings') loadSettings();
}

// Toast Notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let icon = 'info';
    if (type === 'success') icon = 'check_circle';
    if (type === 'error') icon = 'error';

    toast.innerHTML = `<span class="material-symbols-outlined" style="font-size:18px;">${icon}</span> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(20px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// Template Application
function applyTemplate(type) {
    const t = TEMPLATES[type];
    if (!t) return;

    document.getElementById('ai-subject').value = t.subject;
    document.getElementById('ai-tone').value = t.tone;
    document.getElementById('ai-instructions').value = t.instructions;
    showToast(`Loaded "${type.replace('_', ' ')}" template`, 'info');
}

// Stats & Dashboard
async function loadDashboardStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();

        document.getElementById('stat-sent').textContent = data.emails_sent || 0;
        document.getElementById('stat-drafts').textContent = data.ai_drafts || 0;
        document.getElementById('stat-recipients').textContent = data.recipients || 0;
        document.getElementById('stat-failed').textContent = data.failed_emails || 0;

        const tbody = document.querySelector('#recent-activity-table tbody');
        tbody.innerHTML = '';

        if (!data.recent_activity || data.recent_activity.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:var(--text-muted); padding:24px;">No recent campaign activity. Click "Create email" to get started!</td></tr>';
            return;
        }

        data.recent_activity.forEach(item => {
            const dateStr = item.created_at ? new Date(item.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '';
            let statusClass = 'status-draft';
            if (item.status === 'Sent') statusClass = 'status-sent';
            if (item.status === 'Failed') statusClass = 'status-failed';
            if (item.status === 'Partial') statusClass = 'status-partial';

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-weight:600; cursor:pointer;" onclick="openCampaignInEditor(${item.id})">${item.subject}</td>
                <td>${item.recipient_count} recipient(s)</td>
                <td><span class="status-badge ${statusClass}">${item.status}</span></td>
                <td style="color:var(--text-secondary);">${dateStr}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error('Error loading stats:', e);
    }
}

// History View
async function loadHistory() {
    try {
        const res = await fetch('/api/history');
        const data = await res.json();

        const tbody = document.querySelector('#history-table tbody');
        tbody.innerHTML = '';

        if (!data || data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:var(--text-muted); padding:32px;">No email campaigns recorded yet.</td></tr>';
            return;
        }

        data.forEach(item => {
            const createdStr = item.created_at ? new Date(item.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '';
            const sentStr = item.sent_at ? new Date(item.sent_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-';

            let statusClass = 'status-draft';
            if (item.status === 'Sent') statusClass = 'status-sent';
            if (item.status === 'Failed') statusClass = 'status-failed';
            if (item.status === 'Partial') statusClass = 'status-partial';

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-weight:600;">${item.subject}</td>
                <td><span style="font-size:12px; color:var(--text-secondary); background:var(--bg-secondary); padding:2px 6px; border-radius:4px;">${item.tone || 'Custom'}</span></td>
                <td>${item.recipient_count} recipient(s)</td>
                <td><span class="status-badge ${statusClass}">${item.status}</span></td>
                <td style="color:var(--text-secondary);">${createdStr}</td>
                <td style="color:var(--text-secondary);">${sentStr}</td>
                <td>
                    <button class="btn btn-secondary btn-icon" title="Open in Editor" onclick="openCampaignInEditor(${item.id})">
                        <span class="material-symbols-outlined" style="font-size:16px;">edit_note</span>
                    </button>
                    <button class="btn btn-outline btn-icon" title="Delete Campaign" onclick="deleteCampaign(${item.id})" style="margin-left:4px;">
                        <span class="material-symbols-outlined" style="font-size:16px; color:var(--error);">delete</span>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error('Error loading history:', e);
    }
}

async function openCampaignInEditor(campaignId) {
    try {
        const res = await fetch(`/api/campaigns/${campaignId}`);
        if (!res.ok) throw new Error('Could not load campaign');
        const campaign = await res.json();

        currentDraft = {
            subject: campaign.subject,
            content: campaign.content,
            tone: campaign.tone
        };

        document.getElementById('editor-subject').value = campaign.subject;
        document.getElementById('email-content-editable').value = campaign.content;
        document.getElementById('editor-model-badge').textContent = `Campaign #${campaign.id}`;
        navigate('email-editor');
    } catch (e) {
        showToast('Failed to open campaign: ' + e.message, 'error');
    }
}

async function deleteCampaign(campaignId) {
    if (!confirm('Are you sure you want to delete this campaign record?')) return;
    try {
        const res = await fetch(`/api/campaigns/${campaignId}`, { method: 'DELETE' });
        if (res.ok) {
            showToast('Campaign deleted successfully', 'success');
            loadHistory();
            loadDashboardStats();
        } else {
            showToast('Failed to delete campaign', 'error');
        }
    } catch (e) {
        showToast('Error deleting campaign', 'error');
    }
}

// Directory Recipients View
async function loadRecipients() {
    try {
        const res = await fetch('/api/recipients');
        const data = await res.json();

        const tbody = document.querySelector('#recipients-table tbody');
        tbody.innerHTML = '';

        if (!data || data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--text-muted); padding:32px;">No contacts added to directory yet.</td></tr>';
            return;
        }

        data.forEach(item => {
            const dateStr = item.last_contact ? new Date(item.last_contact).toLocaleDateString() : 'Never';
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-weight:600;">${item.name || '-'}</td>
                <td>${item.email}</td>
                <td>${item.emails_sent} sent</td>
                <td style="color:var(--text-secondary);">${dateStr}</td>
                <td>
                    <button class="btn btn-secondary btn-icon" title="Add to Active Campaign" onclick="addEmailToTargetList('${item.email}')">
                        <span class="material-symbols-outlined" style="font-size:16px;">add</span>
                    </button>
                    <button class="btn btn-outline btn-icon" title="Delete Contact" onclick="deleteContact(${item.id})" style="margin-left:4px;">
                        <span class="material-symbols-outlined" style="font-size:16px; color:var(--error);">delete</span>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error('Error loading recipients:', e);
    }
}

async function addDirectoryContact() {
    const nameInput = document.getElementById('directory-name');
    const emailInput = document.getElementById('directory-email');
    const email = emailInput.value.trim().toLowerCase();
    const name = nameInput.value.trim();

    if (!email || !isValidEmail(email)) {
        showToast('Please enter a valid email address.', 'error');
        return;
    }

    try {
        const res = await fetch('/api/recipients', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, name })
        });
        const data = await res.json();
        if (res.ok) {
            showToast('Contact added to directory', 'success');
            nameInput.value = '';
            emailInput.value = '';
            loadRecipients();
            loadDashboardStats();
        } else {
            showToast(data.error || 'Failed to add contact', 'error');
        }
    } catch (e) {
        showToast('Error saving contact', 'error');
    }
}

async function deleteContact(id) {
    if (!confirm('Remove this contact from directory?')) return;
    try {
        const res = await fetch(`/api/recipients/${id}`, { method: 'DELETE' });
        if (res.ok) {
            showToast('Contact removed', 'success');
            loadRecipients();
            loadDashboardStats();
        }
    } catch (e) {
        showToast('Error removing contact', 'error');
    }
}

function addEmailToTargetList(email) {
    if (!recipients.includes(email)) {
        recipients.push(email);
        renderRecipients();
        showToast(`Added ${email} to current campaign`, 'success');
    } else {
        showToast(`${email} is already in the list`, 'info');
    }
}

// Settings View & Test AI
async function loadSettings() {
    try {
        const res = await fetch('/api/settings');
        const data = await res.json();

        const emailEl = document.getElementById('settings-email');
        if (emailEl) emailEl.textContent = data.email || 'Not configured';

        const editorFrom = document.getElementById('editor-from');
        if (editorFrom) editorFrom.textContent = data.email || 'Not configured';

        const confirmFrom = document.getElementById('confirm-from');
        if (confirmFrom) confirmFrom.textContent = data.email || 'Not configured';

        const smtpStatus = document.getElementById('settings-smtp-status');
        if (smtpStatus) {
            if (data.smtp_connected) {
                smtpStatus.className = 'status-badge status-sent';
                smtpStatus.innerHTML = '<span class="material-symbols-outlined" style="font-size:14px">check</span> Connected';
            } else {
                smtpStatus.className = 'status-badge status-failed';
                smtpStatus.innerHTML = 'Not Configured';
            }
        }

        const apiStatus = document.getElementById('settings-api-status');
        if (apiStatus) {
            if (data.api_connected) {
                apiStatus.className = 'status-badge status-sent';
                apiStatus.innerHTML = '<span class="material-symbols-outlined" style="font-size:14px">check</span> Active';
            } else {
                apiStatus.className = 'status-badge status-failed';
                apiStatus.innerHTML = 'Not Configured';
            }
        }
    } catch (e) {
        console.error('Error loading settings:', e);
    }
}

async function testAIConnection() {
    const btn = document.getElementById('btn-test-ai');
    const resultEl = document.getElementById('ai-test-result');
    if (!btn) return;

    btn.disabled = true;
    btn.innerHTML = '<span class="material-symbols-outlined" style="animation: spin 1s linear infinite;">sync</span> Testing...';
    if (resultEl) resultEl.textContent = '';

    try {
        const res = await fetch('/api/test-ai', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        const data = await res.json();
        if (data.success) {
            if (resultEl) {
                resultEl.style.color = 'var(--success)';
                resultEl.textContent = `✓ ${data.message}`;
            }
            showToast(data.message, 'success');
        } else {
            if (resultEl) {
                resultEl.style.color = 'var(--error)';
                resultEl.textContent = `✕ ${data.message}`;
            }
            showToast('AI Connection test failed: ' + data.message, 'error');
        }
    } catch (e) {
        if (resultEl) {
            resultEl.style.color = 'var(--error)';
            resultEl.textContent = '✕ Network error testing AI connection';
        }
        showToast('Network error during test', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span class="material-symbols-outlined">sync</span> Test Gemini Connection';
    }
}

// Recipient Management in Create View
function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function addRecipient() {
    const input = document.getElementById('new-recipient');
    if (!input) return;
    const rawVal = input.value.trim().toLowerCase();

    if (!rawVal) return;

    // Handle comma or space separated emails
    const emailList = rawVal.split(/[,;\s]+/).filter(e => e.length > 0);
    let addedCount = 0;

    for (const email of emailList) {
        if (!isValidEmail(email)) {
            showToast(`"${email}" is not a valid email address.`, 'error');
            continue;
        }
        if (recipients.includes(email)) {
            showToast(`"${email}" is already in the list.`, 'info');
            continue;
        }
        recipients.push(email);
        addedCount++;
    }

    input.value = '';
    renderRecipients();
    if (addedCount > 0) {
        showToast(`Added ${addedCount} recipient(s)`, 'success');
    }
}

function removeRecipient(email) {
    recipients = recipients.filter(r => r !== email);
    renderRecipients();
}

function renderRecipients() {
    const countDisplay = document.getElementById('recipient-count-display');
    if (countDisplay) countDisplay.textContent = recipients.length;

    const editorCountDisplay = document.getElementById('editor-to-count');
    if (editorCountDisplay) editorCountDisplay.textContent = `${recipients.length} recipient(s)`;

    const container = document.getElementById('recipient-list-container');
    if (!container) return;
    container.innerHTML = '';

    if (recipients.length === 0) {
        container.innerHTML = '<div style="padding: 24px 16px; color: var(--text-muted); text-align: center; font-size: 13px;">No recipients added yet. Type an email above or add from Contact Directory.</div>';
        return;
    }

    recipients.forEach(email => {
        const div = document.createElement('div');
        div.className = 'recipient-item';
        div.innerHTML = `
            <div style="display:flex; align-items:center; gap:8px;">
                <span class="material-symbols-outlined" style="font-size:16px; color:var(--success);">check_circle</span>
                <span>${email}</span>
            </div>
            <button class="recipient-remove" onclick="removeRecipient('${email}')" title="Remove">
                <span class="material-symbols-outlined" style="font-size:18px;">close</span>
            </button>
        `;
        container.appendChild(div);
    });
}

// AI Email Generation
async function generateEmail(isRegenerate = false) {
    const subjectInput = document.getElementById('ai-subject');
    const toneInput = document.getElementById('ai-tone');
    const instructionsInput = document.getElementById('ai-instructions');

    const subject = subjectInput ? subjectInput.value.trim() : '';
    const tone = toneInput ? toneInput.value : 'Professional';
    const instructions = instructionsInput ? instructionsInput.value.trim() : '';

    if (!subject) {
        showToast('Please enter an email subject or topic.', 'error');
        if (subjectInput) subjectInput.focus();
        return;
    }

    const btn = document.getElementById('btn-generate');
    const originalText = btn ? btn.innerHTML : '';

    if (!isRegenerate && btn) {
        btn.innerHTML = '<span class="material-symbols-outlined" style="animation: spin 1s linear infinite;">sync</span> Generating with Gemini AI...';
        btn.disabled = true;
    }

    try {
        const res = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ subject, tone, instructions })
        });

        const data = await res.json();

        if (data.error) {
            showToast('AI Generation error: ' + data.error, 'error');
        } else {
            currentDraft = data;
            const editorSubject = document.getElementById('editor-subject');
            if (editorSubject) editorSubject.value = data.subject;

            const editorContent = document.getElementById('email-content-editable');
            if (editorContent) editorContent.value = data.content;

            const modelBadge = document.getElementById('editor-model-badge');
            if (modelBadge) modelBadge.textContent = '✨ Gemini AI';

            showToast('Email generated successfully!', 'success');
            navigate('email-editor');
        }
    } catch (e) {
        console.error(e);
        showToast('Failed to communicate with AI service.', 'error');
    } finally {
        if (!isRegenerate && btn) {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    }
}

// AI Refinements
async function refineWithAI(instruction) {
    const contentEl = document.getElementById('email-content-editable');
    const content = contentEl ? contentEl.value.trim() : '';
    const tone = document.getElementById('ai-tone') ? document.getElementById('ai-tone').value : 'Professional';

    if (!content) {
        showToast('Email body is empty. Please generate or write content first.', 'error');
        return;
    }

    showToast('Applying AI refinement...', 'info');

    try {
        const res = await fetch('/api/refine', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content, instruction, tone })
        });

        const data = await res.json();
        if (data.error) {
            showToast('Refinement error: ' + data.error, 'error');
        } else {
            if (contentEl) contentEl.value = data.content;
            showToast('Refinement applied successfully!', 'success');
        }
    } catch (e) {
        showToast('Failed to apply AI refinement', 'error');
    }
}

async function refineWithCustomInstruction() {
    const input = document.getElementById('custom-refine-instruction');
    const instruction = input ? input.value.trim() : '';

    if (!instruction) {
        showToast('Please type an instruction to refine the email.', 'info');
        if (input) input.focus();
        return;
    }

    const btn = document.getElementById('btn-custom-refine');
    const originalText = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="material-symbols-outlined" style="animation: spin 1s linear infinite;">sync</span> Working...';
    }

    await refineWithAI(instruction);

    if (btn) {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
    if (input) input.value = '';
}

function copyEmailToClipboard() {
    const contentEl = document.getElementById('email-content-editable');
    const content = contentEl ? contentEl.value : '';
    if (!content) {
        showToast('No content to copy.', 'info');
        return;
    }
    navigator.clipboard.writeText(content).then(() => {
        showToast('Email content copied to clipboard!', 'success');
    }).catch(() => {
        showToast('Could not copy to clipboard', 'error');
    });
}

// Save Draft
async function saveDraft() {
    const subjectEl = document.getElementById('editor-subject');
    const contentEl = document.getElementById('email-content-editable');
    const subject = subjectEl ? subjectEl.value.trim() : '';
    const content = contentEl ? contentEl.value.trim() : '';
    const tone = currentDraft ? currentDraft.tone : 'Professional';

    if (!subject || !content) {
        showToast('Subject and email content are required to save draft.', 'error');
        return;
    }

    try {
        const res = await fetch('/api/campaigns', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ subject, content, tone })
        });
        const data = await res.json();
        if (res.ok) {
            showToast('Draft saved to campaign history!', 'success');
            loadDashboardStats();
        } else {
            showToast('Failed to save draft: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (e) {
        showToast('Failed to save draft.', 'error');
    }
}

// Send Campaign
function showSendConfirmation() {
    const contentEl = document.getElementById('email-content-editable');
    const subjectEl = document.getElementById('editor-subject');
    const content = contentEl ? contentEl.value.trim() : '';
    const subject = subjectEl ? subjectEl.value.trim() : '';

    if (!subject) {
        showToast('Please enter an email subject.', 'error');
        return;
    }

    if (!content) {
        showToast('Email content is empty.', 'error');
        return;
    }

    if (recipients.length === 0) {
        showToast('Please add at least one recipient.', 'error');
        navigate('create-email');
        return;
    }

    const confirmSub = document.getElementById('confirm-subject');
    if (confirmSub) confirmSub.textContent = subject;

    const confirmCount = document.getElementById('confirm-count');
    if (confirmCount) confirmCount.textContent = recipients.length;

    const confirmPreview = document.getElementById('confirm-preview');
    if (confirmPreview) confirmPreview.textContent = content.substring(0, 200) + (content.length > 200 ? '...' : '');

    const modalConfirm = document.getElementById('modal-confirm');
    if (modalConfirm) modalConfirm.classList.add('active');
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('active');
}

async function startSending() {
    closeModal('modal-confirm');

    const subject = document.getElementById('editor-subject').value.trim();
    const content = document.getElementById('email-content-editable').value.trim();
    const progressModal = document.getElementById('modal-progress');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const progressLog = document.getElementById('progress-log');

    progressModal.classList.add('active');
    progressBar.style.width = '15%';
    progressText.textContent = `Connecting to SMTP host...`;
    progressLog.innerHTML = '<div>[INIT] Establishing secure TLS connection...</div>';

    try {
        const res = await fetch('/api/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                subject: subject,
                content: content,
                recipients: recipients
            })
        });

        progressBar.style.width = '75%';
        progressText.textContent = `Dispatched campaign. Processing delivery report...`;

        const data = await res.json();
        progressBar.style.width = '100%';

        if (data.results) {
            let successCount = 0;
            data.results.forEach(r => {
                const isSuccess = r.status === 'Sent';
                if (isSuccess) successCount++;
                progressLog.innerHTML += `
                    <div style="color: ${isSuccess ? '#4ADE80' : '#F87171'}">
                        ${isSuccess ? '✓ DELIVERED' : '✕ FAILED'} &rarr; ${r.email} ${r.error ? '(' + r.error + ')' : ''}
                    </div>
                `;
            });

            setTimeout(() => {
                closeModal('modal-progress');
                document.getElementById('success-message').textContent = `${successCount} of ${recipients.length} recipients received the email.`;
                document.getElementById('modal-success').classList.add('active');

                // Clear campaign form state
                recipients = [];
                currentDraft = null;
                const aiSub = document.getElementById('ai-subject');
                if (aiSub) aiSub.value = '';
                const aiInst = document.getElementById('ai-instructions');
                if (aiInst) aiInst.value = '';
                const emailEdit = document.getElementById('email-content-editable');
                if (emailEdit) emailEdit.value = '';

                renderRecipients();
                loadDashboardStats();
            }, 1200);
        } else {
            showToast('Sending failed: ' + (data.error || 'Unknown error'), 'error');
            closeModal('modal-progress');
        }

    } catch (e) {
        console.error(e);
        showToast('Communication error during email dispatch.', 'error');
        closeModal('modal-progress');
    }
}

// Global Spinner Keyframes
const style = document.createElement('style');
style.innerHTML = `
@keyframes spin {
    100% { transform: rotate(360deg); }
}
`;
document.head.appendChild(style);
