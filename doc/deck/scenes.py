"""Manim clips for the deck, exported as looping GIFs. Render with doc/deck/build_clips.sh."""

import csv
import itertools
from pathlib import Path

import numpy as np
from manim import (
    DOWN,
    LEFT,
    ORIGIN,
    OUT,
    RIGHT,
    UP,
    Arrow,
    Arrow3D,
    Axes,
    Circle,
    Create,
    DashedLine,
    FadeIn,
    FadeOut,
    GrowFromEdge,
    Line,
    Rectangle,
    Rotate,
    RoundedRectangle,
    Scene,
    Sphere,
    Text,
    ThreeDScene,
    Transform,
    ValueTracker,
    VGroup,
    always_redraw,
    config,
    linear,
    smooth,
)

BG = "#0B0B0C"
TEXT = "#ECECEC"
MUTED = "#8C8C93"
LINE = "#2A2A2E"
CARD = "#151517"
QUANT = "#2DD4BF"
CLASS = "#F5B544"
BAD = "#F87171"
LEVELS = ["calm", "normal", "wild", "extreme"]
LEVEL_COLORS = ["#9CA3AF", "#E5E7EB", CLASS, BAD]
FONT = "Liberation Sans"

config.background_color = BG
DATA = Path(__file__).resolve().parents[2] / "data" / "bitstamp_daily.csv"


def label(s, size=28, color=TEXT, **kw):
    return Text(s, font=FONT, font_size=size, color=color, **kw)


def load_log_rv():
    with DATA.open() as f:
        rows = list(csv.DictReader(f))
    dates = np.array([np.datetime64(r["date"]) for r in rows])
    rv = np.array([float(r["rv"]) for r in rows])
    keep = rv > 0
    return dates[keep], np.log(rv[keep])


def polyline(points, **kw):
    return VGroup(*[Line(a, b, **kw) for a, b in itertools.pairwise(points)])


class VolatilityLevels(Scene):
    """Real Bitstamp BTC log realized volatility, its four levels, and its memory."""

    def construct(self):
        dates, y = load_log_rv()
        years = 2016 + (dates - np.datetime64("2016-01-01")).astype(int) / 365.25
        train = (dates >= np.datetime64("2016-12-31")) & (dates <= np.datetime64("2022-12-31"))
        edges = np.quantile(y[train], [0.30, 0.70, 0.95])
        lo, hi = np.floor(y.min()), np.ceil(y.max())

        ax = Axes(
            x_range=[2017, 2027, 1],
            y_range=[lo, hi, 2],
            x_length=10.6,
            y_length=5,
            axis_config={"color": LINE, "include_ticks": False, "include_tip": False},
        ).shift(DOWN * 0.4 + LEFT * 0.5)
        year_labels = VGroup(
            *[
                label(str(t), 20, MUTED).next_to(ax.c2p(t, lo), DOWN, 0.15)
                for t in range(2017, 2027, 2)
            ]
        )
        title = label("Ten years of Bitcoin. Each spike is one shaky day.", 30).to_edge(UP, 0.4)
        ylab = label("calmer  →  shakier", 20, MUTED).rotate(np.pi / 2).next_to(ax, LEFT, 0.15)

        trace = polyline(
            [ax.c2p(t, v) for t, v in zip(years, y, strict=True)], stroke_width=1.1, color=MUTED
        )
        self.add(title, ax, year_labels, ylab)
        self.wait(0.5)
        self.play(Create(trace, lag_ratio=1), run_time=5, rate_func=linear)
        self.wait(0.6)

        bounds = [lo, *edges, hi]
        bands, names = VGroup(), VGroup()
        shares = ["3 in 10 days", "4 in 10", "1 in 4", "1 in 20"]
        for i in range(4):
            a, b = ax.c2p(2017, bounds[i]), ax.c2p(2027, bounds[i + 1])
            band = Rectangle(
                width=b[0] - a[0],
                height=b[1] - a[1],
                stroke_width=0,
                fill_color=LEVEL_COLORS[i],
                fill_opacity=0.13,
            ).move_to((a + b) / 2)
            bands.add(band)
            names.add(
                VGroup(label(LEVELS[i], 24, LEVEL_COLORS[i]), label(shares[i], 17, MUTED))
                .arrange(DOWN, buff=0.05, aligned_edge=LEFT)
                .next_to(band, RIGHT, 0.15)
            )
        sub = label("We sort every day into four kinds of weather", 24, MUTED).next_to(
            title, DOWN, 0.15
        )
        self.play(FadeIn(bands), FadeIn(names, shift=LEFT * 0.2), FadeIn(sub), run_time=1.5)
        self.wait(1.2)

        month = np.convolve(y, np.ones(30) / 30, mode="valid")
        smooth_line = polyline(
            [ax.c2p(t, v) for t, v in zip(years[29:], month, strict=True)],
            stroke_width=3.5,
            color=QUANT,
        )
        memo = label("Storms cluster: shaky weeks tend to follow shaky weeks", 24, QUANT).to_edge(
            DOWN, 0.25
        )
        self.play(Create(smooth_line, lag_ratio=1), FadeIn(memo), run_time=3.5, rate_func=linear)
        self.wait(3)


