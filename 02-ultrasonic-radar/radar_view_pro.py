"""Ultrasonic Radar - pro display (pygame).

Usage:
    pip install pyserial pygame
    python radar_view_pro.py COM4      # real radar (use your port)
    python radar_view_pro.py demo      # fake data, no Arduino needed

Keys:  + / -  change range    M  mirror left/right    C  clear
       S  save screenshot     Esc  quit
Close the Arduino Serial Monitor first - only one program can use the port.
"""
import math
import random
import sys
import time

import pygame

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM4"
BAUD = 9600
ALERT_CM = 30            # keep the same as ALERT_CM in radar.ino
FADE_SECONDS = 4.0       # how long a detected point stays on screen
RANGES = [25, 50, 100, 200]

W, H = 1200, 720
CX, CY = W // 2, H - 80
RADIUS = 520

BG = (3, 10, 5)
GRID = (30, 120, 55)
GRID_DIM = (14, 55, 26)
GREEN = (70, 255, 130)
TEXT = (130, 255, 170)
RED = (255, 60, 60)
ORANGE = (255, 170, 40)


class DemoSerial:
    """Pretends to be the Arduino so you can test the display without hardware."""
    def __init__(self):
        self.angle, self.step, self.next_t, self.t0 = 15, 2, 0.0, time.time()
        self.in_waiting = 0

    def read_lines(self):
        out = []
        now = time.time()
        while now >= self.next_t:
            self.next_t = (self.next_t or now) + 0.045
            t = now - self.t0
            d = 85 + 4 * math.sin(self.angle / 9)                    # back wall
            if 55 < self.angle < 75: d = 42                           # box
            if abs(self.angle - (110 + 30 * math.sin(t / 3))) < 6:    # moving hand
                d = 18
            d = int(d + random.uniform(-1.5, 1.5))
            out.append(f"{self.angle},{d}")
            self.angle += self.step
            if self.angle >= 165 or self.angle <= 15:
                self.step = -self.step
        return out


class SerialReader:
    def __init__(self, port):
        import serial
        self.ser = serial.Serial(port, BAUD, timeout=0)
        self.buf = ""

    def read_lines(self):
        n = self.ser.in_waiting
        if n:
            self.buf += self.ser.read(n).decode(errors="ignore")
        lines = []
        while "\n" in self.buf:
            line, self.buf = self.buf.split("\n", 1)
            lines.append(line.strip())
        return lines


def polar(angle_deg, r_px, mirror):
    a = math.radians(180 - angle_deg if mirror else angle_deg)
    return CX + r_px * math.cos(a), CY - r_px * math.sin(a)


def color_for(d):
    if d < ALERT_CM:
        return RED
    if d < ALERT_CM * 2:
        return ORANGE
    return GREEN


def draw_grid(surf, max_cm, font_small, mirror):
    surf.fill(BG)
    for i in range(1, 5):
        r = RADIUS * i / 4
        pygame.draw.arc(surf, GRID, (CX - r, CY - r, 2 * r, 2 * r), 0, math.pi, 2 if i == 4 else 1)
        label = font_small.render(f"{max_cm * i / 4:.0f} cm", True, GRID)
        surf.blit(label, (CX + r - label.get_width() - 4, CY + 6))
    for a in range(0, 181, 15):
        x, y = polar(a, RADIUS, mirror)
        pygame.draw.aaline(surf, GRID if a % 30 == 0 else GRID_DIM, (CX, CY), (x, y))
        if a % 30 == 0:
            lbl = font_small.render(f"{a}°", True, GRID)
            lx, ly = polar(a, RADIUS + 26, mirror)
            surf.blit(lbl, (lx - lbl.get_width() / 2, ly - lbl.get_height() / 2))
    pygame.draw.line(surf, GRID, (CX - RADIUS - 12, CY), (CX + RADIUS + 12, CY), 2)


