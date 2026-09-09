// Administrative dashboard: polling, live alerts, controls, tables, and evidence.
let allChallans = [];
let lastAlertNo = null;

document.addEventListener('DOMContentLoaded', () => {
  // Start the clock and periodic API refreshes after the DOM is ready.
  startClock();
  loadDashboardData();
  loadChallans();
  
  // Polling intervals
  setInterval(loadDashboardData, 3000);
  setInterval(pollLiveAlerts, 1500);
});

function startClock() {
  // Display local time and ISO date for live activity monitoring.
  const clockEl = document.getElementById('liveClock');
  setInterval(() => {
    const now = new Date();
    clockEl.innerText = now.toLocaleTimeString() + ' | ' + now.toISOString().split('T')[0];
  }, 1000);
}

// 1. Fetch KPI, feed, and chart data from the combined analytics endpoint.
async function loadDashboardData() {
  try {
    const res = await fetch('/api/analytics/dashboard');
    if (!res.ok) return;
    const data = await res.json();

    // Update the summary cards with the newest aggregate values.
    document.getElementById('kpiTotalChallans').innerText = data.stats.total_challans;
    document.getElementById('kpiRevenue').innerText = 'PKR ' + Number(data.stats.total_revenue).toLocaleString();
    document.getElementById('kpiPendingRevenue').innerText = 'PKR ' + Number(data.stats.pending_revenue).toLocaleString();

    // Replace the feed with the latest records from the backend.
    renderLiveFeed(data.recent_challans);

    // Render grouped violation data when the API has chart rows.
    if (data.violations_by_type && data.violations_by_type.length > 0) {
      renderViolationsChart(data.violations_by_type);
    }
  } catch (err) {
    console.warn('Dashboard poll error:', err);
  }
}

function renderLiveFeed(challans) {
  const feedList = document.getElementById('liveFeedList');
  if (!feedList || !challans) return;

  if (challans.length === 0) {
    feedList.innerHTML = '<div style="text-align:center; padding: 2rem; color: var(--text-muted);">No recent violations recorded.</div>';
    return;
  }

  feedList.innerHTML = challans.map(c => `
    <div class="feed-item" onclick="openEvidenceModal('${c.challan_no}')" style="cursor: pointer;">
      <div style="display: flex; align-items: center; gap: 12px;">
        <span class="plate-badge">${c.plate_number}</span>
        <div>
          <div style="font-size: 0.85rem; font-weight: 700; color: #f8fafc;">${c.violation_name}</div>
          <div style="font-size: 0.72rem; color: var(--text-muted);">${c.location} | ${c.created_at}</div>
        </div>
      </div>
      <div style="text-align: right;">
        <div style="font-weight: 700; color: #f87171; font-size: 0.9rem;">PKR ${Number(c.fine_amount).toLocaleString()}</div>
        <span class="status-pill ${c.status.toLowerCase()}">${c.status}</span>
      </div>
    </div>
  `).join('');
}

// 2. Check for a new alert and refresh records when one appears.
async function pollLiveAlerts() {
  try {
    const res = await fetch('/api/stream/live_alert');
    if (!res.ok) return;
    const data = await res.json();

    if (data.alert && data.alert.challan_no !== lastAlertNo) {
      lastAlertNo = data.alert.challan_no;
      
      const ticker = document.getElementById('alertTicker');
      document.getElementById('alertTitle').innerText = `VIOLATION DETECTED: [${data.alert.plate_number}]`;
      document.getElementById('alertDesc').innerText = `${data.alert.violation_name} at ${data.alert.location} | Fine: PKR ${data.alert.fine_amount.toLocaleString()}`;
      ticker.style.display = 'flex';

      // Make the new challan visible in both the feed and master table.
      loadDashboardData();
      loadChallans();
    }
  } catch (err) {
    console.warn('Alert poll error:', err);
  }
}

