import cv2
import time
import os
import sqlite3
import numpy as np
import datetime
from fastapi import APIRouter, Response, HTTPException
from fastapi.responses import StreamingResponse

from app.config import DB_PATH, SAMPLE_MEDIA_DIR
from app.anpr.detector import VehiclePlateDetector
from app.anpr.tracker import VehicleTracker
from app.anpr.violation_rules import check_and_create_violations

router = APIRouter(prefix="/api/stream", tags=["Live Stream"])

detector = VehiclePlateDetector()
tracker = VehicleTracker()

# Global stream state
stream_state = {
    "active_camera_id": 1,
    "signal_state": "GREEN", # GREEN, RED
    "speed_limit": 60,
    "simulation_mode": True,
    "last_violation_alert": None,
    "camera_name": "Kalma Chowk Intersect #1",
    "location": "Ferozepur Road, Lahore"
}

# 12 diverse realistic vehicles organized across 3 lanes with realistic staggered spacing
TRAFFIC_FLEET = [
    # Lane 1 (Fast Lane, x=200)
    {"id": 1, "plate": "LEA-21-4589", "type": "sedan", "color": (25, 25, 30), "make": "Civic Oriel", "target_speed": 66, "y": 80, "lane": 1, "cur_speed": 66, "headlight_on": True},
    {"id": 2, "plate": "LHE-5510", "type": "sedan", "color": (30, 30, 180), "make": "Mercedes C200", "target_speed": 84, "y": -280, "lane": 1, "cur_speed": 84, "headlight_on": True},
    {"id": 3, "plate": "FD-2022-78", "type": "suv", "color": (140, 60, 20), "make": "Fortuner 4x4", "target_speed": 74, "y": -640, "lane": 1, "cur_speed": 74, "headlight_on": True},
    {"id": 4, "plate": "ISB-309", "type": "suv", "color": (30, 30, 30), "make": "Sportage AWD", "target_speed": 70, "y": -1000, "lane": 1, "cur_speed": 70, "headlight_on": True},
    
    # Lane 2 (Center Lane, x=440)
    {"id": 5, "plate": "ICT-AB-567", "type": "sedan", "color": (230, 230, 235), "make": "Corolla Grande", "target_speed": 60, "y": -40, "lane": 2, "cur_speed": 60, "headlight_on": True},
    {"id": 6, "plate": "RWP-5120", "type": "sedan", "color": (40, 70, 100), "make": "Yaris ATIV", "target_speed": 58, "y": -400, "lane": 2, "cur_speed": 58, "headlight_on": True},
    {"id": 7, "plate": "AJK-4412", "type": "suv", "color": (90, 95, 100), "make": "Tucson GLS", "target_speed": 64, "y": -760, "lane": 2, "cur_speed": 64, "headlight_on": True},
    {"id": 8, "plate": "FSD-1199", "type": "bus", "color": (180, 100, 30), "make": "Coaster Bus", "target_speed": 48, "y": -1120, "lane": 2, "cur_speed": 48, "headlight_on": True},
    
    # Lane 3 (Right Lane, x=680)
    {"id": 9, "plate": "KHI-8921", "type": "hatchback", "color": (190, 195, 200), "make": "Alto VXR", "target_speed": 52, "y": 180, "lane": 3, "cur_speed": 52, "headlight_on": True},
    {"id": 10, "plate": "PEW-8801", "type": "hatchback", "color": (170, 170, 175), "make": "Swift GLX", "target_speed": 55, "y": -220, "lane": 3, "cur_speed": 55, "headlight_on": True},
    {"id": 11, "plate": "MN-776-LHR", "type": "motorcycle", "color": (180, 80, 20), "make": "Yamaha YBR", "target_speed": 45, "y": -580, "lane": 3, "cur_speed": 45, "headlight_on": True},
    {"id": 12, "plate": "KHI-CC-401", "type": "pickup", "color": (240, 240, 240), "make": "Hilux Revo", "target_speed": 58, "y": -940, "lane": 3, "cur_speed": 58, "headlight_on": True}
]

