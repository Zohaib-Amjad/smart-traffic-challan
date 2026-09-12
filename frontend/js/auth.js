// Shared browser authentication helper and offline API mock for Vercel/client-side demo.
(function () {
  const STORAGE_KEYS = {
    CHALLANS: 'stcs_demo_challans',
    VEHICLES: 'stcs_demo_vehicles',
    USERS: 'stcs_demo_users',
    STATS: 'stcs_demo_stats',
  };

  const DEFAULT_VEHICLES = [
    {
      plate_number: 'LEA-2024-589',
      owner_name: 'Muhammad Ali',
      owner_cnic: '35201-1234567-1',
      owner_phone: '0300-1234567',
      vehicle_make: 'Toyota',
      vehicle_model: 'Corolla Altis',
      vehicle_color: 'Super White',
      vehicle_type: 'Car / Private',
      engine_cc: 1800,
      registration_date: '2024-01-15',
      source: 'registry'
    },
    {
      plate_number: 'ICT-2023-882',
      owner_name: 'Usman Tariq',
      owner_cnic: '35202-4567890-2',
      owner_phone: '0321-4567890',
      vehicle_make: 'Honda',
      vehicle_model: 'Civic Oriel',
      vehicle_color: 'Crystal Black',
      vehicle_type: 'Car / Private',
      engine_cc: 1500,
      registration_date: '2023-06-20',
      source: 'registry'
    },
    {
      plate_number: 'KHI-2022-314',
      owner_name: 'Bilal Ahmed',
      owner_cnic: '42101-1122334-5',
      owner_phone: '0333-1122334',
      vehicle_make: 'Honda',
      vehicle_model: 'CD-70 Dream',
      vehicle_color: 'Flamboyant Red',
      vehicle_type: 'Motorcycle',
      engine_cc: 70,
      registration_date: '2022-03-10',
      source: 'registry'
    },
    {
      plate_number: 'LHR-2021-990',
      owner_name: 'Hamza Shah',
      owner_cnic: '35201-8899001-9',
      owner_phone: '0345-8899001',
      vehicle_make: 'Suzuki',
      vehicle_model: 'Cultus VXL',
      vehicle_color: 'Silky Silver',
      vehicle_type: 'Car / Private',
      engine_cc: 1000,
      registration_date: '2021-11-05',
      source: 'registry'
    },
    {
      plate_number: 'FSD-2023-112',
      owner_name: 'Faisal Mahmood',
      owner_cnic: '33100-3344556-7',
      owner_phone: '0302-3344556',
      vehicle_make: 'Toyota',
      vehicle_model: 'Hilux Revo',
      vehicle_color: 'Graphite Grey',
      vehicle_type: 'Commercial / LTV',
      engine_cc: 2800,
      registration_date: '2023-09-12',
      source: 'registry'
    }
  ];

  const DEFAULT_CHALLANS = [
    {
      id: 1,
      challan_no: 'CH-20260901-7A8B',
      plate_number: 'LEA-2024-589',
      violation_code: 'OS-01',
      violation_name: 'OS-01 Exceeding Prescribed Speed Limit',
      fine_amount: 2000,
      status: 'Unpaid',
      location: 'Mall Road (Near Canal Bridge), Lahore',
      camera_id: 'CAM-01 (Mall Road)',
      created_at: '2026-09-01 10:15:30',
      due_date: '2026-09-15',
      owner_name: 'Muhammad Ali',
      owner_cnic: '35201-1234567-1',
      owner_phone: '0300-1234567',
      vehicle_type: 'Car / Private',
      officer_name: 'Sub-Inspector Farhan',
      evidence_image: null,
      plate_crop: null,
      speed_detected: '84 km/h (Limit: 60 km/h)'
    },
    {
      id: 2,
      challan_no: 'CH-20260902-9C1D',
      plate_number: 'ICT-2023-882',
      violation_code: 'SV-01',
      violation_name: 'SV-01 Disobeying Traffic Signal / Red Light',
      fine_amount: 3000,
      status: 'Paid',
      location: 'F-7 Markaz Signal, Islamabad',
      camera_id: 'CAM-02 (Blue Area)',
      created_at: '2026-09-02 14:30:12',
      due_date: '2026-09-16',
      owner_name: 'Usman Tariq',
      owner_cnic: '35202-4567890-2',
      owner_phone: '0321-4567890',
      vehicle_type: 'Car / Private',
      officer_name: 'Sub-Inspector Farhan',
      evidence_image: null,
      plate_crop: null
    },
    {
      id: 3,
      challan_no: 'CH-20260904-4E5F',
      plate_number: 'KHI-2022-314',
      violation_code: 'NH-01',
      violation_name: 'NH-01 Driving Motorcycle Without Safety Helmet',
      fine_amount: 1000,
      status: 'Unpaid',
      location: 'Sharah-e-Faisal, Karachi',
      camera_id: 'CAM-03 (Clifton)',
      created_at: '2026-09-04 18:20:45',
      due_date: '2026-09-18',
      owner_name: 'Bilal Ahmed',
      owner_cnic: '42101-1122334-5',
      owner_phone: '0333-1122334',
      vehicle_type: 'Motorcycle',
      officer_name: 'Sub-Inspector Farhan',
      evidence_image: null,
      plate_crop: null
    },
    {
      id: 4,
      challan_no: 'CH-20260905-2A3B',
      plate_number: 'LHR-2021-990',
      violation_code: 'WW-01',
      violation_name: 'WW-01 Driving on Wrong Side of the Road',
      fine_amount: 2500,
      status: 'Paid',
      location: 'Main Boulevard Gulberg, Lahore',
      camera_id: 'CAM-04 (Liberty)',
      created_at: '2026-09-05 09:45:00',
      due_date: '2026-09-19',
      owner_name: 'Hamza Shah',
      owner_cnic: '35201-8899001-9',
      owner_phone: '0345-8899001',
      vehicle_type: 'Car / Private',
      officer_name: 'Sub-Inspector Farhan',
      evidence_image: null,
      plate_crop: null
    },
    {
      id: 5,
      challan_no: 'CH-20260906-8C9D',
      plate_number: 'FSD-2023-112',
      violation_code: 'CP-01',
      violation_name: 'CP-01 Using Mobile Phone While Driving',
      fine_amount: 1500,
      status: 'Unpaid',
      location: 'Jaranwala Road, Faisalabad',
      camera_id: 'CAM-05 (Clock Tower)',
      created_at: '2026-09-06 16:10:20',
      due_date: '2026-09-20',
      owner_name: 'Faisal Mahmood',
      owner_cnic: '33100-3344556-7',
      owner_phone: '0302-3344556',
      vehicle_type: 'Commercial / LTV',
      officer_name: 'Sub-Inspector Farhan',
      evidence_image: null,
      plate_crop: null
    }
  ];

  const PUNJAB_VIOLATIONS = [
    { code: 'OS-01', title: 'Exceeding Prescribed Speed Limit', amount: 2000, applicable: true },
    { code: 'SV-01', title: 'Disobeying Traffic Signal / Red Light', amount: 3000, applicable: true },
    { code: 'NH-01', title: 'Driving Motorcycle Without Safety Helmet', amount: 1000, applicable: true },
    { code: 'WW-01', title: 'Driving on Wrong Side of the Road', amount: 2500, applicable: true },
    { code: 'CP-01', title: 'Using Mobile Phone While Driving', amount: 1500, applicable: true },
    { code: 'SB-01', title: 'Driving Without Seatbelt Fastened', amount: 1500, applicable: true },
    { code: 'LP-01', title: 'Unregistered / Defective Number Plate', amount: 2000, applicable: true },
    { code: 'TL-01', title: 'Disobeying Stop / Yield Traffic Sign', amount: 1000, applicable: true },
    { code: 'OL-01', title: 'Overloading Passenger / Cargo Vehicle', amount: 5000, applicable: true },
    { code: 'DL-01', title: 'Driving Without Valid Driving License', amount: 2000, applicable: true }
  ];

  function getStoredList(key, defaultData) {
    try {
      const stored = localStorage.getItem(key);
      if (!stored) {
        localStorage.setItem(key, JSON.stringify(defaultData));
        return defaultData;
      }
      return JSON.parse(stored);
    } catch {
      return defaultData;
    }
  }

  function setStoredList(key, data) {
    try {
      localStorage.setItem(key, JSON.stringify(data));
    } catch (e) {
      console.warn('Storage write failed', e);
    }
  }

  // Pre-initialize storage
  getStoredList(STORAGE_KEYS.CHALLANS, DEFAULT_CHALLANS);
  getStoredList(STORAGE_KEYS.VEHICLES, DEFAULT_VEHICLES);

  async function handleMockRequest(url, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const cleanUrl = url.replace(/^https?:\/\/[^\/]+/, '');
    const path = cleanUrl.split('?')[0];

    // 1. Auth: Login
    if (path === '/api/auth/login' && method === 'POST') {
      let body = {};
      try { body = typeof options.body === 'string' ? JSON.parse(options.body) : options.body || {}; } catch {}
      const role = body.role || 'Officer';
      const email = body.email || (role === 'Officer' ? 'officer@traffic.gov.pk' : (role === 'Admin' ? 'admin@traffic.gov.pk' : 'citizen@test.pk'));
      
      let user = {
        id: role === 'Admin' ? 301 : (role === 'Citizen' ? 101 : 201),
        full_name: role === 'Admin' ? 'Excise Registrar Tahir' : (role === 'Citizen' ? 'Muhammad Ali' : 'Sub-Inspector Farhan'),
        email: email,
        role: role,
        cnic: role === 'Admin' ? '35201-9876543-5' : (role === 'Citizen' ? '35201-1234567-1' : '35201-7654321-3'),
        phone: '0300-1234567',
        badge_number: role === 'Officer' ? 'TP-4821' : null
      };

      return jsonResponse({ success: true, user });
    }

    // 2. Auth: Register
    if (path === '/api/auth/register' && method === 'POST') {
      return jsonResponse({ success: true, message: 'User registered successfully. Please sign in.' });
    }

    // 3. Auth: Logout
    if (path === '/api/auth/logout') {
      return jsonResponse({ success: true, message: 'Logged out.' });
    }

    // 4. Analytics: Dashboard
    if (path === '/api/analytics/dashboard') {
      const challans = getStoredList(STORAGE_KEYS.CHALLANS, DEFAULT_CHALLANS);
      const totalCount = challans.length;
      const totalRevenue = challans.reduce((sum, c) => sum + (c.status === 'Paid' ? Number(c.fine_amount || 0) : 0), 0);
      const pendingRevenue = challans.reduce((sum, c) => sum + (c.status === 'Unpaid' ? Number(c.fine_amount || 0) : 0), 0);

      const countsByType = {};
      challans.forEach(c => {
        const vName = c.violation_name || 'Traffic Violation';
        countsByType[vName] = (countsByType[vName] || 0) + 1;
      });
      const violations_by_type = Object.entries(countsByType).map(([k, v]) => ({ violation_name: k, count: v }));

      return jsonResponse({
        stats: {
          total_challans: totalCount,
          total_revenue: totalRevenue,
          pending_revenue: pendingRevenue,
          paid_count: challans.filter(c => c.status === 'Paid').length,
          unpaid_count: challans.filter(c => c.status === 'Unpaid').length
        },
        recent_challans: challans.slice(0, 8),
        violations_by_type: violations_by_type.length > 0 ? violations_by_type : [
          { violation_name: 'Speed Limit', count: 3 },
          { violation_name: 'Red Light Signal', count: 2 },
          { violation_name: 'No Helmet', count: 1 }
        ]
      });
    }

    // 5. Challans: List
    if (path === '/api/challans' && method === 'GET') {
      const challans = getStoredList(STORAGE_KEYS.CHALLANS, DEFAULT_CHALLANS);
      return jsonResponse(challans);
    }

    // 6. Challans: Single Detail /api/challans/{id}
    const challanMatch = path.match(/^\/api\/challans\/([^\/]+)$/);
    if (challanMatch && method === 'GET') {
      const queryId = decodeURIComponent(challanMatch[1]);
      const challans = getStoredList(STORAGE_KEYS.CHALLANS, DEFAULT_CHALLANS);
      const found = challans.find(c => String(c.challan_no).toLowerCase() === queryId.toLowerCase() || String(c.id) === queryId);
      if (found) {
        return jsonResponse(found);
      }
      return jsonResponse({
        id: 99,
        challan_no: queryId,
        plate_number: 'LEA-2024-589',
        violation_code: 'OS-01',
        violation_name: 'OS-01 Exceeding Prescribed Speed Limit',
        fine_amount: 2000,
        status: 'Unpaid',
        location: 'Mall Road, Lahore',
        camera_id: 'CAM-01',
        created_at: new Date().toISOString().replace('T', ' ').substring(0, 19),
        due_date: '2026-09-30',
        owner_name: 'Muhammad Ali',
        owner_cnic: '35201-1234567-1',
        owner_phone: '0300-1234567',
        vehicle_type: 'Car / Private',
        officer_name: 'Sub-Inspector Farhan'
      });
    }

    // 7. Challans: Generate
    if (path === '/api/challans/generate' && method === 'POST') {
      let body = {};
      try { body = typeof options.body === 'string' ? JSON.parse(options.body) : options.body || {}; } catch {}
      const challans = getStoredList(STORAGE_KEYS.CHALLANS, DEFAULT_CHALLANS);
      
      const randomHex = Math.random().toString(16).substring(2, 6).toUpperCase();
      const todayStr = new Date().toISOString().split('T')[0].replace(/-/g, '');
      const newNo = `CH-${todayStr}-${randomHex}`;
      
      const newChallan = {
        id: Date.now(),
        challan_no: newNo,
        plate_number: (body.plate_number || 'LEA-2024-001').toUpperCase(),
        violation_code: body.violation_code || 'SV-01',
        violation_name: body.violation_name || 'Disobeying Traffic Signal',
        fine_amount: Number(body.fine_amount || 2000),
        status: 'Unpaid',
        location: body.location || 'Ferozepur Road, Lahore',
        camera_id: body.camera_id || 'CAM-01',
        created_at: new Date().toISOString().replace('T', ' ').substring(0, 19),
        due_date: new Date(Date.now() + 14 * 86400000).toISOString().split('T')[0],
        owner_name: body.owner_name || 'Verified Citizen',
        owner_cnic: body.owner_cnic || '35201-1234567-1',
        owner_phone: body.owner_phone || '0300-1234567',
        vehicle_type: body.vehicle_type || 'Car / Private',
        officer_name: body.officer_name || 'Sub-Inspector Farhan'
      };

      challans.unshift(newChallan);
      setStoredList(STORAGE_KEYS.CHALLANS, challans);
      return jsonResponse({ success: true, challan: newChallan, challan_no: newNo });
    }

    // 8. Challans: Update status
    const statusMatch = path.match(/^\/api\/challans\/([^\/]+)\/status$/);
    if (statusMatch && method === 'POST') {
      const targetNo = decodeURIComponent(statusMatch[1]);
      let body = {};
      try { body = typeof options.body === 'string' ? JSON.parse(options.body) : options.body || {}; } catch {}
      const challans = getStoredList(STORAGE_KEYS.CHALLANS, DEFAULT_CHALLANS);
      const item = challans.find(c => String(c.challan_no).toLowerCase() === targetNo.toLowerCase() || String(c.id) === targetNo);
      if (item) {
        item.status = body.status || 'Paid';
        setStoredList(STORAGE_KEYS.CHALLANS, challans);
      }
      return jsonResponse({ success: true, status: body.status || 'Paid' });
    }

    // 9. Challans: Delete
    if (challanMatch && method === 'DELETE') {
      const targetId = decodeURIComponent(challanMatch[1]);
      let challans = getStoredList(STORAGE_KEYS.CHALLANS, DEFAULT_CHALLANS);
      challans = challans.filter(c => String(c.id) !== targetId && String(c.challan_no) !== targetId);
      setStoredList(STORAGE_KEYS.CHALLANS, challans);
      return jsonResponse({ success: true, message: 'Challan deleted.' });
    }

    // 10. Challans: Punjab Schedule
    if (path === '/api/challans/schedule') {
      return jsonResponse({
        law_reference: 'Twelfth Schedule, Provincial Motor Vehicles Ordinance, 1965 (Punjab)',
        fine_bracket_label: 'Standard Motorized Vehicles',
        violations: PUNJAB_VIOLATIONS
      });
    }

    // 11. Vehicles: List
    if (path === '/api/vehicles' && method === 'GET') {
      const vehicles = getStoredList(STORAGE_KEYS.VEHICLES, DEFAULT_VEHICLES);
      return jsonResponse(vehicles);
    }

    // 12. Vehicles: Add
    if (path === '/api/vehicles/add' && method === 'POST') {
      let body = {};
      try { body = typeof options.body === 'string' ? JSON.parse(options.body) : options.body || {}; } catch {}
      const vehicles = getStoredList(STORAGE_KEYS.VEHICLES, DEFAULT_VEHICLES);
      const newV = {
        plate_number: (body.plate_number || 'LHR-2024-999').toUpperCase(),
        owner_name: body.owner_name || 'Registered Citizen',
        owner_cnic: body.owner_cnic || '35201-1234567-1',
        owner_phone: body.owner_phone || '0300-1234567',
        vehicle_make: body.vehicle_make || 'Honda',
        vehicle_model: body.vehicle_model || 'City',
        vehicle_color: body.vehicle_color || 'White',
        vehicle_type: body.vehicle_type || 'Car / Private',
        engine_cc: Number(body.engine_cc || 1300),
        registration_date: new Date().toISOString().split('T')[0],
        source: 'manual'
      };
      vehicles.unshift(newV);
      setStoredList(STORAGE_KEYS.VEHICLES, vehicles);
      return jsonResponse({ success: true, message: 'Vehicle registered successfully.', vehicle: newV });
    }

    // 13. Vehicles: Lookup by plate /api/vehicles/{plate}
    const vehiclePlateMatch = path.match(/^\/api\/vehicles\/([^\/]+)$/);
    if (vehiclePlateMatch && method === 'GET') {
      const plate = decodeURIComponent(vehiclePlateMatch[1]).toUpperCase();
      const vehicles = getStoredList(STORAGE_KEYS.VEHICLES, DEFAULT_VEHICLES);
      const found = vehicles.find(v => v.plate_number.replace(/[-\s]/g, '') === plate.replace(/[-\s]/g, ''));
      if (found) {
        return jsonResponse(found);
      }
      return jsonResponse({
        plate_number: plate,
        owner_name: 'Muhammad Asif',
        owner_cnic: '35201-9988776-3',
        owner_phone: '0300-9988776',
        vehicle_make: 'Toyota',
        vehicle_model: 'Corolla GLi',
        vehicle_color: 'Silver Metallic',
        vehicle_type: 'Car / Private',
        engine_cc: 1300,
        registration_date: '2023-04-10',
        source: 'synthetic'
      });
    }

    // 14. Citizen Challans Lookup
    if (path.startsWith('/api/challans/plate/') || path === '/api/citizen/challans') {
      const challans = getStoredList(STORAGE_KEYS.CHALLANS, DEFAULT_CHALLANS);
      const plate = path.startsWith('/api/challans/plate/')
        ? decodeURIComponent(path.replace('/api/challans/plate/', '')).toUpperCase()
        : null;
      if (plate) {
        const filtered = challans.filter(c => c.plate_number.replace(/[-\s]/g, '') === plate.replace(/[-\s]/g, ''));
        return jsonResponse(filtered.length > 0 ? filtered : [challans[0]]);
      }
      return jsonResponse(challans);
    }

    // 15. Citizen Pay
    if (path === '/api/citizen/pay' && method === 'POST') {
      let body = {};
      try { body = typeof options.body === 'string' ? JSON.parse(options.body) : options.body || {}; } catch {}
      const challans = getStoredList(STORAGE_KEYS.CHALLANS, DEFAULT_CHALLANS);
      const target = challans.find(c => c.challan_no === body.challan_no);
      if (target) {
        target.status = 'Paid';
        setStoredList(STORAGE_KEYS.CHALLANS, challans);
      }
      return jsonResponse({ success: true, message: 'Challan payment marked as paid successfully.' });
    }

    // 16. Reports Summary
    if (path === '/api/reports/summary') {
      const challans = getStoredList(STORAGE_KEYS.CHALLANS, DEFAULT_CHALLANS);
      return jsonResponse({
        total_challans: challans.length,
        total_paid: challans.filter(c => c.status === 'Paid').length,
        total_unpaid: challans.filter(c => c.status === 'Unpaid').length,
        total_fine_collected: challans.reduce((sum, c) => sum + (c.status === 'Paid' ? Number(c.fine_amount || 0) : 0), 0),
        pending_amount: challans.reduce((sum, c) => sum + (c.status === 'Unpaid' ? Number(c.fine_amount || 0) : 0), 0),
        top_violations: [
          { name: 'Speed Limit', count: 18, amount: 36000 },
          { name: 'Red Light Signal', count: 14, amount: 42000 },
          { name: 'No Helmet', count: 9, amount: 9000 },
          { name: 'Wrong Way', count: 6, amount: 15000 }
        ],
        violations_by_camera: [
          { camera_id: 'CAM-01 (Mall Road)', count: 16 },
          { camera_id: 'CAM-02 (Blue Area)', count: 12 },
          { camera_id: 'CAM-03 (Clifton)', count: 10 },
          { camera_id: 'CAM-04 (Liberty)', count: 9 }
        ]
      });
    }

    // 17. ANPR Simulation / OCR
    if (path === '/api/simulate/process_image' && method === 'POST') {
      const samplePlates = ['LEA-2024-589', 'ICT-2023-882', 'LHR-2021-990', 'KHI-2022-314'];
      const chosen = samplePlates[Math.floor(Math.random() * samplePlates.length)];
      return jsonResponse({
        success: true,
        plate_number: chosen,
        confidence: 0.968,
        match_type: 'archive_registry_verified',
        pipeline_stages: {
          original_image: null,
          ai_annotated_frame: null
        }
      });
    }

    // 18. Live alert stream
    if (path === '/api/stream/live_alert') {
      return jsonResponse({ alert: null });
    }

    // 19. Camera / Signal Controls
    if (path.startsWith('/api/stream/')) {
      return jsonResponse({ success: true, message: 'Stream control updated.' });
    }

    return jsonResponse({ success: true, message: 'OK' });
  }

  function jsonResponse(data, status = 200) {
    return new Response(JSON.stringify(data), {
      status: status,
      statusText: status === 200 ? 'OK' : 'Error',
      headers: {
        'Content-Type': 'application/json',
        'X-Powered-By': 'STCS-Client-Engine'
      }
    });
  }

  // Hook into window.fetch
  if (typeof window !== 'undefined' && !window.__STCS_MOCK_HOOKED__) {
    window.__STCS_MOCK_HOOKED__ = true;
    const originalFetch = window.fetch;
    window.fetch = async function (input, init) {
      const url = typeof input === 'string' ? input : (input && input.url ? input.url : '');
      
      if (url.startsWith('/api/') || url.includes('/api/')) {
        try {
          const liveRes = await originalFetch.apply(this, arguments);
          const contentType = liveRes.headers.get('content-type') || '';
          if (liveRes.ok && contentType.includes('application/json')) {
            return liveRes;
          }
          return await handleMockRequest(url, init);
        } catch (netErr) {
          return await handleMockRequest(url, init);
        }
      }

      return originalFetch.apply(this, arguments);
    };
  }
})();

