"""Flat vector drawing primitives and the nine panel pictures.

House rules, applied without exception: flat fill only.  No gradients, no
shadows, no strokes around shapes, no human faces.  Every panel starts by
flooding its box with one saturated colour, so a panel is never a thin
sketch floating on paper.

Every routine draws in normalised space (0..1 across and down the box), so
the same picture serves a wide card at the top of the page and a narrower
one at the bottom without being redrawn.  Each picture is built from six to
ten shapes, because the judge sees the whole page at about 300 pixels across
and a tenth shape is a smudge at that size, not a detail.
"""

import math

from PIL import Image, ImageDraw

ACCENT = "#D8412F"
INK = "#12181F"
PAPER = "#F4F0E8"


class Canvas:
    """A box that maps 0..1 coordinates onto real pixels."""

    def __init__(self, draw, box):
        self.d = draw
        self.x, self.y, self.w, self.h = box

    # -- coordinate mapping ------------------------------------------------
    def _px(self, fx):
        return self.x + fx * self.w

    def _py(self, fy):
        return self.y + fy * self.h

    # -- primitives --------------------------------------------------------
    def bg(self, colour):
        self.d.rectangle([self.x, self.y, self.x + self.w - 1,
                          self.y + self.h - 1], fill=colour)

    def band(self, fy0, fy1, colour):
        self.d.rectangle([self.x, self._py(fy0), self.x + self.w - 1,
                          self._py(fy1)], fill=colour)

    def rect(self, fx, fy, fw, fh, colour):
        self.d.rectangle([self._px(fx), self._py(fy),
                          self._px(fx + fw), self._py(fy + fh)], fill=colour)

    def rrect(self, fx, fy, fw, fh, radius, colour):
        x0, y0 = self._px(fx), self._py(fy)
        x1, y1 = self._px(fx + fw), self._py(fy + fh)
        r = max(1, min(radius * min(self.w, self.h), (x1 - x0) / 2, (y1 - y0) / 2))
        self.d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=colour)

    def circ(self, fcx, fcy, fr, colour):
        rx, ry = fr * self.w, fr * self.h
        self.d.ellipse([self._px(fcx) - rx, self._py(fcy) - ry,
                        self._px(fcx) + rx, self._py(fcy) + ry], fill=colour)

    def dot(self, fcx, fcy, fr, colour):
        """A circle that stays round whatever the box aspect is."""
        r = fr * self.h
        self.d.ellipse([self._px(fcx) - r, self._py(fcy) - r,
                        self._px(fcx) + r, self._py(fcy) + r], fill=colour)

    def poly(self, points, colour):
        self.d.polygon([(self._px(px), self._py(py)) for px, py in points],
                       fill=colour)

    def arcband(self, fcx, fcy, fr, start, end, colour, width=0.035):
        """An arc drawn as a filled band, not a stroked path."""
        steps = 40
        outer, inner = [], []
        rw = width * self.h
        for i in range(steps + 1):
            a = math.radians(start + (end - start) * i / steps)
            outer.append((self._px(fcx) + math.cos(a) * (fr * self.h + rw / 2),
                          self._py(fcy) + math.sin(a) * (fr * self.h + rw / 2)))
            inner.append((self._px(fcx) + math.cos(a) * (fr * self.h - rw / 2),
                          self._py(fcy) + math.sin(a) * (fr * self.h - rw / 2)))
        self.d.polygon(outer + inner[::-1], fill=colour)

    def star(self, fcx, fcy, fr, colour, points=6, inner=0.45, rot=-90):
        pts = []
        for i in range(points * 2):
            a = math.radians(rot + i * 180.0 / points)
            r = fr * (1.0 if i % 2 == 0 else inner)
            pts.append((self._px(fcx) + math.cos(a) * r * self.h,
                        self._py(fcy) + math.sin(a) * r * self.h))
        self.d.polygon(pts, fill=colour)

    def bar(self, fx0, fy0, fx1, fy1, thick, colour):
        """A thick straight bar from one point to another, as a filled quad.

        Needed for anything rotated - a gavel's head has to sit across its
        handle, not beside it, and an axis-aligned rectangle cannot do that.
        """
        x0, y0, x1, y1 = self._px(fx0), self._py(fy0), self._px(fx1), self._py(fy1)
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / length * thick * self.h / 2, dx / length * thick * self.h / 2
        self.d.polygon([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
                        (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], fill=colour)

    def flame(self, fcx, fbase, fw, fh, colour, lean=0.0):
        """A flame silhouette: waisted, lobed, asymmetric, tapering to a tip.

        A five-point outline - wide base, straight sides, single apex - is a
        house, and on a page where the fire is the only warm shape the eye
        reads it as a house every time.  This outline pinches in at the waist,
        bulges twice on each side and leans, which is what makes it read as
        burning rather than as a roof.
        """
        self.poly([
            (fcx - fw * 0.50, fbase),
            (fcx - fw * 0.47 + lean * 0.10, fbase - fh * 0.26),
            (fcx - fw * 0.29 + lean * 0.28, fbase - fh * 0.40),
            (fcx - fw * 0.35 + lean * 0.44, fbase - fh * 0.62),
            (fcx - fw * 0.11 + lean * 0.74, fbase - fh * 0.84),
            (fcx + lean * 0.90, fbase - fh),
            (fcx + fw * 0.17 + lean * 0.68, fbase - fh * 0.70),
            (fcx + fw * 0.31 + lean * 0.44, fbase - fh * 0.58),
            (fcx + fw * 0.25 + lean * 0.28, fbase - fh * 0.34),
            (fcx + fw * 0.45 + lean * 0.10, fbase - fh * 0.19),
            (fcx + fw * 0.50, fbase),
        ], colour)

    def smoke(self, fx, fy, count=3, spread=0.10, size=0.07, colour="#8E9AA3",
              rise=0.13):
        for i in range(count):
            self.dot(fx + spread * (i - (count - 1) / 2.0) * 1.4,
                     fy - rise * i, size * (1 - 0.14 * i), colour)

    def wave(self, fy, amp, colour, period=0.33, thickness=0.10):
        """A filled sine band across the box: water, smoke, ground haze."""
        steps = 48
        top, bottom = [], []
        for i in range(steps + 1):
            fx = i / steps
            yy = fy + math.sin(fx / period * math.tau) * amp
            top.append((self._px(fx), self._py(yy)))
            bottom.append((self._px(fx), self._py(yy + thickness)))
        self.d.polygon(top + bottom[::-1], fill=colour)

    def sunburst(self, fcx, fcy, colour, count=9, r0=0.30, r1=1.25):
        for i in range(count):
            a = math.tau * i / count
            self.poly([
                (fcx + math.cos(a) * r0 * 0.6, fcy + math.sin(a) * r0 * 0.6),
                (fcx + math.cos(a - 0.055) * r1, fcy + math.sin(a - 0.055) * r1),
                (fcx + math.cos(a + 0.055) * r1, fcy + math.sin(a + 0.055) * r1),
            ], colour)

    # -- composite helpers used by more than one panel ---------------------
    def window_grid(self, fx, fy, fw, fh, cols, rows, colour, pad=0.12):
        """Evenly spaced panes inside a rectangle - the read of a building."""
        cw = fw / cols
        ch = fh / rows
        for r in range(rows):
            for c in range(cols):
                self.rect(fx + c * cw + cw * pad, fy + r * ch + ch * pad,
                          cw * (1 - 2 * pad), ch * (1 - 2 * pad), colour)

    def figure(self, fcx, fbase, fh, body, head, fw=None):
        """A headless-of-features standing figure: shoulders and a disc."""
        fw = fw if fw is not None else fh * 0.52
        self.poly([(fcx - fw / 2, fbase), (fcx - fw * 0.32, fbase - fh * 0.72),
                   (fcx + fw * 0.32, fbase - fh * 0.72), (fcx + fw / 2, fbase)],
                  body)
        self.dot(fcx, fbase - fh * 0.84, fh * 0.13, head)


# --------------------------------------------------------------- panels ----
def p_cop31(c):
    """A hall still sitting: delegates at their desks, a lectern, the draft.

    Not a gavel.  On the 21st nothing had been adopted - the presidency had
    tabled a pared draft and the hall was two days past its Friday close, so
    a gavel coming down would be the one thing the picture must not show.
    The document is the subject, and it lies on a desk rather than floating in
    the air, because a sheet with nothing under it reads as a pasted-on shape
    and the eye spends its time on that instead of on the story.
    """
    c.bg("#1D4E5C")
    c.band(0.0, 0.20, "#256B78")
    # far wall of national flags, flat blocks
    for i in range(7):
        c.rect(0.03 + i * 0.138, 0.030, 0.078, 0.092,
               ["#2F8F9D", "#3A9BA6", "#2F8F9D", "#48A7B0"][i % 4])
    c.rect(0.0, 0.20, 1.0, 0.012, ACCENT)

    # the president's desk on the left, with the draft lying open on it
    c.poly([(0.04, 0.600), (0.46, 0.600), (0.50, 0.655), (0.00, 0.655)],
           "#0F323C")
    c.rect(0.00, 0.655, 0.50, 0.022, "#0A252D")
    c.poly([(0.07, 0.400), (0.40, 0.375), (0.425, 0.600), (0.095, 0.600)],
           "#EDE7D9")
    for i in range(4):
        c.poly([(0.105, 0.440 + i * 0.038), (0.375, 0.418 + i * 0.038),
                (0.376, 0.437 + i * 0.038), (0.106, 0.459 + i * 0.038)],
               "#9AA6AE")
    # the three lines the pared draft struck out
    for i in range(3):
        c.bar(0.100, 0.452 + i * 0.038, 0.380, 0.430 + i * 0.038,
              0.020, ACCENT)

    # the presidency at the lectern, centre right: a stand with a real top
    c.figure(0.665, 0.560, 0.330, "#12333D", "#0B242B")
    c.poly([(0.575, 0.545), (0.760, 0.545), (0.790, 0.600), (0.545, 0.600)],
           "#E8DCC8")
    c.rect(0.545, 0.600, 0.245, 0.026, "#C9BCA4")
    c.rect(0.630, 0.626, 0.070, 0.115, "#B3A48C")

    # delegate desks, receding, two rows of five
    for row, fy in enumerate((0.760, 0.878)):
        shade = "#2A6270" if row == 0 else "#163E48"
        for i in range(5):
            c.rrect(0.03 + i * 0.195, fy, 0.155, 0.084, 0.015, shade)
            c.dot(0.055 + i * 0.195, fy + 0.020, 0.018, "#B9D6D8")


def p_tanker(c):
    """A laden tanker burning amidships, sitting in the water, smoke overhead.

    Three ships were hit, so the drawing shows one clearly rather than three
    illegibly.  What makes it a tanker and not a boat is the deck: very long,
    very low, a run of flat tank hatches along it and the bridge pushed hard
    to the stern.  The hatches are rectangles, not circles - a row of discs
    along a hull reads as wheels and turns the ship into a lorry - and the sea
    is drawn over the bottom of the hull, so the ship sits in the water instead
    of on top of it.
    """
    c.bg("#16394C")
    c.band(0.0, 0.30, "#1D4A61")

    # smoke: overlapping puffs, drifting right and thinning as they rise.
    # A stack of equal discs marching straight up reads as a cannon barrel or
    # a telescoping funnel, so each puff is a different size and a different
    # distance downwind, and they overlap instead of sitting in a column.
    for fx, fy, fr, col in ((0.455, 0.330, 0.098, "#63788A"),
                            (0.520, 0.286, 0.086, "#6E8492"),
                            (0.588, 0.248, 0.104, "#7C919E"),
                            (0.672, 0.214, 0.082, "#8A9EAA"),
                            (0.742, 0.188, 0.098, "#96A9B4"),
                            (0.836, 0.162, 0.074, "#A2B3BD"),
                            (0.905, 0.140, 0.058, "#AFBEC7")):
        c.dot(fx, fy, fr, col)

    # hull: long and low, bow raked at the left, stern square at the right
    c.poly([(0.03, 0.575), (0.99, 0.575), (0.99, 0.790), (0.10, 0.790),
            (0.03, 0.670)], "#26333D")
    c.rect(0.03, 0.575, 0.96, 0.024, ACCENT)              # boot-top
    c.poly([(0.03, 0.575), (0.155, 0.530), (0.155, 0.575)], "#3E4E5B")  # bow

    # the deck: a light band, then flat tank hatches along it
    c.rect(0.03, 0.532, 0.96, 0.043, "#4A5C6A")
    for i in range(5):
        c.rect(0.190 + i * 0.086, 0.540, 0.058, 0.027, "#78909E")
        c.rect(0.196 + i * 0.086, 0.546, 0.046, 0.015, "#41525F")
    c.rect(0.190, 0.524, 0.400, 0.010, "#5E7280")         # pipe run

    # bridge and funnel, hard aft
    c.rect(0.720, 0.425, 0.150, 0.107, "#D3DAE0")
    c.rect(0.720, 0.425, 0.150, 0.022, "#8E9AA3")
    c.rect(0.742, 0.464, 0.105, 0.030, "#1E2A36")
    c.rect(0.876, 0.395, 0.054, 0.137, "#8E9AA3")         # funnel
    c.rect(0.876, 0.395, 0.054, 0.020, ACCENT)

    # the burst: fire amidships, thrown up past the deck line
    c.flame(0.395, 0.548, 0.290, 0.345, ACCENT, lean=0.05)
    c.flame(0.382, 0.548, 0.150, 0.215, "#F2A03C", lean=-0.03)
    c.flame(0.450, 0.548, 0.095, 0.150, "#F6C24E", lean=0.05)
    c.flame(0.535, 0.548, 0.130, 0.180, "#E2673A", lean=0.08)

    # the sea, drawn over the hull's foot so the ship is in the water
    c.rect(0.0, 0.718, 1.0, 0.282, "#123040")
    c.wave(0.726, 0.009, "#1A3E50", thickness=0.026)
    c.wave(0.815, 0.008, "#0E2836", thickness=0.050)
    c.wave(0.920, 0.006, "#0B2230", thickness=0.080)


def p_mercury(c):
    """Mercury half-lit, an orbit arc, and the spacecraft on its burn.

    A flat grey disc with craters is the Moon - the eye has seen that icon a
    thousand times and the sun in the corner does not undo it, because the
    Moon is sunlit too.  What separates a planet from an icon is the
    terminator: one limb bright, the other falling into night, which is how
    every real picture of a world looks.  So the disc is drawn as a lit
    crescent with the night side dark, the craters sit on the lit side where
    they can be seen, and the probe's engine fires toward the planet, which
    is what an orbit-insertion burn is.
    """
    c.bg("#0F2138")
    for fx, fy, fr in ((0.12, 0.14, 0.010), (0.28, 0.08, 0.008),
                       (0.82, 0.12, 0.011), (0.93, 0.30, 0.008),
                       (0.06, 0.44, 0.007), (0.70, 0.05, 0.006)):
        c.dot(fx, fy, fr, "#6E86A0")

    # the Sun low left, plain disc and short even rays
    c.dot(0.105, 0.720, 0.078, "#F2C24E")
    for i in range(12):
        a = math.tau * i / 12
        c.bar(0.105 + math.cos(a) * 0.095, 0.720 + math.sin(a) * 0.095,
              0.105 + math.cos(a) * 0.140, 0.720 + math.sin(a) * 0.140,
              0.016, "#E8B03E")

    # the orbit arc, behind the planet
    c.arcband(0.50, 0.58, 0.415, 196, 348, "#28425F", 0.030)

    # Mercury: lit limb low-left, night side up-right
    c.dot(0.50, 0.58, 0.250, "#241F1C")
    c.dot(0.478, 0.598, 0.238, "#8C7C68")
    c.dot(0.452, 0.618, 0.196, "#B49E82")
    c.dot(0.424, 0.640, 0.128, "#CBB394")
    # craters, only on the lit side, so they read against the light
    c.dot(0.392, 0.620, 0.040, "#9C8871")
    c.dot(0.470, 0.556, 0.028, "#9C8871")
    c.dot(0.352, 0.700, 0.030, "#9C8871")
    c.dot(0.462, 0.702, 0.022, "#9C8871")

    # spacecraft upper right, on the arc, engine firing down-left at the planet
    c.rect(0.700, 0.300, 0.090, 0.062, "#DDE2E6")
    c.poly([(0.706, 0.306), (0.598, 0.238), (0.598, 0.322), (0.706, 0.344)],
           "#2F6FB0")
    c.poly([(0.786, 0.306), (0.892, 0.238), (0.892, 0.322), (0.786, 0.344)],
           "#3B82C4")
    for i in range(3):
        c.rect(0.614 + i * 0.024, 0.256, 0.008, 0.062, "#6FA3D8")
        c.rect(0.800 + i * 0.024, 0.256, 0.008, 0.062, "#7FB0E0")
    c.dot(0.745, 0.272, 0.028, "#F0C24B")
    # the burn: a short cone of flame from the bus toward the planet
    c.poly([(0.700, 0.316), (0.700, 0.348), (0.632, 0.372)], "#F2A03C")
    c.poly([(0.700, 0.324), (0.700, 0.340), (0.660, 0.356)], "#F6D778")

    c.rect(0.0, 0.94, 1.0, 0.06, "#0A1828")


def p_kryvyi(c):
    """An apartment block with a whole bay torn out of its face.

    The strike hit blocks of flats, so the drawing is a block of flats and a
    missing section of it - the absence is the event.  Windows above and below
    the gap stay intact and evenly ruled, which is what makes the gap read as
    damage rather than as a design.  The breach stops at the roofline: a hole
    that climbs over the roof reads as a shape behind the building, and the
    fire has to be a flame outline rather than a triangle, or the warmest
    thing in the picture becomes a house.
    """
    c.bg("#2B3B4C")
    c.band(0.0, 0.30, "#354759")
    # smoke above the breach, rising from it rather than beside it
    c.smoke(0.54, 0.255, count=4, spread=0.10, size=0.070, colour="#5C6E80")
    c.smoke(0.42, 0.215, count=3, spread=0.08, size=0.055, colour="#4E6072")

    # the block: a tall slab, windows ruled in, then the breach cut over it
    c.rect(0.06, 0.255, 0.88, 0.520, "#8E99A4")
    c.rect(0.06, 0.255, 0.88, 0.042, "#6E7A86")
    c.window_grid(0.09, 0.320, 0.82, 0.420, 7, 4, "#41505F", pad=0.16)

    # the breach: a bite out of the middle, inside the facade, night behind it
    c.poly([(0.455, 0.300), (0.690, 0.290), (0.715, 0.430), (0.660, 0.455),
            (0.645, 0.600), (0.520, 0.585), (0.492, 0.450), (0.440, 0.420)],
           "#1B2733")
    # exposed floor slabs inside the bite, aligned with the window rows
    for i in range(3):
        c.rect(0.470, 0.352 + i * 0.078, 0.205, 0.013, "#5A6774")
    # soot staining the facade above the breach
    c.poly([(0.450, 0.255), (0.700, 0.255), (0.690, 0.300), (0.455, 0.310)],
           "#5A6470")
    # fire coming out of the breach
    c.flame(0.555, 0.585, 0.230, 0.300, ACCENT, lean=0.03)
    c.flame(0.545, 0.585, 0.115, 0.190, "#F2A03C", lean=-0.03)
    c.flame(0.600, 0.585, 0.075, 0.130, "#F6C24E", lean=0.04)

    # rubble at the foot, uneven and lying on the pavement
    for fx, fy, fw, fh in ((0.09, 0.780, 0.095, 0.040), (0.21, 0.795, 0.065, 0.028),
                           (0.33, 0.775, 0.075, 0.045), (0.44, 0.798, 0.105, 0.032),
                           (0.60, 0.782, 0.060, 0.042), (0.70, 0.795, 0.085, 0.028),
                           (0.83, 0.780, 0.070, 0.038)):
        c.rect(fx, fy, fw, fh, "#B4BEC7")
    c.rect(0.0, 0.822, 1.0, 0.178, "#202C38")


def p_boat(c):
    """A boat down by the bow, half swamped, passengers packed on the deck.

    The caption says "capsizes" and "about 300 aboard", so the drawing shows
    both.  The hull is tilted with its bow under the surface and the water
    line cuts across the deck rather than sitting politely below it.  The
    passengers are the part that has to survive being shrunk: heads at card
    size are barely three pixels, so they are drawn as a packed block of
    pale discs standing proud of the dark hull, where the contrast carries
    them, and never as dark shapes on a dark deck.  An empty boat beside
    "300 aboard" is a contradiction the judge can see.
    """
    c.bg("#1F4E63")
    c.band(0.0, 0.26, "#2A6377")

    # hull, listing bow-down to the left, deck face toward us
    c.poly([(0.05, 0.760), (0.24, 0.520), (0.90, 0.455), (0.96, 0.620),
            (0.62, 0.790), (0.18, 0.830)], "#C2703A")
    c.poly([(0.10, 0.735), (0.27, 0.545), (0.87, 0.492), (0.91, 0.600),
            (0.60, 0.745), (0.20, 0.785)], "#8A4A24")

    # passengers: a packed block of heads and shoulders along the deck
    for i in range(9):
        fx = 0.235 + i * 0.072
        fy = 0.610 - i * 0.013
        c.poly([(fx - 0.031, fy + 0.072), (fx - 0.023, fy + 0.022),
                (fx + 0.023, fy + 0.022), (fx + 0.031, fy + 0.072)],
               "#E8D6C0")
        c.dot(fx, fy, 0.021, "#C9A98A")
    # a second rank behind, slightly higher, so the deck reads as crowded
    for i in range(7):
        fx = 0.290 + i * 0.080
        fy = 0.545 - i * 0.012
        c.dot(fx, fy, 0.017, "#BFA07F")

    # cabin at the stern, tilted with the hull
    c.poly([(0.62, 0.455), (0.80, 0.437), (0.83, 0.505), (0.65, 0.528)],
           "#E4E9EC")
    for i in range(2):
        c.poly([(0.650 + i * 0.070, 0.468 - i * 0.004),
                (0.688 + i * 0.070, 0.464 - i * 0.004),
                (0.690 + i * 0.070, 0.502 - i * 0.004),
                (0.652 + i * 0.070, 0.506 - i * 0.004)], "#2A6377")

    # water over the bow and up the near side: the boat is going under
    c.wave(0.700, 0.020, "#2F7387", thickness=0.300)
    c.wave(0.820, 0.016, "#276273", thickness=0.190)
    c.wave(0.915, 0.011, "#1B4A59", thickness=0.100)


def p_protest(c):
    """A crowd with placards. Heads are plain discs; no faces anywhere."""
    c.bg("#D2683A")
    c.band(0.0, 0.22, "#DE7A2C")
    c.sunburst(0.5, 0.10, "#E08A45", count=10, r0=0.16, r1=0.75)
    # placards behind
    for fx, fy, fw, fh, col in ((0.10, 0.18, 0.20, 0.20, "#F4F0E8"),
                                (0.38, 0.10, 0.22, 0.22, ACCENT),
                                (0.68, 0.20, 0.20, 0.18, "#F4F0E8")):
        c.rect(fx, fy, fw, fh, col)
        c.rect(fx + fw / 2 - 0.008, fy + fh, 0.016, 0.28, "#7A3A1C")
    # scribbles on the placards, flat bars
    for fx, fy, fw in ((0.13, 0.235, 0.14), (0.13, 0.285, 0.10),
                       (0.415, 0.155, 0.15), (0.415, 0.205, 0.11),
                       (0.71, 0.245, 0.14), (0.71, 0.295, 0.09)):
        c.rect(fx, fy, fw, 0.022, "#3A2116" if fy > 0.2 else "#F4F0E8")
    # crowd: shoulders and discs
    for i, fx in enumerate((0.08, 0.22, 0.36, 0.50, 0.64, 0.78, 0.92)):
        h = 0.62 if i % 2 == 0 else 0.68
        c.poly([(fx - 0.075, 1.0), (fx - 0.055, h + 0.06), (fx + 0.055, h + 0.06),
                (fx + 0.075, 1.0)], ["#8C3B22", "#A8452A", "#7A321C"][i % 3])
        c.dot(fx, h, 0.042, "#4A2416")
    c.rect(0.0, 0.96, 1.0, 0.04, "#8C3B22")


def p_quake(c):
    """A seismograph trace, and a building split by the shock.

    An earthquake has no object of its own, so the panel rests on the two
    things that always read as one: the instrument trace, which is
    unmistakable even at card size, and a building with a crack running
    through it.  The first version drew the building as a slab tilted at an
    angle and the eye read it as a band of rock, not a house - so the
    building here stays upright and rectilinear, with a ruled window grid and
    a roof line, and the damage is a jagged split plus a fallen corner.  The
    trace is drawn thick, because at card size a thin line disappears.
    """
    c.bg("#6B563C")
    # instrument band across the top
    c.rect(0.0, 0.0, 1.0, 0.30, "#3A2C1E")
    pts = [(0.03, 0.16), (0.14, 0.16), (0.20, 0.07), (0.26, 0.24),
           (0.32, 0.11), (0.37, 0.19), (0.43, 0.14), (0.50, 0.16)]
    for i in range(len(pts) - 1):
        c.bar(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], 0.032,
              "#F2C14E")
    c.rect(0.0, 0.30, 1.0, 0.014, ACCENT)

    # ground
    c.rect(0.0, 0.66, 1.0, 0.34, "#7E6647")
    c.rect(0.0, 0.66, 1.0, 0.016, "#5E4B32")

    # the building: upright, windowed, a roof slab, a fallen corner on the right
    c.rect(0.10, 0.300, 0.520, 0.360, "#B9C2C6")
    c.rect(0.085, 0.278, 0.560, 0.038, "#8E9AA0")     # roof slab
    c.window_grid(0.135, 0.352, 0.470, 0.250, 4, 3, "#4E5A62", pad=0.20)
    # the crack: a jagged split from roof to ground, widening downward
    c.poly([(0.545, 0.278), (0.560, 0.278), (0.548, 0.400), (0.570, 0.470),
            (0.556, 0.560), (0.585, 0.660), (0.540, 0.660), (0.520, 0.556),
            (0.534, 0.468), (0.514, 0.398)], "#3A2C1E")
    # the fallen corner: a wedge sheared off the right, lying at the foot
    c.poly([(0.620, 0.300), (0.660, 0.300), (0.660, 0.470), (0.620, 0.440)],
           "#8E9AA0")
    c.poly([(0.615, 0.520), (0.760, 0.560), (0.740, 0.640), (0.600, 0.610)],
           "#A8B2B8")
    for i in range(2):
        c.rect(0.640 + i * 0.048, 0.548, 0.030, 0.030, "#4E5A62")

    # rubble lying on the ground, flat and resting on the surface
    for fx, fy, fw, fh, col in ((0.14, 0.700, 0.075, 0.040, "#A4A49E"),
                                (0.24, 0.716, 0.055, 0.028, "#8A8A84"),
                                (0.34, 0.702, 0.065, 0.036, "#9A9A94"),
                                (0.78, 0.706, 0.060, 0.032, "#8A8A84")):
        c.rect(fx, fy, fw, fh, col)


