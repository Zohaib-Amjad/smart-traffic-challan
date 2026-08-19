import time
import math

class VehicleTracker:
    """
    Tracks vehicles across consecutive video frames to estimate speed and
    prevent duplicate violation triggers.
    """
    def __init__(self, pixel_to_kmh_ratio=1.4, cooldown_seconds=30):
        # Store active tracks: {track_id: {"last_pos": (cx, cy), "last_time": timestamp, "speed": kmh, "plate": str, "last_challan_time": timestamp}}
        self.tracks = {}
        self.next_track_id = 1
        self.pixel_to_kmh_ratio = pixel_to_kmh_ratio
        self.cooldown_seconds = cooldown_seconds
        
    def update(self, detections):
        """
        Matches incoming detections with existing tracks using centroid distance.
        """
        current_time = time.time()
        updated_detections = []
        
        # Clean up stale tracks older than 5 seconds
        stale_ids = [tid for tid, data in self.tracks.items() if current_time - data["last_time"] > 5.0]
        for tid in stale_ids:
            del self.tracks[tid]
            
        for det in detections:
            x, y, w, h = det["vehicle_bbox"]
            cx, cy = x + w // 2, y + h // 2
            
            # Find closest existing track
            best_track_id = None
            min_dist = 120 # pixel matching threshold
            
            for tid, data in self.tracks.items():
                lx, ly = data["last_pos"]
                dist = math.hypot(cx - lx, cy - ly)
                if dist < min_dist:
                    min_dist = dist
                    best_track_id = tid
                    
            if best_track_id is None:
                best_track_id = self.next_track_id
                self.next_track_id += 1
                estimated_speed = 45 # default starting baseline speed in km/h
                self.tracks[best_track_id] = {
                    "last_pos": (cx, cy),
                    "last_time": current_time,
                    "speed": estimated_speed,
                    "plate": det["plate_number"],
                    "last_challan_time": 0
                }
            else:
                track = self.tracks[best_track_id]
                dt = current_time - track["last_time"]
                lx, ly = track["last_pos"]
                
                if dt > 0.05:
                    pixel_dist = math.hypot(cx - lx, cy - ly)
                    raw_speed = (pixel_dist / dt) * 0.15 * self.pixel_to_kmh_ratio
                    # Exponential smoothing filter
                    estimated_speed = int(0.7 * track["speed"] + 0.3 * raw_speed)
                    estimated_speed = max(15, min(140, estimated_speed)) # clamp between 15 and 140 km/h
                else:
                    estimated_speed = track["speed"]
                    
                track["last_pos"] = (cx, cy)
                track["last_time"] = current_time
                track["speed"] = estimated_speed
                if det["plate_number"] != "UNKNOWN":
                    track["plate"] = det["plate_number"]
                    
            det["track_id"] = best_track_id
            det["speed_kmh"] = self.tracks[best_track_id]["speed"]
            updated_detections.append(det)
            
        return updated_detections

    def can_generate_challan(self, track_id, plate_number):
        """
        Checks if cooldown has elapsed for this track/plate to avoid multiple fines for same incident.
        """
        now = time.time()
        track = self.tracks.get(track_id)
        if track:
            if now - track["last_challan_time"] > self.cooldown_seconds:
                track["last_challan_time"] = now
                return True
            return False
        return True