window.addEventListener('DOMContentLoaded', async () => {
  await ensureSessionMatchesServer();
  enforceCitizenScope();
});

// Shared browser authentication helper used by every protected page.
const AUTH_STORAGE_KEY = 'currentUser';

async function ensureSessionMatchesServer() {
  const storedUser = getCurrentUser();
  if (!storedUser) {
    return null;
  }

  try {
    const res = await fetch('/api/auth/me', { credentials: 'same-origin' });
    if (!res.ok) {
      localStorage.removeItem(AUTH_STORAGE_KEY);
      return null;
    }

    const data = await res.json();
    const serverUser = data?.user || null;
    if (!serverUser) {
      localStorage.removeItem(AUTH_STORAGE_KEY);
      return null;
    }

    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(serverUser));
    return serverUser;
  } catch (error) {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    return null;
  }
}

function getCurrentUser() {
  // Corrupted browser storage is treated as a logged-out state.
  try {
    const storedUser = JSON.parse(localStorage.getItem(AUTH_STORAGE_KEY) || 'null');
    if (!storedUser || !storedUser.role) {
      localStorage.removeItem(AUTH_STORAGE_KEY);
      return null;
    }
    return storedUser;
  } catch (error) {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    return null;
  }
}

function requireAuth() {
  // Preserve the requested URL so login can return to the original workflow.
  if (getCurrentUser()) {
    return true;
  }

  const next = `${window.location.pathname}${window.location.search}`;
  window.location.replace(`/login.html?next=${encodeURIComponent(next)}`);
  return false;
}

