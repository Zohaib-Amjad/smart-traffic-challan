/**
 * Smart Traffic Challan System - Interactive Client-Side Mock Backend
 * Provides full offline / Vercel demo support for all roles (Officer, Admin, Citizen).
 * Automatically activates when live FastAPI server is unavailable.
 */

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
    const searchParams = new URLSearchParams(cleanUrl.split('?')[1] || '');

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

      // Violation distribution
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
      // Fallback synthetic challan
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

    // Default fallback
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
  if (typeof window !== 'undefined') {
    const originalFetch = window.fetch;
    window.fetch = async function (input, init) {
      const url = typeof input === 'string' ? input : (input && input.url ? input.url : '');
      
      // If it's an API route:
      if (url.startsWith('/api/') || url.includes('/api/')) {
        try {
          const liveRes = await originalFetch.apply(this, arguments);
          // If server returned valid JSON, use live server
          const contentType = liveRes.headers.get('content-type') || '';
          if (liveRes.ok && contentType.includes('application/json')) {
            return liveRes;
          }
          // If server returned 404/500/HTML (e.g. Vercel static hosting), fallback to mock
          return await handleMockRequest(url, init);
        } catch (netErr) {
          // Network error or offline -> handle locally
          return await handleMockRequest(url, init);
        }
      }

      return originalFetch.apply(this, arguments);
    };
  }
})();
