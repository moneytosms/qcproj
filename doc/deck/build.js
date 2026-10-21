// Builds doc/IEG313_Schrodingers_Cat_Presentation_v3.pptx. Run doc/deck/build.sh.
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const HERE = __dirname;
const OUT = path.join(HERE, "..", "IEG313_Schrodingers_Cat_Presentation_v3.pptx");
const CLIPS = path.join(HERE, "media", "clips");
const CIRC = path.join(HERE, "circuits");
const LOGO = path.join(HERE, "..", "..", "report", "assets", "iiitk-logo.jpg");

const BG = "0B0B0C", CARD = "151517", LINE = "2A2A2E", TEXT = "ECECEC", SOFT = "B8B8BE", MUTED = "8C8C93";
const QUANT = "2DD4BF", CLASS = "F5B544", BAD = "F87171";
const LEVEL = ["9CA3AF", "E5E7EB", CLASS, BAD];
const FONT = "Arial";
const W = 13.333, H = 7.5, M = 0.6, CW = W - 2 * M;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "Can a qubit forecast a storm?";
pres.author = "Schrodinger's Cat";
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: BG },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.72, w: CW, h: 0.8, fontSize: 32, bold: true, color: TEXT, fontFace: FONT, valign: "top", align: "left", margin: 0 }, text: "" } },
    { text: { text: "Schrödinger's Cat · IEG313", options: { x: M, y: H - 0.45, w: 5, h: 0.3, fontSize: 11, color: MUTED, fontFace: FONT, margin: 0 } } },
  ],
  slideNumber: { x: W - M - 0.6, y: H - 0.45, w: 0.6, h: 0.3, fontSize: 11, color: MUTED, fontFace: FONT, align: "right" },
});
pres.defineSlideMaster({ title: "BLANK", background: { color: BG } });

// ---------- helpers ----------
const imgSize = (f) => {
  const b = fs.readFileSync(f);
  if (f.endsWith(".gif")) return { w: b.readUInt16LE(6), h: b.readUInt16LE(8) };
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
};
function text(s, t, o) {
  s.addText(t, { fontFace: FONT, color: TEXT, fontSize: 21, margin: 0, valign: "top", isTextBox: true, ...o });
}
function card(s, x, y, w, h, stroke = LINE) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: CARD }, line: { color: stroke, width: 1 } });
}
function image(s, f, x, y, w, h) {
  const d = imgSize(f);
  const k = Math.min(w / d.w, h / d.h);
  s.addImage({ path: f, x: x + (w - d.w * k) / 2, y: y + (h - d.h * k) / 2, w: d.w * k, h: d.h * k });
}
const clip = (name, ext = "gif") => path.join(CLIPS, `${name}.${ext}`);
const circ = (name) => path.join(CIRC, `${name}.png`);
// Paragraphs separated by a small gap.
const paras = (...ps) => ps.flatMap((p, i) => [...(Array.isArray(p) ? p : [{ text: p, options: {} }]).map((r, j, a) => (j === a.length - 1 && i < ps.length - 1 ? { ...r, options: { ...r.options, breakLine: true } } : r)), ...(i < ps.length - 1 ? [{ text: " ", options: { breakLine: true, fontSize: 9 } }] : [])]);

let chapter = "";
function content(title) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: chapter });
  text(s, chapter.toUpperCase(), { x: M, y: 0.35, w: 8, h: 0.3, fontSize: 13, bold: true, color: QUANT, charSpacing: 2 });
  s.addText(title, { placeholder: "title" });
  return s;
}
// Full-width animation with a short caption underneath.
function clipSlide(title, name, caption) {
  const s = content(title);
  image(s, clip(name), M + 0.9, 1.55, CW - 1.8, 4.85);
  if (caption) text(s, caption, { x: M, y: 6.45, w: CW, h: 0.45, fontSize: 16, color: SOFT, align: "center" });
  return s;
}
function divider(num, title, sub) {
  chapter = title;
  pres.addSection({ title });
  const s = pres.addSlide({ masterName: "BLANK", sectionTitle: title });
  text(s, num, { x: M + 0.2, y: 2.0, w: 3, h: 1.2, fontSize: 72, bold: true, color: QUANT });
  text(s, title, { x: M + 0.2, y: 3.2, w: CW, h: 1.0, fontSize: 46, bold: true });
  text(s, sub, { x: M + 0.2, y: 4.3, w: 10.5, h: 1.2, fontSize: 24, color: SOFT });
}
function infoCard(s, x, y, w, h, head, body, color = TEXT, stroke = LINE) {
  // ponytail: rough Arial width estimate decides whether the heading takes two lines
  const headH = head.length > (w - 0.6) * 5.6 ? 1.0 : 0.6;
  card(s, x, y, w, h, stroke);
  text(s, head, { x: x + 0.3, y: y + 0.28, w: w - 0.6, h: headH, fontSize: 23, bold: true, color });
  text(s, body, { x: x + 0.3, y: y + 0.4 + headH, w: w - 0.6, h: h - 0.6 - headH, fontSize: 18, color: SOFT });
}
function arrow(s, x, y, w, color = MUTED) {
  s.addShape(pres.shapes.LINE, { x, y, w, h: 0, line: { color, width: 2, endArrowType: "triangle" } });
}
function hbar(s, rows, { x, y, labelW, rowH, scale, offset = 0, fs = 19 }) {
  rows.forEach(([l, v, c], i) => {
    const yy = y + i * rowH;
    text(s, l, { x, y: yy, w: labelW, h: rowH - 0.1, fontSize: fs, color: c === MUTED ? MUTED : c === QUANT ? QUANT : TEXT, align: "right", valign: "middle" });
    s.addShape(pres.shapes.RECTANGLE, { x: x + labelW + 0.2, y: yy + 0.1, w: scale * (v - offset), h: rowH - 0.3, fill: { color: c }, line: { color: c, width: 0 } });
  });
}

