// Builds doc/IEG313_Schrodingers_Cat_Presentation_v2.pptx. Run doc/deck/build.sh.
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const HERE = __dirname;
const OUT = path.join(HERE, "..", "IEG313_Schrodingers_Cat_Presentation_v2.pptx");
const CLIPS = path.join(HERE, "media", "clips");
const CIRC = path.join(HERE, "circuits");
const LOGO = path.join(HERE, "..", "..", "report", "assets", "iiitk-logo.jpg");

const BG = "0B0B0C", CARD = "151517", LINE = "2A2A2E", TEXT = "ECECEC", MUTED = "8C8C93";
const QUANT = "2DD4BF", CLASS = "F5B544", BAD = "F87171";
const FONT = "Arial";
const W = 13.333, H = 7.5, M = 0.6;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "Quantum Volatility Range Forecaster";
pres.author = "Schrodinger's Cat";
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: BG },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.4, w: W - 2 * M, h: 0.9, fontSize: 34, bold: true, color: TEXT, fontFace: FONT, valign: "top", align: "left", margin: 0 }, text: "" } },
    { text: { text: "Schrödinger's Cat · IEG313", options: { x: M, y: H - 0.45, w: 5, h: 0.3, fontSize: 11, color: MUTED, fontFace: FONT, margin: 0 } } },
  ],
  slideNumber: { x: W - M - 0.6, y: H - 0.45, w: 0.6, h: 0.3, fontSize: 11, color: MUTED, fontFace: FONT, align: "right" },
});
pres.defineSlideMaster({ title: "BLANK", background: { color: BG } });

// ---------- helpers ----------
const pngSize = (f) => {
  const b = fs.readFileSync(f);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
};
const b64 = (f) => "data:image/png;base64," + fs.readFileSync(f).toString("base64");

function content(title, section) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  return s;
}
function text(s, t, o) {
  s.addText(t, { fontFace: FONT, color: TEXT, fontSize: 20, margin: 0, valign: "top", isTextBox: true, ...o });
}
function card(s, x, y, w, h, stroke = LINE, fill = CARD) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: { color: stroke, width: 1 } });
}
// image fitted inside a box, centered
function image(s, f, x, y, w, h) {
  const d = pngSize(f);
  const k = Math.min(w / d.w, h / d.h);
  const iw = d.w * k, ih = d.h * k;
  s.addImage({ path: f, x: x + (w - iw) / 2, y: y + (h - ih) / 2, w: iw, h: ih });
}
function stat(s, x, y, w, big, label, color = TEXT, bigSize = 54) {
  text(s, big, { x, y, w, h: 0.95, fontSize: bigSize, bold: true, color });
  text(s, label, { x, y: y + 1.0, w, h: 0.9, fontSize: 17, color: MUTED });
}
function bullets(s, items, o) {
  s.addText(
    items.map((t, i) => ({ text: t, options: { bullet: { indent: 22 }, breakLine: i < items.length - 1, paraSpaceAfter: 10 } })),
    { fontFace: FONT, color: TEXT, fontSize: 20, margin: 0, valign: "top", isTextBox: true, ...o }
  );
}
function video(s, name, x = M, y = 1.35, w = W - 2 * M) {
  const h = (w * 9) / 16;
  s.addMedia({ type: "video", path: path.join(CLIPS, name + ".mp4"), cover: b64(path.join(CLIPS, name + ".png")), x, y, w, h });
}
function divider(num, title, sub, section) {
  pres.addSection({ title: section });
  const s = pres.addSlide({ masterName: "BLANK", sectionTitle: section });
  text(s, num, { x: M + 0.2, y: 2.0, w: 3, h: 1.2, fontSize: 72, bold: true, color: QUANT });
  text(s, title, { x: M + 0.2, y: 3.2, w: W - 2 * M, h: 1.0, fontSize: 44, bold: true });
  text(s, sub, { x: M + 0.2, y: 4.25, w: 10, h: 0.9, fontSize: 22, color: MUTED });
  return s;
}
// horizontal bar chart drawn with shapes: rows = [label, value, color]
function hbars(s, rows, { x, y, w, rowH = 0.52, max, fmt = (v) => v.toFixed(3), labelW = 3.4 }) {
  const barW = w - labelW - 1.1;
  rows.forEach(([lab, v, col], i) => {
    const yy = y + i * rowH;
    text(s, lab, { x, y: yy, w: labelW - 0.2, h: rowH - 0.1, fontSize: 17, color: col === MUTED ? MUTED : TEXT, align: "right", valign: "middle" });
    const bw = Math.max((barW * v) / max, 0.04);
    s.addShape(pres.shapes.RECTANGLE, { x: x + labelW, y: yy + 0.08, w: bw, h: rowH - 0.22, fill: { color: col }, line: { color: col, width: 0 } });
    text(s, fmt(v), { x: x + labelW + bw + 0.12, y: yy, w: 1.0, h: rowH - 0.1, fontSize: 17, bold: true, color: col, valign: "middle" });
  });
}
function legend(s, x, y) {
  [["quantum", QUANT], ["classical", CLASS], ["paper / naive", MUTED]].forEach(([t, c], i) => {
    s.addShape(pres.shapes.RECTANGLE, { x: x + i * 1.9, y: y + 0.08, w: 0.22, h: 0.22, fill: { color: c }, line: { color: c, width: 0 } });
    text(s, t, { x: x + i * 1.9 + 0.32, y, w: 1.6, h: 0.38, fontSize: 15, color: MUTED, valign: "middle" });
  });
}

