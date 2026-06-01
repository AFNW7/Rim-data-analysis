from __future__ import annotations


SHOOTING_ACCURACY_CURVE_POINTS: tuple[tuple[float, float], ...] = (
    (-20.0, 0.70),
    (-10.0, 0.80),
    (-6.0, 0.83),
    (-4.0, 0.85),
    (-2.0, 0.87),
    (0.0, 0.89),
    (2.0, 0.93),
    (4.0, 0.94),
    (6.0, 0.95),
    (8.0, 0.96),
    (10.0, 0.97),
    (12.0, 0.975),
    (14.0, 0.98),
    (16.0, 0.98333),
    (18.0, 0.98666),
    (20.0, 0.99),
    (22.0, 0.9925),
    (26.0, 0.995),
    (30.0, 0.9965),
    (40.0, 0.998),
    (60.0, 0.999),
)

LAYER_PRIORITY: dict[str, int] = {
    "overhead": 70,
    "shell": 60,
    "strappedhead": 55,
    "middle": 40,
    "onskin": 20,
    "eyecover": 15,
    "belt": 10,
    "utility": 5,
}

DISTANCE_BANDS: tuple[tuple[int, str], ...] = (
    (3, "close"),
    (12, "short"),
    (25, "medium"),
    (9999, "long"),
)
