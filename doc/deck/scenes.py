"""Manim clips embedded in the deck. Render with doc/deck/build.sh."""

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
    Create,
    DashedLine,
    FadeIn,
    FadeOut,
    Line,
    Rectangle,
    Rotate,
    RoundedRectangle,
    Scene,
    Sphere,
    Text,
    ThreeDScene,
    Transform,
    VGroup,
    always_redraw,
    config,
    linear,
    rate_functions,
    smooth,
)

BG = "#0B0B0C"
TEXT = "#ECECEC"
MUTED = "#8C8C93"
LINE = "#2A2A2E"
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
                label(str(t), 18, MUTED).next_to(ax.c2p(t, lo), DOWN, 0.15)
                for t in range(2017, 2027, 2)
            ]
        )
        title = label("Bitcoin, one point per day: how wild was that day?", 30).to_edge(UP, 0.4)
        ylab = label("log realized volatility", 18, MUTED).rotate(np.pi / 2).next_to(ax, LEFT, 0.1)

        pts = [ax.c2p(t, v) for t, v in zip(years, y)]
        trace = VGroup(
            *[Line(a, b, stroke_width=1.1, color=MUTED) for a, b in itertools.pairwise(pts)]
        )

        self.play(FadeIn(title), Create(ax), FadeIn(year_labels), FadeIn(ylab), run_time=1)
        self.play(Create(trace, lag_ratio=1), run_time=4, rate_func=linear)
        self.wait(0.5)

        bounds = [lo, *edges, hi]
        bands = VGroup()
        names = VGroup()
        shares = ["30% of days", "40%", "25%", "5%"]
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
                VGroup(label(LEVELS[i], 22, LEVEL_COLORS[i]), label(shares[i], 16, MUTED))
                .arrange(DOWN, buff=0.05, aligned_edge=LEFT)
                .next_to(band, RIGHT, 0.15)
            )
        sub = label(
            "Four levels, cut at training-period quantiles 30 / 70 / 95%", 22, MUTED
        ).next_to(title, DOWN, 0.15)
        self.play(FadeIn(bands), FadeIn(names, shift=LEFT * 0.2), FadeIn(sub), run_time=1.5)
        self.wait(1)

        week = np.convolve(y, np.ones(30) / 30, mode="valid")
        mpts = [ax.c2p(t, v) for t, v in zip(years[29:], week)]
        month = VGroup(
            *[Line(a, b, stroke_width=3, color=QUANT) for a, b in itertools.pairwise(mpts)]
        )
        memo = label(
            "30-day average: wild days come in clusters (volatility has memory)", 22, QUANT
        ).to_edge(DOWN, 0.25)
        self.play(Create(month, lag_ratio=1), FadeIn(memo), run_time=3, rate_func=linear)
        self.wait(2)


def rot(axis, angle, v):
    c, s = np.cos(angle), np.sin(angle)
    x, y, z = v
    if axis == "y":
        return np.array([c * x + s * z, y, -s * x + c * z])
    return np.array([c * x - s * y, s * x + c * y, z])