// ---------- 0. title ----------
pres.addSection({ title: "Opening" });
{
  const s = pres.addSlide({ masterName: "BLANK", sectionTitle: "Opening" });
  text(s, "IEG313 · Quantum Computing for Engineers", { x: M + 0.2, y: 1.2, w: 9, h: 0.5, fontSize: 18, color: QUANT });
  text(s, "Can a quantum circuit forecast how wild tomorrow will be?", { x: M + 0.2, y: 1.85, w: 10.5, h: 2.0, fontSize: 46, bold: true });
  text(s, "Rebuilding, stress-testing and upgrading a quantum volatility model for Bitcoin", { x: M + 0.2, y: 4.0, w: 10, h: 0.9, fontSize: 22, color: MUTED });
  text(s, "Team Schrödinger's Cat", { x: M + 0.2, y: 5.4, w: 6, h: 0.45, fontSize: 20, bold: true });
  text(s, "Srimoneyshankar Ajith · Bharadwaj B Chand · Nidhi Rakesh · Vishnunath A Suresh · Gopi Krish", { x: M + 0.2, y: 5.85, w: 11, h: 0.45, fontSize: 16, color: MUTED });
  if (fs.existsSync(LOGO)) s.addImage({ path: LOGO, x: W - M - 1.2, y: 0.6, w: 1.2, h: 1.2, transparency: 0 });
}

// ---------- 1. what is volatility ----------
divider("01", "What we are forecasting", "Volatility: how much a price shakes in a day", "Volatility");
{
  const s = content("Some days are calm. Some days are not.", "Volatility");
  card(s, M, 1.6, 5.8, 2.6);
  stat(s, M + 0.4, 1.9, 5, "0.29%", "12 Aug 2023: Bitcoin's calmest day in our data", MUTED, 66);
  card(s, M + 6.3, 1.6, 5.8, 2.6, BAD);
  stat(s, M + 6.7, 1.9, 5, "31.4%", "13 Mar 2020: the day after the Covid crash", BAD, 66);
  text(s, "Daily volatility (square root of realized variance), Bitstamp BTC, 3,610 days from Dec 2016 to Oct 2026. Typical day: 2.7%.", { x: M, y: 4.6, w: W - 2 * M, h: 0.8, fontSize: 18, color: MUTED });
  text(s, "That is a 100× range. A good forecast has to cope with both.", { x: M, y: 5.5, w: W - 2 * M, h: 0.6, fontSize: 22, bold: true });
}
{
  const s = content("Measuring it: add up every small move", "Volatility");
  image(s, path.join(CIRC, "rv.png"), M, 1.6, 5.4, 1.6);
  bullets(s, [
    "Split each day into 288 five-minute steps",
    "Take each step's price change (log return)",
    "Square them so ups and downs both count, then add",
    "Big total = wild day. This is realized volatility (RV)",
  ], { x: M + 6.0, y: 1.7, w: 6.1, h: 3.4, fontSize: 21 });
  card(s, M, 4.6, 5.4, 1.6);
  text(s, "We forecast log RV: it turns a 100× range into an even scale", { x: M + 0.3, y: 4.8, w: 4.9, h: 1.2, fontSize: 18, color: MUTED });
}
{
  const s = content("Ten years of Bitcoin, sorted into four levels", "Volatility");
  video(s, "VolatilityLevels", M + 1.1, 1.3, W - 2 * M - 2.2);
}
{
  const s = content("Why forecast it", "Volatility");
  const items = [
    ["Risk", "How much could I lose tomorrow? Banks and funds size positions on this number"],
    ["Pricing", "Option prices are mostly a bet on future volatility"],
    ["It is predictable", "Wild days cluster. Yesterday, last week and last month tell you a lot about tomorrow"],
  ];
  items.forEach(([h, b], i) => {
    const x = M + i * 4.1;
    card(s, x, 1.7, 3.8, 3.6, i === 2 ? QUANT : LINE);
    text(s, h, { x: x + 0.3, y: 2.0, w: 3.2, h: 0.6, fontSize: 26, bold: true, color: i === 2 ? QUANT : TEXT });
    text(s, b, { x: x + 0.3, y: 2.75, w: 3.2, h: 2.4, fontSize: 19, color: MUTED });
  });
  text(s, "That memory is what the classical HAR model (Corsi, 2009) uses: average of yesterday, last 7 days, last 30 days. It is the bar to beat.", { x: M, y: 5.7, w: W - 2 * M, h: 0.8, fontSize: 19 });
}

