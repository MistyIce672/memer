"""
Interactive gesture recorder.

Instead of eyeballing `--debug` numbers, you strike a pose and let the app
figure out which blendshapes distinguish it, then it writes a ready-to-paste
gesture function with tuned thresholds.

    python main.py --record tongue_out

Controls (shown on screen):
    SPACE  capture a sample of the gesture (hold the pose, tap a few times)
    B      capture a "neutral"/baseline sample (relaxed face) — optional but
           strongly recommended; it lets the recorder tell what actually
           changed vs. your resting face.
    C      clear all captured samples and start over
    S      analyze + save the suggested gesture to recordings/NAME.py
    Q/Esc  quit

What it captures: every MediaPipe blendshape score plus the hand count. That
covers face/expression gestures and "N hands up" cases automatically. Gestures
that depend on *where* a hand is (fingertip near chin, etc.) still need a hand-
written distance check — the saved file points that out when it applies.
"""

import config

# Tuning knobs for the suggestion heuristic.
_MIN_ACTIVE = 0.25   # a blendshape must reach at least this in the pose to matter
_MARGIN = 0.15       # ...and beat the baseline by at least this much
_MAX_CONDS = 3       # cap positive conditions so we don't overfit to noise


class GestureRecorder:
    def __init__(self, name):
        self.name = name
        self.samples = []    # list[(blendshapes: dict, num_hands: int, has_face: bool)]
        self.baselines = []

    # --- capture --------------------------------------------------------
    def capture(self, f, baseline=False):
        sample = (dict(f.blendshapes), f.num_hands, f.has_face)
        (self.baselines if baseline else self.samples).append(sample)

    def clear(self):
        self.samples.clear()
        self.baselines.clear()

    # --- on-screen status ----------------------------------------------
    def overlay_lines(self):
        return [
            f"REC gesture: {self.name}",
            f"samples: {len(self.samples)}   baseline: {len(self.baselines)}",
            "SPACE=capture  B=baseline  C=clear  S=save  Q=quit",
        ]

    # --- analysis -------------------------------------------------------
    def _names(self):
        seen = set()
        for bs, _, _ in self.samples + self.baselines:
            seen.update(bs.keys())
        return seen

    def suggest(self):
        """Return (conditions: list[str], notes: list[str])."""
        conds, notes = [], []
        if not self.samples:
            return conds, ["No gesture samples captured — nothing to analyze."]

        base_max = {}  # blendshape -> highest value seen while neutral
        base_min = {}
        for name in self._names():
            b_vals = [bs.get(name, 0.0) for bs, _, _ in self.baselines]
            base_max[name] = max(b_vals) if b_vals else 0.0
            base_min[name] = min(b_vals) if b_vals else 0.0

        scored = []  # (margin, condition_str)
        for name in self._names():
            g_vals = [bs.get(name, 0.0) for bs, _, _ in self.samples]
            g_min, g_max = min(g_vals), max(g_vals)

            # Blendshape that is reliably HIGH during the pose.
            up_margin = g_min - base_max[name]
            if g_min >= _MIN_ACTIVE and up_margin >= _MARGIN:
                thr = round((base_max[name] + g_min) / 2, 2)
                scored.append((up_margin, f'f.blend("{name}") > {thr:.2f}'))
                continue

            # Blendshape reliably LOW during the pose but high when neutral
            # (needs baseline to be meaningful, e.g. mouthPucker < 0.1).
            if self.baselines:
                down_margin = base_min[name] - g_max
                if base_min[name] >= _MIN_ACTIVE and down_margin >= _MARGIN:
                    thr = round((g_max + base_min[name]) / 2, 2)
                    scored.append((down_margin, f'f.blend("{name}") < {thr:.2f}'))

        scored.sort(reverse=True)
        conds = [c for _, c in scored[:_MAX_CONDS]]

        if any('f.blend' in c for c in conds):
            conds.insert(0, "f.has_face")

        # Hand count, if consistently present across the pose.
        min_hands = min(n for _, n, _ in self.samples)
        base_hands = max((n for _, n, _ in self.baselines), default=0)
        if min_hands > 0 and min_hands > base_hands:
            conds.append(f"f.num_hands >= {min_hands}")
            notes.append(
                "This pose uses hands. If the meme depends on *where* the hand "
                "is (e.g. fingertip near chin), add a distance check by hand, "
                "e.g.  dist(f.hands[0].index_tip, f.face_point(152)) < 0.09")

        if not conds:
            notes.append(
                "Couldn't find a distinctive blendshape. Capture more samples, "
                "add baseline frames (B), or the pose may need a hand-position "
                "check written by hand.")
        elif not self.baselines:
            notes.append(
                "No baseline captured — thresholds are rough. Recapture with a "
                "few B (neutral) frames for tighter, more reliable thresholds.")
        return conds, notes

    def render_code(self, conds, priority=25):
        if conds:
            body = "return (\n        " + "\n        and ".join(conds) + "\n    )"
        else:
            body = "return False  # TODO: no distinctive signal found; edit me"
        return (
            f'@gesture("{self.name}", priority={priority})\n'
            f"def {self.name}(f):\n"
            f'    """Recorded gesture."""\n'
            f"    {body}\n"
        )

    def save(self):
        """Analyze, write recordings/NAME.py, return (path, code, notes)."""
        conds, notes = self.suggest()
        code = self.render_code(conds)
        config_line = f'    "{self.name}": "{self.name}.gif",'

        out_dir = config.ROOT / "recordings"
        out_dir.mkdir(exist_ok=True)
        path = out_dir / f"{self.name}.py"

        lines = [
            f"# Recorded gesture: {self.name}",
            f"# samples={len(self.samples)} baseline={len(self.baselines)}",
            "#",
            "# 1) Paste this function into gestures.py:",
            "",
            code,
            "# 2) Add this line to GESTURE_MEMES in config.py",
            "#    (drop matching art into memes/ first):",
            f"#{config_line}",
        ]
        if notes:
            lines.append("#")
            lines.append("# Notes:")
            lines += [f"#   - {n}" for n in notes]
        path.write_text("\n".join(lines) + "\n")
        return path, code, notes