def rot(axis, angle, v):
    c, s = np.cos(angle), np.sin(angle)
    x, y, z = v
    if axis == "y":
        return np.array([c * x + s * z, y, -s * x + c * z])
    return np.array([c * x - s * y, s * x + c * y, z])


# One example day (scaled return r, variance s) and our fitted rebuild angles.
R_EX, S_EX = 0.5, 0.8
THETA, LAM = -4.557, 1.700
STEPS = [
    ("y", np.arcsin(R_EX), "RY(arcsin r)", "yesterday's return tips the arrow"),
    ("z", np.arccos(R_EX**2), "RZ(arccos r²)", "...and swings it around"),
    ("y", np.arcsin(2 * S_EX - 1), "RY(arcsin(2σ²−1))", "yesterday's volatility tips it"),
    ("z", np.arccos(S_EX**2), "RZ(arccos σ⁴)", "...and swings it again"),
    ("z", LAM, "U3: λ", "the learned turn, part 1"),
    ("y", THETA, "U3: θ", "the learned turn, part 2"),
]


class BlochBase(ThreeDScene):
    R = 2.4

    def setup_sphere(self, title_text):
        R = self.R
        self.set_camera_orientation(phi=68 * np.pi / 180, theta=25 * np.pi / 180)
        sphere = Sphere(radius=R, resolution=(16, 32)).set_style(
            fill_color="#1A1A1D", fill_opacity=0.15, stroke_color=LINE, stroke_width=0.6
        )
        axes = VGroup(
            Line(-R * 1.15 * RIGHT, R * 1.15 * RIGHT, color=LINE),
            Line(-R * 1.15 * UP, R * 1.15 * UP, color=LINE),
            Line(-R * 1.15 * OUT, R * 1.15 * OUT, color=MUTED),
        )
        top, bot = label("0", 28, TEXT), label("1", 28, MUTED)
        self.add_fixed_orientation_mobjects(top, bot)
        top.move_to(OUT * (R + 0.4))
        bot.move_to(-OUT * (R + 0.4))
        title = label(title_text, 30).to_corner(UP + LEFT, 0.4)
        self.add_fixed_in_frame_mobjects(title)
        self.frame_box = Rectangle(width=0.55, height=4, stroke_color=LINE).to_edge(RIGHT, 1.3)
        cap = label("chance of\nreading 0", 20, MUTED).next_to(self.frame_box, DOWN, 0.2)
        self.add_fixed_in_frame_mobjects(self.frame_box, cap)
        return VGroup(sphere, axes, title, cap)

    def bar_for(self, vec):
        p0 = 0.5 + 0.5 * vec[2]
        b = Rectangle(
            width=0.55,
            height=max(4 * p0, 0.01),
            stroke_width=0,
            fill_color=QUANT,
            fill_opacity=0.85,
        )
        b.align_to(self.frame_box, DOWN).align_to(self.frame_box, LEFT)
        t = label(f"{p0:.0%}", 24, QUANT).next_to(self.frame_box, UP, 0.15)
        return VGroup(b, t)

    def swap_fixed(self, old, new, run_time=0.4):
        self.play(*[FadeOut(m) for m in old], run_time=run_time / 2)
        self.add_fixed_in_frame_mobjects(*new)
        self.play(*[FadeIn(m) for m in new], run_time=run_time / 2)
        return new