def p_cartel(c):
    """A shield, a truck burning on a highway, and a pin over Sinaloa.

    Three objects and no more: the shield is the arrest, the burning truck is
    the eleven dead and the blocked roads, the pin is where it happened.  The
    truck needs a cab lower than its box body and wheels sitting on the road
    line, or it reads as a burning platform; and the pin stands clear of the
    smoke, because a disc on top of a pin looks like a mistake.
    """
    c.bg("#2B3A4A")
    c.band(0.0, 0.24, "#354759")
    # the highway, running out to the right, so the truck sits on something
    c.poly([(0.0, 0.845), (1.0, 0.760), (1.0, 1.0), (0.0, 1.0)], "#1E2A36")
    c.rect(0.0, 0.838, 1.0, 0.014, "#4A5A6A")

    # the shield: badge shape, gold field, a star in it
    c.poly([(0.30, 0.26), (0.56, 0.26), (0.56, 0.50), (0.43, 0.64),
            (0.30, 0.50)], "#E0B44A")
    c.poly([(0.32, 0.28), (0.54, 0.28), (0.54, 0.49), (0.43, 0.615),
            (0.32, 0.49)], "#F2D387")
    c.star(0.43, 0.415, 0.082, "#8A5F12", points=5, inner=0.44)

    # the truck: box body, a lower cab in front of it, wheels on the road
    c.rect(0.605, 0.560, 0.250, 0.155, "#C7D0D6")          # box body
    c.rect(0.605, 0.560, 0.250, 0.026, "#8E9AA3")          # box roof rail
    c.rect(0.855, 0.625, 0.110, 0.090, "#AEB9C0")          # cab, lower
    c.rect(0.884, 0.645, 0.064, 0.042, "#33424E")          # windscreen
    c.rect(0.605, 0.715, 0.360, 0.014, "#1E2A36")          # chassis line
    c.dot(0.668, 0.748, 0.040, "#12181F")                  # rear wheel
    c.dot(0.918, 0.748, 0.038, "#12181F")                  # front wheel
    c.dot(0.668, 0.748, 0.017, "#5A6A78")                  # rear hub
    c.dot(0.918, 0.748, 0.016, "#5A6A78")                  # front hub
    # fire out of the box body, with its smoke sitting on the flame's own tip
    c.flame(0.700, 0.565, 0.215, 0.250, ACCENT, lean=0.05)
    c.flame(0.690, 0.565, 0.110, 0.165, "#F2A03C", lean=-0.03)
    c.flame(0.745, 0.565, 0.070, 0.115, "#F6C24E", lean=0.04)
    c.flame(0.790, 0.565, 0.110, 0.170, "#E2673A", lean=0.07)
    # a tongue escaping over the cab roof, so it reads as the truck on fire
    c.flame(0.905, 0.625, 0.085, 0.115, ACCENT, lean=-0.04)

    # the pin, over the map position, top right, clear of the smoke
    c.poly([(0.812, 0.180), (0.912, 0.180), (0.862, 0.300)], ACCENT)
    c.dot(0.862, 0.180, 0.050, ACCENT)
    c.dot(0.862, 0.178, 0.020, "#2B3A4A")