// ---------- 2. the paper ----------
divider("02", "The paper", "Takaishi (2026), Fractal and Fractional 10(7):442", "Paper");
{
  const s = content("What the paper set out to do", "Paper");
  text(s, "Use a quantum circuit as a volatility model, in the style of GARCH, and check whether the data it generates looks like real markets.", { x: M, y: 1.6, w: 7.2, h: 1.8, fontSize: 24 });
  bullets(s, [
    "Inputs: yesterday's return r and variance σ²",
    "Output: tomorrow's variance",
    "Trained on Bitcoin realized volatility",
    "Judged by multifractal analysis (MFDFA) of generated paths",
  ], { x: M, y: 3.6, w: 7.2, h: 2.8, fontSize: 20 });
  card(s, M + 7.8, 1.6, 4.3, 4.6, QUANT);
  stat(s, M + 8.1, 1.9, 3.8, "1 qubit", "a single quantum bit carries the whole model", QUANT, 48);
  stat(s, M + 8.1, 3.9, 3.8, "3 angles", "θ, φ, λ: the only trainable numbers", TEXT, 48);
}
{
  const s = content("The paper's circuit", "Paper");
  card(s, M, 1.5, W - 2 * M, 2.5);
  image(s, path.join(CIRC, "paper.png"), M + 0.3, 1.6, W - 2 * M - 0.6, 2.3);
  const cols = [
    ["Encode", "Yesterday's return and variance become rotation angles (amber gates)", CLASS],
    ["Learn", "One trainable rotation U3(θ, φ, λ), fitted with COBYLA to minimise squared error", QUANT],
    ["Read", "Probability of measuring 0 is tomorrow's variance. Feed it back in to generate a whole path", TEXT],
  ];
  cols.forEach(([h, b, c], i) => {
    const x = M + i * 4.1;
    text(s, h, { x, y: 4.15, w: 3.8, h: 0.5, fontSize: 24, bold: true, color: c });
    text(s, b, { x, y: 4.75, w: 3.8, h: 1.8, fontSize: 18, color: MUTED });
  });
}
{
  const s = content("Watch the qubit move", "Paper");
  video(s, "PaperQubit", M + 1.1, 1.3, W - 2 * M - 2.2);
}
{
  const s = content("What the paper claimed", "Paper");
  card(s, M, 1.6, 5.8, 2.6);
  stat(s, M + 0.4, 1.85, 5, "h(2) ≈ 0.5", "generated returns: no long memory, like real returns", TEXT, 48);
  card(s, M + 6.3, 1.6, 5.8, 2.6);
  stat(s, M + 6.7, 1.85, 5, "h(2) ≈ 0.05–0.1", "volatility increments: 'rough volatility', like real markets", TEXT, 48);
  text(s, "The catch", { x: M, y: 4.6, w: 4, h: 0.5, fontSize: 24, bold: true, color: BAD });
  text(s, "Evidence was a look at generated data. No forecast was scored on days the model had not seen, and no simpler model was compared.", { x: M, y: 5.15, w: W - 2 * M, h: 1.2, fontSize: 20 });
}

