"""Live radar screen for the Arduino ultrasonic radar.

Usage:
    pip install pyserial matplotlib numpy
    python radar_view.py COM3            # Windows
    python radar_view.py /dev/ttyACM0    # Linux
Close the Arduino Serial Monitor first - only one program can use the port.
"""
import math
import sys

import matplotlib.pyplot as plt
import numpy as np
import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM3"
BAUD = 9600
MAX_CM = 100  # radar range shown on screen

ser = serial.Serial(PORT, BAUD, timeout=1)
readings = {}  # angle -> latest distance

plt.style.use("dark_background")
plt.ion()
fig = plt.figure("Ultrasonic Radar")
ax = fig.add_subplot(projection="polar")
ax.set_thetamin(0)
ax.set_thetamax(180)
ax.set_rlim(0, MAX_CM)
ax.set_title("Ultrasonic Radar (cm)", color="lime")
dots = ax.scatter([], [], s=14, c="red")
sweep, = ax.plot([], [], c="lime", lw=2)

current_angle = 90
while plt.fignum_exists(fig.number):
    # read everything waiting, then redraw once
    while ser.in_waiting:
        raw = ser.readline().decode(errors="ignore").strip()
        try:
            angle, dist = (int(v) for v in raw.split(","))
        except ValueError:
            continue
        readings[angle] = dist
        current_angle = angle

    pts = [(math.radians(a), d) for a, d in readings.items() if 0 < d <= MAX_CM]
    dots.set_offsets(np.array(pts) if pts else np.empty((0, 2)))
    theta = math.radians(current_angle)
    sweep.set_data([theta, theta], [0, MAX_CM])
    plt.pause(0.03)

ser.close()
