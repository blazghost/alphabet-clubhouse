// usage: node tools/timing-test.mjs   (needs chromium on PATH)
// Runs index.html headless with a fake speech engine and checks that a
// round advances when speech ends, a dropped utterance cannot stall the
// queue, and leaving an activity cancels its pending next round.
import { readFileSync, writeFileSync, mkdtempSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { tmpdir } from "node:os"; import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const page = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "..", "index.html"), "utf8");
const stub = `<script>
window.LOG = []; const T0 = Date.now(); const log = s => LOG.push((Date.now() - T0) + " " + s);
let cur = null, dropNext = false;
const fake = { paused:false, speaking:false, getVoices:() => [], resume(){},
  speak(u){ log("speak " + u.text);
    if(dropNext){ dropNext = false; log("dropped"); return; }
    const a = setTimeout(() => { u.onstart && u.onstart(); }, 100);
    const b = setTimeout(() => { cur = null; log("end " + u.text); u.onend && u.onend(); }, 100 + u.text.length * 40);
    cur = {u, a, b}; },
  cancel(){ if(cur){ clearTimeout(cur.a); clearTimeout(cur.b); log("cancel " + cur.u.text);
    const u = cur.u; cur = null; u.onerror && u.onerror(); } } };
Object.defineProperty(window, "speechSynthesis", {value: fake});
window.setDrop = () => { dropNext = true; };
/* headless virtual time does not run media, so clips "play" for 300 ms */
window.Audio = function(){ const a = {volume:1, pause(){}, play(){ log("clip"); setTimeout(() => a.onended && a.onended(), 300); return Promise.resolve(); }}; return a; };
</script>`;
const test = `<script>
const wait = ms => new Promise(r => setTimeout(r, ms));
new MutationObserver(() => log("PROMPT " + promptText.textContent))
  .observe(promptText, {childList:true, subtree:true, characterData:true});
function clickTarget(){
  const want = promptText.querySelector("b").textContent;
  [...playArea.querySelectorAll(".tile")].find(t => t.textContent === want).click(); }
(async () => {
  openActivity("which"); await wait(8000);
  log("CLICK1"); clickTarget(); await wait(30000);
  setDrop(); log("CLICK2"); clickTarget(); await wait(30000);
  log("CLICK3"); clickTarget(); await wait(300); log("HOME"); goHome(); await wait(20000);
  document.title = "DONE"; document.body.setAttribute("data-log", JSON.stringify(LOG));
})();
</script>`;
const html = stub + page + test;   // the page is a fragment: no head or body
const dir = mkdtempSync(join(tmpdir(), "abc-")); writeFileSync(join(dir, "t.html"), html);
const dom = execFileSync("chromium", ["--headless", "--enable-logging=stderr", "--v=0", "--no-sandbox", "--disable-gpu", "--user-data-dir=" + join(dir, "p"),
  "--autoplay-policy=no-user-gesture-required", "--virtual-time-budget=120000", "--dump-dom", "file://" + join(dir, "t.html")],
  {encoding: "utf8", stdio: ["ignore", "pipe", process.env.DEBUG ? "inherit" : "ignore"], maxBuffer: 64 << 20});
const m = dom.match(/data-log="([^"]*)"/); if(!m) throw new Error("test page did not finish");
const L = JSON.parse(m[1].replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">"))
  .map(s => { const i = s.indexOf(" "); return {t: +s.slice(0, i), e: s.slice(i + 1)}; });
if(process.env.DUMP) console.log(L.map(x => x.t + " " + x.e).join("\n"));
const ix = e => L.findIndex(x => x.e === e), at = e => L[ix(e)].t;
const after = (i, pre) => L.find((x, j) => j > i && x.e.startsWith(pre));   // by event order
const lastEndBefore = t => L.filter(x => x.t < t && x.e.startsWith("end ")).pop().t;

// 1. after a right answer: no line cut off, next prompt ~0.8 s after the voice stops
const c1 = at("CLICK1"), p1 = after(ix("CLICK1"), "PROMPT").t;
const cutOff = L.filter(x => x.t > c1 + 5 && x.t <= p1 && x.e.startsWith("cancel "));
const beat = p1 - lastEndBefore(p1);
console.log(`round 1: teaching ran ${((p1 - c1) / 1000).toFixed(1)}s, next prompt ${beat} ms after speech ended, ${cutOff.length} lines cut off`);
console.assert(cutOff.length === 0, "teaching was cut off by the next question");
console.assert(beat >= 700 && beat <= 1200, "beat after speech should be ~800 ms, was " + beat);

// 2. a dropped utterance is skipped after the 4 s start guard, not after the length guard
const di = L.findIndex((x, j) => j > ix("CLICK2") && x.e === "dropped"), d = L[di].t, nx = after(di, "speak ").t;
console.log(`dropped line: queue moved on after ${nx - d} ms`);
console.assert(nx - d >= 3900 && nx - d <= 4300, "start guard should be 4 s, was " + (nx - d));

// 3. leaving the activity: the old round never fires
const stray = after(ix("HOME"), "PROMPT");
console.log(`after going home: ${stray ? "STRAY PROMPT " + stray.e : "no stray round"}`);
console.assert(!stray, "old round fired after goHome");