// 3. Send camera, signal, and speed-limit controls to the API.
async function setSignal(state) {
  try {
    const res = await fetch(`/api/stream/set_signal/${state}`, { method: 'POST' });
    const data = await res.json();
    if (data.status === 'success') {
      console.log('Signal changed to:', state);
    }
  } catch (err) {
    alert('Failed to set signal: ' + err.message);
  }
}

async function setSpeedLimit(limit) {
  try {
    const res = await fetch(`/api/stream/set_speed_limit/${limit}`, { method: 'POST' });
    const data = await res.json();
    if (data.status === 'success') {
      console.log('Speed limit set to:', limit);
    }
  } catch (err) {
    alert('Failed to update speed limit: ' + err.message);
  }
}

async function changeCamera(cameraId) {
  try {
    const res = await fetch(`/api/stream/select_camera/${cameraId}`, { method: 'POST' });
    const data = await res.json();
    if (data.status === 'success') {
      console.log('Switched camera to:', data.active_camera.name);
    }
  } catch (err) {
    alert('Failed to switch camera: ' + err.message);
  }
}

// 4. Load history and filter it locally for quick table searching.
async function loadChallans() {
  try {
    const res = await fetch('/api/challans?limit=100');
    if (!res.ok) return;
    const data = await res.json();
    allChallans = data.items || [];
    filterChallans();
  } catch (err) {
    console.warn('Error loading challans:', err);
  }
}