// ---------- 3. rebuild ----------
divider("03", "Step 1: rebuild it exactly", "Before changing anything, reproduce the paper on its own data", "Rebuild");
{
  const s = content("The rebuild matches", "Rebuild");
  const st = [
    ["0.00205", "training error (MSE), best of 10 converged starts"],
    ["0.449", "correlation of one-day forecasts with actual"],
    ["0.4976", "h(2) of generated returns (paper: ≈ 0.5)"],
    ["0.0525", "h(2) of volatility increments (paper: 0.05–0.1)"],
  ];
  st.forEach(([b, l], i) => {
    const x = M + (i % 2) * 6.15, y = 1.6 + Math.floor(i / 2) * 2.35;
    card(s, x, y, 5.9, 2.1);
    stat(s, x + 0.35, y + 0.25, 5.2, b, l, i < 2 ? TEXT : QUANT, 48);
  });
  text(s, "Fitted angles: θ = −4.557, φ = 0.360, λ = 1.700 on the author's 913 days of Bitcoin data", { x: M, y: 6.4, w: W - 2 * M, h: 0.5, fontSize: 16, color: MUTED });
}
{
  const s = content("Surprise: one of the three knobs does nothing", "Rebuild");
  text(s, "φ", { x: M, y: 1.5, w: 2.5, h: 2.2, fontSize: 150, bold: true, color: BAD });
  text(s, "U3 ends with a spin about the measurement axis. Spinning there cannot change the chance of reading 0, so φ never affects the forecast.", { x: M + 2.8, y: 1.7, w: 6.0, h: 2.2, fontSize: 22 });
  card(s, M + 9.2, 1.6, 2.9, 4.4);
  stat(s, M + 9.45, 1.85, 2.5, "0.0", "largest output change when φ was varied", BAD, 48);
  stat(s, M + 9.45, 3.85, 2.5, "3×10⁻¹⁶", "gap between circuit and closed form", MUTED, 32);
  text(s, "Closed form we derived and checked:  P(0) = ½ + ½ n·b , where n depends only on θ and λ", { x: M + 2.8, y: 4.3, w: 6.0, h: 1.4, fontSize: 18, color: MUTED });
  text(s, "So the model really has 2 trainable numbers, not 3.", { x: M + 2.8, y: 5.6, w: 6.0, h: 0.6, fontSize: 20, bold: true, color: TEXT });
}
{
  const s = content("Four gaps we wanted to close", "Rebuild");
  const gaps = [
    ["1", "Memory of one day", "Only yesterday goes in, yet volatility remembers weeks"],
    ["2", "One number out", "A single guess, with no sense of how unsure it is"],
    ["3", "Mismatched goals", "Trained on squared error, but praised for realism"],
    ["4", "No held-out test", "Nothing scored on unseen days or against a classical rival"],
  ];
  gaps.forEach(([n, h, b], i) => {
    const x = M + (i % 2) * 6.15, y = 1.6 + Math.floor(i / 2) * 2.4;
    card(s, x, y, 5.9, 2.15);
    text(s, n, { x: x + 0.3, y: y + 0.25, w: 0.8, h: 0.9, fontSize: 44, bold: true, color: BAD });
    text(s, h, { x: x + 1.15, y: y + 0.3, w: 4.5, h: 0.5, fontSize: 22, bold: true });
    text(s, b, { x: x + 1.15, y: y + 0.9, w: 4.5, h: 1.1, fontSize: 18, color: MUTED });
  });
}

// ---------- 4. what we built ----------
divider("04", "Step 2: what we changed", "Same idea, rebuilt as an honest forecasting test", "Changes");
{
  const s = content("Original vs ours", "Changes");
  const rows = [
    ["", "Paper", "Ours"],
    ["Qubits", "1", "2"],
    ["Memory", "yesterday only", "yesterday, 7 days, 30 days"],
    ["Output", "one number", "probability of each of 4 levels"],
    ["Training goal", "squared error", "log loss (+ optional realism term)"],
    ["Test", "none", "657 sealed days, 20 seeds"],
    ["Rivals", "none", "HAR, GARCH, softmax, small network"],
  ];
  const opt = (c, i) => ({ color: i === 0 ? MUTED : c, bold: i === 0, fontSize: 19, fontFace: FONT, valign: "middle", margin: [0, 0.12, 0, 0.12] });
  s.addTable(
    rows.map((r, i) => [
      { text: r[0], options: { ...opt(MUTED, i), color: MUTED } },
      { text: r[1], options: opt(TEXT, i) },
      { text: r[2], options: { ...opt(QUANT, i), color: i === 0 ? MUTED : QUANT } },
    ]),
    { x: M, y: 1.55, w: W - 2 * M, colW: [3.0, 3.8, 5.33], rowH: 0.62, fill: { color: BG }, border: { type: "solid", color: LINE, pt: 1 } }
  );
}
{
  const s = content("Four levels fit exactly in two qubits", "Changes");
  const lv = [["|00⟩", "calm", "lowest 30%", "9CA3AF"], ["|01⟩", "normal", "next 40%", "E5E7EB"], ["|10⟩", "wild", "next 25%", CLASS], ["|11⟩", "extreme", "top 5%", BAD]];
  lv.forEach(([k, n, q, c], i) => {
    const x = M + i * 3.05;
    card(s, x, 1.7, 2.8, 2.9, c);
    text(s, k, { x: x + 0.3, y: 1.95, w: 2.3, h: 0.8, fontSize: 40, bold: true, color: c });
    text(s, n, { x: x + 0.3, y: 2.9, w: 2.3, h: 0.5, fontSize: 26, bold: true });
    text(s, q, { x: x + 0.3, y: 3.5, w: 2.3, h: 0.5, fontSize: 18, color: MUTED });
  });
  text(s, "Two qubits have exactly four outcomes. Measuring gives a probability for each level, so the forecast says how sure it is, not just one number.", { x: M, y: 5.0, w: W - 2 * M, h: 1.0, fontSize: 20 });
  text(s, "Level edges are the 30 / 70 / 95% quantiles of the training period only.", { x: M, y: 6.0, w: W - 2 * M, h: 0.5, fontSize: 16, color: MUTED });
}
{
  const s = content("Our circuit", "Changes");
  card(s, M, 1.55, W - 2 * M, 3.0);
  image(s, path.join(CIRC, "ours.png"), M + 0.3, 1.65, W - 2 * M - 0.6, 2.8);
  const cols = [
    ["Amber gates", "Inputs: log RV of yesterday, 7-day and 30-day averages, yesterday's return", CLASS],
    ["Teal gates", "8 trainable numbers per layer, CNOT links the qubits", QUANT],
    ["Layers", "Inputs re-enter each layer. Validation picked 3 layers", TEXT],
  ];
  cols.forEach(([h, b, c], i) => {
    const x = M + i * 4.1;
    text(s, h, { x, y: 4.85, w: 3.8, h: 0.5, fontSize: 22, bold: true, color: c });
    text(s, b, { x, y: 5.4, w: 3.8, h: 1.2, fontSize: 17, color: MUTED });
  });
}
{
  const s = content("From inputs to a forecast", "Changes");
  video(s, "OurForecast", M + 1.1, 1.3, W - 2 * M - 2.2);
}
{
  const s = content("The hybrid: let quantum correct classical", "Changes");
  card(s, M, 1.6, W - 2 * M, 1.5);
  image(s, path.join(CIRC, "hybrid.png"), M + 0.3, 1.7, W - 2 * M - 0.6, 1.3);
  bullets(s, [
    "Start from the classical HAR forecast (amber)",
    "The circuit adds a correction, scaled by one learned strength γ (teal)",
    "γ = 0 gives back the classical model exactly, so any gain is the circuit's own",
  ], { x: M, y: 3.5, w: W - 2 * M, h: 2.5, fontSize: 21 });
}