// ---------- opening ----------
chapter = "Opening";
pres.addSection({ title: "Opening" });
{
  const s = pres.addSlide({ masterName: "BLANK", sectionTitle: "Opening" });
  text(s, "IEG313 · Quantum Computing for Engineers", { x: M + 0.2, y: 1.1, w: 9, h: 0.5, fontSize: 18, color: QUANT });
  text(s, "Can a qubit forecast a storm?", { x: M + 0.2, y: 1.95, w: CW, h: 1.1, fontSize: 52, bold: true });
  text(s, "Rebuilding a quantum model of market volatility, improving it, and testing it fairly against classical methods", { x: M + 0.2, y: 3.25, w: 10, h: 1.1, fontSize: 24, color: SOFT });
  text(s, "Team Schrödinger's Cat", { x: M + 0.2, y: 5.2, w: 6, h: 0.45, fontSize: 20, bold: true });
  text(s, "Srimoneyshankar Ajith · Bharadwaj B Chand · Nidhi Rakesh · Vishnunath A Suresh · Gopi Krish", { x: M + 0.2, y: 5.65, w: 11, h: 0.45, fontSize: 16, color: MUTED });
  if (fs.existsSync(LOGO)) s.addImage({ path: LOGO, x: W - M - 1.2, y: 0.6, w: 1.2, h: 1.2 });
}
{
  const s = content("Where we're headed today");
  const stops = [
    ["Markets have weather", "what volatility is"],
    ["A one-qubit idea", "the paper we started from"],
    ["Rebuild it", "and a surprise inside"],
    ["Our upgrade", "memory and a weather report"],
    ["A fair race", "quantum vs classical"],
    ["What we learned", "the honest verdict"],
  ];
  const step = CW / stops.length;
  s.addShape(pres.shapes.LINE, { x: M + step / 2, y: 3.05, w: CW - step, h: 0, line: { color: LINE, width: 3 } });
  stops.forEach(([h, b], i) => {
    const cx = M + step * i + step / 2;
    s.addShape(pres.shapes.OVAL, { x: cx - 0.32, y: 2.73, w: 0.64, h: 0.64, fill: { color: i === 0 ? QUANT : CARD }, line: { color: QUANT, width: 2 } });
    text(s, String(i + 1), { x: cx - 0.32, y: 2.73, w: 0.64, h: 0.64, fontSize: 20, bold: true, color: i === 0 ? BG : QUANT, align: "center", valign: "middle" });
    text(s, h, { x: cx - step / 2 + 0.05, y: 3.65, w: step - 0.1, h: 0.85, fontSize: 19, bold: true, align: "center" });
    text(s, b, { x: cx - step / 2 + 0.05, y: 4.5, w: step - 0.1, h: 0.8, fontSize: 16, color: SOFT, align: "center" });
  });
  text(s, "No quantum background needed beyond the basics. We'll explain each idea as it comes up.", { x: M, y: 5.8, w: CW, h: 0.5, fontSize: 18, color: MUTED });
}

