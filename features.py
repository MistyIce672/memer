"""
Turns raw MediaPipe results into a friendly `Features` object that gesture
detectors can read without touching MediaPipe internals.

Everything is in normalized image coordinates (0..1), so thresholds are
resolution-independent.
"""

from dataclasses import dataclass, field
from math import hypot


@dataclass
class Hand:
    """One detected hand: 21 landmarks as (x, y, z) tuples, plus handedness."""
    landmarks: list          # list[(x, y, z)]
    label: str               # "Left" or "Right" (as seen by the camera)

    # MediaPipe hand landmark indices (see the hand model diagram):
    WRIST = 0
    THUMB_TIP = 4
    INDEX_MCP = 5
    INDEX_TIP = 8
    MIDDLE_MCP = 9
    MIDDLE_TIP = 12
    RING_TIP = 16
    PINKY_TIP = 20

    def point(self, idx):
        return self.landmarks[idx]

    @property
    def index_tip(self):
        return self.landmarks[self.INDEX_TIP]


@dataclass
class Features:
    """All the per-frame data a gesture detector might need."""
    blendshapes: dict = field(default_factory=dict)  # name -> score 0..1
    face: list = field(default_factory=list)          # list[(x, y, z)] or []
    hands: list = field(default_factory=list)         # list[Hand]

    @property
    def has_face(self):
        return bool(self.face)

    @property
    def num_hands(self):
        return len(self.hands)

    def blend(self, name, default=0.0):
        """Blendshape score by name, e.g. blend('jawOpen')."""
        return self.blendshapes.get(name, default)

    def face_point(self, idx):
        return self.face[idx]

    @property
    def face_width(self):
        """Rough normalized face width (cheek to cheek). Used to scale
        distance thresholds so they don't depend on how close you sit."""
        if not self.face:
            return 0.15
        left = self.face[234]   # left cheek
        right = self.face[454]  # right cheek
        return max(abs(left[0] - right[0]), 1e-3)


def dist(a, b):
    """2D Euclidean distance between two (x, y, ...) points."""
    return hypot(a[0] - b[0], a[1] - b[1])


def build_features(face_result, hand_result):
    """Assemble a Features object from MediaPipe Tasks results."""
    f = Features()

    if face_result and face_result.face_landmarks:
        lm = face_result.face_landmarks[0]
        f.face = [(p.x, p.y, p.z) for p in lm]

    if face_result and face_result.face_blendshapes:
        for cat in face_result.face_blendshapes[0]:
            f.blendshapes[cat.category_name] = cat.score

    if hand_result and hand_result.hand_landmarks:
        handedness = hand_result.handedness or []
        for i, lm in enumerate(hand_result.hand_landmarks):
            label = "Right"
            if i < len(handedness) and handedness[i]:
                label = handedness[i][0].category_name
            f.hands.append(Hand(
                landmarks=[(p.x, p.y, p.z) for p in lm],
                label=label,
            ))

    return f
