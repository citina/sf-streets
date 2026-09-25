# Style updates from ticket-clock to pick up here

On 2026-09-25 Citina reworked LA Street Rules and USC Ticket Clock (ticket-clock commit `9204808`, live). This page was
ported from LA Street Rules before that, so it still has the old styles (checked 2026-09-25: `--ink-3:#8a8880` on text,
sizes 10.5–13px, `Use my location`, the tooltip without the fix, method as a `<dl>`, a blue location dot).
Port these when the page gets to them. The reference is `~/Desktop/ticket-clock/docs/streets/index.html`.

## 1. Type: five sizes, no light-gray text

Her complaint was "too many small gray text". The old pages used 13 sizes under 20px (9.5 to 18.5), and the lightest gray
`#8a8880` is 3.2:1 contrast on `--plane`, below the 4.5:1 minimum for small text.

| Size | For |
|---|---|
| 12px | mono uppercase labels (mast, `.code`, `.p-eyebrow`, `.card h4`, `.ctl-label`, stat keys like `.verdict .k` / `.glance .k`), chart ticks, map tags |
| 14px | small text: notes, legends (including the legend's note line), captions, `.evid`, chip.sm, suggestion notes, tooltips, sources |
| 15px | the block card and search messages (`.rule-line`, `.side-txt`, `.p-sub`, kind rows, `.find-msg`) |
| 16px | reading text (method, asides, About) and **every text input** (under 16px, iPhones zoom in when it's tapped) |
| 18.5px | the lede |

- **Text color:** use `--ink` or `--ink-2`, never `--ink-3`. In light mode `--ink-3` is now `#65645e` (5.3:1), kept only for small non-text bits (chevrons, arrows).
- **SF classes still to move:**
  - 13px: `.mode .m-sub`, `.chip.sm`, `.legend`, `footer`
  - 12.5px: `.note`, `.sugg li small`, `#tip`
  - 11px: `.mast`, `.code`, `.card h4`, `.maptag`, `.src`
  - 10.5px: `.ctl-label`, `.p-eyebrow`, `.verdict .k`, `.glance .k`, `.hours-ax`
- **Tooltip:** `#tip` is 14px with `max-width:280px`.

## 2. Intro

One lede paragraph, not a lede plus a `.lede-note`. LA's is "Enter an LA address to see its street-sweeping schedule and
next sweep dates, its meters, and recent parking-ticket patterns. Most LA streets are swept every other week, even
where the sign shows only the day. See an example" (the link scrolls to the example section, shown once it loads).
Here each mode has its own lede: keep each to one paragraph.

## 3. Find bar

- **Layout:** she kept the original: the dark "location" button first, the search box beside it (under it on phones). She tried
  search first with an "or" and an outlined button, then asked for the old design back.
- **Button label:** "Show blocks near me", not "Use my location".
- **Line under the bar:** her wording, with no "exact":
  `<p class="loc-note" id="locNote">“Show blocks near me” only centers the map. The page doesn't send or save your location.</p>`
  (button gets `aria-describedby="locNote"`; `.loc-note{font-size:14px;color:var(--ink-2);margin:8px 0 0}`).
  Keep it true: the page must not send the coordinates anywhere. If the plan's direct data.sf.gov queries for the visible area
  happen, recheck this line and the method note.
- **Magnifier in the search box**, placeholder starting with "Enter":
  ```html
  <div class="searchbox">
    <svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="6.8" cy="6.8" r="5" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="m10.6 10.6 4.4 4.4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
    <input type="search" id="q" placeholder="Enter an address or neighborhood" …>
  ```
  ```css
  .searchbox>svg{position:absolute;left:11px;top:12px;width:16px;height:16px;color:var(--ink-2);pointer-events:none}
  .searchbox input{font:16px "Barlow",system-ui,sans-serif; … padding:8px 10px 8px 34px}
  ```
  The placeholder must fit a 360px phone after the icon's 34px: about 270px of 16px Barlow. "Enter a street, address or
  neighborhood" (274px) doesn't; this page's "Street, address, corner or neighborhood" would need shortening too
  (measure it with a canvas `measureText` in the page).

## 4. "Your location" dot: red, not blue

The blue dot got lost among the blue block lines. Add `--map-you:#d62828;` to the `--map-*` tokens, then:
```js
S('circle',{cx:fix[0],cy:fix[1],r:16*u,fill:'var(--map-you)','fill-opacity':.18,stroke:'var(--map-you)','stroke-opacity':.45,'stroke-width':1,'vector-effect':'non-scaling-stroke'},gYou);
S('circle',{cx:fix[0],cy:fix[1],r:7*u,fill:'var(--map-you)',stroke:'#fff','stroke-width':3,'vector-effect':'non-scaling-stroke'},gYou);
```
Legend swatch: `width:14px;height:14px;border-radius:50%;background:var(--map-you);border:2.5px solid #fff;box-shadow:0 0 0 3px color-mix(in oklab,var(--map-you) 25%,transparent)`.

## 5. Tooltips

- Mouse only (`if(e.pointerType==='mouse')`): on touch screens a finger scrolling past flashed them.
- Measure the tip at the top left, then clamp it on screen. Measured where it last was (near the right edge) it came out
  narrow and tall and could go off the top:
  ```js
  function showTip(e, html){ tip.innerHTML=html; tip.style.left=tip.style.top='0px'; tip.hidden=false; const r=tip.getBoundingClientRect(); let x=e.clientX+14, y=e.clientY+14;
    if(x+r.width>innerWidth-8) x=e.clientX-r.width-14; if(y+r.height>innerHeight-8) y=e.clientY-r.height-14;
    tip.style.left=Math.max(8,Math.min(x,innerWidth-r.width-8))+'px'; tip.style.top=Math.max(8,Math.min(y,innerHeight-r.height-8))+'px'; }
  ```
- No tooltip on anything that opens the same text inline (LA's ticket-kind rows had one; it covered the opened note).

## 6. "How this was measured": closed rows

Each `dt`/`dd` became `<details><summary>Data</summary><p>…</p></details>`, **all closed** (she asked for Limits closed
too), Sources is the last row, and there's **no line under the last row** (she asked). This cut the section from ~2,250px
to ~450px on a phone. Here both method `<dl>`s (drive and walk) would change.
```css
.method{max-width:var(--measure);margin:18px 0 0}
.method details{border-top:1px solid var(--rule)}
.method summary{cursor:pointer;list-style:none;display:flex;justify-content:space-between;gap:12px;padding:12px 2px;font-weight:600}
.method summary::-webkit-details-marker{display:none}
.method summary::after{content:"+";color:var(--ink-2);font-weight:400}
.method details[open] summary::after{content:"−"}
.method details>p,.method details>ul{color:var(--ink-2);margin:0 0 16px}
.method details>ul{padding-left:18px;font-size:15px}
.method details>ul li+li{margin-top:4px}
```

## 7. The block card (LA wording, adapt for SFMTA)

- **Subtitle:** "505 LADOT tickets since Sep 17, 2024" (not "Worked out from …").
- **No sweeping schedule:** "**No sweeping schedule found.** This block isn't on any of StreetsLA's posted sweeping routes,
  and no sweeping tickets have been written here since … Check your street at streets.lacity.gov." (with a few tickets:
  "…routes, though 2 sweeping tickets have been written here since …").
- **No meters:** "No meters appear in LADOT's inventory for this block, and no meter tickets since …".
- **Metered block:** "12 metered spaces on this block." She removed "Their hours are on the meters." SF has
  meter hours (`qq7v-hds4`), so show them instead.
- **Card's last line:** "This card is worked out from LADOT citations recorded since … Ticket history may not include every
  rule that applies here."
- **Ticket kinds:** 5 before "Show all N kinds" (was 8). On phones the count/bar column is 76px (`@media (max-width:480px)`)
  so the kind's line wraps less, and a time range never breaks inside ("9–10 pm"):
  ```js
  function usual(r){ return r.map(([a,b])=>fmtRange(a,b).replace(/ /g,' ').replace('–','⁠–⁠')).join(' or '); }
  ```
- **A kind's dot chart:**
  - A bold heading above it: "What time of day these tickets were written" (`.kchart-t{font-size:14px;font-weight:600;margin:12px 0 6px}`).
  - Axis labels "12am 3am 6am 9am noon 3pm 6pm 9pm 12am", every 6 hours when the chart is under 340px.
  - The note under it: "Each dot is about N tickets, stacked by the half hour."

## 8. About section

- **Paragraph:** shortened to about 88 words. Keep "USC Viterbi" wording (never just "USC"); the full origin story lives only on her website.
- **Cards:**
  - LA Street Rules: "Every block in the City of Los Angeles: its sweeping schedule, its meters, and what gets ticketed there."
  - Curb Log: "Available parking right now on Vermont Ave by W 36th St, and how it usually changes on weekdays, from LADOT's parking sensors."

## Her wording rules that came with these

- Never claim 100% unless it's literally 100%.
- Labels say literally what they mean (for example, "no sweeping schedule found", not "no sweeping").
- No "safe time" claims.
- Privacy lines promise only what the page itself does.
