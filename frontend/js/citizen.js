let activeChallanForPay = null;
let activeChallanForDispute = null;
let currentPayMethod = 'JazzCash';

document.addEventListener('DOMContentLoaded', () => {
  // Check if URL has ?challan= parameter
  const urlParams = new URLSearchParams(window.location.search);
  const challanParam = urlParams.get('challan');
  if (challanParam) {
    document.getElementById('citizenSearchInput').value = challanParam;
    executeSearch(challanParam);
  }
});

function handleSearch(e) {
  e.preventDefault();
  const q = document.getElementById('citizenSearchInput').value.trim();
  if (q) executeSearch(q);
}

function quickSearch(plate) {
  document.getElementById('citizenSearchInput').value = plate;
  executeSearch(plate);
}

async function executeSearch(query) {
  const resultsContainer = document.getElementById('resultsContainer');
  const noResults = document.getElementById('noResults');

  resultsContainer.style.display = 'none';
  noResults.style.display = 'none';

  try {
    const res = await fetch(`/api/citizen/search?query=${encodeURIComponent(query)}`);
    if (!res.ok) throw new Error('Failed to fetch records');
    const data = await res.json();

    if (!data.found || (!data.vehicle && data.challans.length === 0)) {
      noResults.style.display = 'block';
      return;
    }

    resultsContainer.style.display = 'block';

    // Populate Vehicle Details
    const v = data.vehicle;
    if (v) {
      document.getElementById('resPlate').innerText = v.plate_number;
      document.getElementById('resOwner').innerText = v.owner_name;
      document.getElementById('resVehicle').innerText = `${v.vehicle_make} ${v.vehicle_model} (${v.vehicle_color})`;
      document.getElementById('resTaxStatus').innerText = (v.tax_status || 'Paid').toUpperCase();
    } else {
      document.getElementById('resPlate').innerText = query.toUpperCase();
      document.getElementById('resOwner').innerText = 'Unregistered / Temporary Citizen';
      document.getElementById('resVehicle').innerText = 'Vehicle Information Pending';
    }

    document.getElementById('resPendingFine').innerText = `PKR ${data.summary.total_pending_amount.toLocaleString()}`;
    document.getElementById('resChallanCount').innerText = `Showing ${data.challans.length} citations (${data.summary.pending_count} Pending)`;

    // Populate Challans List
    renderCitizenChallans(data.challans);
  } catch (err) {
    alert('Search error: ' + err.message);
  }
}

