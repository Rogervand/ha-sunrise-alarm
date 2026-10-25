/*
 * Sunrise Alarm Card — served by the sunrise_alarm integration.
 *
 *   type: custom:sunrise-alarm-card
 *   entity: sensor.bedroom_next_alarm
 *
 * One card per alarm. Everything (time, days, on/off, Sonos speaker and
 * favorite, volume, lights, brightness, ramp time) is set from the card.
 */

const CARD_VERSION = "1.1.0";
const DOMAIN = "sunrise_alarm";
const DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
const SLIDERS = ["volume_start", "volume_end", "brightness", "ramp_minutes", "run_minutes"];

const STYLE = `
  :host { display: block; }
  ha-card { position: relative; overflow: hidden; padding: 16px; }
  ha-card.waking {
    background: linear-gradient(180deg,
      color-mix(in srgb, #ffb547 20%, var(--ha-card-background, var(--card-background-color))) 0%,
      var(--ha-card-background, var(--card-background-color)) 70%);
  }
  .top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .name { font-size: 15px; font-weight: 500; color: var(--secondary-text-color);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .time-row { display: flex; align-items: baseline; gap: 6px; margin-top: 2px; position: relative; width: max-content; }
  .time { font-size: 56px; line-height: 1.05; font-weight: 300; letter-spacing: -1.5px;
    color: var(--primary-text-color); font-variant-numeric: tabular-nums; }
  .ampm { font-size: 18px; color: var(--secondary-text-color); }
  .off .time, .off .ampm { color: var(--disabled-text-color, #9e9e9e); }
  .time-row input { position: absolute; inset: 0; opacity: 0; width: 100%; height: 100%;
    cursor: pointer; border: 0; padding: 0; font-size: 16px; }
  .summary { font-size: 14px; color: var(--secondary-text-color); min-height: 20px; }
  .summary b { color: var(--primary-text-color); font-weight: 500; }
  .days { display: flex; gap: 6px; margin-top: 14px; }
  .day { flex: 1; min-width: 0; height: 36px; border-radius: 18px; cursor: pointer;
    border: 1px solid var(--divider-color); background: transparent;
    color: var(--secondary-text-color); font: 500 13px/1 inherit; font-family: inherit; }
  .day.on { background: var(--primary-color); border-color: var(--primary-color);
    color: var(--text-primary-color, #fff); }
  .off .day.on { background: var(--disabled-text-color, #9e9e9e); border-color: var(--disabled-text-color, #9e9e9e); }
  button:focus-visible, select:focus-visible, input:focus-visible, .toggle:focus-visible {
    outline: 2px solid var(--primary-color); outline-offset: 2px; }
  .stop { width: 100%; height: 52px; margin-top: 14px; border: 0; border-radius: 14px;
    background: #f08a24; color: #fff; font: 500 16px/1 inherit; font-family: inherit; cursor: pointer; }
  .stop[hidden] { display: none; }

  .toggle { display: block; margin: 14px -16px -16px; padding: 12px 16px;
    border-top: 1px solid var(--divider-color); cursor: pointer; background: none; border-left: 0;
    border-right: 0; border-bottom: 0; width: calc(100% + 32px); text-align: left; font-family: inherit;
    color: var(--primary-text-color); }
  .toggle .head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .toggle .label { font-size: 14px; font-weight: 500; }
  .brief { display: grid; grid-template-columns: auto 1fr; column-gap: 12px; row-gap: 4px;
    margin-top: 8px; font-size: 13px; }
  .brief .k { color: var(--secondary-text-color); }
  .brief .v { color: var(--primary-text-color); min-width: 0; overflow-wrap: anywhere; }
  .brief .v.none { color: var(--secondary-text-color); }
  .brief .sub, .chip .sub { color: var(--secondary-text-color); }
  .brief [hidden] { display: none; }
  .open .brief { display: none; }
  .chev { width: 18px; height: 18px; flex: none; transition: transform 150ms; fill: var(--secondary-text-color); }
  .open .chev { transform: rotate(180deg); }
  .open .toggle { margin-bottom: 0; }

  .settings { display: none; padding-top: 4px; }
  .open .settings { display: block; }
  .group { margin-top: 14px; }
  .group h3 { margin: 0 0 8px; font-size: 12px; font-weight: 600; letter-spacing: .06em;
    text-transform: uppercase; color: var(--secondary-text-color); }
  .field { margin-bottom: 10px; }
  .field > label, .slider-head { display: flex; justify-content: space-between; font-size: 13px;
    color: var(--secondary-text-color); margin-bottom: 4px; }
  .slider-head b { color: var(--primary-text-color); font-weight: 500; font-variant-numeric: tabular-nums; }
  select { width: 100%; height: 40px; padding: 0 10px; border-radius: 10px; font: 14px inherit;
    font-family: inherit; border: 1px solid var(--divider-color); color: var(--primary-text-color);
    background: var(--ha-card-background, var(--card-background-color)); }
  select:disabled { opacity: .5; }
  input[type=range] { width: 100%; margin: 0; accent-color: var(--primary-color); height: 28px; }
  .hint { font-size: 12px; color: var(--secondary-text-color); margin-top: 4px; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
  .chip { display: inline-flex; align-items: center; gap: 4px; height: 30px; padding: 0 4px 0 12px;
    border-radius: 15px; font-size: 13px; color: var(--primary-text-color);
    background: color-mix(in srgb, var(--primary-text-color) 8%, transparent); }
  .chip button { width: 24px; height: 24px; border: 0; border-radius: 12px; cursor: pointer;
    background: none; color: var(--secondary-text-color); font-size: 16px; line-height: 1; padding: 0; }
  .test { margin-top: 6px; height: 40px; padding: 0 16px; border-radius: 10px; cursor: pointer;
    border: 1px solid var(--divider-color); background: transparent; color: var(--primary-text-color);
    font: 500 14px inherit; font-family: inherit; }
  .warn { color: var(--error-color); font-size: 14px; }
  .loading { color: var(--secondary-text-color); font-size: 14px; min-height: 120px; }
`;