function requireRole(...allowedRoles) {
  const user = getCurrentUser();
  if (user && allowedRoles.includes(user.role)) {
    if (user.role === 'Citizen') {
      const citizenOnlyPaths = ['/number_plate.html', '/number-plate', '/number_plate', '/citizen', '/citizen.html', '/login.html', '/login'];
      const currentPath = window.location.pathname;
      if (!citizenOnlyPaths.includes(currentPath) && !currentPath.startsWith('/challan/') && !currentPath.startsWith('/challans')) {
        const next = new URLSearchParams(window.location.search).get('next');
        const target = next && next.startsWith('/') && !next.startsWith('//') ? next : '/number_plate.html';
        window.location.replace(target);
        return false;
      }
    }
    return true;
  }

  const next = `${window.location.pathname}${window.location.search}`;
  window.location.replace(user ? '/index.html' : `/login.html?next=${encodeURIComponent(next)}`);
  return false;
}

function enforceCitizenScope() {
  const user = getCurrentUser();
  if (!user || user.role !== 'Citizen') {
    return true;
  }

  const currentPath = window.location.pathname;

  if (currentPath === '/login' || currentPath === '/login.html') {
    window.location.replace('/number_plate.html');
    return false;
  }
  const allowedCitizenPaths = [
    '/',
    '/index.html',
    '/login',
    '/login.html',
    '/number_plate.html',
    '/number-plate',
    '/number_plate',
    '/citizen.html',
    '/citizen'
  ];

  const next = new URLSearchParams(window.location.search).get('next');
  const safeNext = next && next.startsWith('/') && !next.startsWith('//') ? next : '/number_plate.html';
  const isLoginFlow = (currentPath === '/login' || currentPath === '/login.html') && new URLSearchParams(window.location.search).has('next');

  const isCitizenAllowed = allowedCitizenPaths.includes(currentPath)
    || currentPath.startsWith('/challan/')
    || currentPath.startsWith('/challans')
    || currentPath.startsWith('/api/');

  if (!isCitizenAllowed) {
    window.location.replace(safeNext);
    return false;
  }

  if (isLoginFlow) {
    return true;
  }

  if ((currentPath === '/login' || currentPath === '/login.html') && safeNext) {
    window.location.replace(safeNext);
    return false;
  }

  return true;
}