class PaperQubit(ThreeDScene):
    """The paper's single qubit on the Bloch sphere, and why phi never matters."""

    def construct(self):
        r, s = 0.2, 0.3  # example inputs (scaled return, variance)
        theta, lam = -4.557, 1.700  # our fitted rebuild parameters (phi = 0.360 has no effect)
        steps = [
            ("y", np.arcsin(r), "RY(arcsin r)", "return enters"),
            ("z", np.arccos(r * r), "RZ(arccos r²)", "return enters"),
            ("y", np.arcsin(2 * s - 1), "RY(arcsin(2σ²−1))", "variance enters"),
            ("z", np.arccos(s * s), "RZ(arccos σ⁴)", "variance enters"),
            ("z", lam, "U3: RZ(λ)", "trainable"),
            ("y", theta, "U3: RY(θ)", "trainable"),
        ]
        R = 2.4
        self.set_camera_orientation(phi=70 * np.pi / 180, theta=30 * np.pi / 180)
        sphere = Sphere(radius=R, resolution=(18, 36)).set_style(
            fill_color="#1A1A1D", fill_opacity=0.18, stroke_color=LINE, stroke_width=0.6
        )
        axes = VGroup(
            Line(-R * 1.15 * RIGHT, R * 1.15 * RIGHT, color=LINE),
            Line(-R * 1.15 * UP, R * 1.15 * UP, color=LINE),
            Line(-R * 1.15 * OUT, R * 1.15 * OUT, color=MUTED),
        )
        top = label("|0⟩", 26, TEXT)
        bot = label("|1⟩", 26, MUTED)
        self.add_fixed_orientation_mobjects(top, bot)
        top.move_to(OUT * (R + 0.45))
        bot.move_to(-OUT * (R + 0.45))

        v = np.array([0.0, 0.0, 1.0])
        arrow = Arrow3D(ORIGIN, R * v, color=QUANT, thickness=0.03)
        drop = always_redraw(
            lambda: DashedLine(
                arrow.get_end(), [0, 0, arrow.get_end()[2]], color=QUANT, stroke_width=2
            )
        )

        title = label("The paper: one qubit, rotated by yesterday's data", 30).to_corner(
            UP + LEFT, 0.4
        )
        gate = label(" ", 28, QUANT).to_corner(DOWN + LEFT, 0.6)
        role = label(" ", 20, MUTED).next_to(gate, UP, 0.15, aligned_edge=LEFT)
        self.add_fixed_in_frame_mobjects(title, gate, role)

        barframe = Rectangle(width=0.5, height=4, stroke_color=LINE).to_edge(RIGHT, 1.2)
        p_label = label("P(0) = tomorrow's\nvolatility forecast", 18, MUTED).next_to(
            barframe, DOWN, 0.2
        )
        self.add_fixed_in_frame_mobjects(barframe, p_label)

        def bar_for(vec):
            p0 = 0.5 + 0.5 * vec[2]
            b = Rectangle(
                width=0.5,
                height=max(4 * p0, 0.01),
                stroke_width=0,
                fill_color=QUANT,
                fill_opacity=0.85,
            )
            b.align_to(barframe, DOWN).align_to(barframe, LEFT)
            t = label(f"{p0:.2f}", 22, QUANT).next_to(barframe, UP, 0.15)
            return VGroup(b, t)

        bar = bar_for(v)
        self.add_fixed_in_frame_mobjects(bar)
        self.play(FadeIn(sphere), FadeIn(axes), FadeIn(title), run_time=1)
        self.add(arrow, drop)
        self.wait(0.4)

        for axis, angle, name, why in steps:
            new_gate = label(name, 28, QUANT).to_corner(DOWN + LEFT, 0.6)
            new_role = label(why, 20, MUTED).next_to(new_gate, UP, 0.15, aligned_edge=LEFT)
            self.add_fixed_in_frame_mobjects(new_gate, new_role)
            self.play(
                FadeOut(gate), FadeOut(role), FadeIn(new_gate), FadeIn(new_role), run_time=0.4
            )
            gate, role = new_gate, new_role
            v = rot(axis, angle, v)
            new_bar = bar_for(v)
            self.add_fixed_in_frame_mobjects(new_bar)
            self.remove(new_bar)
            self.play(
                Rotate(arrow, angle, axis=UP if axis == "y" else OUT, about_point=ORIGIN),
                Transform(bar, new_bar),
                run_time=1.3,
                rate_func=smooth,
            )
            self.wait(0.2)

        last = label("U3: RZ(φ), spin φ freely", 28, BAD).to_corner(DOWN + LEFT, 0.6)
        note = label("P(0) does not move: φ has no effect", 22, BAD).next_to(
            last, UP, 0.15, aligned_edge=LEFT
        )
        self.add_fixed_in_frame_mobjects(last, note)
        self.play(FadeOut(gate), FadeOut(role), FadeIn(last), FadeIn(note), run_time=0.5)
        self.play(
            Rotate(arrow, 2 * np.pi, axis=OUT, about_point=ORIGIN), run_time=4, rate_func=linear
        )
        self.wait(1.5)


