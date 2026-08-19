let selectedPresetPlate = 'LEA-21-4589';
let selectedPresetType = 'sedan';

function switchInputTab(tab) {
  const imgSec = document.getElementById('imageInputSection');
  const vidSec = document.getElementById('videoInputSection');
  const tabImgBtn = document.getElementById('tabImageBtn');
  const tabVidBtn = document.getElementById('tabVideoBtn');

  if (tab === 'image') {
    imgSec.style.display = 'block';
    vidSec.style.display = 'none';
    tabImgBtn.classList.add('active');
    tabVidBtn.classList.remove('active');
  } else {
    imgSec.style.display = 'none';
    vidSec.style.display = 'block';
    tabImgBtn.classList.remove('active');
    tabVidBtn.classList.add('active');
  }
}

function loadSamplePreset(plate, vType = 'sedan') {
  selectedPresetPlate = plate;
  selectedPresetType = vType;
  document.getElementById('imageFileInput').value = '';
  console.log(`Selected preset plate: ${plate} (${vType})`);
}

function createRealisticVehicleCanvasBlob(plateText, vType = 'sedan') {
  return new Promise((resolve) => {
    const canvas = document.createElement('canvas');
    canvas.width = 720;
    canvas.height = 460;
    const ctx = canvas.getContext('2d');

    // Asphalt road
    ctx.fillStyle = '#262c33';
    ctx.fillRect(0, 0, 720, 460);

    // Hazard Kerbs
    for (let ky = 0; ky < 460; ky += 30) {
      ctx.fillStyle = (Math.floor(ky / 30) % 2 === 0) ? '#eab308' : '#1e293b';
      ctx.fillRect(40, ky, 15, 30);
      ctx.fillRect(665, ky, 15, 30);
    }

    // Lane dashes
    ctx.strokeStyle = '#f8fafc';
    ctx.lineWidth = 3;
    ctx.setLineDash([25, 25]);
    ctx.beginPath();
    ctx.moveTo(250, 0); ctx.lineTo(250, 460);
    ctx.moveTo(470, 0); ctx.lineTo(470, 460);
    ctx.stroke();
    ctx.setLineDash([]);

    const cx = 360;
    const cy = 190;

    // Drop shadow
    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
    ctx.beginPath();
    ctx.ellipse(cx, cy + 140, 120, 40, 0, 0, Math.PI * 2);
    ctx.fill();

    if (vType === 'motorcycle') {
      ctx.fillStyle = '#1e293b';
      ctx.fillRect(cx - 15, cy - 20, 30, 140);
      ctx.fillStyle = '#0284c7';
      ctx.beginPath();
      ctx.ellipse(cx, cy + 30, 28, 18, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#334155';
      ctx.beginPath();
      ctx.arc(cx, cy - 10, 18, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#cbd5e1';
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(cx - 35, cy); ctx.lineTo(cx + 35, cy);
      ctx.stroke();
      ctx.fillStyle = '#ef4444';
      ctx.fillRect(cx - 12, cy + 90, 24, 12);
      drawCanvasPlate(ctx, cx - 45, cy + 106, 90, 26, plateText);
    } else if (vType === 'suv') {
      const w = 180, h = 260;
      const x = cx - w / 2, y = cy - 40;
      ctx.fillStyle = '#1e293b';
      ctx.strokeStyle = '#0f172a';
      ctx.lineWidth = 3;
      roundRect(ctx, x, y, w, h, 16, true, true);
      ctx.strokeStyle = '#94a3b8';
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(x + 20, y + 20); ctx.lineTo(x + 20, y + 170);
      ctx.moveTo(x + w - 20, y + 20); ctx.lineTo(x + w - 20, y + 170);
      ctx.stroke();
      ctx.fillStyle = '#0f172a';
      ctx.fillRect(x + 15, y + 160, w - 30, 14);
      ctx.fillStyle = '#ef4444';
      ctx.fillRect(cx - 20, y + 164, 40, 6);
      ctx.fillStyle = '#0f172a';
      roundRect(ctx, x + 18, y + 178, w - 36, 32, 6, true, false);
      ctx.fillStyle = '#ef4444';
      ctx.fillRect(x + 10, y + 214, 35, 16);
      ctx.fillRect(x + w - 45, y + 214, 35, 16);
      drawCanvasPlate(ctx, cx - 55, y + 222, 110, 28, plateText);
    } else {
      const w = 160, h = 250;
      const x = cx - w / 2, y = cy - 40;
      ctx.fillStyle = '#0f172a';
      ctx.strokeStyle = '#334155';
      ctx.lineWidth = 3;
      roundRect(ctx, x, y, w, h, 20, true, true);
      ctx.fillStyle = '#1e293b';
      roundRect(ctx, x + 20, y + 30, w - 40, 45, 6, true, false);
      roundRect(ctx, x + 18, y + 150, w - 36, 40, 6, true, false);
      ctx.fillStyle = '#dc2626';
      ctx.fillRect(x + 10, y + 195, 30, 16);
      ctx.fillRect(x + w - 40, y + 195, 30, 16);
      drawCanvasPlate(ctx, cx - 55, y + 205, 110, 28, plateText);
    }

    canvas.toBlob((blob) => {
      resolve(blob);
    }, 'image/jpeg', 0.95);
  });
}

function drawCanvasPlate(ctx, px, py, pw, ph, text) {
  ctx.fillStyle = '#ffffff';
  ctx.strokeStyle = '#059669';
  ctx.lineWidth = 2.5;
  ctx.fillRect(px, py, pw, ph);
  ctx.strokeRect(px, py, pw, ph);
  ctx.fillStyle = '#059669';
  ctx.fillRect(px, py, 14, ph);
  ctx.fillStyle = '#000000';
  ctx.font = 'bold 15px monospace';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(text, px + (pw / 2) + 6, py + (ph / 2));
}

function roundRect(ctx, x, y, width, height, radius, fill, stroke) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
  if (fill) ctx.fill();
  if (stroke) ctx.stroke();
}

// 1. Process Uploaded Image
async function runSimulationPipeline() {
  const btn = document.getElementById('btnRunPipeline');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing Neural Pipeline...';

  const fileInput = document.getElementById('imageFileInput');
  const violationType = document.getElementById('simViolationType').value;
  const speed = document.getElementById('simSpeedSlider').value;

  let imageBlob = null;
  if (fileInput.files && fileInput.files[0]) {
    imageBlob = fileInput.files[0];
  } else {
    imageBlob = await createRealisticVehicleCanvasBlob(selectedPresetPlate, selectedPresetType);
  }

  const formData = new FormData();
  formData.append('file', imageBlob, 'test_vehicle.jpg');
  formData.append('violation_type', violationType);
  formData.append('speed_simulated', speed);

  try {
    const res = await fetch('/api/simulate/process_image', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) throw new Error('Pipeline execution failed');
    const data = await res.json();

    const container = document.getElementById('pipelineContainer');
    container.style.display = 'block';

    document.getElementById('imgStage1').src = data.pipeline_stages.original_image;
    document.getElementById('imgStage2').src = data.pipeline_stages.edge_detection;
    document.getElementById('imgStage3').src = data.pipeline_stages.plate_crop;
    document.getElementById('imgStage4').src = data.pipeline_stages.binary_threshold;
    document.getElementById('imgStage5').src = data.pipeline_stages.ai_annotated_frame;

    document.getElementById('simResPlate').innerText = data.plate_number;
    document.getElementById('simResConf').innerText = `${Math.round(data.confidence * 100)}%`;

    if (data.violation_result) {
      document.getElementById('simResViolation').innerText = data.violation_result.violation_name;
      document.getElementById('simResFine').innerText = `PKR ${Number(data.violation_result.fine_amount).toLocaleString()}`;
      document.getElementById('resPdfBtn').href = `/api/challans/${data.violation_result.challan_no}/pdf`;
      document.getElementById('resPdfBtn').style.display = 'inline-flex';
    } else {
      document.getElementById('simResViolation').innerText = 'No Violation (Normal Flow)';
      document.getElementById('simResFine').innerText = 'PKR 0';
      document.getElementById('resPdfBtn').style.display = 'none';
    }

    container.scrollIntoView({ behavior: 'smooth' });

  } catch (err) {
    alert('Pipeline error: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-play"></i> Process Image (Detect & Generate Challan)';
  }
}

// 2. Process Uploaded Video
async function runVideoProcessing() {
  const fileInput = document.getElementById('videoFileInput');
  if (!fileInput.files || !fileInput.files[0]) {
    alert('Please choose a video file (.mp4, .avi, .mov) first.');
    return;
  }

  const btn = document.getElementById('btnRunVideo');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing Video Frames...';

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  formData.append('speed_limit', document.getElementById('videoSpeedLimit').value);
  formData.append('signal_state', document.getElementById('videoSignalState').value);

  try {
    const res = await fetch('/api/simulate/process_video', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) throw new Error('Video processing failed');
    const data = await res.json();

    const resultsBox = document.getElementById('videoResultsBox');
    resultsBox.style.display = 'block';

    document.getElementById('vidFrames').innerText = data.total_frames_processed;
    document.getElementById('vidPlatesCount').innerText = `${data.vehicles_identified} Plates (${data.plates_recognized.join(', ')})`;
    document.getElementById('vidViolationsCount').innerText = data.violations_generated_count;

    const listEl = document.getElementById('vidChallanList');
    if (data.challans && data.challans.length > 0) {
      listEl.innerHTML = data.challans.map(ch => `
        <div style="background: rgba(30,41,59,0.7); padding: 10px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center;">
          <div>
            <b>${ch.challan_no}</b> - Plate: <span class="plate-badge">${ch.plate_number}</span> (${ch.violation_name})
          </div>
          <div>
            <a href="/api/challans/${ch.challan_no}/pdf" target="_blank" class="btn btn-sm btn-primary">
              <i class="fa-solid fa-file-pdf"></i> Download PDF Ticket
            </a>
          </div>
        </div>
      `).join('');
    } else {
      listEl.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem;">No violations triggered in video.</div>';
    }

  } catch (err) {
    alert('Video processing error: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-play"></i> Process Full Video Stream';
  }
}