function logout() {
  // Clear identity and temporary detection previews before returning to login.
  fetch('/api/auth/logout', {method: 'POST', keepalive: true}).catch(() => {});
  localStorage.removeItem(AUTH_STORAGE_KEY);
  sessionStorage.removeItem('lastDetectedPlate');
  sessionStorage.removeItem('lastPreviewImg');
  window.location.replace('/login.html');
}

function applyPublicNavAuth() {
  // Guest links stay on public pages; logout appears only after login.
  const loggedIn = !!getCurrentUser();
  document.querySelectorAll('[data-auth]').forEach((el) => {
    el.hidden = !loggedIn;
  });
  document.querySelectorAll('[data-guest]').forEach((el) => {
    el.hidden = loggedIn;
  });
}

function openAdministrativeControl(event) {
  // Administrative Control is only available after a successful login.
  if (event) {
    event.preventDefault();
  }

  if (!getCurrentUser()) {
    window.location.replace(`/login.html?next=${encodeURIComponent('/dashboard.html')}`);
    return false;
  }

  window.location.assign('/dashboard.html');
  return false;
}

function redirectAfterAuth(defaultPath = null) {
  // Accept only local paths from the next parameter.
  const next = new URLSearchParams(window.location.search).get('next');
  const user = getCurrentUser();
  const roleDefault = user && user.role === 'Citizen'
    ? '/number_plate.html'
    : (user && user.role === 'Admin' ? '/vehicles.html' : '/dashboard.html');

  const safeNext = next && next.startsWith('/') && !next.startsWith('//') ? next : null;
  let destination = safeNext || (defaultPath || roleDefault);

  if (user && user.role === 'Citizen') {
    const citizenOnlyPaths = ['/number_plate.html', '/number-plate', '/number_plate', '/challan/', '/challans'];
    const allowedCitizenDestination = citizenOnlyPaths.some((path) => destination === path || destination.startsWith(path));
    destination = allowedCitizenDestination ? destination : '/number_plate.html';
  } else if (user && user.role === 'Admin') {
    destination = '/vehicles.html';
  } else if (user && user.role === 'Officer') {
    destination = '/dashboard.html';
  }

  window.location.replace(destination);
}