// ---------- 5. fair test ----------
divider("05", "A fair fight", "Quantum and classical models get the same inputs and the same rules", "Fair test");
{
  const s = content("Rules written before scoring", "Fair test");
  video(s, "SealedTest", M + 1.1, 1.3, W - 2 * M - 2.2);
}
{
  const s = content("The classical rivals", "Fair test");
  const r = [
    ["Softmax", "same 4 inputs, plain linear model with 4 outputs"],
    ["Small network", "same inputs, one small hidden layer"],
    ["HAR", "the standard 7/30-day memory model, two versions"],
    ["GARCH", "textbook volatility model, calibrated"],
    ["Frequency", "always predicts 30 / 40 / 25 / 5%: the floor"],
  ];
  r.forEach(([h, b], i) => {
    const y = 1.6 + i * 0.95;
    card(s, M, y, W - 2 * M, 0.8);
    text(s, h, { x: M + 0.3, y, w: 3.0, h: 0.8, fontSize: 21, bold: true, color: CLASS, valign: "middle" });
    text(s, b, { x: M + 3.4, y, w: 8.5, h: 0.8, fontSize: 19, color: MUTED, valign: "middle" });
  });
}
{
  const s = content("How we score: log loss", "Fair test");
  card(s, M, 1.55, W - 2 * M, 1.4);
  image(s, path.join(CIRC, "logloss.png"), M + 0.3, 1.65, W - 2 * M - 0.6, 1.2);
  text(s, "Each day, look at the probability the model gave to the level that actually happened.", { x: M, y: 3.3, w: 6.2, h: 1.2, fontSize: 21 });
  const ex = [["gave it 90%", "0.11"], ["gave it 50%", "0.69"], ["gave it 10%", "2.30"]];
  ex.forEach(([a, b], i) => {
    const x = M + 6.9 + 0;
    const y = 3.25 + i * 0.95;
    card(s, x, y, 5.2, 0.8);
    text(s, a, { x: x + 0.3, y, w: 2.8, h: 0.8, fontSize: 19, color: MUTED, valign: "middle" });
    text(s, b, { x: x + 3.2, y, w: 1.8, h: 0.8, fontSize: 26, bold: true, color: i === 2 ? BAD : TEXT, valign: "middle", align: "right" });
  });
  text(s, "Lower is better. Confident and wrong is punished hardest.", { x: M, y: 4.6, w: 6.2, h: 1.0, fontSize: 19, color: QUANT });
  text(s, "Realism score: how well simulated paths match real 1, 7 and 30-day memory and volatility-of-volatility. Lower is better.", { x: M, y: 6.25, w: W - 2 * M, h: 0.6, fontSize: 15, color: MUTED });
}