# Lane positions in X coordinates
LANE_X_COORDS = {1: 200, 2: 440, 3: 680}
MIN_FOLLOWING_DISTANCE = 250 # Minimum distance between front and rear bumper in same lane to prevent any overlap

def draw_front_sedan(frame, x, y, color, plate_text):
    """Draws front perspective of a modern aerodynamic sedan moving downwards towards camera."""
    w, h = 150, 220
    
    # 1. Road drop shadow
    shadow_overlay = frame.copy()
    cv2.ellipse(shadow_overlay, (x + w//2, y + h - 10), (w//2 + 10, 30), 0, 0, 360, (15, 15, 15), -1)
    cv2.addWeighted(shadow_overlay, 0.6, frame, 0.4, 0, frame)
    
    # 2. Main Car Body (Tapered front hood, wider cabin)
    body_pts = np.array([
        [x + 18, y + 10], [x + w - 18, y + 10],   # Roof top edge
        [x + w - 4, y + 60], [x + w - 6, y + 140], # Flanks
        [x + w, y + 190],                          # Front wheel arch
        [x + w - 15, y + h], [x + 15, y + h],      # Front bumper edge
        [x, y + 190],                              # Left front wheel arch
        [x + 6, y + 140], [x + 4, y + 60]          # Left flank
    ], np.int32)
    
    cv2.fillPoly(frame, [body_pts], color)
    cv2.polylines(frame, [body_pts], True, (20, 20, 25), 2)
    
    # 3. Side Mirrors (Angled outwards)
    cv2.rectangle(frame, (x - 8, y + 70), (x + 4, y + 85), color, -1)
    cv2.rectangle(frame, (x + w - 4, y + 70), (x + w + 8, y + 85), color, -1)
    
    # 4. Roof Panel & Sunroof
    cv2.rectangle(frame, (x + 24, y + 12), (x + w - 24, y + 55), color, -1)
    cv2.rectangle(frame, (x + 35, y + 18), (x + w - 35, y + 48), (25, 30, 35), -1) # Sunroof
    
    # 5. Front Windshield (Tinted glass with rearview mirror and driver silhouette)
    fw_pts = np.array([[x + 22, y + 58], [x + w - 22, y + 58], [x + w - 14, y + 115], [x + 14, y + 115]], np.int32)
    cv2.fillPoly(frame, [fw_pts], (30, 38, 48))
    cv2.polylines(frame, [fw_pts], True, (15, 15, 15), 1)
    # Rearview mirror
    cv2.rectangle(frame, (x + w//2 - 8, y + 62), (x + w//2 + 8, y + 68), (15, 15, 15), -1)
    # Driver silhouette (Right Hand Drive - Pakistan)
    cv2.circle(frame, (x + w - 38, y + 88), 12, (20, 25, 30), -1) # Head
    
    # 6. Front Hood with aerodynamic crease lines
    cv2.line(frame, (x + 38, y + 120), (x + 30, y + 185), (200, 200, 200), 1)
    cv2.line(frame, (x + w - 38, y + 120), (x + w - 30, y + 185), (200, 200, 200), 1)
    
    # 7. Front Grille (Black honeycomb with chrome trim)
    cv2.rectangle(frame, (x + 34, y + 172), (x + w - 34, y + 198), (15, 15, 15), -1)
    cv2.rectangle(frame, (x + 34, y + 172), (x + w - 34, y + 198), (210, 215, 220), 1)
    # Emblem
    cv2.circle(frame, (x + w//2, y + 185), 6, (220, 225, 230), -1)
    
    # 8. LED Xenon Headlights (Crystal white with DRL glow)
    # Left Headlight
    hl_left = np.array([[x + 10, y + 168], [x + 32, y + 172], [x + 30, y + 192], [x + 8, y + 185]], np.int32)
    cv2.fillPoly(frame, [hl_left], (245, 250, 255))
    cv2.polylines(frame, [hl_left], True, (0, 200, 255), 1)
    # Right Headlight
    hl_right = np.array([[x + w - 32, y + 172], [x + w - 10, y + 168], [x + w - 8, y + 185], [x + w - 30, y + 192]], np.int32)
    cv2.fillPoly(frame, [hl_right], (245, 250, 255))
    cv2.polylines(frame, [hl_right], True, (0, 200, 255), 1)
    
    # 9. Lower Fog Lamps
    cv2.circle(frame, (x + 16, y + 208), 4, (240, 245, 255), -1)
    cv2.circle(frame, (x + w - 16, y + 208), 4, (240, 245, 255), -1)
    
    # 10. Front License Plate (Clean, white with green province badge)
    px, py = x + w//2 - 48, y + 194
    pw, ph = 96, 25
    cv2.rectangle(frame, (px, py), (px + pw, py + ph), (255, 255, 255), -1)
    cv2.rectangle(frame, (px, py), (px + pw, py + ph), (0, 120, 0), 2)
    cv2.rectangle(frame, (px, py), (px + 12, py + ph), (0, 120, 0), -1)
    cv2.putText(frame, plate_text, (px + 16, py + 17), cv2.FONT_HERSHEY_DUPLEX, 0.42, (0, 0, 0), 1)
    
    return (x, y, w, h), (px, py, pw, ph), frame[py:py+ph, px:px+pw]

def draw_front_suv(frame, x, y, color, plate_text):
    """Draws front perspective of a muscular 4x4 SUV with high stance and aggressive grille."""
    w, h = 165, 240
    
    # Drop shadow
    shadow_overlay = frame.copy()
    cv2.ellipse(shadow_overlay, (x + w//2, y + h - 10), (w//2 + 12, 32), 0, 0, 360, (15, 15, 15), -1)
    cv2.addWeighted(shadow_overlay, 0.6, frame, 0.4, 0, frame)
    
    # Main Body
    body_pts = np.array([
        [x + 18, y + 10], [x + w - 18, y + 10],
        [x + w - 5, y + 60], [x + w - 4, y + 150],
        [x + w, y + 205],                          # Wheel arches
        [x + w - 10, y + h], [x + 10, y + h],      # Bumper
        [x, y + 205],
        [x + 4, y + 150], [x + 5, y + 60]
    ], np.int32)
    cv2.fillPoly(frame, [body_pts], color)
    cv2.polylines(frame, [body_pts], True, (25, 25, 30), 2)
    
    # Roof Rails
    cv2.line(frame, (x + 22, y + 10), (x + 22, y + 70), (190, 195, 200), 3)
    cv2.line(frame, (x + w - 22, y + 10), (x + w - 22, y + 70), (190, 195, 200), 3)
    
    # Front Windshield
    fw_pts = np.array([[x + 20, y + 55], [x + w - 20, y + 55], [x + w - 12, y + 120], [x + 12, y + 120]], np.int32)
    cv2.fillPoly(frame, [fw_pts], (30, 38, 48))
    # Driver silhouette (RHD)
    cv2.circle(frame, (x + w - 40, y + 90), 13, (20, 25, 30), -1)
    
    # Wide Bold Chrome Grille
    cv2.rectangle(frame, (x + 30, y + 180), (x + w - 30, y + 215), (20, 25, 30), -1)
    cv2.rectangle(frame, (x + 30, y + 180), (x + w - 30, y + 215), (200, 205, 210), 2)
    # Horizontal Grille Slats
    for gy in [y + 190, y + 200]:
        cv2.line(frame, (x + 32, gy), (x + w - 32, gy), (180, 185, 190), 2)
        
    # Angular LED Projector Headlamps
    hl_l = np.array([[x + 10, y + 175], [x + 28, y + 180], [x + 26, y + 205], [x + 8, y + 198]], np.int32)
    cv2.fillPoly(frame, [hl_l], (245, 250, 255))
    hl_r = np.array([[x + w - 28, y + 180], [x + w - 10, y + 175], [x + w - 8, y + 198], [x + w - 26, y + 205]], np.int32)
    cv2.fillPoly(frame, [hl_r], (245, 250, 255))
    
    # Skid Plate
    cv2.rectangle(frame, (x + 35, y + h - 8), (x + w - 35, y + h), (180, 185, 190), -1)
    
    # Plate
    px, py = x + w//2 - 48, y + 210
    pw, ph = 96, 25
    cv2.rectangle(frame, (px, py), (px + pw, py + ph), (255, 255, 255), -1)
    cv2.rectangle(frame, (px, py), (px + pw, py + ph), (0, 100, 0), 2)
    cv2.rectangle(frame, (px, py), (px + 12, py + ph), (0, 100, 0), -1)
    cv2.putText(frame, plate_text, (px + 16, py + 17), cv2.FONT_HERSHEY_DUPLEX, 0.42, (0, 0, 0), 1)
    
    return (x, y, w, h), (px, py, pw, ph), frame[py:py+ph, px:px+pw]

def draw_front_hatchback(frame, x, y, color, plate_text):
    """Draws front perspective of a compact city hatchback."""
    w, h = 135, 190
    
    cv2.ellipse(frame, (x + w//2, y + h - 8), (w//2 + 8, 25), 0, 0, 360, (25, 25, 25), -1)
    
    body_pts = np.array([
        [x + 15, y + 10], [x + w - 15, y + 10],
        [x + w - 4, y + 50], [x + w, y + 140],
        [x + w - 8, y + h], [x + 8, y + h],
        [x, y + 140], [x + 4, y + 50]
    ], np.int32)
    cv2.fillPoly(frame, [body_pts], color)
    cv2.polylines(frame, [body_pts], True, (25, 25, 30), 2)
    
    # Windshield
    fw_pts = np.array([[x + 18, y + 45], [x + w - 18, y + 45], [x + w - 10, y + 95], [x + 10, y + 95]], np.int32)
    cv2.fillPoly(frame, [fw_pts], (35, 42, 50))
    
    # Headlights
    cv2.circle(frame, (x + 18, y + 150), 10, (245, 250, 255), -1)
    cv2.circle(frame, (x + w - 18, y + 150), 10, (245, 250, 255), -1)
    
    # Plate
    px, py = x + w//2 - 46, y + 160
    pw, ph = 92, 24
    cv2.rectangle(frame, (px, py), (px + pw, py + ph), (255, 255, 255), -1)
    cv2.rectangle(frame, (px, py), (px + pw, py + ph), (0, 120, 0), 2)
    cv2.putText(frame, plate_text, (px + 8, py + 16), cv2.FONT_HERSHEY_DUPLEX, 0.38, (0, 0, 0), 1)
    
    return (x, y, w, h), (px, py, pw, ph), frame[py:py+ph, px:px+pw]

def draw_front_motorcycle(frame, x, y, color, plate_text):
    """Draws front perspective of a motorbike with rider, round headlamp, and front plate."""
    w, h = 90, 150
    cx = x + w // 2
    
    cv2.ellipse(frame, (cx, y + h - 8), (22, 14), 0, 0, 360, (20, 20, 20), -1)
    
    # Rider Helmet & Visor
    cv2.circle(frame, (cx, y + 30), 18, (40, 40, 45), -1)
    cv2.circle(frame, (cx, y + 30), 18, (255, 255, 255), 1)
    cv2.ellipse(frame, (cx, y + 32), (14, 6), 0, 0, 180, (15, 15, 15), -1)
    
    # Rider Shoulders
    cv2.ellipse(frame, (cx, y + 60), (28, 16), 0, 0, 360, color, -1)
    
    # Handlebars & Mirrors
    cv2.line(frame, (cx - 32, y + 45), (cx + 32, y + 45), (160, 160, 160), 3)
    cv2.circle(frame, (cx - 32, y + 42), 4, (120, 120, 120), -1)
    cv2.circle(frame, (cx + 32, y + 42), 4, (120, 120, 120), -1)
    
    # Bright Round Front Headlight
    cv2.circle(frame, (cx, y + 95), 14, (255, 255, 250), -1)
    cv2.circle(frame, (cx, y + 95), 14, (0, 200, 255), 2)
    
    # Front Tire
    cv2.rectangle(frame, (cx - 8, y + 110), (cx + 8, y + 145), (25, 25, 30), -1)
    
    # Front Plate
    px, py = cx - 40, y + 120
    pw, ph = 80, 22
    cv2.rectangle(frame, (px, py), (px + pw, py + ph), (255, 255, 255), -1)
    cv2.rectangle(frame, (px, py), (px + pw, py + ph), (0, 100, 0), 1)
    cv2.putText(frame, plate_text, (px + 4, py + 15), cv2.FONT_HERSHEY_DUPLEX, 0.35, (0, 0, 0), 1)
    
    return (x, y, w, h), (px, py, pw, ph), frame[py:py+ph, px:px+pw]

def draw_front_pickup(frame, x, y, color, plate_text):
    """Draws front of a double-cabin pickup truck with high clearance and chrome bullbar grille."""
    w, h = 160, 245
    
    cv2.ellipse(frame, (x + w//2, y + h - 10), (w//2 + 10, 32), 0, 0, 360, (20, 20, 20), -1)
    
    # Cabin
    cv2.rectangle(frame, (x + 10, y + 10), (x + w - 10, y + 130), color, -1)
    # Windshield
    fw_pts = np.array([[x + 18, y + 45], [x + w - 18, y + 45], [x + w - 10, y + 110], [x + 10, y + 110]], np.int32)
    cv2.fillPoly(frame, [fw_pts], (30, 35, 42))
    
    # Heavy Duty Grille
    cv2.rectangle(frame, (x + 15, y + 165), (x + w - 15, y + 215), (25, 25, 30), -1)
    cv2.rectangle(frame, (x + 15, y + 165), (x + w - 15, y + 215), (190, 195, 200), 2)
    
    # Headlights
    cv2.rectangle(frame, (x + 8, y + 165), (x + 28, y + 195), (245, 250, 255), -1)
    cv2.rectangle(frame, (x + w - 28, y + 165), (x + w - 8, y + 195), (245, 250, 255), -1)
    
    # Plate
    px, py = x + w//2 - 48, y + 215
    pw, ph = 96, 25
    cv2.rectangle(frame, (px, py), (px + pw, py + ph), (255, 255, 255), -1)
    cv2.rectangle(frame, (px, py), (px + pw, py + ph), (0, 100, 0), 2)
    cv2.putText(frame, plate_text, (px + 12, py + 17), cv2.FONT_HERSHEY_DUPLEX, 0.40, (0, 0, 0), 1)
    
    return (x, y, w, h), (px, py, pw, ph), frame[py:py+ph, px:px+pw]

def draw_front_bus(frame, x, y, color, plate_text):
    """Draws front of a commercial coaster passenger bus with yellow plate."""
    w, h = 175, 260
    
    cv2.ellipse(frame, (x + w//2, y + h - 10), (w//2 + 12, 35), 0, 0, 360, (20, 20, 20), -1)
    
    # Bus Boxy Body
    cv2.rectangle(frame, (x + 8, y + 10), (x + w - 8, y + h), color, -1)
    cv2.rectangle(frame, (x + 8, y + 10), (x + w - 8, y + h), (30, 30, 35), 2)
    
    # Panoramic Front Windshield
    cv2.rectangle(frame, (x + 14, y + 45), (x + w - 14, y + 135), (25, 30, 35), -1)
    # Destination board
    cv2.rectangle(frame, (x + 35, y + 20), (x + w - 35, y + 40), (20, 20, 20), -1)
    cv2.putText(frame, "LAHORE - ISLAMABAD", (x + 40, y + 34), cv2.FONT_HERSHEY_SIMPLEX, 0.28, (0, 220, 255), 1)
    
    # Dual Headlights
    cv2.circle(frame, (x + 24, y + 195), 10, (250, 255, 255), -1)
    cv2.circle(frame, (x + w - 24, y + 195), 10, (250, 255, 255), -1)
    
    # Commercial Yellow License Plate
    px, py = x + w//2 - 48, y + 225
    pw, ph = 96, 25
    cv2.rectangle(frame, (px, py), (px + pw, py + ph), (0, 215, 255), -1) # Yellow
    cv2.rectangle(frame, (px, py), (px + pw, py + ph), (0, 0, 0), 2)
    cv2.putText(frame, plate_text, (px + 10, py + 17), cv2.FONT_HERSHEY_DUPLEX, 0.40, (0, 0, 0), 1)
    
    return (x, y, w, h), (px, py, pw, ph), frame[py:py+ph, px:px+pw]

def update_traffic_physics_no_overlap(stop_line_y, is_red_signal, speed_limit):
    """
    Intelligent car-following physics engine:
    1. Prevents any vehicle from overlapping the car in front of it in the same lane.
    2. Manages realistic queuing at red lights.
    3. Handles overspeeding violators blowing through red signals.
    """
    # Group vehicles by lane
    lanes_dict = {1: [], 2: [], 3: []}
    for v in TRAFFIC_FLEET:
        lanes_dict[v["lane"]].append(v)
        
    for lane_id, v_list in lanes_dict.items():
        # Sort vehicles in this lane by Y descending (the one with largest Y is further ahead)
        v_list.sort(key=lambda x: x["y"], reverse=True)
        
        for i, v in enumerate(v_list):
            front_v = v_list[i - 1] if i > 0 else None
            
            # Determine maximum target speed & stopping target
            desired_speed = v["target_speed"]
            
            # 1. Check Red Light Stop Line condition
            if is_red_signal:
                # If vehicle is approaching stop line from above
                dist_to_stop_line = (stop_line_y - 230) - v["y"]
                
                # Check if this vehicle is an overspeeding violator (> speed_limit + 10)
                is_violator = (v["target_speed"] > speed_limit + 10)
                
                if not is_violator and 0 < dist_to_stop_line < 220:
                    # Decelerate to stop at the stop line
                    desired_speed = max(0, int(desired_speed * (dist_to_stop_line / 220.0)))
                    
            # 2. Car-Following Buffer (Prevent overlap with vehicle in front)
            if front_v is not None:
                gap = front_v["y"] - v["y"]
                if gap < MIN_FOLLOWING_DISTANCE:
                    # Match or reduce speed of vehicle ahead
                    desired_speed = min(desired_speed, front_v["cur_speed"])
                    if front_v["cur_speed"] == 0 or gap < (MIN_FOLLOWING_DISTANCE - 40):
                        # Force stop at safe distance behind front car
                        desired_speed = 0
                        v["y"] = min(v["y"], front_v["y"] - MIN_FOLLOWING_DISTANCE)
                        
            # Smooth acceleration / deceleration
            if v["cur_speed"] < desired_speed:
                v["cur_speed"] = min(desired_speed, v["cur_speed"] + 2)
            elif v["cur_speed"] > desired_speed:
                v["cur_speed"] = max(desired_speed, v["cur_speed"] - 4)
                
            # Advance position downwards
            v["y"] += int(v["cur_speed"] * 0.12)
            
            # Respawn vehicle when it exits bottom of screen
            if v["y"] > 540 + 260:
                # Find rearmost vehicle in this lane to ensure no overlap at top
                rearmost_y = min([veh["y"] for veh in v_list])
                # Place at least MIN_FOLLOWING_DISTANCE behind the rearmost vehicle
                v["y"] = min(-280, rearmost_y - MIN_FOLLOWING_DISTANCE - np.random.randint(20, 80))
                v["cur_speed"] = v["target_speed"]

def generate_simulated_frame():
    """
    Renders HD CCTV traffic scene with downwards road arrows, incoming front-view vehicles,
    and intelligent collision-free car-following physics.
    """
    w, h = 960, 540
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    
    # 1. Asphalt Roadway
    frame[:] = (42, 47, 51)
    
    # Road Kerbs & Grass Sidewalks
    cv2.rectangle(frame, (0, 0), (110, h), (34, 75, 42), -1) # Left grass
    cv2.rectangle(frame, (w - 110, 0), (w, h), (34, 75, 42), -1) # Right grass
    
    # Hazard kerbstones (Yellow & Black alternating stripes)
    for ky in range(0, h, 30):
        k_col = (0, 200, 240) if (ky // 30) % 2 == 0 else (20, 20, 20)
        cv2.rectangle(frame, (110, ky), (120, ky + 30), k_col, -1)
        cv2.rectangle(frame, (w - 120, ky), (w - 110, ky + 30), k_col, -1)
        
    # 2. Road Lane Dividers (3 Lanes: lines at x=340 and x=580)
    for ly in [340, 580]:
        for dy in range(0, h, 60):
            cv2.line(frame, (ly, dy), (ly, dy + 35), (240, 240, 245), 3)
            # Reflective Cat-eyes (road studs)
            cv2.circle(frame, (ly, dy + 45), 3, (0, 220, 255), -1)
            
    # Directional White Arrows pointing DOWNWARDS (Matching Traffic Flow)
    for ax in [230, 470, 710]:
        for ay in [100, 380]:
            # Arrow pointing DOWNWARDS
            cv2.arrowedLine(frame, (ax, ay), (ax, ay + 40), (200, 205, 210), 3, tipLength=0.35)

    # 3. Virtual Stop Line & Thermoplastic Zebra Pedestrian Crossing
    stop_line_y = int(h * 0.65)
    
    # Thermoplastic Zebra Crossing Stripes
    for zx in range(130, w - 130, 50):
        cv2.rectangle(frame, (zx, stop_line_y + 12), (zx + 32, stop_line_y + 42), (200, 205, 210), -1)
        
    # Stop Line
    is_red_signal = (stream_state["signal_state"] == "RED")
    line_color = (0, 0, 255) if is_red_signal else (0, 255, 100)
    cv2.line(frame, (120, stop_line_y), (w - 120, stop_line_y), line_color, 4)
    cv2.putText(frame, "STOP LINE (RADAR SENSOR)", (130, stop_line_y - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, line_color, 1)

    # 4. Traffic Signal Lamp on Overhead Pole (Top Right)
    cv2.rectangle(frame, (w - 70, 40), (w - 20, 130), (20, 25, 30), -1)
    cv2.rectangle(frame, (w - 70, 40), (w - 20, 130), (100, 105, 110), 2)
    # Red Lamp
    r_col = (0, 0, 255) if is_red_signal else (30, 30, 60)
    cv2.circle(frame, (w - 45, 60), 12, r_col, -1)
    # Yellow Lamp
    cv2.circle(frame, (w - 45, 85), 10, (20, 40, 50), -1)
    # Green Lamp
    g_col = (0, 255, 0) if not is_red_signal else (20, 50, 30)
    cv2.circle(frame, (w - 45, 110), 12, g_col, -1)

    # 5. Update Traffic Physics with No Overlap
    update_traffic_physics_no_overlap(stop_line_y, is_red_signal, stream_state["speed_limit"])

    # 6. Render Vehicles Front View
    detections = []
    
    for v in TRAFFIC_FLEET:
        vx = LANE_X_COORDS[v["lane"]]
        vy = int(v["y"])
        
        # Only render if in visible vertical range
        if -140 <= vy <= h + 60:
            v_type = v.get("type", "sedan")
            
            if v_type == "sedan":
                v_box, p_box, crop = draw_front_sedan(frame, vx, vy, v["color"], v["plate"])
            elif v_type == "suv":
                v_box, p_box, crop = draw_front_suv(frame, vx, vy, v["color"], v["plate"])
            elif v_type == "hatchback":
                v_box, p_box, crop = draw_front_hatchback(frame, vx, vy, v["color"], v["plate"])
            elif v_type == "motorcycle":
                v_box, p_box, crop = draw_front_motorcycle(frame, vx, vy, v["color"], v["plate"])
            elif v_type == "pickup":
                v_box, p_box, crop = draw_front_pickup(frame, vx, vy, v["color"], v["plate"])
            elif v_type == "bus":
                v_box, p_box, crop = draw_front_bus(frame, vx, vy, v["color"], v["plate"])
            else:
                v_box, p_box, crop = draw_front_sedan(frame, vx, vy, v["color"], v["plate"])
                
            detections.append({
                "vehicle_bbox": v_box,
                "plate_bbox": p_box,
                "plate_crop": crop,
                "plate_number": v["plate"],
                "confidence": 0.95,
                "vehicle_type": v_type.title()
            })
            
    # 7. Run Tracker & Violation Logic
    tracked_dets = tracker.update(detections)
    
    cam_info = {
        "id": stream_state["active_camera_id"],
        "name": stream_state["camera_name"],
        "location": stream_state["location"],
        "speed_limit": stream_state["speed_limit"],
        "signal_state": stream_state["signal_state"]
    }
    
    new_violations = check_and_create_violations(frame, tracked_dets, cam_info, tracker)
    if new_violations:
        stream_state["last_violation_alert"] = new_violations[-1]

    # 8. AI Bounding Boxes & HUD Overlays
    for td in tracked_dets:
        vx, vy, vw, vh = td["vehicle_bbox"]
        plate = td["plate_number"]
        speed = td.get("speed_kmh", 45)
        
        is_violating = (speed > stream_state["speed_limit"]) or (is_red_signal and (vy + vh // 2) > stop_line_y)
        box_color = (0, 0, 255) if is_violating else (0, 255, 120)
        
        cv2.rectangle(frame, (vx, vy), (vx + vw, vy + vh), box_color, 2)
        
        # Plate & Speed Tag
        tag_text = f"[{plate}] {speed} km/h"
        cv2.rectangle(frame, (vx, vy - 24), (vx + len(tag_text) * 11, vy), box_color, -1)
        cv2.putText(frame, tag_text, (vx + 4, vy - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 0, 0), 1)

    # 9. Professional CCTV Camera Top Status HUD
    cv2.rectangle(frame, (0, 0), (w, 36), (15, 23, 42), -1)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cv2.putText(frame, f"● REC  CAM-01 [HD-ANPR]  |  {stream_state['location']}", (15, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (240, 240, 240), 1)
                
    cv2.putText(frame, f"LIMIT: {stream_state['speed_limit']} KM/H", (w - 360, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 255), 1)
                
    sig_text = f"SIGNAL: {stream_state['signal_state']}"
    cv2.putText(frame, sig_text, (w - 180, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255) if is_red_signal else (0, 255, 100), 1)

    return frame

def stream_generator():
    """Yields MJPEG stream continuously."""
    while True:
        frame = generate_simulated_frame()
        ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ret:
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
        time.sleep(0.04) # ~25 FPS

@router.get("/video_feed")
def video_feed():
    return StreamingResponse(
        stream_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.post("/set_signal/{state}")
def set_signal(state: str):
    state_upper = state.upper()
    if state_upper in ["RED", "GREEN", "YELLOW"]:
        stream_state["signal_state"] = state_upper
        
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("UPDATE cameras SET signal_state = ? WHERE id = ?", (state_upper, stream_state["active_camera_id"]))
        conn.commit()
        conn.close()
        
        return {"status": "success", "signal_state": state_upper}
    raise HTTPException(status_code=400, detail="Invalid signal state. Use RED or GREEN")

@router.post("/set_speed_limit/{limit}")
def set_speed_limit(limit: int):
    if 20 <= limit <= 140:
        stream_state["speed_limit"] = limit
        return {"status": "success", "speed_limit": limit}
    raise HTTPException(status_code=400, detail="Speed limit must be between 20 and 140")

@router.post("/select_camera/{camera_id}")
def select_camera(camera_id: int):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cameras WHERE id = ?", (camera_id,))
    cam = cursor.fetchone()
    conn.close()
    
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    stream_state["active_camera_id"] = cam["id"]
    stream_state["camera_name"] = cam["name"]
    stream_state["location"] = cam["location"]
    stream_state["speed_limit"] = cam["speed_limit"]
    stream_state["signal_state"] = cam["signal_state"]
    
    return {"status": "success", "active_camera": dict(cam)}

@router.get("/live_alert")
def get_live_alert():
    """Polls latest triggered violation."""
    alert = stream_state.get("last_violation_alert")
    return {"alert": alert}