const CHEVRON = `<svg class="chev" viewBox="0 0 24 24" aria-hidden="true"><path d="M7.41 8.58 12 13.17l4.59-4.59L18 10l-6 6-6-6z"/></svg>`;

function fireEvent(node, type, detail) {
  node.dispatchEvent(new CustomEvent(type, { detail, bubbles: true, composed: true }));
}
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

class SunriseAlarmCard extends HTMLElement {
  static getConfigElement() { return document.createElement("sunrise-alarm-card-editor"); }

  static getStubConfig(hass) {
    const entity = Object.keys(hass.states).find((id) => SunriseAlarmCard.isAlarm(hass.states[id]));
    return { entity: entity || "" };
  }

  static isAlarm(st) {
    return !!(st && st.entity_id.startsWith("sensor.") && st.attributes.config_entry_id &&
      st.attributes.settings && st.attributes.entities);
  }

  setConfig(config) {
    if (!config || !config.entity) throw new Error("Set 'entity' to an alarm's Next alarm sensor");
    this._config = { ...config };
    this._built = false;
    try { this._open = localStorage.getItem(`sunrise-alarm-open:${config.entity}`) === "1"; } catch (e) { this._open = false; }
    if (this._hass) this._render();
  }

  set hass(hass) { this._hass = hass; this._render(); }

  getCardSize() { return this._open ? 10 : 4; }
  getGridOptions() { return { columns: 6, min_columns: 4, rows: "auto" }; }

  connectedCallback() {
    this._tick = setInterval(() => this._hass && this._render(), 60000);
  }
  disconnectedCallback() { clearInterval(this._tick); }

  // ---------------------------------------------------------------- helpers
  get _lang() { return this._hass.locale?.language || this._hass.language || navigator.language; }

  _use24h() {
    const fmt = this._hass.locale?.time_format;
    if (fmt === "24") return true;
    if (fmt === "12") return false;
    return !new Intl.DateTimeFormat(this._lang, { hour: "numeric" }).resolvedOptions().hour12;
  }