class PaperQubit(BlochBase):
    """The paper's single qubit on the Bloch sphere: yesterday's data turns the arrow."""

    def construct(self):
        frame = self.setup_sphere("Yesterday's market turns the arrow")
        v = np.array([0.0, 0.0, 1.0])
        arrow = Arrow3D(ORIGIN, self.R * v, color=QUANT, thickness=0.035)
        drop = always_redraw(
            lambda: DashedLine(
                arrow.get_end(), [0, 0, arrow.get_end()[2]], color=QUANT, stroke_width=2
            )
        )
        bar = self.bar_for(v)
        self.add_fixed_in_frame_mobjects(bar)
        self.add(frame)
        self.add(arrow, drop)
        self.wait(0.6)

        texts = [label(" ", 10)]
        for axis, angle, name, why in STEPS:
            g = label(name, 30, QUANT).to_corner(DOWN + LEFT, 0.6)
            w = label(why, 24, TEXT).next_to(g, UP, 0.15, aligned_edge=LEFT)
            texts = self.swap_fixed(texts, [g, w])
            v = rot(axis, angle, v)
            new_bar = self.bar_for(v)
            self.add_fixed_in_frame_mobjects(new_bar)
            self.remove(new_bar)
            self.play(
                Rotate(arrow, angle, axis=UP if axis == "y" else OUT, about_point=ORIGIN),
                Transform(bar, new_bar),
                run_time=1.8,
                rate_func=smooth,
            )
            self.wait(0.3)

        end = label("Where the arrow points = tomorrow's forecast", 26, QUANT).to_corner(
            DOWN + LEFT, 0.6
        )
        self.swap_fixed(texts, [end], run_time=0.6)
        self.wait(3)


class PhiSpin(BlochBase):
    """Turning phi spins the arrow around the vertical axis, so the forecast never changes."""

    def construct(self):
        frame = self.setup_sphere("The third dial, φ, spins the arrow sideways")
        v = np.array([0.0, 0.0, 1.0])
        for axis, angle, _, _ in STEPS:
            v = rot(axis, angle, v)
        arrow = Arrow3D(ORIGIN, self.R * v, color=QUANT, thickness=0.035)
        z = self.R * v[2]
        ring = Circle(radius=self.R * np.hypot(v[0], v[1]), color=BAD, stroke_width=2).shift(
            OUT * z
        )
        drop = always_redraw(
            lambda: DashedLine(
                arrow.get_end(), [0, 0, arrow.get_end()[2]], color=QUANT, stroke_width=2
            )
        )
        bar = self.bar_for(v)
        self.add_fixed_in_frame_mobjects(bar)
        self.add(frame)
        self.add(arrow, drop)
        self.play(Create(ring), run_time=1)
        note = label("Its height never changes, so neither does the forecast", 26, BAD).to_corner(
            DOWN + LEFT, 0.6
        )
        self.add_fixed_in_frame_mobjects(note)
        self.play(FadeIn(note), run_time=0.5)
        self.play(
            Rotate(arrow, 2 * np.pi, axis=OUT, about_point=ORIGIN), run_time=6, rate_func=linear
        )
        self.wait(2)