function getActiveNavKey() {
  const nav = document.getElementById('appNav');
  if (nav && nav.dataset.active) {
    return nav.dataset.active;
  }

  const path = window.location.pathname;
  if (path === '/' || path.endsWith('/index.html')) return 'home';
  if (path.includes('dashboard')) return 'dashboard';
  if (path.includes('vehicles')) return 'vehicles';
  if (path.includes('number-plate') || path.includes('number_plate') || path.includes('citizen')) return 'number-plate';
  if (path.includes('reports')) return 'reports';
  if (path.includes('challans') || path.includes('challan') || path.includes('generate_challan')) {
    return 'challans';
  }
  return '';
}

function adminControlGroupHtml(user) {
  const isOfficer = user.role === 'Officer';
  const isAdmin = user.role === 'Admin';
  const vehicleLink = isAdmin
    ? '<a href="/vehicles.html" class="nav-item" data-nav="vehicles"><i class="fa-solid fa-car"></i> Vehicle Registration</a>'
    : (isOfficer
      ? '<a href="/vehicles.html" class="nav-item" data-nav="vehicles"><i class="fa-solid fa-car"></i> Registered Vehicles</a>'
      : '');
  const challanGroup = isOfficer ? `
          <div class="nav-dropdown">
            <button type="button" class="nav-item" data-nav="challans" aria-haspopup="true" aria-expanded="false">
              <i class="fa-solid fa-file-lines"></i> Challan Management
              <i class="fa-solid fa-chevron-down" style="font-size: 0.65rem;"></i>
            </button>
            <div class="nav-dropdown-menu">
              <a href="/generate_challan.html" class="nav-item" data-nav="generate-challan">Generate Challan</a>
              <a href="/challans.html" class="nav-item" data-nav="challan-history">Challan History</a>
            </div>
          </div>` : '';

  return `
    <div class="nav-cluster">
      <div class="nav-group">
        ${isOfficer ? '<a href="/dashboard.html" class="nav-item nav-parent" data-nav="dashboard"><img class="nav-parent-icon" src="/static/admin-control.svg?v=15" alt=""> Administrative Control</a>' : ''}
        <div class="nav-children" role="group" aria-label="Administrative Control modules">
          ${vehicleLink}
          ${isOfficer ? '<a href="/number_plate.html" class="nav-item" data-nav="number-plate"><i class="fa-solid fa-camera"></i> Number Plate Recognition</a>' : ''}
          ${challanGroup}
          ${isOfficer ? '<a href="/reports.html" class="nav-item" data-nav="reports"><i class="fa-solid fa-chart-column"></i> Reports</a>' : ''}
        </div>
      </div>
    </div>
    <a href="#" class="nav-item nav-logout" onclick="logout(); return false;"><i class="fa-solid fa-arrow-right-from-bracket"></i> Logout</a>
  `;
}

