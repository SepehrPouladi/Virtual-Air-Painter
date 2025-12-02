import cv2
import mediapipe as mp
import numpy as np
import math
import time

# --- 1. Initialization and State Variables ---

canvas_width = 800
canvas_height = 600

# Color definitions (BGR)
BLUE = (255, 0, 0)
GREEN = (0, 255, 0)
RED = (0, 0, 255)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (100, 100, 100)
YELLOW = (0, 255, 255)

current_color = GREEN  
current_thickness = 5

PINCH_THRESHOLD = 0.05 
CLICK_COOLDOWN = 0.3 # Cooldown time in seconds after a button click

pen_active_state = False 
last_click_time = 0 
is_pinching_moment = False 

all_drawing_points = []
current_drawing_line = []

# Create the white canvas
canvas = np.zeros((canvas_height, canvas_width, 3), dtype=np.uint8)
canvas.fill(255) 

# --- 2. Button Configuration ---
class Button:
    def __init__(self, x, y, w, h, text, default_color, action):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.text = text
        self.default_color = default_color
        self.action = action

button_w, button_h = 100, 50
margin = 20
# button_start_x calculation removed from here, as it needs actual frame width (w)

# The global 'buttons' list is removed here and will be defined inside the loop.

def draw_buttons(frame, buttons_list, hover_index=-1):
    """Draws all configured buttons on the frame."""
    for i, btn in enumerate(buttons_list):
        color = btn.default_color
        # Highlight button if finger is hovering over it
        if i == hover_index:
            color = YELLOW # Hover color

        cv2.rectangle(frame, (btn.x, btn.y), (btn.x + btn.w, btn.y + btn.h), color, cv2.FILLED)
        
        text_x = btn.x + int(btn.w / 2) - int(len(btn.text) * 7) # Basic centering
        text_y = btn.y + int(btn.h / 2) + 7
        # Font thickness increased to 2 for a bolder look
        cv2.putText(frame, btn.text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

# --- 3. MediaPipe Hands Setup ---
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)

# --- 4. Webcam Setup and Main Loop ---
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Webcam failed to open.")
    exit()

def calculate_distance(p1, p2):
    return math.hypot(p1.x - p2.x, p1.y - p2.y)

def execute_button_action(action):
    """Executes the action associated with the button."""
    global current_color, canvas, all_drawing_points, current_drawing_line, pen_active_state, current_thickness, last_click_time

    if time.time() - last_click_time < CLICK_COOLDOWN:
        return # Block click if still in cooldown

    last_click_time = time.time()

    # Removed "TOGGLE" action
    if action == "COLOR_R":
        current_color = RED
    elif action == "COLOR_G":
        current_color = GREEN
    elif action == "COLOR_B":
        current_color = BLUE
    elif action == "CLEAR":
        canvas.fill(255) 
        all_drawing_points = []
        current_drawing_line = []

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)

    h, w, _ = frame.shape
    
    # --- DYNAMIC BUTTON DEFINITION (Calculated based on actual frame width 'w') ---
    button_start_x = w - button_w - margin # Calculate X based on frame width (w)

    buttons = [
        Button(button_start_x, margin + 0*(button_h + margin), button_w, button_h, "RED", RED, "COLOR_R"),
        Button(button_start_x, margin + 1*(button_h + margin), button_w, button_h, "GREEN", GREEN, "COLOR_G"),
        Button(button_start_x, margin + 2*(button_h + margin), button_w, button_h, "BLUE", BLUE, "COLOR_B"),
        Button(button_start_x, margin + 3*(button_h + margin), button_w, button_h, "CLEAR", DARK_GRAY, "CLEAR")
    ]
    # -----------------------------------------------------------------------------
    
    current_x, current_y = None, None
    pinch_detected = False 
    hovering_button_index = -1

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            p_index = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            p_thumb = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
            
            # --- Gesture Control (Pinch) ---
            distance = calculate_distance(p_index, p_thumb)
            
            if distance < PINCH_THRESHOLD:
                pinch_detected = True
                if not is_pinching_moment:
                    is_pinching_moment = True
            else: 
                is_pinching_moment = False

            # --- Tracking Pointer ---
            current_x = int(p_index.x * w)
            current_y = int(p_index.y * h)

            # --- 5. UI Button Interaction ---
            button_clicked = False
            for i, btn in enumerate(buttons):
                if btn.x < current_x < btn.x + btn.w and btn.y < current_y < btn.y + btn.h:
                    hovering_button_index = i
                    
                    if pinch_detected and is_pinching_moment:
                        execute_button_action(btn.action)
                        button_clicked = True
                        break # Only process one click per frame

            # If a button was clicked, flash green on the button boundary
            if button_clicked:
                 btn = buttons[hovering_button_index]
                 cv2.rectangle(frame, (btn.x, btn.y), (btn.x + btn.w, btn.y + btn.h), (0, 255, 0), 3)

            # --- Drawing Logic ---
            if not button_clicked:
                if pen_active_state:
                    # Drawing is active, add point
                    cv2.circle(frame, (current_x, current_y), 10, YELLOW, -1) 
                    current_drawing_line.append((current_x, current_y))
                else:
                    # Pen is inactive, show pointer only
                    cv2.circle(frame, (current_x, current_y), 7, DARK_GRAY, -1) 

                    # Finalize line if pen was just deactivated
                    if current_drawing_line:
                        all_drawing_points.append(list(current_drawing_line)) 
                        current_drawing_line = []
    
    else: 
        # Hand disappeared
        is_pinching_moment = False
        if current_drawing_line:
            all_drawing_points.append(list(current_drawing_line)) 
            current_drawing_line = []

    # --- 6. Draw all lines on the canvas ---
    for line_of_points in all_drawing_points:
        if len(line_of_points) > 1:
            for i in range(1, len(line_of_points)):
                cv2.line(canvas, line_of_points[i-1], line_of_points[i], current_color, current_thickness)
    
    if len(current_drawing_line) > 1:
        for i in range(1, len(current_drawing_line)):
            cv2.line(canvas, current_drawing_line[i-1], current_drawing_line[i], current_color, current_thickness)

    # --- 7. Display Status and Buttons ---
    draw_buttons(frame, buttons, hovering_button_index)

    status_text = "PEN ACTIVE (for inactivate pen : press t,T)" if pen_active_state else "PEN INACTIVE (for activate pen : press t,T)"
    
    # Draw status bar at the bottom
    cv2.rectangle(frame, (0, h - 35), (w, h), (50, 50, 50), -1)
    cv2.putText(frame, status_text, (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)


    # Display active color
    color_name = "Blue" if current_color == BLUE else "Green" if current_color == GREEN else "Red"
    cv2.rectangle(frame, (w - 150, h - 35), (w, h), current_color, -1)
    cv2.putText(frame, f"Color: {color_name}", (w - 140, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    # Display frames
    # Updated window title to include the new 'T' toggle key
    cv2.imshow('Camera Feed (Q: Quit, T: Toggle Pen)', frame)
    cv2.imshow('Virtual Canvas', canvas)

    # --- 8. Keyboard Controls (Thickness and Toggle) ---
    key = cv2.waitKey(1) & 0xFF
    
    if key == ord('q'): 
        break
    elif key == ord('t'): # Added Toggle control for the pen
        pen_active_state = not pen_active_state
    elif key == ord('+'): 
        current_thickness = min(current_thickness + 1, 20) 
    elif key == ord('-'): 
        current_thickness = max(current_thickness - 1, 1) 


# --- 9. Resource Cleanup ---
cap.release()
cv2.destroyAllWindows()
hands.close()