class OurForecast(Scene):
    """Our two-qubit model: four inputs in, a probability for each level out."""

    def construct(self):
        title = label("Our version gives a forecast like a weather report", 30).to_edge(UP, 0.4)
        inputs = ["yesterday", "the last week", "the last month", "yesterday's price move"]
        chips = (
            VGroup(
                *[
                    RoundedRectangle(
                        corner_radius=0.12,
                        width=3.4,
                        height=0.66,
                        stroke_color=LINE,
                        fill_color=CARD,
                        fill_opacity=1,
                    )
                    for _ in inputs
                ]
            )
            .arrange(DOWN, buff=0.28)
            .to_edge(LEFT, 0.5)
            .shift(DOWN * 0.3)
        )
        chip_text = VGroup(*[label(t, 22).move_to(c) for t, c in zip(inputs, chips, strict=True)])
        head = label("what it looks at", 20, MUTED).next_to(chips, UP, 0.2)

        box = RoundedRectangle(
            corner_radius=0.2,
            width=2.8,
            height=3.0,
            stroke_color=QUANT,
            fill_color="#0F1F1D",
            fill_opacity=1,
        ).next_to(chips, RIGHT, 0.8)
        wires = VGroup(
            *[
                Line(
                    box.get_left() + RIGHT * 0.3 + UP * dy,
                    box.get_right() + LEFT * 0.3 + UP * dy,
                    color=QUANT,
                )
                for dy in (0.7, -0.7)
            ]
        )
        box_text = label("2 qubits", 26, QUANT).move_to(box)
        arrows_in = VGroup(
            *[
                Arrow(
                    c.get_right(),
                    box.get_left() + UP * (0.9 - 0.6 * i),
                    buff=0.08,
                    color=LINE,
                    stroke_width=2,
                )
                for i, c in enumerate(chips)
            ]
        )
        origin = np.array([box.get_right()[0] + 0.9, -2.0, 0])

        def bars(p):
            g = VGroup()
            for i, pi in enumerate(p):
                b = Rectangle(
                    width=0.8,
                    height=max(3.2 * pi, 0.02),
                    stroke_width=0,
                    fill_color=LEVEL_COLORS[i],
                    fill_opacity=0.9,
                )
                b.move_to(origin + RIGHT * (1.0 * i + 0.4), aligned_edge=DOWN)
                g.add(VGroup(b, label(f"{pi:.0%}", 20, LEVEL_COLORS[i]).next_to(b, UP, 0.08)))
            return g

        names = VGroup(
            *[
                label(n, 20, LEVEL_COLORS[i]).move_to(origin + RIGHT * (1.0 * i + 0.4) + DOWN * 0.3)
                for i, n in enumerate(LEVELS)
            ]
        )
        out_arrow = Arrow(
            box.get_right(), origin + UP * 1.4 + LEFT * 0.1, buff=0.1, color=LINE, stroke_width=2
        )

        self.add(title)
        self.play(FadeIn(chips), FadeIn(chip_text), FadeIn(head), run_time=0.8)
        self.play(Create(arrows_in), FadeIn(box), Create(wires), FadeIn(box_text), run_time=1.2)
        days = [[0.55, 0.38, 0.06, 0.01], [0.22, 0.51, 0.23, 0.04], [0.05, 0.30, 0.48, 0.17]]
        captions = ["a quiet week", "things are picking up", "a stormy week"]
        cur = bars(days[0])
        cap = label(f"Example: {captions[0]}", 22, MUTED).to_edge(DOWN, 0.3)
        self.play(
            Create(out_arrow), FadeIn(names), FadeIn(cur, shift=UP * 0.2), FadeIn(cap), run_time=1
        )
        self.wait(1)
        for p, c in zip(days[1:], captions[1:], strict=True):
            new_cap = label(f"Example: {c}", 22, MUTED).to_edge(DOWN, 0.3)
            self.play(Transform(cur, bars(p)), Transform(cap, new_cap), run_time=1.4)
            self.wait(1)
        self.wait(2)