function closeNavDropdowns(except) {
  document.querySelectorAll('.nav-dropdown.open').forEach((dropdown) => {
    if (dropdown === except) {
      return;
    }
    dropdown.classList.remove('open');
    const trigger = dropdown.querySelector(':scope > .nav-item');
    if (trigger) {
      trigger.setAttribute('aria-expanded', 'false');
    }
  });
}

function placeNavDropdown(dropdown) {
  const trigger = dropdown.querySelector(':scope > .nav-item');
  const menu = dropdown.querySelector('.nav-dropdown-menu');
  if (!trigger || !menu) {
    return;
  }

  const rect = trigger.getBoundingClientRect();
  menu.style.top = `${Math.round(rect.bottom)}px`;
  menu.style.left = `${Math.round(rect.left)}px`;
}

function bindNavDropdowns() {
  document.querySelectorAll('.nav-dropdown').forEach((dropdown) => {
    const trigger = dropdown.querySelector(':scope > .nav-item');
    const menu = dropdown.querySelector('.nav-dropdown-menu');
    if (!trigger || !menu || trigger.dataset.dropdownBound === '1') {
      return;
    }

    trigger.dataset.dropdownBound = '1';
    trigger.setAttribute('aria-haspopup', 'true');
    trigger.setAttribute('aria-expanded', 'false');

    const open = () => {
      closeNavDropdowns(dropdown);
      dropdown.classList.add('open');
      trigger.setAttribute('aria-expanded', 'true');
      placeNavDropdown(dropdown);
    };

    const close = () => {
      window.setTimeout(() => {
        dropdown.classList.remove('open');
        trigger.setAttribute('aria-expanded', 'false');
      }, 120);
    };

    trigger.addEventListener('mouseenter', open);
    trigger.addEventListener('mouseleave', close);
    menu.addEventListener('mouseenter', open);
    menu.addEventListener('mouseleave', close);

    trigger.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      const isOpen = dropdown.classList.contains('open');
      if (isOpen) {
        dropdown.classList.remove('open');
        trigger.setAttribute('aria-expanded', 'false');
      } else {
        open();
      }
    });
  });

  if (!window.__navDropdownGlobalBound) {
    window.__navDropdownGlobalBound = true;
    document.addEventListener('click', (event) => {
      if (!event.target.closest('.nav-dropdown')) {
        closeNavDropdowns(null);
      }
    });
    window.addEventListener('resize', () => {
      const openDropdown = document.querySelector('.nav-dropdown.open');
      if (openDropdown) {
        placeNavDropdown(openDropdown);
      }
    });
  }
}