  _fmt(hhmm) {
    const [h, m] = hhmm.split(":").map(Number);
    const mm = String(m).padStart(2, "0");
    if (this._use24h()) return { time: `${String(h).padStart(2, "0")}:${mm}`, ampm: "" };
    return { time: `${((h + 11) % 12) + 1}:${mm}`, ampm: h < 12 ? "AM" : "PM" };
  }

  _name(id) { return this._hass.states[id]?.attributes.friendly_name || id; }

  _speakers() {
    const ents = this._hass.entities || {};
    let ids = Object.keys(this._hass.states).filter((id) => id.startsWith("media_player."));
    const sonos = ids.filter((id) => ents[id]?.platform === "sonos");
    if (sonos.length || Object.keys(ents).length) ids = sonos;
    return ids.sort((a, b) => this._name(a).localeCompare(this._name(b)));
  }

  _favorites() {
    const ents = this._hass.entities || {};
    const id = Object.keys(this._hass.states).find((eid) => {
      const st = this._hass.states[eid];
      return eid.startsWith("sensor.") && st.attributes.items && typeof st.attributes.items === "object" &&
        (ents[eid]?.platform === "sonos" || eid.includes("favorites"));
    });
    if (!id) return null;
    return Object.entries(this._hass.states[id].attributes.items)
      .map(([fid, title]) => ({ id: fid, title }))
      .sort((a, b) => a.title.localeCompare(b.title));
  }

  // Live state of the alarm's devices, as short text ("18% · playing", "45%", "off")
  _volumeNow(id) {
    const st = this._hass.states[id];
    if (!st || st.state === "unavailable" || st.state === "unknown") return "unavailable";
    if (st.state === "off") return "off";
    const v = st.attributes.volume_level;
    if (v == null) return st.state;
    const pct = `${Math.round(v * 100)}%`;
    if (st.attributes.is_volume_muted) return `${pct} (muted)`;
    return ["playing", "paused", "idle"].includes(st.state) ? `${pct} · ${st.state}` : pct;
  }

  _brightnessNow(id) {
    const st = this._hass.states[id];
    if (!st || st.state === "unavailable" || st.state === "unknown") return "unavailable";
    if (st.state !== "on") return "off";
    const b = st.attributes.brightness;
    return b == null ? "on" : `${Math.max(1, Math.round(b / 2.55))}%`;
  }

  _lights() {
    return Object.keys(this._hass.states).filter((id) => id.startsWith("light."))
      .sort((a, b) => this._name(a).localeCompare(this._name(b)));
  }

  _update(data) {
    const st = this._hass.states[this._config.entity];
    return this._hass.callService(DOMAIN, "update", { config_entry_id: st.attributes.config_entry_id, ...data })
      .catch((err) => fireEvent(this, "hass-notification", { message: err.message || String(err) }));
  }

  _callService(domain, service, data) {
    return this._hass.callService(domain, service, data)
      .catch((err) => fireEvent(this, "hass-notification", { message: err.message || String(err) }));
  }

  _busy(el) {
    // Don't overwrite a control the user is touching
    return el === this.shadowRoot.activeElement || el.dataset.dragging === "1";
  }