class HybridNudge(Scene):
    """Hybrid: classical HAR probabilities, nudged by the circuit with strength gamma."""

    def construct(self):
        title = label("The hybrid: a classical forecast with a quantum second opinion", 30).to_edge(
            UP, 0.4
        )
        base = np.array([0.08, 0.36, 0.44, 0.12])
        q = np.array([0.02, 0.18, 0.55, 0.25])
        gamma = ValueTracker(0.0)
        origin = np.array([-2.6, -2.2, 0])

        def probs():
            logits = np.log(base) + gamma.get_value() * (q - 0.25)
            e = np.exp(logits - logits.max())
            return e / e.sum()

        def bars():
            p = probs()
            g = VGroup()
            for i, pi in enumerate(p):
                col = CLASS if gamma.get_value() < 0.05 else LEVEL_COLORS[i]
                b = Rectangle(
                    width=1.0,
                    height=max(5.2 * pi, 0.02),
                    stroke_width=0,
                    fill_color=col,
                    fill_opacity=0.9,
                )
                b.move_to(origin + RIGHT * (1.3 * i + 0.5), aligned_edge=DOWN)
                g.add(b)
            return g

        names = VGroup(
            *[
                label(n, 22, LEVEL_COLORS[i]).move_to(
                    origin + RIGHT * (1.3 * i + 0.5) + DOWN * 0.35
                )
                for i, n in enumerate(LEVELS)
            ]
        )
        live = always_redraw(bars)
        dial_line = Line(RIGHT * 3.0, RIGHT * 6.0, color=LINE, stroke_width=6).shift(DOWN * 0.2)
        knob = always_redraw(
            lambda: Circle(radius=0.16, color=QUANT, fill_opacity=1).move_to(
                dial_line.point_from_proportion(gamma.get_value() / 6)
            )
        )
        dial_lab = label("quantum nudge, γ", 22, QUANT).next_to(dial_line, UP, 0.35)
        ends = VGroup(
            label("off", 18, MUTED).next_to(dial_line, DOWN, 0.25, aligned_edge=LEFT),
            label("strong", 18, MUTED).next_to(dial_line, DOWN, 0.25, aligned_edge=RIGHT),
        )
        cap0 = label("Dial at zero: exactly the classical forecast", 24, CLASS).to_edge(DOWN, 0.35)
        self.add(title, live, names)
        self.play(
            Create(dial_line),
            FadeIn(knob),
            FadeIn(dial_lab),
            FadeIn(ends),
            FadeIn(cap0),
            run_time=0.8,
        )
        self.wait(1.5)
        cap1 = label(
            "Turn it up: the circuit shifts the odds where it disagrees", 24, QUANT
        ).to_edge(DOWN, 0.35)
        self.play(Transform(cap0, cap1), run_time=0.5)
        self.play(gamma.animate.set_value(4.5), run_time=3, rate_func=smooth)
        self.wait(1)
        cap2 = label("Training decides how far to turn it", 24, TEXT).to_edge(DOWN, 0.35)
        self.play(Transform(cap0, cap2), gamma.animate.set_value(2.0), run_time=1.5)
        self.wait(2.5)