// ---------- 6. results ----------
divider("06", "What happened", "Fresh Bitcoin data, 657 test days from Jan 2025 to Oct 2026", "Results");
{
  const s = content("Against the paper's model: a big jump", "Results");
  const st = [["1.196", "0.570", "log loss"], ["0.840", "0.504", "QLIKE (volatility error)"], ["215.3", "33.5", "realism distance"]];
  st.forEach(([a, b, l], i) => {
    const x = M + i * 4.1;
    card(s, x, 1.6, 3.8, 3.6);
    text(s, l, { x: x + 0.3, y: 1.8, w: 3.3, h: 0.5, fontSize: 19, color: MUTED });
    text(s, a, { x: x + 0.3, y: 2.4, w: 3.3, h: 0.8, fontSize: 34, color: MUTED, strike: "sngStrike" });
    text(s, b, { x: x + 0.3, y: 3.3, w: 3.3, h: 1.1, fontSize: 60, bold: true, color: QUANT });
    text(s, "paper → ours", { x: x + 0.3, y: 4.5, w: 3.3, h: 0.4, fontSize: 15, color: MUTED });
  });
  text(s, "Lower is better on all three. Same 20 seeds, same test days. This comparison was added after the main test results were seen.", { x: M, y: 5.6, w: W - 2 * M, h: 0.9, fontSize: 18, color: MUTED });
}
{
  const s = content("But classical models with the same inputs do better", "Results");
  hbars(s, [
    ["Softmax (same inputs)", 0.5184, CLASS],
    ["HAR residual", 0.5221, CLASS],
    ["Small network", 0.5228, CLASS],
    ["Hybrid quantum", 0.5454, QUANT],
    ["Quantum (ours)", 0.5695, QUANT],
    ["GARCH", 0.6321, CLASS],
    ["Frequency only", 1.1485, MUTED],
    ["Paper's model", 1.196, MUTED],
  ], { x: M, y: 1.5, w: W - 2 * M, rowH: 0.56, max: 1.25, fmt: (v) => v.toFixed(3) });
  legend(s, M + 3.4, 6.05);
  text(s, "test log loss, lower is better · mean of 20 seeds", { x: M + 3.4, y: 6.5, w: 6, h: 0.4, fontSize: 14, color: MUTED });
}
{
  const s = content("Is the gap real or luck?", "Results");
  text(s, "Quantum minus softmax, test log loss", { x: M, y: 1.6, w: 8, h: 0.5, fontSize: 20, color: MUTED });
  // number line from -0.02 to +0.08
  const x0 = M + 0.5, x1 = W - M - 0.5, lo = -0.02, hi = 0.08;
  const X = (v) => x0 + ((v - lo) / (hi - lo)) * (x1 - x0);
  const yL = 3.4;
  s.addShape(pres.shapes.LINE, { x: x0, y: yL, w: x1 - x0, h: 0, line: { color: LINE, width: 2 } });
  s.addShape(pres.shapes.LINE, { x: X(0), y: yL - 0.7, w: 0, h: 1.4, line: { color: TEXT, width: 2, dashType: "dash" } });
  text(s, "0 = no difference", { x: X(0) - 1.0, y: yL + 0.8, w: 2.0, h: 0.4, fontSize: 15, color: TEXT, align: "center" });
  s.addShape(pres.shapes.RECTANGLE, { x: X(0.037), y: yL - 0.18, w: X(0.0643) - X(0.037), h: 0.36, fill: { color: BAD, transparency: 30 }, line: { color: BAD, width: 1 } });
  s.addShape(pres.shapes.OVAL, { x: X(0.0511) - 0.14, y: yL - 0.14, w: 0.28, h: 0.28, fill: { color: TEXT }, line: { color: TEXT, width: 0 } });
  text(s, "+0.051", { x: X(0.0511) - 1.0, y: yL - 1.05, w: 2.0, h: 0.6, fontSize: 30, bold: true, color: BAD, align: "center" });
  text(s, "95% interval +0.037 to +0.064", { x: X(0.0511) - 1.6, y: yL + 0.35, w: 3.2, h: 0.4, fontSize: 15, color: MUTED, align: "center" });
  text(s, "← quantum better", { x: x0, y: yL + 0.35, w: 2.6, h: 0.4, fontSize: 15, color: MUTED });
  text(s, "The whole interval sits above zero: the classical model is truly better on these days, not by chance. Intervals come from a 7-day block bootstrap over test days.", { x: M, y: 5.0, w: W - 2 * M, h: 1.2, fontSize: 20 });
}
{
  const s = content("Same story on the paper's own data", "Results");
  hbars(s, [
    ["HAR quantile", 0.5289, CLASS],
    ["HAR residual", 0.5295, CLASS],
    ["Small network", 0.5784, CLASS],
    ["Softmax", 0.5822, CLASS],
    ["Quantum (ours)", 0.692, QUANT],
  ], { x: M, y: 1.6, w: 8.2, rowH: 0.75, max: 0.8 });
  card(s, M + 8.6, 1.6, 3.5, 2.2);
  text(s, "Author's data", { x: M + 8.9, y: 1.85, w: 3.0, h: 0.5, fontSize: 20, bold: true });
  text(s, "529 / 177 / 177 day split, 20 seeds, test sealed before scoring", { x: M + 8.9, y: 2.45, w: 3.0, h: 2.6, fontSize: 17, color: MUTED });
  text(s, "test log loss, lower is better", { x: M, y: 5.6, w: 8, h: 0.4, fontSize: 14, color: MUTED });
}
{
  const s = content("Training for realism: a real trade-off", "Results");
  const panel = (x, head, rows, verdict, vc) => {
    card(s, x, 1.6, 5.9, 4.4);
    text(s, head, { x: x + 0.35, y: 1.85, w: 5.2, h: 0.5, fontSize: 22, bold: true });
    rows.forEach(([l, a, b, good], i) => {
      const y = 2.6 + i * 1.05;
      text(s, l, { x: x + 0.35, y, w: 2.6, h: 0.8, fontSize: 17, color: MUTED, valign: "middle" });
      text(s, `${a}  →  ${b}`, { x: x + 2.8, y, w: 2.9, h: 0.8, fontSize: 24, bold: true, color: good ? QUANT : BAD, valign: "middle" });
    });
    text(s, verdict, { x: x + 0.35, y: 4.9, w: 5.2, h: 0.9, fontSize: 17, color: vc });
  };
  panel(M, "Paper's data", [["forecast log loss", "0.692", "0.862", false], ["realism distance", "19.72", "31.86", false]], "Both got worse", BAD);
  panel(M + 6.2, "Fresh Bitcoin", [["forecast log loss", "0.570", "0.604", false], ["realism distance", "33.5", "29.0", true]], "Paths look more real, forecasts get worse", CLASS);
  text(s, "Without → with the realism term. Lower is better for both measures.", { x: M, y: 6.25, w: W - 2 * M, h: 0.4, fontSize: 15, color: MUTED });
}
{
  const s = content("Better circuits close the gap, but not all of it", "Results");
  hbars(s, [
    ["v1 quantum", 0.5695, QUANT],
    ["v2 quantum", 0.5288, QUANT],
    ["v3 quantum", 0.5145, QUANT],
    ["Classical softmax v2", 0.4962, CLASS],
  ], { x: M, y: 1.7, w: 8.4, rowH: 0.85, max: 0.62, labelW: 3.0 });
  card(s, M + 8.8, 1.6, 3.3, 3.9);
  stat(s, M + 9.1, 1.85, 2.9, "−0.014", "v3 beats v2, interval −0.022 to −0.007", QUANT, 40);
  stat(s, M + 9.1, 3.55, 2.9, "+0.018", "classical still ahead of v3", CLASS, 40);
  text(s, "v2 and v3 add calendar inputs and more restarts. Scored on test days already looked at, so indicative only.", { x: M, y: 5.8, w: W - 2 * M, h: 0.8, fontSize: 16, color: MUTED });
}
{
  const s = content("Ten coins: no clean win", "Results");
  const rows = [
    ["Coin", "Quantum hybrid", "Softmax", "Network"],
    ["BTC", "0.534", "0.531", "0.534"],
    ["ETH", "0.655", "0.653", "0.661"],
    ["SOL", "0.400", "0.426", "0.417"],
    ["DOGE", "0.761", "0.763", "0.773"],
  ];
  s.addTable(
    rows.map((r, i) =>
      r.map((c, j) => ({ text: c, options: { fontSize: 19, fontFace: FONT, bold: i === 0 || j === 0, color: i === 0 ? MUTED : j === 1 ? QUANT : j === 0 ? TEXT : CLASS, align: j ? "center" : "left", valign: "middle", margin: [0, 0.12, 0, 0.12] } }))
    ),
    { x: M, y: 1.6, w: 6.6, colW: [1.1, 2.3, 1.6, 1.6], rowH: 0.62, fill: { color: BG }, border: { type: "solid", color: LINE, pt: 1 } }
  );
  text(s, "Test log loss. Quantum nominally best on SOL and DOGE, but every paired interval includes zero.", { x: M, y: 4.9, w: 6.6, h: 1.2, fontSize: 16, color: MUTED });
  card(s, M + 7.1, 1.6, 5.0, 4.5);
  text(s, "Pre-written pass rule", { x: M + 7.4, y: 1.85, w: 4.5, h: 0.5, fontSize: 20, bold: true });
  text(s, "Quantum ≥ 5% better than both classical rivals on all three coins of a panel", { x: M + 7.4, y: 2.4, w: 4.4, h: 1.0, fontSize: 16, color: MUTED });
  [["LTC · BNB · ADA", "−2.8% · −6.9% · +1.2%"], ["LINK · DOT · AVAX", "only AVAX passed (+5.7%)"]].forEach(([p, r], i) => {
    const y = 3.5 + i * 1.2;
    text(s, p, { x: M + 7.4, y, w: 3.0, h: 0.45, fontSize: 18, bold: true });
    text(s, "FAIL", { x: M + 10.6, y, w: 1.2, h: 0.45, fontSize: 18, bold: true, color: BAD, align: "right" });
    text(s, r, { x: M + 7.4, y: y + 0.45, w: 4.4, h: 0.45, fontSize: 16, color: MUTED });
  });
}