  // ---------------------------------------------------------------- build
  _build() {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const lang = this._lang;
    const dayFmt = (opts) => DAYS.map((_, i) => new Intl.DateTimeFormat(lang, opts).format(new Date(2024, 0, 1 + i)));
    const letters = dayFmt({ weekday: "narrow" }), longs = dayFmt({ weekday: "long" });

    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <ha-card>
        <div class="top">
          <div class="name"></div>
          <ha-switch aria-label="Alarm on/off"></ha-switch>
        </div>
        <div class="time-row">
          <span class="time"></span><span class="ampm"></span>
          <input type="time" aria-label="Alarm time">
        </div>
        <div class="summary"></div>
        <div class="days" role="group" aria-label="Repeat days">
          ${DAYS.map((d, i) => `<button class="day" data-day="${d}" aria-label="${longs[i]}">${letters[i]}</button>`).join("")}
        </div>
        <button class="stop" hidden>Stop</button>

        <button class="toggle" aria-expanded="false">
          <span class="head"><span class="label">Wake-up settings</span>${CHEVRON}</span>
          <span class="brief">
            <span class="k">Station</span><span class="v" data-brief="station"></span>
            <span class="k" data-brief-k="volume">Volume</span><span class="v" data-brief="volume"></span>
            <span class="k">Lights</span><span class="v" data-brief="lights"></span>
            <span class="k">Ramp time</span><span class="v" data-brief="ramp"></span>
            <span class="k">Turns off</span><span class="v" data-brief="run"></span>
          </span>
        </button>
        <div class="settings">
          <div class="group">
            <h3>Music</h3>
            <div class="field"><label for="speaker">Sonos speaker</label><select id="speaker"></select>
              <div class="hint now-volume" hidden></div></div>
            <div class="field"><label for="favorite">Sonos favorite</label><select id="favorite"></select>
              <div class="hint fav-hint" hidden></div></div>
            <div class="field">
              <div class="slider-head"><span>Start volume</span><b data-out="volume_start"></b></div>
              <input type="range" id="volume_start" min="0" max="100" step="1" aria-label="Start volume">
            </div>
            <div class="field">
              <div class="slider-head"><span>End volume</span><b data-out="volume_end"></b></div>
              <input type="range" id="volume_end" min="0" max="100" step="1" aria-label="End volume">
            </div>
          </div>
          <div class="group">
            <h3>Lights</h3>
            <div class="chips"></div>
            <div class="field"><select id="add-light" aria-label="Add a light"></select></div>
            <div class="field">
              <div class="slider-head"><span>Brightness</span><b data-out="brightness"></b></div>
              <input type="range" id="brightness" min="50" max="100" step="5" aria-label="Brightness">
            </div>
          </div>
          <div class="group">
            <h3>Timing</h3>
            <div class="field">
              <div class="slider-head"><span>Ramp time</span><b data-out="ramp_minutes"></b></div>
              <input type="range" id="ramp_minutes" min="1" max="60" step="1" aria-label="Ramp time">
              <div class="hint">Lights rise from off and volume rises from start to end over this time, starting at the alarm time.</div>
            </div>
            <div class="field">
              <div class="slider-head"><span>Turn off after</span><b data-out="run_minutes"></b></div>
              <input type="range" id="run_minutes" min="5" max="300" step="5" aria-label="Turn off after">
              <div class="hint">Counted from the alarm time. Then the music pauses and the lights turn off.</div>
            </div>
            <button class="test">Test now</button>
          </div>
        </div>
      </ha-card>`;

    const $ = (s) => this.shadowRoot.querySelector(s);
    const ents = () => this._hass.states[this._config.entity].attributes.entities;

    $("ha-switch").addEventListener("change", (ev) => this._update({ enabled: ev.target.checked }));
    $(".time-row input").addEventListener("change", (ev) => ev.target.value && this._update({ time: ev.target.value }));
    this.shadowRoot.querySelectorAll(".day").forEach((btn) => btn.addEventListener("click", () => {
      const days = new Set(this._hass.states[this._config.entity].attributes.days);
      days.has(btn.dataset.day) ? days.delete(btn.dataset.day) : days.add(btn.dataset.day);
      this._update({ days: DAYS.filter((d) => days.has(d)) });
    }));
    $(".stop").addEventListener("click", () => this._callService("button", "press", { entity_id: ents().stop }));
    $(".test").addEventListener("click", () => this._callService("button", "press", { entity_id: ents().test }));
    $(".toggle").addEventListener("click", () => {
      this._open = !this._open;
      try { localStorage.setItem(`sunrise-alarm-open:${this._config.entity}`, this._open ? "1" : "0"); } catch (e) { /* ignore */ }
      this._render();
    });

    $("#speaker").addEventListener("change", (ev) => this._update({ speaker: ev.target.value || null }));
    $("#favorite").addEventListener("change", (ev) => {
      const opt = ev.target.selectedOptions[0];
      this._update({ favorite_id: ev.target.value || null, favorite_name: ev.target.value ? opt.textContent : null });
    });
    $("#add-light").addEventListener("change", (ev) => {
      const id = ev.target.value;
      ev.target.value = "";
      if (!id) return;
      const lights = this._hass.states[this._config.entity].attributes.settings.lights || [];
      this._update({ lights: [...lights, id] });
    });
    $(".chips").addEventListener("click", (ev) => {
      const id = ev.target.closest("button")?.dataset.remove;
      if (!id) return;
      const lights = this._hass.states[this._config.entity].attributes.settings.lights || [];
      this._update({ lights: lights.filter((l) => l !== id) });
    });

    for (const key of SLIDERS) {
      const el = $(`#${key}`);
      const out = this.shadowRoot.querySelector(`[data-out="${key}"]`);
      el.addEventListener("pointerdown", () => { el.dataset.dragging = "1"; });
      el.addEventListener("input", () => { out.textContent = this._fmtSlider(key, el.value); });
      el.addEventListener("change", () => {
        el.dataset.dragging = "0";
        const v = Number(el.value);
        const data = { [key]: v };
        // Keep end volume >= start volume
        const s = this._hass.states[this._config.entity].attributes.settings;
        if (key === "volume_start" && v > s.volume_end) data.volume_end = v;
        if (key === "volume_end" && v < s.volume_start) data.volume_start = v;
        // Keep the run time at least as long as the ramp
        if (key === "ramp_minutes" && v > s.run_minutes) data.run_minutes = Math.ceil(v / 5) * 5;
        if (key === "run_minutes" && v < s.ramp_minutes) data.ramp_minutes = v;
        this._update(data);
      });
    }
    this._built = true;
    this._lists = {};
  }

  _fmtSlider(key, v) {
    if (key === "ramp_minutes") return `${v} min`;
    if (key === "run_minutes") return this._fmtDuration(Number(v));
    return `${v}%`;
  }

  _fmtDuration(mins) {
    const h = Math.floor(mins / 60), m = mins % 60;
    return h ? (m ? `${h} h ${m} min` : `${h} h`) : `${m} min`;
  }

  _fmtClock(iso) {
    const d = new Date(iso);
    const t = this._fmt(`${d.getHours()}:${d.getMinutes()}`);
    return `${t.time}${t.ampm ? " " + t.ampm : ""}`;
  }

  _setOptions(sel, key, options, value) {
    // options: [[value, label]]; rebuild only when the list changes
    const sig = JSON.stringify(options);
    if (this._lists[key] !== sig) {
      sel.innerHTML = options.map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join("");
      this._lists[key] = sig;
    }
    if (!this._busy(sel)) sel.value = value ?? "";
  }

  // ---------------------------------------------------------------- render
  _render() {
    if (!this._config || !this._hass) return;
    const st = this._hass.states[this._config.entity];
    if (!SunriseAlarmCard.isAlarm(st)) {
      if (!this.shadowRoot) this.attachShadow({ mode: "open" });
      this._built = false;
      // While Home Assistant is starting (or the alarm hasn't loaded yet) the
      // sensor is missing or unavailable: wait quietly, it fills in by itself.
      const starting = this._hass.config?.state && this._hass.config.state !== "RUNNING";
      const waiting = starting || (st && st.state === "unavailable");
      const html = waiting
        ? `<div class="loading">${esc(this._config.name || "Alarm")} · loading…</div>`
        : `<div class="warn">${esc(this._config.entity)} isn't a Sunrise Alarm "Next alarm" sensor. Pick one in the card editor.</div>`;
      if (this._placeholder !== html) {
        this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card>${html}</ha-card>`;
        this._placeholder = html;
      }
      return;
    }
    this._placeholder = null;
    if (!this._built) this._build();
    const $ = (s) => this.shadowRoot.querySelector(s);
    const a = st.attributes, s = a.settings;
    const waking = a.status === "waking" || a.status === "running";

    const card = $("ha-card");
    card.className = [waking ? "waking" : "", a.enabled || waking ? "" : "off", this._open ? "open" : ""].join(" ");
    $(".name").textContent = this._config.name ||
      (a.friendly_name || "").replace(/\s*Next alarm$/i, "") || "Alarm";
    const sw = $("ha-switch");
    sw.checked = !!a.enabled;
    if (a.enabled) sw.setAttribute("checked", ""); else sw.removeAttribute("checked");

    const t = this._fmt(a.alarm_time);
    $(".time").textContent = t.time;
    $(".ampm").textContent = t.ampm;
    const ti = $(".time-row input");
    if (!this._busy(ti)) ti.value = a.alarm_time;

    $(".summary").innerHTML = this._summary(st);
    this.shadowRoot.querySelectorAll(".day").forEach((b) => {
      const on = a.days.includes(b.dataset.day);
      b.classList.toggle("on", on);
      b.setAttribute("aria-pressed", on);
    });
    $(".stop").hidden = !waking;

    // Collapsed summary: station, live volume, lights with live brightness, ramp time
    const brief = (key, html, plain) => {
      const el = this.shadowRoot.querySelector(`[data-brief="${key}"]`);
      const out = html || "None";
      if (el.dataset.sig !== out) { el.innerHTML = out; el.dataset.sig = out; }
      el.classList.toggle("none", !html);
      el.title = plain || "";
    };
    const station = s.speaker ? `${s.favorite_name || "Resume playback"} on ${this._name(s.speaker)}` : "";
    brief("station", esc(station), station);

    const showVol = !!s.speaker;
    this.shadowRoot.querySelector('[data-brief-k="volume"]').hidden = !showVol;
    this.shadowRoot.querySelector('[data-brief="volume"]').hidden = !showVol;
    if (showVol) {
      const now = this._volumeNow(s.speaker);
      const target = `alarm ${s.volume_start}–${s.volume_end}%`;
      brief("volume", `${esc(now)} <span class="sub">· ${target}</span>`, `Now ${now} · ${target}`);
    }

    const lightsNow = (s.lights || []).map((id) => `${this._name(id)} ${this._brightnessNow(id)}`);
    brief("lights", lightsNow.length
      ? `${esc(lightsNow.join(", "))} <span class="sub">· alarm ${s.brightness}%</span>` : "",
      lightsNow.length ? `Now ${lightsNow.join(", ")} · alarm ${s.brightness}%` : "");
    brief("ramp", `${s.ramp_minutes} min`, `${s.ramp_minutes} min`);
    const run = a.off_at ? `at ${this._fmtClock(a.off_at)}` : `after ${this._fmtDuration(s.run_minutes ?? 60)}`;
    brief("run", esc(run), run);
    $(".toggle").setAttribute("aria-expanded", this._open);

    if (!this._open) return;

    // Music
    const speakers = this._speakers();
    const spOpts = [["", "None"], ...speakers.map((id) => [id, this._name(id)])];
    if (s.speaker && !speakers.includes(s.speaker)) spOpts.push([s.speaker, this._name(s.speaker)]);
    this._setOptions($("#speaker"), "speaker", spOpts, s.speaker);

    const favs = this._favorites();
    const favOpts = [["", s.speaker ? "Resume what was playing" : "Choose a speaker first"]];
    (favs || []).forEach((f) => favOpts.push([f.id, f.title]));
    if (s.favorite_id && !(favs || []).some((f) => f.id === s.favorite_id))
      favOpts.push([s.favorite_id, s.favorite_name || s.favorite_id]);
    const favSel = $("#favorite");
    this._setOptions(favSel, "favorite", favOpts, s.favorite_id);
    favSel.disabled = !s.speaker;
    const nowVol = $(".now-volume");
    nowVol.hidden = !s.speaker;
    if (s.speaker) nowVol.textContent = `Now: ${this._volumeNow(s.speaker)}`;
    const hint = $(".fav-hint");
    hint.hidden = !!favs;
    hint.textContent = "Turn on the \"Sonos favorites\" sensor (Settings → Devices & services → Sonos → entities) to list your favorites.";

    // Lights
    const lights = s.lights || [];
    const chips = lights.map((id) => `<span class="chip">${esc(this._name(id))} <span class="sub">${esc(this._brightnessNow(id))}</span><button data-remove="${esc(id)}" aria-label="Remove ${esc(this._name(id))}">×</button></span>`).join("");
    if ($(".chips").dataset.sig !== chips) { $(".chips").innerHTML = chips; $(".chips").dataset.sig = chips; }
    const avail = this._lights().filter((id) => !lights.includes(id));
    this._setOptions($("#add-light"), "lights", [["", lights.length ? "Add another light…" : "Add a light…"], ...avail.map((id) => [id, this._name(id)])], "");

    for (const key of SLIDERS) {
      const el = $(`#${key}`);
      if (!this._busy(el)) {
        el.value = s[key];
        this.shadowRoot.querySelector(`[data-out="${key}"]`).textContent = this._fmtSlider(key, s[key]);
      }
    }
  }

  _summary(st) {
    const a = st.attributes;
    const off = a.off_at ? ` · turns off at ${esc(this._fmtClock(a.off_at))}` : "";
    if (a.status === "waking") return `<b>Waking up</b>${off}`;
    if (a.status === "running") return `<b>On</b>${off}`;
    if (!a.enabled) return "Off";
    if (!st.state || ["unknown", "unavailable"].includes(st.state)) return "";
    const d = new Date(st.state), now = new Date();
    const start = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
    const diff = Math.round((start(d) - start(now)) / 86400000);
    const when = diff === 0 ? "today" : diff === 1 ? "tomorrow"
      : new Intl.DateTimeFormat(this._lang, { weekday: "long" }).format(d);
    const mins = Math.max(0, Math.round((d - now) / 60000)), h = Math.floor(mins / 60), m = mins % 60;
    const rem = h >= 24 ? "" : !h ? `in ${m} min` : m ? `in ${h} h ${m} min` : `in ${h} h`;
    return `Starts <b>${when}</b>${rem ? " · " + rem : ""}${a.days.length ? "" : " · once"}`;
  }
}