def main():
    demo = PORT.lower() == "demo"
    try:
        src = DemoSerial() if demo else SerialReader(PORT)
    except Exception as e:  # serial.SerialException and friends
        print(f"Could not open {PORT}: {e}\nIs the Arduino Serial Monitor still open?")
        return

    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Ultrasonic Radar")
    clock = pygame.time.Clock()
    font_big = pygame.font.SysFont("consolas", 34, bold=True)
    font = pygame.font.SysFont("consolas", 22, bold=True)
    font_small = pygame.font.SysFont("consolas", 16)

    range_idx, mirror = 2, False
    grid = pygame.Surface((W, H))
    draw_grid(grid, RANGES[range_idx], font_small, mirror)
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)

    points = {}                  # angle -> (distance, time seen)
    angle, prev_angle, direction = 90, 90, 1
    last_dist, last_data = -1, 0.0

    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                elif ev.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    range_idx = min(range_idx + 1, len(RANGES) - 1)
                elif ev.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    range_idx = max(range_idx - 1, 0)
                elif ev.key == pygame.K_m:
                    mirror = not mirror
                elif ev.key == pygame.K_c:
                    points.clear()
                elif ev.key == pygame.K_s:
                    name = f"radar_{time.strftime('%Y%m%d_%H%M%S')}.png"
                    pygame.image.save(screen, name)
                    print("saved", name)
                if ev.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS,
                              pygame.K_MINUS, pygame.K_KP_MINUS, pygame.K_m):
                    draw_grid(grid, RANGES[range_idx], font_small, mirror)

        now = time.time()
        for line in src.read_lines():
            try:
                a, d = (int(v) for v in line.split(","))
            except ValueError:
                continue
            if a != angle:
                direction = 1 if a > angle else -1
            prev_angle, angle, last_dist, last_data = angle, a, d, now
            if d > 0:
                points[a] = (d, now)
            else:
                points.pop(a, None)

        max_cm = RANGES[range_idx]
        screen.blit(grid, (0, 0))
        overlay.fill((0, 0, 0, 0))

        # sweep afterglow (fading wedge behind the beam)
        for k in range(28):
            a1 = angle - direction * k * 1.3
            a2 = a1 - direction * 1.3
            alpha = int(110 * (1 - k / 28) ** 1.6)
            pygame.draw.polygon(overlay, (*GREEN, alpha),
                                [(CX, CY), polar(a1, RADIUS, mirror), polar(a2, RADIUS, mirror)])

        # detections: dot + "shadow" line to the edge, fading with age
        closest = None
        for a, (d, seen) in list(points.items()):
            age = now - seen
            if age > FADE_SECONDS:
                del points[a]
                continue
            if d > max_cm:
                continue
            life = 1 - age / FADE_SECONDS
            col = color_for(d)
            r_px = RADIUS * d / max_cm
            p = polar(a, r_px, mirror)
            edge = polar(a, RADIUS, mirror)
            pygame.draw.line(overlay, (*col, int(70 * life)), p, edge, 6)
            pygame.draw.circle(overlay, (*col, int(90 * life)), p, 11)
            pygame.draw.circle(overlay, (*col, int(255 * life)), p, 5)
            if closest is None or d < closest[0]:
                closest = (d, a)

        screen.blit(overlay, (0, 0))
        beam_end = polar(angle, RADIUS, mirror)
        pygame.draw.line(screen, GREEN, (CX, CY), beam_end, 3)
        pygame.draw.circle(screen, GREEN, (CX, CY), 6)

        # HUD
        screen.blit(font_big.render("ULTRASONIC RADAR", True, TEXT), (24, 18))
        dist_txt = f"{last_dist} cm" if last_dist > 0 else "--"
        screen.blit(font.render(f"Angle    {angle:3d}°", True, TEXT), (24, 66))
        screen.blit(font.render(f"Distance {dist_txt}", True, TEXT), (24, 94))
        src_txt = "DEMO MODE" if demo else f"{PORT} @ {BAUD}"
        screen.blit(font_small.render(f"{src_txt}   range {max_cm} cm", True, GRID), (24, 126))
        if closest:
            t = font.render(f"Closest  {closest[0]} cm @ {closest[1]}°", True, color_for(closest[0]))
            screen.blit(t, (W - t.get_width() - 24, 66))
        if 0 < last_dist < ALERT_CM and int(now * 4) % 2 == 0:
            warn = font_big.render(f"!  OBJECT CLOSE  {last_dist} cm  !", True, RED)
            screen.blit(warn, (W / 2 - warn.get_width() / 2, 22))
        if now - last_data > 2:
            ns = font_big.render("NO SIGNAL - check cable / port", True, ORANGE)
            screen.blit(ns, (W / 2 - ns.get_width() / 2, H / 2 - 120))
        help_txt = "+/- range   M mirror   C clear   S screenshot   Esc quit"
        screen.blit(font_small.render(help_txt, True, GRID_DIM), (24, H - 28))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
