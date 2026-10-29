"""Figures + verified numbers for the study guide. Run: uv run python study-guide/scripts/make_figs.py"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "study-guide" / "fig"
sys.path.insert(0, str(ROOT / "src"))
from qcvol.quantum import BornCircuit, paper_probability  # noqa: E402

BLUE, TEAL, AMBER, RED, GREY, INK = "#2b5fa5", "#1a8f84", "#e0a21b", "#c4452d", "#8a8f98", "#1d2430"
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": GREY, "axes.labelcolor": INK, "text.color": INK,
                     "xtick.color": INK, "ytick.color": INK, "figure.dpi": 150, "savefig.bbox": "tight"})
facts = {}


def save(name):
    plt.savefig(OUT / f"{name}.png")
    plt.close()


raw = np.genfromtxt(ROOT / "data/bitstamp_daily.csv", delimiter=",", skip_header=1, dtype=None, encoding=None, usecols=(0, 2))
dates = np.array([r[0] for r in raw], dtype="datetime64[D]")
ylog = np.log(np.array([r[1] for r in raw], float))
facts["n_days"] = len(dates)

# 1. real log-RV history
fig, ax = plt.subplots(figsize=(8, 3))
ax.plot(dates, ylog, color=BLUE, lw=0.6)
roll = np.convolve(ylog, np.ones(30) / 30, mode="valid")
ax.plot(dates[29:], roll, color=AMBER, lw=1.6, label="30-day average")
ax.set_ylabel("log(RV)")
ax.legend(frameon=False)
save("rv_history")

# 2. toy calm vs wild day
rng = np.random.default_rng(3)
t = np.arange(288)
calm = 100 + np.cumsum(rng.normal(0, 0.03, 288))
wild = 100 + np.cumsum(rng.normal(0, 0.25, 288))
wild += calm[-1] - wild[-1]
fig, ax = plt.subplots(figsize=(7.5, 2.8))
ax.plot(t / 12, calm, color=TEAL, label="calm day")
ax.plot(t / 12, wild, color=RED, label="wild day (same ending price)")
ax.set_xlabel("hour of day")
ax.set_ylabel("price (illustration)")
ax.legend(frameon=False)
save("calm_vs_wild")

# 3. market hours
fig, ax = plt.subplots(figsize=(8, 2.4))
for i, d in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
    ax.barh(1, 24, left=24 * i, color=TEAL, edgecolor="white", height=0.5)
    if i < 5:
        ax.barh(0, 6.5, left=24 * i + 9.5, color=AMBER, edgecolor="white", height=0.5)
    ax.text(24 * i + 12, 1.5, d, ha="center", fontsize=10)
ax.set_yticks([0, 1])
ax.set_yticklabels(["US stock market\n(9:30-16:00 ET, Mon-Fri)", "Crypto (24/7)"])
ax.set_xticks([])
ax.spines["bottom"].set_visible(False)
ax.set_ylim(-0.4, 2)
save("market_hours")


# 4. Bloch sphere
def sphere(ax):
    u, v = np.mgrid[0:2 * np.pi:40j, 0:np.pi:20j]
    ax.plot_wireframe(np.cos(u) * np.sin(v), np.sin(u) * np.sin(v), np.cos(v), color="#d5dae1", lw=0.4)
    th = np.linspace(0, 2 * np.pi, 200)
    ax.plot(np.cos(th), np.sin(th), 0, color=GREY, lw=1)
    ax.text(0, 0, 1.3, r"$|0\rangle$", ha="center", fontsize=13)
    ax.text(0, 0, -1.45, r"$|1\rangle$", ha="center", fontsize=13)
    ax.plot([0, 0], [0, 0], [-1.1, 1.1], color=INK, lw=0.8)
    ax.plot([-1.1, 1.1], [0, 0], [0, 0], color=INK, lw=0.5)
    ax.plot([0, 0], [-1.1, 1.1], [0, 0], color=INK, lw=0.5)
    ax.text(1.3, 0, 0, "x", fontsize=10)
    ax.text(0, 1.3, 0, "y", fontsize=10)
    ax.set_axis_off()
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(22, 35)


fig = plt.figure(figsize=(4.4, 4.4))
ax = fig.add_subplot(projection="3d")
sphere(ax)
th, ph = np.radians(55), np.radians(60)
vec = np.array([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th)])
ax.quiver(0, 0, 0, *vec, color=RED, lw=3, arrow_length_ratio=0.12)
ax.plot([vec[0], vec[0]], [vec[1], vec[1]], [0, vec[2]], color=RED, ls=":", lw=1)
ax.plot([0, vec[0]], [0, vec[1]], [0, 0], color=RED, ls=":", lw=1)
tt = np.linspace(0, th, 30)
ax.plot(0.45 * np.sin(tt) * np.cos(ph), 0.45 * np.sin(tt) * np.sin(ph), 0.45 * np.cos(tt), color=AMBER, lw=2)
pp = np.linspace(0, ph, 30)
ax.plot(0.4 * np.cos(pp), 0.4 * np.sin(pp), 0 * pp, color=BLUE, lw=2)
ax.text(0.1, 0.22, 0.55, r"$\theta$", color=AMBER, fontsize=14)
ax.text(0.5, 0.12, 0, r"$\varphi$", color=BLUE, fontsize=14)
save("bloch_basic")

# 5. rotations
fig = plt.figure(figsize=(8.6, 4.2))
ax = fig.add_subplot(121, projection="3d")
sphere(ax)
for a, c in [(0, GREY), (40, AMBER), (90, TEAL), (140, BLUE)]:
    r = np.radians(a)
    ax.quiver(0, 0, 0, np.sin(r), 0, np.cos(r), color=c, lw=2.5, arrow_length_ratio=0.1)
arc = np.linspace(0, np.pi, 60)
ax.plot(np.sin(arc), 0 * arc, np.cos(arc), color=RED, lw=1, ls="--")
ax.set_title(r"$R_Y$: tilts the arrow (height changes)", fontsize=10)
ax = fig.add_subplot(122, projection="3d")
sphere(ax)
r0 = np.radians(55)
for a, c in [(0, GREY), (50, AMBER), (110, TEAL), (200, BLUE)]:
    r = np.radians(a)
    ax.quiver(0, 0, 0, np.sin(r0) * np.cos(r), np.sin(r0) * np.sin(r), np.cos(r0), color=c, lw=2.5, arrow_length_ratio=0.1)
cc = np.linspace(0, 2 * np.pi, 100)
ax.plot(np.sin(r0) * np.cos(cc), np.sin(r0) * np.sin(cc), np.cos(r0) + 0 * cc, color=RED, lw=1, ls="--")
ax.set_title(r"$R_Z$: spins around vertical axis", fontsize=10)
save("rotations")

# 6. P0 vs angle
x = np.linspace(0, np.pi, 200)
fig, ax = plt.subplots(figsize=(6.5, 3))
ax.plot(np.degrees(x), np.cos(x / 2) ** 2, color=BLUE, lw=2)
ax.set_xlabel(r"angle $\theta$ from the north pole (degrees)")
ax.set_ylabel("P(read 0)")
for a in (0, 90, 180):
    ax.scatter([a], [np.cos(np.radians(a) / 2) ** 2], color=RED, zorder=3)
ax.annotate("north pole: always 0", (0, 1), (15, 0.9), fontsize=9)
ax.annotate("equator: 50/50", (90, 0.5), (100, 0.58), fontsize=9)
ax.annotate("south pole: always 1", (180, 0), (95, 0.1), fontsize=9)
save("p0_vs_angle")

# 7. phi is flat, lambda matters (paper model, fitted theta/lambda from the rebuild)
r_, v_ = 0.3, 0.4
theta_, lam_ = -4.5567, 1.6997
phis = np.linspace(0, 2 * np.pi, 100)
p_phi = [paper_probability(np.array([r_]), np.array([v_]), (theta_, p, lam_))[0] for p in phis]
p_lam = [paper_probability(np.array([r_]), np.array([v_]), (theta_, 0.36, l))[0] for l in phis]
fig, ax = plt.subplots(1, 2, figsize=(8, 2.8), sharey=True)
ax[0].plot(phis, p_phi, color=RED, lw=2)
ax[0].set_xlabel(r"$\varphi$ (radians)")
ax[0].set_ylabel("forecast P0")
ax[0].set_title(r"changing $\varphi$: flat line", fontsize=10)
ax[1].plot(phis, p_lam, color=TEAL, lw=2)
ax[1].set_xlabel(r"$\lambda$ (radians)")
ax[1].set_title(r"changing $\lambda$: forecast moves", fontsize=10)
save("phi_flat")
facts["phi_range"] = float(np.ptp(p_phi))
facts["lam_range"] = float(np.ptp(p_lam))

# 8. log loss penalty
p = np.linspace(0.01, 1, 300)
fig, ax = plt.subplots(figsize=(6.2, 3))
ax.plot(p, -np.log(p), color=RED, lw=2)
for q in (0.9, 0.5, 0.1):
    ax.scatter([q], [-np.log(q)], color=INK, zorder=3)
    ax.annotate(f"{-np.log(q):.2f}", (q, -np.log(q)), (q + 0.03, -np.log(q) + 0.15))
ax.set_xlabel("probability you gave to what actually happened")
ax.set_ylabel("penalty  -ln(p)")
save("logloss_curve")
facts["penalty"] = {str(q): float(-np.log(q)) for q in (0.9, 0.5, 0.1, 0.01)}

# 9. four levels on real data (training period)
tr_y = ylog[dates <= np.datetime64("2022-12-31")][30:]
te_y = ylog[dates >= np.datetime64("2025-01-01")]
edges = np.quantile(tr_y, [0.30, 0.70, 0.95])
facts["edges"] = edges.tolist()
cols = [TEAL, BLUE, AMBER, RED]
names = ["calm", "normal", "wild", "extreme"]
fig, ax = plt.subplots(figsize=(7.5, 3))
ax.hist(tr_y, bins=60, color="#cfd6e0")
bounds = [tr_y.min(), *edges, tr_y.max()]
top = ax.get_ylim()[1]
for i in range(4):
    ax.axvspan(bounds[i], bounds[i + 1], color=cols[i], alpha=0.25)
    ax.text((bounds[i] + bounds[i + 1]) / 2, top * 0.92, names[i], ha="center", color=cols[i], fontweight="bold")
for e in edges:
    ax.axvline(e, color=INK, lw=1)
ax.set_xlabel("log(RV) of a day")
ax.set_ylabel("number of days")
save("levels_real")


def lab(v):
    return np.searchsorted(edges, v, side="right")


facts["share_train"] = [float((lab(tr_y) == k).mean()) for k in range(4)]
facts["share_test"] = [float((lab(te_y) == k).mean()) for k in range(4)]

# 10. memory
y = ylog
acf = [np.corrcoef(y[:-k], y[k:])[0, 1] for k in range(1, 61)]
fig, ax = plt.subplots(figsize=(6.5, 3))
ax.bar(range(1, 61), acf, color=BLUE)
ax.set_xlabel("days apart")
ax.set_ylabel("correlation of log RV")
save("memory_acf")
facts["acf"] = {str(k): float(acf[k - 1]) for k in (1, 7, 30, 60)}

# 11. HAR windows
fig, ax = plt.subplots(figsize=(8, 1.9))
ax.set_xlim(-31, 2)
ax.set_ylim(-0.2, 1.7)
ax.axis("off")
ax.barh(0.9, 30, left=-30, height=0.3, color=BLUE, alpha=0.35)
ax.text(-15, 0.9, "average of last 30 days", ha="center", va="center")
ax.barh(0.5, 7, left=-7, height=0.3, color=TEAL, alpha=0.5)
ax.text(-3.5, 0.5, "7-day avg", ha="center", va="center", fontsize=9)
ax.barh(0.1, 1, left=-1, height=0.3, color=AMBER)
ax.text(-2, 0.1, "yesterday", ha="right", va="center", fontsize=9)
ax.barh(0.5, 1, left=0, height=1.1, color=RED, alpha=0.9)
ax.text(0.5, 1.5, "TODAY\n(to predict)", ha="center", fontsize=9, color=RED)
save("har_windows")

# 12. two-qubit output example
c = BornCircuit(3)
prm = np.random.default_rng(5).normal(0, 0.8, c.n_params)
pr = c.probabilities(np.array([[0.4, -0.2, 0.1, 0.6]]), prm)[0]
facts["two_qubit_probs"] = pr.tolist()
facts["two_qubit_params"] = c.n_params
fig, ax = plt.subplots(figsize=(5.2, 2.6))
ax.bar(["|00>\ncalm", "|01>\nnormal", "|10>\nwild", "|11>\nextreme"], pr, color=cols)
ax.set_ylabel("probability")
for i, v in enumerate(pr):
    ax.text(i, v + 0.01, f"{v:.0%}", ha="center")
save("two_qubit_out")

# 13. headline results
fig, ax = plt.subplots(figsize=(7.5, 3))
labels = ["Original paper model", "Quantum v1", "Quantum v2", "Quantum v3", "Classical softmax (v2 inputs)"]
vals = [1.196, 0.5695, 0.529, 0.5145, 0.4962]
ax.barh(labels, vals, color=[GREY, BLUE, BLUE, BLUE, RED])
for i, v in enumerate(vals):
    ax.text(v + 0.01, i, f"{v:.3f}", va="center")
ax.invert_yaxis()
ax.set_xlabel("test log loss, fresh Bitcoin (lower = better)")
save("fresh_results")

(OUT / "facts.json").write_text(json.dumps(facts, indent=1))
print(json.dumps(facts, indent=1))