// ---------- 7. conclusion ----------
divider("07", "What it means", "Keeping it honest", "Conclusion");
{
  const s = content("Three takeaways", "Conclusion");
  const t = [
    ["The paper rebuilds", "Numbers reproduce, but φ is dead: the model really has two knobs", TEXT],
    ["Design matters most", "Memory and probability outputs cut log loss from 1.196 to 0.570", QUANT],
    ["No quantum advantage", "Classical models with the same inputs matched or beat every quantum variant", CLASS],
  ];
  t.forEach(([h, b, c], i) => {
    const y = 1.6 + i * 1.6;
    card(s, M, y, W - 2 * M, 1.35);
    text(s, String(i + 1), { x: M + 0.35, y, w: 0.8, h: 1.35, fontSize: 44, bold: true, color: c, valign: "middle" });
    text(s, h, { x: M + 1.3, y: y + 0.2, w: 10.5, h: 0.5, fontSize: 24, bold: true });
    text(s, b, { x: M + 1.3, y: y + 0.75, w: 10.5, h: 0.5, fontSize: 18, color: MUTED });
  });
}
{
  const s = content("Limits, and what comes next", "Conclusion");
  text(s, "Limits", { x: M, y: 1.6, w: 5.8, h: 0.5, fontSize: 24, bold: true, color: BAD });
  bullets(s, [
    "Simulator only: an IBM hardware script exists but was not run",
    "v2/v3 scored on test days already seen",
    "20 seeds are not 20 markets",
    "Fresh test had no 'extreme' days",
  ], { x: M, y: 2.25, w: 5.8, h: 4.0, fontSize: 19 });
  text(s, "Next", { x: M + 6.4, y: 1.6, w: 5.6, h: 0.5, fontSize: 24, bold: true, color: QUANT });
  bullets(s, [
    "Run on real IBM quantum hardware, with noise",
    "Diebold–Mariano tests for forecast differences",
    "Try other quantum models: reservoirs, Born machines",
    "New, untouched test period for v3",
  ], { x: M + 6.4, y: 2.25, w: 5.6, h: 4.0, fontSize: 19 });
}
{
  const s = content("Team", "Conclusion");
  const team = [
    ["Srimoneyshankar Ajith", "Coordination, Binance data pipeline, ETH/BTC/SOL/DOGE studies, RY-HAR hybrid"],
    ["Bharadwaj B Chand", "Paper rebuild check, memory experiments, realism study, classical baselines"],
    ["Nidhi Rakesh", "qvol package, v2 models, fresh-data study, paper comparison, IBM script"],
    ["Vishnunath A Suresh", "Literature survey, metrics and statistical design, report and presentation"],
    ["Gopi Krish", "Integration and PR review, automated checks, LTC/BNB/ADA and LINK/DOT/AVAX studies, plots"],
  ];
  team.forEach(([n, r], i) => {
    const y = 1.55 + i * 0.98;
    card(s, M, y, W - 2 * M, 0.82);
    text(s, n, { x: M + 0.3, y, w: 3.6, h: 0.82, fontSize: 19, bold: true, valign: "middle" });
    text(s, r, { x: M + 4.0, y, w: 8.0, h: 0.82, fontSize: 16, color: MUTED, valign: "middle" });
  });
}
{
  const s = pres.addSlide({ masterName: "BLANK", sectionTitle: "Conclusion" });
  text(s, "Thank you", { x: M + 0.2, y: 2.4, w: 10, h: 1.3, fontSize: 64, bold: true });
  text(s, "Questions?", { x: M + 0.2, y: 3.8, w: 10, h: 0.8, fontSize: 32, color: QUANT });
  text(s, "Code, data and full report: github.com/moneytosms/qcproj", { x: M + 0.2, y: 5.2, w: 10, h: 0.5, fontSize: 18, color: MUTED });
}

pres.writeFile({ fileName: OUT }).then((f) => console.log("wrote", f));