// ---------- 01 markets have weather ----------
divider("01", "Markets have weather", "Before any quantum, a quick look at what we're trying to predict.");
{
  const s = content("Prices don't just move. Sometimes they shake.");
  image(s, clip("CalmVsWild", "png"), M, 1.55, 7.4, 4.2);
  text(s, paras(
    "Picture two days for Bitcoin. On one it barely twitches; on the other it lurches up and down for hours.",
    "Both can end at the same price, yet they feel completely different to anyone holding it.",
    [{ text: "That restlessness is called ", options: {} }, { text: "volatility", options: { bold: true, color: QUANT } }, { text: ", and it's what this whole project tries to forecast.", options: {} }],
  ), { x: M + 7.8, y: 1.8, w: 4.3, h: 4.2, fontSize: 20 });
  text(s, "Illustration, not real data", { x: M, y: 5.85, w: 7.4, h: 0.35, fontSize: 13, color: MUTED, align: "center" });
}
{
  const s = content("How do you measure a shake?");
  text(s, "Think of driving down a road and counting every bump.", { x: M, y: 1.6, w: CW, h: 0.6, fontSize: 26, color: QUANT });
  const steps = [
    ["Chop the day up", "into 288 five-minute slices"],
    ["Measure each move", "how far the price went in that slice"],
    ["Square and add", "so drops count as much as jumps"],
  ];
  steps.forEach(([h, b], i) => {
    const x = M + i * 4.15;
    infoCard(s, x, 2.45, 3.75, 1.85, h, b, TEXT);
    if (i < 2) arrow(s, x + 3.8, 3.37, 0.3);
  });
  card(s, M, 4.6, 4.3, 1.5);
  image(s, circ("rv"), M + 0.2, 4.7, 3.9, 1.3);
  text(s, "A smooth day adds up to a small number; a bumpy day to a big one. This total is called realized volatility, and it's the quantity we forecast.", { x: M + 4.7, y: 4.75, w: 7.4, h: 1.4, fontSize: 19, color: SOFT });
}
clipSlide("Ten years of Bitcoin's weather", "VolatilityLevels", "Real data: Bitcoin on the Bitstamp exchange, December 2016 to October 2026");
{
  const s = content("Four kinds of weather");
  text(s, "Rather than chasing an exact number, we sort each day into one of four kinds of weather, a bit like a forecast that says sunny, cloudy, rainy or stormy.", { x: M, y: 1.55, w: CW, h: 1.0, fontSize: 21 });
  const lv = [["calm", "about 3 in 10 days"], ["normal", "about 4 in 10"], ["wild", "about 1 in 4"], ["extreme", "about 1 in 20"]];
  lv.forEach(([n, q], i) => {
    const x = M + i * 3.05;
    card(s, x, 2.85, 2.8, 2.2, LEVEL[i]);
    text(s, n, { x: x + 0.3, y: 3.15, w: 2.3, h: 0.7, fontSize: 32, bold: true, color: LEVEL[i] });
    text(s, q, { x: x + 0.3, y: 4.0, w: 2.3, h: 0.6, fontSize: 18, color: SOFT });
  });
  text(s, "The cut-offs are set using older data only, so no information from the future sneaks in.", { x: M, y: 5.45, w: CW, h: 0.6, fontSize: 18, color: MUTED });
}
{
  const s = content("Storms cluster, and that's why forecasting works");
  text(s, "A stormy week is usually followed by more storms; calm spells tend to last too. Volatility has memory.", { x: M, y: 1.55, w: CW, h: 0.9, fontSize: 22 });
  ["yesterday", "the last week", "the last month"].forEach((t, i) => {
    const y = 2.75 + i * 0.95;
    card(s, M + 0.4, y, 3.4, 0.75);
    text(s, t, { x: M + 0.4, y, w: 3.4, h: 0.75, fontSize: 20, align: "center", valign: "middle" });
    arrow(s, M + 3.9, y + 0.375, 1.3);
  });
  card(s, M + 5.35, 3.15, 2.6, 1.75, CLASS);
  text(s, "tomorrow", { x: M + 5.35, y: 3.15, w: 2.6, h: 1.75, fontSize: 24, bold: true, color: CLASS, align: "center", valign: "middle" });
  text(s, paras(
    [{ text: "The classic forecaster", options: { bold: true, color: CLASS } }],
    "A well-known model called HAR (Corsi, 2009) does exactly this: it blends yesterday, the past week and the past month. It's simple and hard to beat, so it's the bar any new model has to clear.",
  ), { x: M + 8.4, y: 2.8, w: 3.7, h: 3.2, fontSize: 18, color: SOFT });
}
{
  const s = content("Why anyone cares");
  const items = [
    ["Managing risk", "Banks and funds decide how much to hold based on how rough tomorrow might be."],
    ["Pricing insurance", "Options are insurance on prices, and their cost depends mostly on expected volatility."],
    ["Crypto especially", "Bitcoin's weather swings far more than most markets, so a good forecast is worth more."],
  ];
  items.forEach(([h, b], i) => infoCard(s, M + i * 4.1, 1.7, 3.8, 2.9, h, b, i === 2 ? QUANT : TEXT, i === 2 ? QUANT : LINE));
  text(s, "So the question is natural: could a quantum computer be a good weather forecaster for markets?", { x: M, y: 5.0, w: CW, h: 0.8, fontSize: 22, bold: true });
}