class OurForecast(Scene):
    """Our two-qubit model: four inputs in, four level probabilities out, as a nudge on HAR."""

    def construct(self):
        title = label("Ours: two qubits give a probability for each level", 30).to_edge(UP, 0.4)
        inputs = ["yesterday", "last 7 days", "last 30 days", "yesterday's return"]
        chips = (
            VGroup(
                *[
                    RoundedRectangle(
                        corner_radius=0.12,
                        width=2.9,
                        height=0.62,
                        stroke_color=LINE,
                        fill_color="#151517",
                        fill_opacity=1,
                    )
                    for _ in inputs
                ]
            )
            .arrange(DOWN, buff=0.28)
            .to_edge(LEFT, 0.6)
            .shift(DOWN * 0.3)
        )
        chip_text = VGroup(*[label(t, 20).move_to(c) for t, c in zip(inputs, chips)])
        head = label("inputs (log RV averages)", 18, MUTED).next_to(chips, UP, 0.2)

        box = RoundedRectangle(
            corner_radius=0.2,
            width=3.4,
            height=3.3,
            stroke_color=QUANT,
            fill_color="#0F1F1D",
            fill_opacity=1,
        )
        box.next_to(chips, RIGHT, 0.9)
        wires = VGroup(
            *[
                Line(
                    box.get_left() + RIGHT * 0.3 + UP * dy,
                    box.get_right() + LEFT * 0.3 + UP * dy,
                    color=QUANT,
                    stroke_width=2,
                )
                for dy in (0.6, -0.6)
            ]
        )
        box_text = (
            VGroup(label("2 qubits", 24, QUANT), label("inputs re-enter\nevery layer", 16, MUTED))
            .arrange(DOWN, 0.15)
            .move_to(box)
        )
        box_text[0].shift(UP * 0.0)
        arrows_in = VGroup(
            *[
                Arrow(
                    c.get_right(),
                    box.get_left() + UP * (0.9 - 0.6 * i),
                    buff=0.08,
                    color=LINE,
                    stroke_width=2,
                    max_tip_length_to_length_ratio=0.08,
                )
                for i, c in enumerate(chips)
            ]
        )

        base_x = box.get_right()[0] + 1.0
        heights = 3.0
        bars_origin = np.array([base_x, -2.1, 0])

        def bars(p, color_override=None, op=0.9):
            g = VGroup()
            for i, pi in enumerate(p):
                col = color_override or LEVEL_COLORS[i]
                b = Rectangle(
                    width=0.75,
                    height=max(heights * pi, 0.02),
                    stroke_width=0,
                    fill_color=col,
                    fill_opacity=op,
                )
                b.move_to(bars_origin + RIGHT * (0.95 * i + 0.375), aligned_edge=DOWN)
                t = label(f"{pi:.0%}", 18, col).next_to(b, UP, 0.08)
                g.add(VGroup(b, t))
            return g

        names = VGroup(
            *[
                label(n, 18, LEVEL_COLORS[i]).move_to(
                    bars_origin + RIGHT * (0.95 * i + 0.375) + DOWN * 0.3
                )
                for i, n in enumerate(LEVELS)
            ]
        )
        out_arrow = Arrow(
            box.get_right(),
            bars_origin + UP * 1.5 + LEFT * 0.1,
            buff=0.1,
            color=LINE,
            stroke_width=2,
        )

        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(chips), FadeIn(chip_text), FadeIn(head), run_time=0.8)
        self.play(Create(arrows_in), FadeIn(box), Create(wires), FadeIn(box_text), run_time=1.2)

        days = [[0.55, 0.38, 0.06, 0.01], [0.22, 0.51, 0.23, 0.04], [0.05, 0.30, 0.48, 0.17]]
        cur = bars(days[0])
        self.play(Create(out_arrow), FadeIn(names), FadeIn(cur, shift=UP * 0.2), run_time=1)
        cap = label("Illustrative days: calm week → turbulent week", 18, MUTED).to_edge(DOWN, 0.3)
        self.play(FadeIn(cap), run_time=0.4)
        for p in days[1:]:
            self.play(Transform(cur, bars(p)), run_time=1.2)
            self.wait(0.5)
        self.wait(0.8)

        hyb = (
            VGroup(
                label("Hybrid version:", 22, TEXT),
                label("start from classical HAR's probabilities,", 22, CLASS),
                label("let the circuit nudge them by strength γ", 22, QUANT),
                label("γ = 0  →  exactly the classical model", 18, MUTED),
            )
            .arrange(DOWN, aligned_edge=LEFT, buff=0.12)
            .to_corner(DOWN + LEFT, 0.5)
        )
        self.play(
            FadeOut(cap),
            FadeOut(chips),
            FadeOut(chip_text),
            FadeOut(head),
            FadeOut(arrows_in),
            run_time=0.6,
        )
        base = [0.08, 0.36, 0.44, 0.12]
        nudged = [0.06, 0.33, 0.47, 0.14]
        self.play(FadeIn(hyb, shift=UP * 0.2), Transform(cur, bars(base, CLASS, 0.7)), run_time=1)
        self.wait(0.8)
        self.play(
            Transform(cur, bars(nudged)), run_time=1.4, rate_func=rate_functions.ease_in_out_sine
        )
        self.wait(2)


