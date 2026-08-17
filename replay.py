"""
replay.py — animated race replay using pygame.

Renders an interactive track map with cars moving in real time,
a live leaderboard, a weather panel, and playback controls
(pause/resume, rewind/fast-forward, speed adjustment, restart).

No data-fetching happens here — takes the dict produced by
f1_data.get_race_replay_data().
"""

import bisect

import pygame

WIDTH, HEIGHT = 1200, 720
TRACK_MARGIN = 90
LEADERBOARD_WIDTH = 220

BG_COLOR = (12, 12, 16)
TRACK_COLOR = (90, 90, 100)
TEXT_COLOR = (235, 235, 235)
DIM_TEXT_COLOR = (160, 160, 165)
CAR_RADIUS = 6


class RaceReplay:
    def __init__(self, data: dict, initial_speed: float = 1.0):
        self.data = data
        self.speed = initial_speed
        self.paused = False
        self.current_time = 0.0
        self.max_time = data["max_time"]

        self.screen = None
        self.clock = None
        self.font = None
        self.small_font = None

    # ---- geometry ----

    def _project(self, x: float, y: float) -> tuple[int, int]:
        x_min, x_max = self.data["x_range"]
        y_min, y_max = self.data["y_range"]
        track_w = WIDTH - 2 * TRACK_MARGIN - LEADERBOARD_WIDTH
        track_h = HEIGHT - 2 * TRACK_MARGIN
        x_span = max(x_max - x_min, 1)
        y_span = max(y_max - y_min, 1)
        scale = min(track_w / x_span, track_h / y_span)
        px = TRACK_MARGIN + (x - x_min) * scale
        py = TRACK_MARGIN + (y - y_min) * scale
        return int(px), int(py)

    def _interp_position(self, code: str, t: float):
        track = self.data["driver_tracks"].get(code)
        if not track or not track["t"]:
            return None

        times = track["t"]
        idx = bisect.bisect_left(times, t)

        if idx <= 0:
            return track["x"][0], track["y"][0]
        if idx >= len(times):
            return track["x"][-1], track["y"][-1]

        t0, t1 = times[idx - 1], times[idx]
        frac = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
        x0, x1 = track["x"][idx - 1], track["x"][idx]
        y0, y1 = track["y"][idx - 1], track["y"][idx]
        return x0 + (x1 - x0) * frac, y0 + (y1 - y0) * frac

    # ---- data lookups for a given playback time ----

    def _current_lap_and_position(self, code: str, t: float):
        entries = self.data["driver_laps_info"].get(code, [])
        completed = [e for e in entries if e["end_time"] <= t]

        if completed:
            last = completed[-1]
            total_laps = self.data["total_laps"] or last["lap_number"]
            lap_number = min(last["lap_number"] + 1, total_laps)
            position = last["position"]
        else:
            lap_number = 1
            position = None

        if position is None:
            position = self.data.get("grid_positions", {}).get(code)

        return lap_number, position

    def _current_weather(self, t: float):
        weather = self.data["weather"]
        if not weather:
            return None
        best = weather[0]
        for w in weather:
            if w["t"] <= t:
                best = w
            else:
                break
        return best

    def _standings(self, t: float):
        rows = []
        leader_lap = 0
        for code in self.data["driver_tracks"]:
            lap_num, position = self._current_lap_and_position(code, t)
            leader_lap = max(leader_lap, lap_num or 0)
            rows.append((position if position else 99, code, lap_num))
        rows.sort(key=lambda r: r[0])
        return rows, leader_lap

    # ---- main loop ----

    def run(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(f"{self.data['event_name']} — Race Replay")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 20, bold=True)
        self.small_font = pygame.font.SysFont("arial", 14)

        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            running = self._handle_events()

            if not self.paused:
                self.current_time += dt * self.speed
                if self.current_time >= self.max_time:
                    self.current_time = self.max_time
                    self.paused = True

            self._draw()
            pygame.display.flip()

        pygame.quit()

    def _handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE,):
                    self.paused = not self.paused
                elif event.key == pygame.K_RIGHT:
                    self.current_time = min(self.max_time, self.current_time + 5)
                elif event.key == pygame.K_LEFT:
                    self.current_time = max(0, self.current_time - 5)
                elif event.key == pygame.K_UP:
                    self.speed = min(self.speed * 2, 16)
                elif event.key == pygame.K_DOWN:
                    self.speed = max(self.speed / 2, 0.25)
                elif event.key == pygame.K_r:
                    self.current_time = 0
                    self.paused = False
                elif event.key == pygame.K_ESCAPE:
                    return False
        return True

    # ---- drawing ----

    def _draw(self):
        self.screen.fill(BG_COLOR)
        standings, leader_lap = self._standings(self.current_time)

        self._draw_track()
        self._draw_cars()
        self._draw_hud(leader_lap)
        self._draw_weather()
        self._draw_leaderboard(standings)
        self._draw_controls()

    def _draw_track(self):
        outline = self.data.get("track_outline")
        if not outline or not outline.get("x"):
            return
        points = [self._project(x, y) for x, y in zip(outline["x"], outline["y"])]
        if len(points) > 1:
            pygame.draw.lines(self.screen, TRACK_COLOR, False, points, 4)

    def _draw_cars(self):
        for code, _ in self.data["driver_tracks"].items():
            pos = self._interp_position(code, self.current_time)
            if pos is None:
                continue
            px, py = self._project(*pos)
            color = _hex_to_rgb(self.data["colors"].get(code, "#FFFFFF"))
            pygame.draw.circle(self.screen, color, (px, py), CAR_RADIUS)
            label = self.small_font.render(code, True, TEXT_COLOR)
            self.screen.blit(label, (px + 8, py - 8))

    def _draw_hud(self, leader_lap: int):
        x, y = 20, 20
        total_laps = self.data["total_laps"] or "?"
        lap_text = self.font.render(f"Lap: {leader_lap}/{total_laps}", True, TEXT_COLOR)
        self.screen.blit(lap_text, (x, y))
        y += 28

        time_text = self.small_font.render(
            f"Race Time: {_format_time(self.current_time)} (x{self.speed:g})"
            + ("  [PAUSED]" if self.paused else ""),
            True, DIM_TEXT_COLOR,
        )
        self.screen.blit(time_text, (x, y))

    def _draw_weather(self):
        w = self._current_weather(self.current_time)
        x, y = 20, 90
        title = self.font.render("Weather", True, TEXT_COLOR)
        self.screen.blit(title, (x, y))
        y += 26

        if w:
            lines = [
                f"Track: {w['track_temp']:.1f}°C",
                f"Air: {w['air_temp']:.1f}°C",
                f"Humidity: {w['humidity']:.0f}%",
                f"Wind: {w['wind_speed']:.1f} km/h",
                f"Rain: {'WET' if w['rainfall'] else 'DRY'}",
            ]
            for line in lines:
                text = self.small_font.render(line, True, DIM_TEXT_COLOR)
                self.screen.blit(text, (x, y))
                y += 18

    def _draw_leaderboard(self, standings):
        panel_x = WIDTH - LEADERBOARD_WIDTH + 10
        y = 20
        title = self.font.render("Leaderboard", True, TEXT_COLOR)
        self.screen.blit(title, (panel_x, y))
        y += 30

        for pos, code, lap_num in standings:
            color = _hex_to_rgb(self.data["colors"].get(code, "#FFFFFF"))
            pos_str = str(pos) if pos != 99 else "-"
            line = self.small_font.render(f"{pos_str}. {code}", True, color)
            self.screen.blit(line, (panel_x, y))
            y += 20

    def _draw_controls(self):
        lines = [
            "Controls:",
            "[SPACE] Pause/Resume",
            "[←/→]  Rewind/Fast-forward",
            "[↑/↓]  Speed +/-",
            "[R]     Restart",
        ]
        y = HEIGHT - 18 * len(lines) - 15
        for line in lines:
            text = self.small_font.render(line, True, DIM_TEXT_COLOR)
            self.screen.blit(text, (20, y))
            y += 18


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return (255, 255, 255)
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _format_time(t: float) -> str:
    m = int(t // 60)
    s = int(t % 60)
    return f"{m:02d}:{s:02d}"


def run_replay(data: dict, initial_speed: float = 1.0):
    """Launch the interactive replay window. Blocks until the window is closed."""
    RaceReplay(data, initial_speed).run()