// ---------- 02 the paper ----------
divider("02", "A one-qubit idea", "In 2026, a paper by Takaishi asked whether a single qubit could work as a volatility model.");
{
  const s = content("The idea in one picture");
  image(s, clip("PaperQubit", "png"), M, 1.45, 6.6, 3.7);
  text(s, paras(
    "A qubit's state can be drawn as an arrow inside a sphere.",
    [{ text: "The paper feeds in yesterday's price move and yesterday's volatility by ", options: {} }, { text: "turning that arrow", options: { bold: true, color: QUANT } }, { text: ". Then one learned turn is added on top.", options: {} }],
    "Finally we measure. The chance of reading 0 becomes the forecast for tomorrow's volatility.",
  ), { x: M + 7.0, y: 1.7, w: 5.1, h: 4.3, fontSize: 20 });
  text(s, "The paper: Takaishi, Fractal and Fractional 10(7):442, 2026", { x: M, y: 5.6, w: 6.6, h: 0.4, fontSize: 14, color: MUTED, align: "center" });
}
clipSlide("Watch yesterday's market turn the arrow", "PaperQubit", "One example day. Each turn is one gate in the paper's circuit; the bar on the right is the forecast.");
{
  const s = content("The same thing, written as a circuit");
  card(s, M, 1.5, CW, 2.5);
  image(s, circ("paper"), M + 0.3, 1.6, CW - 0.6, 2.3);
  const cols = [
    ["Read the data", "The amber gates turn the arrow by angles made from yesterday's return and volatility.", CLASS],
    ["Learn", "The teal gate has three adjustable angles. Training tunes them so forecasts match history.", QUANT],
    ["Forecast, then repeat", "The measured chance becomes tomorrow's forecast, which can be fed back in to simulate a whole price history.", TEXT],
  ];
  cols.forEach(([h, b, c], i) => {
    const x = M + i * 4.1;
    text(s, h, { x, y: 4.3, w: 3.8, h: 0.5, fontSize: 22, bold: true, color: c });
    text(s, b, { x, y: 4.85, w: 3.8, h: 1.7, fontSize: 17, color: SOFT });
  });
}
{
  const s = content("What the paper found");
  text(s, "The author let the circuit invent its own price history and then compared its texture with real Bitcoin.", { x: M, y: 1.55, w: CW, h: 0.9, fontSize: 22 });
  infoCard(s, M, 2.7, 5.9, 2.4, "The made-up prices", "wander like real prices do, with no hidden long-term pattern.", QUANT);
  infoCard(s, M + 6.2, 2.7, 5.9, 2.4, "The made-up volatility", "is jagged and 'rough', just like real markets. This roughness is a well-known feature of real volatility.", QUANT);
  text(s, "Measured with multifractal analysis (MFDFA). The paper's conclusion is that the circuit produces realistic-looking data.", { x: M, y: 5.45, w: CW, h: 0.8, fontSize: 16, color: MUTED });
}
{
  const s = content("The questions it left open");
  const q = [
    ["Can it remember more than one day?", "It only ever sees yesterday, but we just saw that volatility remembers weeks."],
    ["Can it say how sure it is?", "It gives one number, with no sense of whether a storm is likely or just possible."],
    ["Does looking real mean forecasting well?", "It was trained on one goal and praised for another."],
    ["Would it beat a simple classical model?", "Nothing was scored on unseen days, or compared against a classical rival."],
  ];
  q.forEach(([h, b], i) => {
    const x = M + (i % 2) * 6.15, y = 1.6 + Math.floor(i / 2) * 2.35;
    card(s, x, y, 5.9, 2.1);
    text(s, "?", { x: x + 0.3, y: y + 0.25, w: 0.6, h: 0.9, fontSize: 44, bold: true, color: CLASS });
    text(s, h, { x: x + 1.0, y: y + 0.3, w: 4.6, h: 0.75, fontSize: 20, bold: true });
    text(s, b, { x: x + 1.0, y: y + 1.05, w: 4.6, h: 0.95, fontSize: 17, color: SOFT });
  });
}

// ---------- 03 rebuild ----------
divider("03", "First, rebuild it", "You can't fairly improve something until you've reproduced it.");
{
  const s = content("Our rebuild matches the paper");
  text(s, "We rewrote the model from scratch and trained it on the author's own Bitcoin data. It behaved just like the original.", { x: M, y: 1.55, w: CW, h: 0.9, fontSize: 22 });
  const checks = [
    ["Fits the history", "Trained the same way, it tracks past volatility just as closely"],
    ["Realistic prices", "Its invented prices show the same texture the paper found"],
    ["Rough volatility", "Its invented volatility is just as jagged as reported"],
  ];
  checks.forEach(([h, b], i) => {
    const x = M + i * 4.1;
    card(s, x, 2.7, 3.8, 2.6, QUANT);
    text(s, "✓", { x: x + 0.3, y: 2.85, w: 0.8, h: 0.8, fontSize: 36, bold: true, color: QUANT });
    text(s, h, { x: x + 0.3, y: 3.65, w: 3.2, h: 0.5, fontSize: 21, bold: true });
    text(s, b, { x: x + 0.3, y: 4.2, w: 3.2, h: 1.0, fontSize: 16, color: SOFT });
  });
  text(s, "That gave us a trustworthy starting point to build on.", { x: M, y: 5.65, w: CW, h: 0.6, fontSize: 19, color: MUTED });
}
{
  const s = content("A surprise: one of the three dials isn't connected");
  text(s, "φ", { x: M + 0.2, y: 1.4, w: 2.2, h: 2.4, fontSize: 160, bold: true, color: BAD });
  text(s, paras(
    "The learned gate has three dials: θ, φ and λ. While rebuilding, we noticed φ never changes the forecast, whatever value it takes.",
    [{ text: "Think of a globe. ", options: { bold: true, color: QUANT } }, { text: "Spinning it around its axis moves every city east or west, but nobody's latitude changes. φ is exactly that kind of spin, and the forecast only depends on 'latitude'.", options: {} }],
  ), { x: M + 2.8, y: 1.6, w: 9.3, h: 3.4, fontSize: 21 });
  card(s, M + 2.8, 5.0, 9.3, 1.1);
  text(s, "So the model really has two working dials, not three. We confirmed this with a formula and by direct testing.", { x: M + 3.1, y: 5.0, w: 8.8, h: 1.1, fontSize: 18, color: SOFT, valign: "middle" });
}
clipSlide("Seeing it happen", "PhiSpin", "Turning φ swings the arrow around the red circle. Its height, and so the forecast, stays put.");