class SealedTest(Scene):
    """Date split for the fresh Bitstamp study, with the test block sealed."""

    def construct(self):
        title = label("One honest split, decided before looking", 30).to_edge(UP, 0.5)
        segs = [
            ("train", "2017 – 2022", 2192, "#52525B", "models learn here"),
            ("validation", "2023 – 2024", 731, CLASS, "pick settings here"),
            ("test", "Jan 2025 – Oct 2026", 657, QUANT, "scored once, at the end"),
        ]
        total = sum(s[2] for s in segs)
        W = 12
        x = -W / 2
        blocks = VGroup()
        texts = VGroup()
        for name, span, n, col, role in segs:
            w = W * n / total
            r = Rectangle(
                width=w - 0.05, height=1.1, stroke_width=0, fill_color=col, fill_opacity=0.85
            )
            r.move_to([x + w / 2, 0.3, 0])
            blocks.add(r)
            texts.add(
                VGroup(
                    label(name, 24, TEXT),
                    label(f"{n:,} days", 18, MUTED),
                    label(span, 16, MUTED),
                    label(role, 16, TEXT if col == "#52525B" else col),
                )
                .arrange(DOWN, buff=0.08, aligned_edge=LEFT)
                .next_to(r, DOWN, 0.25, aligned_edge=LEFT)
            )
            x += w
        self.play(FadeIn(title), run_time=0.5)
        for b, t in zip(blocks, texts):
            self.play(Create(b), FadeIn(t, shift=UP * 0.15), run_time=0.9)
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
            label("SEALED", 26, TEXT),
        ).move_to(blocks[2])
        rules = (
            VGroup(
                label(
                    "Same inputs, data and optimizer budget for quantum and classical models",
                    20,
                    TEXT,
                ),
                label("20 random seeds per model  ·  failed fits are kept, not dropped", 20, MUTED),
            )
            .arrange(DOWN, buff=0.12)
            .to_edge(DOWN, 0.5)
        )
        self.play(FadeIn(seal, scale=1.2), run_time=0.8)
        self.play(FadeIn(rules, shift=UP * 0.2), run_time=0.8)
        self.wait(2)