class SunriseAlarmCardEditor extends HTMLElement {
  setConfig(config) { this._config = config; this._render(); }
  set hass(hass) { this._hass = hass; if (this._form) this._form.hass = hass; else this._render(); }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (s) => ({ entity: "Alarm", name: "Name (optional)" })[s.name] || s.name;
      this._form.computeHelper = (s) => s.name === "entity"
        ? "Pick the alarm's \"Next alarm\" sensor. Add new alarms under Settings → Devices & services → Sunrise Alarm Clock."
        : undefined;
      this._form.addEventListener("value-changed", (ev) => fireEvent(this, "config-changed", { config: ev.detail.value }));
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = [
      { name: "entity", required: true,
        selector: { entity: { filter: { integration: DOMAIN, domain: "sensor", device_class: "timestamp" } } } },
      { name: "name", selector: { text: {} } },
    ];
    this._form.data = this._config;
  }
}

if (!customElements.get("sunrise-alarm-card")) {
  customElements.define("sunrise-alarm-card", SunriseAlarmCard);
  customElements.define("sunrise-alarm-card-editor", SunriseAlarmCardEditor);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "sunrise-alarm-card",
    name: "Sunrise Alarm",
    description: "One alarm: time, days, Sonos favorite and lights",
    preview: true,
    documentationURL: "https://github.com/Rogervand/ha-sunrise-alarm",
  });
  console.info(`%c SUNRISE-ALARM-CARD %c ${CARD_VERSION} `,
    "background:#f08a24;color:#fff;font-weight:600", "background:#333;color:#fff");
}