// ---------- 04 our upgrade ----------
divider("04", "Our upgrade", "Keep the quantum idea. Fix the gaps.");
{
  const s = content("Three changes, one for each open question");
  const c = [
    ["Give it memory", "Feed in yesterday, the last week and the last month, the same information the classic HAR model uses.", QUANT],
    ["Make it say how sure it is", "Instead of one number, forecast the chance of each of the four kinds of weather.", QUANT],
    ["Judge it on forecasting", "Score it on days it has never seen, against classical models given the same information.", CLASS],
  ];
  c.forEach(([h, b, col], i) => infoCard(s, M + i * 4.1, 1.7, 3.8, 3.2, h, b, col, col));
}
{
  const s = content("Four kinds of weather fit neatly into two qubits");
  text(s, "Measuring two qubits always gives one of four answers. That matches our four kinds of weather one for one, so the circuit naturally hands back a probability for each.", { x: M, y: 1.55, w: CW, h: 1.0, fontSize: 21 });
  [["00", "calm"], ["01", "normal"], ["10", "wild"], ["11", "extreme"]].forEach(([k, n], i) => {
    const x = M + i * 3.05;
    card(s, x, 2.85, 2.8, 2.2, LEVEL[i]);
    text(s, k, { x: x + 0.3, y: 3.05, w: 2.3, h: 0.9, fontSize: 44, bold: true, color: LEVEL[i] });
    text(s, n, { x: x + 0.3, y: 4.05, w: 2.3, h: 0.6, fontSize: 24, bold: true });
  });
  text(s, "The result reads like a weather report: '60% calm, 30% normal, 8% wild, 2% extreme'.", { x: M, y: 5.45, w: CW, h: 0.6, fontSize: 19, color: QUANT });
}
clipSlide("From the last month to tomorrow's forecast", "OurForecast", "The percentages here are made up to show the idea; real results come later.");
{
  const s = content("Inside our circuit");
  card(s, M, 1.5, CW, 3.0);
  image(s, circ("ours"), M + 0.3, 1.6, CW - 0.6, 2.8);
  const cols = [
    ["Amber gates read the data", "Each one turns a qubit by an amount set by one input: yesterday, the week, the month or yesterday's move.", CLASS],
    ["Teal gates are learned", "Training tunes them. A link between the two qubits lets them work together.", QUANT],
    ["Read it more than once", "The whole block repeats a few times, re-reading the data each time. Three repeats worked best.", TEXT],
  ];
  cols.forEach(([h, b, c], i) => {
    const x = M + i * 4.1;
    text(s, h, { x, y: 4.75, w: 3.8, h: 0.5, fontSize: 20, bold: true, color: c });
    text(s, b, { x, y: 5.3, w: 3.8, h: 1.3, fontSize: 16, color: SOFT });
  });
}
clipSlide("A second version: quantum as a second opinion", "HybridNudge", "With the dial at zero it is exactly the classical model, so any improvement belongs to the circuit.");