function applyActiveNav() {
  const activeKey = getActiveNavKey();
  if (!activeKey) return;

  const currentPath = window.location.pathname;
  const nav = document.getElementById('appNav');
  if (!nav) return;

  const activeParent = nav.querySelector(`.nav-parent[data-nav="${activeKey}"]`);
  if (activeParent) {
    activeParent.classList.add('active');
  }

  const activeLink = nav.querySelector(`.nav-children .nav-item[data-nav="${activeKey}"]`);
  if (activeLink) {
    activeLink.classList.add('active');
  }

  const generateLink = nav.querySelector('.nav-dropdown-menu a[data-nav="generate-challan"]');
  const historyLink = nav.querySelector('.nav-dropdown-menu a[data-nav="challan-history"]');
  if (generateLink && historyLink) {
    generateLink.classList.toggle('active', currentPath.includes('generate_challan') || currentPath.includes('generate-challan'));
    historyLink.classList.toggle('active', currentPath.includes('challans') || currentPath.includes('challan_detail'));
  }
}

function mountAppNav() {
  const nav = document.getElementById('appNav');
  if (!nav) {
    return;
  }

  const mode = nav.dataset.navMode || 'app';
  const loggedIn = !!getCurrentUser();

  if (mode === 'guest') {
    const path = window.location.pathname;
    nav.innerHTML = path.includes('login')
      ? '<a href="/register.html" class="nav-item">Register</a>'
      : '<a href="/login.html" class="nav-item">Login</a>';
    return;
  }

  if (mode === 'public') {
    nav.innerHTML = `
      <a href="/login.html?next=${encodeURIComponent('/number_plate.html')}" class="nav-item"><i class="fa-solid fa-wand-magic-sparkles"></i> Vehicle Details</a>
      <a href="/login.html" class="nav-item">Login</a>
      <a href="/register.html" class="nav-item">Sign up</a>`;
    return;
  }

  if (loggedIn || mode === 'app') {
    const user = getCurrentUser();
    if (!user) {
      nav.innerHTML = '<a href="/login.html" class="nav-item">Login</a>';
      return;
    }
    if (user.role === 'Citizen') {
      nav.innerHTML = `
        <a href="/number_plate.html" class="nav-item"><i class="fa-solid fa-car"></i> My Details</a>
        <a href="#" class="nav-item nav-logout" onclick="logout(); return false;"><i class="fa-solid fa-arrow-right-from-bracket"></i> Logout</a>`;
      return;
    }
    nav.innerHTML = adminControlGroupHtml(user);
    applyActiveNav();
    bindNavDropdowns();
    applyPublicNavAuth();
    return;
  }

  nav.innerHTML = `
    <a href="/login.html?next=${encodeURIComponent('/dashboard.html')}" class="nav-item" onclick="return openAdministrativeControl(event);">
      <img class="nav-parent-icon" src="/static/admin-control.svg?v=14" alt=""> Administrative Control
    </a>
    <a href="/login.html" class="nav-item" data-guest>Sign in</a>
    <a href="/register.html" class="nav-item" data-guest>Register</a>
  `;
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mountAppNav);
} else {
  mountAppNav();
}