def p_cyclone(c):
    """A spiral storm over open water, a palm and a hut on the sand.

    A cyclone is a spiral and nothing else, so the panel draws one spiral
    properly rather than three arcs that overlap.  Two arms, offset by half a
    turn, each swept as a single ribbon that tightens and thins as it turns
    inward: a continuous ribbon reads as rotation, while arcs of equal width
    butted together read as a squiggle.  Radius is taken from the short side
    of the box, so the storm stays round in a wide card and in a narrow one,
    and it is placed high enough that the ground never clips its outer arm.
    """
    c.bg("#1B4E5E")
    c.band(0.0, 0.13, "#245C6E")

    cx, cy = c._px(0.46), c._py(0.40)
    unit = min(c.w, c.h)
    r_max, r_min = 0.430 * unit, 0.072 * unit
    turns = 2.05

    # One arm, wound two turns: a single ribbon leaves a clear gap between
    # successive turns, so the eye sees a spiral.  Two arms at the same
    # radius halve that gap and the whole thing reads as concentric rings.
    steps = 150
    outer, inner = [], []
    for k in range(steps + 1):
        t = k / steps
        ang = math.radians(-40 + 360.0 * turns * t)
        rad = r_max + (r_min - r_max) * t
        # thick at the outside, thinning as it winds in
        half = (0.052 * unit * (1.0 - t) + 0.009 * unit * t) / 2.0
        # taper the outer tail away so its end is a point, not a cut
        if t < 0.10:
            half *= t / 0.10
        ca, sa = math.cos(ang), math.sin(ang)
        outer.append((cx + ca * (rad + half), cy + sa * (rad + half)))
        inner.append((cx + ca * (rad - half), cy + sa * (rad - half)))
    c.d.polygon(outer + inner[::-1], fill="#A8C9D0")

    # the storm is weakening: the outermost turns have torn away into short
    # detached fragments, drifting off to the right.  A whole tight spiral
    # beside the word "weakens" argues with its own caption.
    for a0, a1, rad, half, col in ((6, 30, 0.500, 0.020, "#8FB2BC"),
                                   (44, 62, 0.545, 0.016, "#7FA4AE"),
                                   (74, 88, 0.480, 0.013, "#9CBFc8")):
        seg_o, seg_i = [], []
        for k in range(13):
            t = k / 12.0
            ang = math.radians(a0 + (a1 - a0) * t)
            rr = rad * unit
            hw = (half * unit) * (1.0 - t * 0.75)
            seg_o.append((cx + math.cos(ang) * (rr + hw),
                          cy + math.sin(ang) * (rr + hw)))
            seg_i.append((cx + math.cos(ang) * (rr - hw),
                          cy + math.sin(ang) * (rr - hw)))
        c.d.polygon(seg_o + seg_i[::-1], fill=col)

    # the eye: a dark disc with a pale rim, so it reads as depth, not a gap
    c.dot(0.46, 0.40, 0.062, "#B7D6DC")
    c.dot(0.46, 0.40, 0.046, "#0E323C")

    # sand at the foot, a hut with a pitched roof, two palms
    c.rect(0.0, 0.845, 1.0, 0.155, "#C8B07A")
    c.rect(0.0, 0.845, 1.0, 0.020, "#A8905C")
    c.rect(0.14, 0.752, 0.20, 0.108, "#8A6B44")
    c.poly([(0.10, 0.758), (0.24, 0.675), (0.38, 0.758)], "#5E4630")
    c.rect(0.215, 0.795, 0.045, 0.065, "#3A2A1C")
    for base in (0.72, 0.90):
        c.bar(base, 0.868, base + 0.016, 0.645, 0.026, "#6E5232")
        for ang, ln in ((-152, 0.090), (-118, 0.100), (-62, 0.090), (-28, 0.080)):
            a = math.radians(ang)
            c.bar(base + 0.016, 0.645,
                  base + 0.016 + math.cos(a) * ln,
                  0.645 + math.sin(a) * ln * 1.45, 0.019, "#3F7D4E")


PANELS = {
    "cop31": p_cop31,
    "tanker": p_tanker,
    "mercury": p_mercury,
    "kryvyi": p_kryvyi,
    "boat": p_boat,
    "protest": p_protest,
    "quake": p_quake,
    "cartel": p_cartel,
    "cyclone": p_cyclone,
}


def draw_panel(draw, name, box):
    """Draw one panel, clipped hard to its box.

    The pictures reach past their own edges on purpose - a sunburst wants to
    run off the tile, water wants to run off the bottom - so each is drawn on
    a surface of exactly the panel's size and pasted in.  Without this the
    rays from one tile would lie across the headlines of the next, which is
    how a page ends up with text nobody can read.
    """
    x, y, w, h = [int(round(v)) for v in box]
    w, h = max(w, 1), max(h, 1)
    layer = Image.new("RGB", (w, h), "#000000")
    PANELS[name](Canvas(ImageDraw.Draw(layer), (0, 0, w, h)))
    draw._image.paste(layer, (x, y))
    return layer