// ---------- 05 a fair race ----------
divider("05", "A fair race", "A good result means nothing unless the race was fair.");
clipSlide("The final exam stayed locked", "SealedTest", "We wrote down the rules first, trained and tuned, sealed everything, and only then opened the test period.");
{
  const s = content("Who we raced against");
  const r = [
    ["A simple statistical model", "the same four inputs, no quantum parts"],
    ["A small neural network", "the same inputs, a little more flexible"],
    ["HAR", "the classic memory-based forecaster"],
    ["GARCH", "the textbook volatility model"],
    ["Just guess the usual mix", "always predicts the long-run share of each weather type"],
  ];
  r.forEach(([h, b], i) => {
    const y = 1.55 + i * 0.86;
    card(s, M, y, CW, 0.74);
    text(s, h, { x: M + 0.3, y, w: 4.4, h: 0.74, fontSize: 20, bold: true, color: CLASS, valign: "middle" });
    text(s, b, { x: M + 4.8, y, w: 7.2, h: 0.74, fontSize: 18, color: SOFT, valign: "middle" });
  });
  text(s, "Every model got the same data and the same training effort, and was run 20 times from different random starts so that luck evens out.", { x: M, y: 5.95, w: CW, h: 0.7, fontSize: 17, color: MUTED });
}
{
  const s = content("How we keep score");
  text(s, "Imagine a weather forecaster. If they say 90% sun and it pours, they should lose more points than a forecaster who said 50%.", { x: M, y: 1.55, w: CW, h: 1.0, fontSize: 22 });
  const ex = [["Gave the right answer a high chance", 0.12, QUANT, "small penalty"], ["Hedged their bets", 0.35, TEXT, "medium penalty"], ["Confident and wrong", 1.0, BAD, "big penalty"]];
  ex.forEach(([a, v, c, t], i) => {
    const y = 2.85 + i * 0.95;
    text(s, a, { x: M, y, w: 4.5, h: 0.7, fontSize: 19, color: SOFT, valign: "middle" });
    s.addShape(pres.shapes.RECTANGLE, { x: M + 4.7, y: y + 0.15, w: 5.0 * v, h: 0.4, fill: { color: c }, line: { color: c, width: 0 } });
    text(s, t, { x: M + 4.85 + 5.0 * v, y, w: 2.4, h: 0.7, fontSize: 17, color: c, valign: "middle" });
  });
  text(s, "Add up the penalties over every test day and you get the score, called log loss. Lower is better. It rewards forecasts that are both confident and right.", { x: M, y: 5.8, w: CW, h: 0.8, fontSize: 18, color: SOFT });
}