function renderCitizenChallans(challans) {
  const container = document.getElementById('citizenChallansList');
  if (!container) return;

  if (challans.length === 0) {
    container.innerHTML = `
      <div class="card" style="text-align: center; padding: 2rem; color: var(--text-muted);">
        <i class="fa-solid fa-circle-check" style="color: #10b981; font-size: 24px; margin-bottom: 8px;"></i>
        <div>No citations found for this vehicle. Drive safely!</div>
      </div>
    `;
    return;
  }

  container.innerHTML = challans.map(ch => {
    const statusLower = (ch.status || '').toLowerCase();
    const isPending = statusLower !== 'paid';
    const evidenceImg = ch.evidence_image ? `/evidence/${ch.evidence_image}` : '';
    const statusLabel = ch.status || 'Unpaid';
    const statusClass = isPending ? 'pending' : 'paid';

    return `
      <div class="card" style="border-left: 4px solid ${isPending ? '#ef4444' : '#10b981'};">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px; margin-bottom: 12px;">
          <div>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
              <b style="font-family: monospace; color: #38bdf8; font-size: 1rem;">${ch.challan_no}</b>
              <span class="status-pill ${statusClass}">${statusLabel.toUpperCase()}</span>
            </div>
            <h4 style="font-size: 1.05rem; font-weight: 700; color: #f8fafc;">${ch.violation_name}</h4>
            <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 2px;">
              <i class="fa-solid fa-location-dot"></i> ${ch.location || 'N/A'} ${ch.camera_name ? '(' + ch.camera_name + ')' : ''} &bull; <i class="fa-solid fa-calendar"></i> ${ch.created_at}
            </div>
            ${ch.due_date ? `<div style="font-size: 0.78rem; color: #F59E0B; margin-top: 2px;"><i class="fa-solid fa-clock"></i> <b>Payment Due:</b> ${ch.due_date}</div>` : ''}
          </div>
          <div style="text-align: right;">
            <div style="font-size: 0.75rem; color: var(--text-muted);">FINE AMOUNT</div>
            <div style="font-size: 1.3rem; font-weight: 800; color: ${isPending ? '#ef4444' : '#34d399'};">
              PKR ${Number(ch.fine_amount).toLocaleString()}
            </div>
          </div>
        </div>

        <!-- Evidence snapshot row if present -->
        ${evidenceImg ? `
          <div style="background: rgba(15, 23, 42, 0.6); padding: 10px; border-radius: var(--radius-md); margin-bottom: 12px; display: flex; gap: 10px; align-items: center;">
            <img src="${evidenceImg}" style="width: 140px; height: 75px; object-fit: cover; border-radius: 4px; border: 1px solid var(--border-color);" alt="Evidence">
            <div style="font-size: 0.78rem; color: var(--text-muted);">
              <div><b>Surveillance Proof Snapshot</b></div>
              <div>Camera: ${ch.camera_name || 'Traffic Camera'}</div>
              <div>Speed Recorded: ${ch.speed_detected} km/h (Limit: ${ch.speed_limit} km/h)</div>
            </div>
          </div>
        ` : ''}

        <!-- Actions -->
        <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 10px; border-top: 1px solid var(--border-color);">
          <div>
            ${ch.paid_at ? `<span style="font-size: 0.75rem; color: #34d399;"><i class="fa-solid fa-circle-check"></i> Paid on ${ch.paid_at} via ${ch.payment_method || 'Online'}</span>` : ''}
          </div>
          <div style="display: flex; gap: 8px;">
            <a href="/api/challans/${ch.challan_no}/pdf" target="_blank" class="btn btn-sm btn-secondary">
              <i class="fa-solid fa-file-pdf"></i> PDF
            </a>
            ${isPending ? `
              <button class="btn btn-sm btn-secondary" onclick="openDisputeModal('${ch.challan_no}')">
                <i class="fa-solid fa-scale-balanced"></i> Dispute
              </button>
              <button class="btn btn-sm btn-success" onclick="openPaymentModal('${ch.challan_no}', '${ch.violation_name}', ${ch.fine_amount})">
                <i class="fa-solid fa-credit-card"></i> Pay Online
              </button>
            ` : ''}
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// Payment Modal Logic
function openPaymentModal(challanNo, violation, amount) {
  activeChallanForPay = challanNo;
  document.getElementById('payModalChallanNo').innerText = `Ticket #: ${challanNo}`;
  document.getElementById('payModalAmount').innerText = `PKR ${Number(amount).toLocaleString()}`;
  document.getElementById('payModalViolation').innerText = violation;
  document.getElementById('paymentModal').style.display = 'flex';
}

function selectPayMethod(method, btnEl) {
  currentPayMethod = method;
  document.querySelectorAll('.pay-method-btn').forEach(b => {
    b.classList.remove('active');
    b.style.borderColor = 'var(--border-color)';
  });
  btnEl.classList.add('active');
  btnEl.style.borderColor = '#38bdf8';

  const label = document.getElementById('payAccountLabel');
  const input = document.getElementById('payAccountNumber');

  if (method === 'JazzCash') {
    label.innerText = 'JazzCash Mobile Account Number (03XXXXXXXXX):';
    input.placeholder = '03001234567';
    input.value = '03004589123';
  } else if (method === 'EasyPaisa') {
    label.innerText = 'EasyPaisa Mobile Account Number (03XXXXXXXXX):';
    input.placeholder = '03451234567';
    input.value = '03455544332';
  } else {
    label.innerText = '1Link Debit/Credit Card Number:';
    input.placeholder = '4214 XXXX XXXX XXXX';
    input.value = '4214 8890 1234 5678';
  }
}

async function processPayment() {
  if (!activeChallanForPay) return;

  const btn = document.getElementById('btnConfirmPay');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing Secure Payment...';

  try {
    const res = await fetch('/api/citizen/pay', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        challan_no: activeChallanForPay,
        payment_method: currentPayMethod,
        account_number: document.getElementById('payAccountNumber').value || '03000000000',
        payer_name: 'Citizen'
      })
    });

    const data = await res.json();
    if (res.ok && data.status === 'success') {
      alert(`🎉 PAYMENT SUCCESSFUL!\n\nTransaction ID: ${data.receipt.transaction_ref}\nAmount: PKR ${data.receipt.amount_paid.toLocaleString()}\nMethod: ${data.receipt.payment_method}\n\nYour citation status has been updated to PAID.`);
      closeModal('paymentModal');
      // Refresh search
      const q = document.getElementById('citizenSearchInput').value.trim();
      if (q) executeSearch(q);
    } else {
      alert('Payment failed: ' + (data.detail || data.message || 'Unknown error'));
    }
  } catch (err) {
    alert('Payment error: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-lock"></i> Authorize & Pay Fine Now';
  }
}

// Dispute Modal Logic
function openDisputeModal(challanNo) {
  activeChallanForDispute = challanNo;
  document.getElementById('disputeModalChallanNo').innerText = `Ticket #: ${challanNo}`;
  document.getElementById('disputeReasonText').value = '';
  document.getElementById('disputeModal').style.display = 'flex';
}

async function submitDispute() {
  if (!activeChallanForDispute) return;
  const reason = document.getElementById('disputeReasonText').value.trim();
  if (!reason) {
    alert('Please enter your reason for dispute.');
    return;
  }

  try {
    const res = await fetch('/api/challans/dispute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        challan_no: activeChallanForDispute,
        reason: reason
      })
    });

    const data = await res.json();
    if (res.ok && data.status === 'success') {
      alert('Dispute submitted successfully! Our traffic verification team will inspect the CCTV photographic footage.');
      closeModal('disputeModal');
      const q = document.getElementById('citizenSearchInput').value.trim();
      if (q) executeSearch(q);
    } else {
      alert('Dispute submission failed: ' + (data.detail || data.message));
    }
  } catch (err) {
    alert('Error: ' + err.message);
  }
}

function closeModal(modalId) {
  document.getElementById(modalId).style.display = 'none';
}