function filterChallans() {
  const searchQ = document.getElementById('tableSearchInput').value.trim().toUpperCase();
  const statusQ = document.getElementById('statusFilter').value;

  const filtered = allChallans.filter(c => {
    const matchesPlate = !searchQ || c.plate_number.toUpperCase().includes(searchQ) || c.challan_no.toUpperCase().includes(searchQ);
    const matchesStatus = (statusQ === 'ALL') || (c.status === statusQ);
    return matchesPlate && matchesStatus;
  });

  const tbody = document.getElementById('challansTableBody');
  if (!tbody) return;

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding: 2rem; color: var(--text-muted);">No challans match the selected filter.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(c => `
    <tr>
      <td><b style="color: #38bdf8; font-family: monospace;">${c.challan_no}</b></td>
      <td><span class="plate-badge">${c.plate_number}</span></td>
      <td>
        <div><b>${c.owner_name || 'Citizen'}</b></div>
        <div style="font-size: 0.72rem; color: var(--text-muted);">${c.vehicle_make || ''} ${c.vehicle_model || ''}</div>
      </td>
      <td><span style="color: #f87171; font-weight: 600;">${c.violation_name}</span></td>
      <td><span style="font-size: 0.8rem;">${c.location}</span></td>
      <td><b>PKR ${Number(c.fine_amount).toLocaleString()}</b></td>
      <td><span class="status-pill ${c.status.toLowerCase()}">${c.status}</span></td>
      <td style="font-size: 0.75rem; color: var(--text-muted);">${c.created_at}</td>
      <td>
        <div style="display: flex; gap: 6px;">
          <button class="btn btn-sm btn-secondary" onclick="openEvidenceModal('${c.challan_no}')" title="View Evidence">
            <i class="fa-solid fa-eye"></i>
          </button>
          <a href="/api/challans/${c.challan_no}/pdf" target="_blank" class="btn btn-sm btn-primary" title="Download PDF">
            <i class="fa-solid fa-file-arrow-down"></i>
          </a>
        </div>
      </td>
    </tr>
  `).join('');
}

// 5. Fetch one challan and render owner, offence, and evidence details.
async function openEvidenceModal(challanNo) {
  try {
    const res = await fetch(`/api/challans/${challanNo}`);
    if (!res.ok) return;
    const ch = await res.json();

    document.getElementById('modalChallanNo').innerText = ch.challan_no;
    document.getElementById('modalDate').innerText = `Issued on: ${ch.created_at} | Location: ${ch.location}`;
    document.getElementById('modalPdfBtn').href = `/api/challans/${ch.challan_no}/pdf`;

    const modalBody = document.getElementById('modalBody');
    const evidenceImg = ch.evidence_image ? `/evidence/${ch.evidence_image}` : '/static/sample_media/placeholder_proof.jpg';
    const plateImg = ch.plate_crop ? `/evidence/${ch.plate_crop}` : '';

    modalBody.innerHTML = `
      <!-- Offense Overview -->
      <div style="background: rgba(30, 41, 59, 0.6); padding: 12px; border-radius: var(--radius-md); border: 1px solid var(--border-color);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">VIOLATION CHARGE</div>
            <div style="font-size: 1.05rem; font-weight: 700; color: #ef4444;">${ch.violation_name}</div>
          </div>
          <div style="text-align: right;">
            <div style="font-size: 0.75rem; color: var(--text-muted);">PAYABLE FINE</div>
            <div style="font-size: 1.2rem; font-weight: 800; color: #10b981;">PKR ${Number(ch.fine_amount).toLocaleString()}</div>
          </div>
        </div>
        <div style="display: flex; gap: 10px; font-size: 0.8rem; color: var(--text-muted);">
          <span><i class="fa-solid fa-gauge"></i> Recorded Speed: <b>${ch.speed_detected} km/h</b> (Limit: ${ch.speed_limit} km/h)</span>
          <span>•</span>
          <span><i class="fa-solid fa-camera"></i> Camera: <b>${ch.camera_name}</b></span>
        </div>
      </div>

      <!-- Vehicle & Owner Information -->
      <div style="background: rgba(30, 41, 59, 0.4); padding: 12px; border-radius: var(--radius-md); border: 1px solid var(--border-color); font-size: 0.82rem;">
        <div style="font-weight: 700; color: #38bdf8; margin-bottom: 6px;"><i class="fa-solid fa-car"></i> Registered Vehicle Profile</div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px;">
          <div><b>Plate Number:</b> <span class="plate-badge">${ch.plate_number}</span></div>
          <div><b>Vehicle:</b> ${ch.vehicle_make || 'N/A'} ${ch.vehicle_model || ''} (${ch.vehicle_color || ''})</div>
          <div><b>Owner Name:</b> ${ch.owner_name || 'N/A'}</div>
          <div><b>Owner CNIC:</b> ${ch.owner_cnic || 'N/A'}</div>
          <div><b>Phone:</b> ${ch.owner_phone || 'N/A'}</div>
          <div><b>Address:</b> ${ch.owner_address || 'N/A'}</div>
        </div>
      </div>

      <!-- Photographic Proof -->
      <div>
        <div style="font-size: 0.82rem; font-weight: 700; color: var(--text-muted); margin-bottom: 6px;">
          <i class="fa-solid fa-image"></i> CCTV SURVEILLANCE & CROPPED PLATE EVIDENCE
        </div>
        <div class="proof-grid">
          <div>
            <img src="${evidenceImg}" class="proof-img" style="height: 180px;" alt="CCTV Violation Snapshot" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'400\\' height=\\'200\\'><rect fill=\\'%231e293b\\' width=\\'400\\' height=\\'200\\'/><text fill=\\'%2394a3b8\\' x=\\'50%\\' y=\\'50%\\' dominant-baseline=\\'middle\\' text-anchor=\\'middle\\'>Snapshot Stored in System</text></svg>'">
          </div>
          <div>
            <img src="${plateImg}" class="proof-img" style="height: 180px;" alt="Plate ROI Crop" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'200\\' height=\\'200\\'><rect fill=\\'%230f172a\\' width=\\'200\\' height=\\'200\\'/><text fill=\\'%2338bdf8\\' x=\\'50%\\' y=\\'50%\\' dominant-baseline=\\'middle\\' text-anchor=\\'middle\\' font-weight=\\'bold\\'>${ch.plate_number}</text></svg>'">
          </div>
        </div>
      </div>
    `;

    document.getElementById('evidenceModal').style.display = 'flex';
  } catch (err) {
    alert('Error loading challan detail: ' + err.message);
  }
}

function closeModal(modalId) {
  document.getElementById(modalId).style.display = 'none';
}