// ---------- 06 what happened ----------
divider("06", "What happened", "Scored on fresh Bitcoin data: January 2025 to October 2026, days no model had seen.");
clipSlide("The race, in one picture", "ResultsRace", "Each bar is the average penalty. Shorter bars mean better forecasts.");
{
  const s = content("Good news: our redesign roughly halves the error");
  text(s, "≈ ½", { x: M, y: 1.5, w: 3.4, h: 2.0, fontSize: 110, bold: true, color: QUANT });
  text(s, "Our two-qubit model makes about half the forecasting error of the paper's one-qubit model, and its invented price paths look far more like real ones too.", { x: M + 3.7, y: 1.75, w: 8.4, h: 1.6, fontSize: 22 });
  text(s, "Why? Mostly the design, not the qubits:", { x: M, y: 3.85, w: CW, h: 0.5, fontSize: 20, bold: true });
  infoCard(s, M, 4.45, 5.9, 1.75, "Memory", "Seeing the past week and month, not just yesterday", QUANT);
  infoCard(s, M + 6.2, 4.45, 5.9, 1.75, "Honest uncertainty", "Giving odds for each kind of weather, not one number", QUANT);
}
{
  const s = content("But the classical model still wins, and not by luck");
  text(s, "Was the classical lead just a lucky stretch of days? We checked by re-running the comparison on thousands of reshuffled versions of the test period.", { x: M, y: 1.55, w: CW, h: 1.0, fontSize: 21 });
  const x0 = M + 0.6, x1 = W - M - 0.6, lo = -0.02, hi = 0.08;
  const X = (v) => x0 + ((v - lo) / (hi - lo)) * (x1 - x0);
  const yL = 3.75;
  s.addShape(pres.shapes.LINE, { x: x0, y: yL, w: x1 - x0, h: 0, line: { color: LINE, width: 2 } });
  s.addShape(pres.shapes.LINE, { x: X(0), y: yL - 0.6, w: 0, h: 1.2, line: { color: TEXT, width: 2, dashType: "dash" } });
  text(s, "no difference", { x: X(0) - 1.0, y: yL + 0.7, w: 2.0, h: 0.4, fontSize: 16, align: "center" });
  text(s, "← quantum ahead", { x: x0, y: yL - 0.95, w: 2.6, h: 0.4, fontSize: 16, color: QUANT });
  text(s, "classical ahead →", { x: x1 - 2.6, y: yL - 0.95, w: 2.6, h: 0.4, fontSize: 16, color: CLASS, align: "right" });
  s.addShape(pres.shapes.RECTANGLE, { x: X(0.037), y: yL - 0.2, w: X(0.0643) - X(0.037), h: 0.4, fill: { color: CLASS, transparency: 35 }, line: { color: CLASS, width: 1 } });
  s.addShape(pres.shapes.OVAL, { x: X(0.0511) - 0.15, y: yL - 0.15, w: 0.3, h: 0.3, fill: { color: TEXT }, line: { color: TEXT, width: 0 } });
  text(s, "where the gap landed", { x: X(0.0511) - 1.6, y: yL + 0.35, w: 3.2, h: 0.4, fontSize: 16, color: SOFT, align: "center" });
  text(s, "In 95% of the reshuffles the gap stayed well on the classical side, nowhere near zero. The classical model is genuinely better on these days.", { x: M, y: 5.3, w: CW, h: 1.0, fontSize: 20 });
}
{
  const s = content("The paper's own data tells the same story");
  text(s, "We also ran the full fair race on the author's original data set, with its own locked final exam.", { x: M, y: 1.55, w: CW, h: 0.9, fontSize: 21 });
  hbar(s, [["HAR", 0.5289, CLASS], ["HAR, second version", 0.5295, CLASS], ["Small neural network", 0.5784, CLASS], ["Simple statistical model", 0.5822, CLASS], ["Our quantum model", 0.692, QUANT]], { x: M, y: 2.6, labelW: 3.6, rowH: 0.66, scale: 10 });
  text(s, "Shorter is better. Every classical model came in ahead of the quantum one.", { x: M, y: 6.05, w: CW, h: 0.5, fontSize: 17, color: MUTED });
}
{
  const s = content("Looking real vs forecasting well");
  text(s, "We also tried rewarding the model for producing realistic-looking price paths, the paper's original goal. It turns out to be a trade-off.", { x: M, y: 1.55, w: CW, h: 1.0, fontSize: 21 });
  const panel = (x, head, a, b, verdict, vc) => {
    card(s, x, 2.8, 5.9, 3.3);
    text(s, head, { x: x + 0.35, y: 3.05, w: 5.2, h: 0.5, fontSize: 22, bold: true });
    [["Forecasts", a], ["Realistic paths", b]].forEach(([l, good], i) => {
      const y = 3.75 + i * 0.8;
      text(s, l, { x: x + 0.35, y, w: 2.8, h: 0.6, fontSize: 19, color: SOFT, valign: "middle" });
      text(s, good ? "▲ better" : "▼ worse", { x: x + 3.2, y, w: 2.4, h: 0.6, fontSize: 20, bold: true, color: good ? QUANT : BAD, valign: "middle" });
    });
    text(s, verdict, { x: x + 0.35, y: 5.4, w: 5.2, h: 0.6, fontSize: 17, color: vc });
  };
  panel(M, "On fresh Bitcoin data", false, true, "Paths looked more real, forecasts slipped a little", CLASS);
  panel(M + 6.2, "On the paper's data", false, false, "Both got worse", BAD);
}
{
  const s = content("We kept improving the circuit");
  text(s, "Two more rounds of design (adding calendar effects and more careful training) steadily closed the gap. The classical model stayed just ahead.", { x: M, y: 1.55, w: CW, h: 1.0, fontSize: 21 });
  hbar(s, [["First version", 0.5695, QUANT], ["Second version", 0.5288, QUANT], ["Third version", 0.5145, QUANT], ["Best classical", 0.4962, CLASS]], { x: M, y: 2.8, labelW: 2.8, rowH: 0.78, scale: 24, offset: 0.3 });
  text(s, "Bars start part-way along so the differences are visible. These later rounds were scored on days we had already looked at, so treat them as a hint, not proof.", { x: M, y: 6.0, w: CW, h: 0.7, fontSize: 16, color: MUTED });
}
{
  const s = content("Ten coins later: no clean win");
  text(s, "To check Bitcoin wasn't a special case, we ran the same race on nine more coins.", { x: M, y: 1.55, w: CW, h: 0.6, fontSize: 21 });
  const coins = [
    ["BTC", "neck and neck", MUTED], ["ETH", "neck and neck", MUTED], ["SOL", "slightly ahead, within noise", QUANT], ["DOGE", "slightly ahead, within noise", QUANT], ["LTC", "behind", BAD],
    ["BNB", "behind", BAD], ["ADA", "slightly ahead, too small", QUANT], ["LINK", "did not pass", MUTED], ["DOT", "did not pass", MUTED], ["AVAX", "clearly ahead, but alone", QUANT],
  ];
  coins.forEach(([n, st, c], i) => {
    const x = M + (i % 5) * 2.45, y = 2.4 + Math.floor(i / 5) * 1.6;
    card(s, x, y, 2.25, 1.4, c);
    text(s, n, { x: x + 0.25, y: y + 0.2, w: 1.8, h: 0.5, fontSize: 24, bold: true, color: c === MUTED ? TEXT : c });
    text(s, st, { x: x + 0.25, y: y + 0.72, w: 1.85, h: 0.6, fontSize: 15, color: SOFT });
  });
  text(s, "Before running it we set a clear bar: quantum must beat both classical rivals by at least 5% on every coin in a group. No group cleared it.", { x: M, y: 5.75, w: CW, h: 0.8, fontSize: 18 });
}