class SealedTest(Scene):
    """Date split for the fresh Bitstamp study, with the test block sealed."""

    def construct(self):
        title = label("We locked the final exam away before we started", 30).to_edge(UP, 0.5)
        segs = [
            ("learn", "2017 – 2022", 2192, "#52525B", "models study here"),
            ("tune", "2023 – 2024", 731, CLASS, "we pick settings here"),
            ("final exam", "2025 – 2026", 657, QUANT, "opened once, at the end"),
        ]
        total = sum(s[2] for s in segs)
        W = 12
        x = -W / 2
        blocks, texts = VGroup(), VGroup()
        for name, span, n, col, role in segs:
            w = W * n / total
            r = Rectangle(
                width=w - 0.05, height=1.1, stroke_width=0, fill_color=col, fill_opacity=0.85
            )
            r.move_to([x + w / 2, 0.4, 0])
            blocks.add(r)
            texts.add(
                VGroup(
                    label(name, 26, TEXT),
                    label(span, 18, MUTED),
                    label(role, 18, TEXT if col == "#52525B" else col),
                )
                .arrange(DOWN, buff=0.08, aligned_edge=LEFT)
                .next_to(r, DOWN, 0.25, aligned_edge=LEFT)
            )
            x += w
        self.add(title)
        for b, t in zip(blocks, texts, strict=True):
            self.play(GrowFromEdge(b, LEFT), FadeIn(t, shift=UP * 0.15), run_time=1.0)
        seal = VGroup(
            RoundedRectangle(
                corner_radius=0.1,
                width=blocks[2].width,
                height=1.1,
                stroke_color=TEXT,
                stroke_width=3,
                fill_color=BG,
                fill_opacity=0.75,
            ),
            label("LOCKED", 28, TEXT),
        ).move_to(blocks[2])
        rule = label(
            "Every model, quantum or classical, gets exactly the same treatment", 22, TEXT
        ).to_edge(DOWN, 0.6)
        self.play(FadeIn(seal, scale=1.2), run_time=0.8)
        self.play(FadeIn(rule, shift=UP * 0.2), run_time=0.8)
        self.wait(3)


class ResultsRace(Scene):
    """Mean test log loss on fresh Bitcoin: the paper's model, ours, and the best classical rival."""

    def construct(self):
        title = label("How wrong was each forecaster? Shorter is better.", 30).to_edge(UP, 0.5)
        rows = [
            ("the paper's model", 1.196, MUTED, "where we started"),
            ("our quantum model", 0.570, QUANT, "about half the error"),
            ("quantum + classical hybrid", 0.545, QUANT, "a little better again"),
            ("best classical model", 0.518, CLASS, "still the winner"),
        ]
        x0, scale = -2.6, 7.0
        self.add(title)
        for i, (name, v, col, note) in enumerate(rows):
            y = 1.6 - i * 1.25
            lab = label(name, 24, TEXT if col != MUTED else MUTED).move_to(
                [x0 - 0.25, y, 0], aligned_edge=RIGHT
            )
            bar = Rectangle(
                width=scale * v / 1.2, height=0.6, stroke_width=0, fill_color=col, fill_opacity=0.9
            )
            bar.move_to([x0, y, 0], aligned_edge=LEFT)
            tag = label(note, 20, col).next_to(bar, RIGHT, 0.25)
            self.play(FadeIn(lab), GrowFromEdge(bar, LEFT), run_time=1.1)
            self.play(FadeIn(tag), run_time=0.4)
            self.wait(0.8)
        foot = label("Average over 20 runs on the 657 locked test days", 20, MUTED).to_edge(
            DOWN, 0.5
        )
        self.play(FadeIn(foot), run_time=0.6)
        self.wait(3)


class CalmVsWild(Scene):
    """Still image: two illustrative days with the same start and finish but very different shaking."""

    def construct(self):
        rng = np.random.default_rng(7)
        n = 288
        panels = VGroup()
        for i, (name, sigma, col) in enumerate(
            [("a calm day", 0.15, MUTED), ("a wild day", 1.0, BAD)]
        ):
            steps = rng.standard_normal(n) * sigma
            path = np.concatenate([[0], np.cumsum(steps)])
            path -= np.linspace(0, path[-1], n + 1)  # same start and finish
            ax = Axes(
                x_range=[0, n, n],
                y_range=[-14, 14, 7],
                x_length=5.6,
                y_length=3.6,
                axis_config={"color": LINE, "include_ticks": False, "include_tip": False},
            )
            line = polyline([ax.c2p(t, v) for t, v in enumerate(path)], stroke_width=2.5, color=col)
            panel = VGroup(ax, line, label(name, 30, col).next_to(ax, UP, 0.3))
            panel.shift(RIGHT * (3.4 if i else -3.4))
            panels.add(panel)
        foot = label(
            "Same opening price, same closing price. Very different day.", 26, TEXT
        ).to_edge(DOWN, 0.6)
        self.add(panels, foot)