// ---------- 07 what we learned ----------
divider("07", "What we learned", "The honest verdict, and where this could go next.");
{
  const s = content("Three things to take away");
  const t = [
    ["The paper holds up, with a twist", "We reproduced its results, and found one of its three dials does nothing at all.", TEXT],
    ["Good design matters most", "Adding memory and honest uncertainty roughly halved the error.", QUANT],
    ["No quantum advantage, yet", "Classical models given the same information matched or beat every quantum version we built.", CLASS],
  ];
  t.forEach(([h, b, c], i) => {
    const y = 1.6 + i * 1.6;
    card(s, M, y, CW, 1.35);
    text(s, String(i + 1), { x: M + 0.35, y, w: 0.8, h: 1.35, fontSize: 44, bold: true, color: c, valign: "middle" });
    text(s, h, { x: M + 1.3, y: y + 0.22, w: 10.5, h: 0.5, fontSize: 24, bold: true });
    text(s, b, { x: M + 1.3, y: y + 0.78, w: 10.5, h: 0.5, fontSize: 18, color: SOFT });
  });
}
{
  const s = content("Why didn't quantum win here?");
  text(s, "Our reading of the results:", { x: M, y: 1.55, w: CW, h: 0.5, fontSize: 20, color: MUTED });
  const r = [
    ["Two qubits is tiny", "A laptop simulates our circuit instantly. There is nothing here a classical computer struggles with."],
    ["Same information, same answers", "Given the same inputs, a small classical model can express much the same forecasts."],
    ["Advantage needs hard problems", "Quantum computers shine on tasks that overwhelm classical machines. A four-input forecast is not one of them."],
  ];
  r.forEach(([h, b], i) => infoCard(s, M + i * 4.1, 2.2, 3.8, 3.5, h, b, i === 2 ? QUANT : TEXT));
  text(s, "That's not a failure of the idea, just a clear picture of where it currently stands.", { x: M, y: 6.0, w: CW, h: 0.6, fontSize: 18 });
}
{
  const s = content("Being honest about our limits");
  const list = (items, x, y) =>
    s.addText(items.map((t, i) => ({ text: t, options: { bullet: { indent: 20 }, breakLine: i < items.length - 1, paraSpaceAfter: 12 } })), { x, y, w: 5.6, h: 4.0, fontFace: FONT, fontSize: 18, color: SOFT, margin: 0, valign: "top", isTextBox: true });
  text(s, "What to keep in mind", { x: M, y: 1.6, w: 5.8, h: 0.5, fontSize: 23, bold: true, color: CLASS });
  list([
    "Everything ran on a simulator, not real quantum hardware",
    "Later circuit versions were scored on days we had already seen",
    "20 runs on one market are not the same as 20 markets",
    "The test period happened to have no 'extreme' days",
  ], M, 2.25);
  text(s, "Where we'd go next", { x: M + 6.4, y: 1.6, w: 5.6, h: 0.5, fontSize: 23, bold: true, color: QUANT });
  list([
    "Run the circuit on real IBM quantum hardware, noise and all",
    "Stronger statistical tests for comparing forecasts",
    "Try other quantum models, such as quantum reservoirs",
    "A brand-new, untouched test period for the latest version",
  ], M + 6.4, 2.25);
}
{
  const s = content("The team");
  const team = [
    ["Srimoneyshankar Ajith", "Coordination, Binance data pipeline, ETH/BTC/SOL/DOGE studies, RY-HAR hybrid"],
    ["Bharadwaj B Chand", "Paper rebuild check, memory experiments, realism study, classical baselines"],
    ["Nidhi Rakesh", "qvol package, v2 models, fresh-data study, paper comparison, IBM script"],
    ["Vishnunath A Suresh", "Literature survey, metrics and statistical design, report and presentation"],
    ["Gopi Krish", "Integration and PR review, automated checks, LTC/BNB/ADA and LINK/DOT/AVAX studies, plots"],
  ];
  team.forEach(([n, r], i) => {
    const y = 1.6 + i * 0.98;
    card(s, M, y, CW, 0.82);
    text(s, n, { x: M + 0.3, y, w: 3.7, h: 0.82, fontSize: 19, bold: true, valign: "middle" });
    text(s, r, { x: M + 4.1, y, w: 7.9, h: 0.82, fontSize: 16, color: SOFT, valign: "middle" });
  });
}
{
  const s = pres.addSlide({ masterName: "BLANK", sectionTitle: chapter });
  text(s, "Thank you", { x: M + 0.2, y: 2.3, w: 10, h: 1.3, fontSize: 64, bold: true });
  text(s, "We'd love to hear your questions.", { x: M + 0.2, y: 3.7, w: 10, h: 0.8, fontSize: 30, color: QUANT });
  text(s, "Code, data and the full report: github.com/moneytosms/qcproj", { x: M + 0.2, y: 5.1, w: 10, h: 0.5, fontSize: 18, color: MUTED });
}

pres.writeFile({ fileName: OUT }).then((f) => console.log("wrote", f));
