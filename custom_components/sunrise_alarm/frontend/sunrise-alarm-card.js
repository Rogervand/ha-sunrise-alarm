/*
 * Sunrise Alarm Card — served by the sunrise_alarm integration.
 * type: custom:sunrise-alarm-card
 * entity: sensor.<alarm>_next_alarm
 */

const CARD_VERSION = "0.1.0";
const DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

const STYLE = `
  :host { display: block; }
  ha-card {
    position: relative; overflow: hidden;
    padding: 16px 16px 14px;
    transition: background 600ms ease;
  }
  ha-card.pre_wake {
    background: linear-gradient(180deg,
      color-mix(in srgb, #ff9a3c 10%, var(--ha-card-background, var(--card-background-color))) 0%,
      var(--ha-card-background, var(--card-background-color)) 75%);
  }
  ha-card.ringing, ha-card.snoozed {
    background: linear-gradient(180deg,
      color-mix(in srgb, #ffb547 22%, var(--ha-card-background, var(--card-background-color))) 0%,
      var(--ha-card-background, var(--card-background-color)) 85%);
  }
  .sun {
    position: absolute; left: 50%; bottom: -140px; width: 240px; height: 240px;
    margin-left: -120px; border-radius: 50%; pointer-events: none;
    background: radial-gradient(circle, rgba(255,190,90,.45) 0%, rgba(255,150,60,0) 70%);
    opacity: 0; transform: translateY(40px);
    transition: opacity 900ms ease, transform 1400ms ease;
  }
  ha-card.pre_wake .sun { opacity: .6; transform: translateY(0); }
  ha-card.ringing .sun, ha-card.snoozed .sun { opacity: 1; transform: translateY(-30px); }
  .content { position: relative; }
  .top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .name { font-size: 15px; font-weight: 500; color: var(--secondary-text-color);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .time-row { display: flex; align-items: baseline; gap: 6px; margin: 2px 0 2px; position: relative; }
  .time {
    font-size: 56px; line-height: 1.05; font-weight: 300; letter-spacing: -1.5px;
    color: var(--primary-text-color); font-variant-numeric: tabular-nums;
    background: none; border: 0; padding: 0; cursor: pointer; font-family: inherit;
  }
  .time:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 4px; border-radius: 6px; }
  .ampm { font-size: 18px; color: var(--secondary-text-color); font-weight: 400; }
  .off .time, .off .ampm { color: var(--disabled-text-color, #9e9e9e); }
  input[type=time] {
    position: absolute; inset: 0; opacity: 0; width: 100%; height: 100%;
    cursor: pointer; border: 0; padding: 0; font-size: 16px;
  }
  .summary { font-size: 14px; color: var(--secondary-text-color); min-height: 20px; }
  .summary b { color: var(--primary-text-color); font-weight: 500; }
  .days { display: flex; gap: 6px; margin-top: 14px; }
  .day {
    flex: 1; min-width: 0; height: 36px; border-radius: 18px; cursor: pointer;
    border: 1px solid var(--divider-color); background: transparent;
    color: var(--secondary-text-color); font: 500 13px/1 inherit; font-family: inherit;
    transition: background 150ms, color 150ms, border-color 150ms;
  }
  .day.on { background: var(--primary-color); border-color: var(--primary-color);
    color: var(--text-primary-color, #fff); }
  .off .day.on { background: var(--disabled-text-color, #9e9e9e);
    border-color: var(--disabled-text-color, #9e9e9e); }
  .day:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
  .actions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 16px; }
  .actions.single { grid-template-columns: 1fr; }
  .btn {
    height: 52px; border-radius: 14px; border: 0; cursor: pointer;
    font: 500 16px/1 inherit; font-family: inherit;
    display: flex; align-items: center; justify-content: center; gap: 8px;
  }
  .btn ha-icon { --mdc-icon-size: 22px; }
  .snooze { background: color-mix(in srgb, var(--primary-text-color) 8%, transparent);
    color: var(--primary-text-color); }
  .dismiss { background: #f08a24; color: #fff; }
  .warn { color: var(--error-color); font-size: 14px; }
  .meta { margin-top: 12px; display: flex; gap: 14px; font-size: 13px;
    color: var(--secondary-text-color); flex-wrap: wrap; }
  .meta span { display: inline-flex; align-items: center; gap: 4px; }
  .meta ha-icon { --mdc-icon-size: 16px; }
`;

function fireEvent(node, type, detail) {
  node.dispatchEvent(new CustomEvent(type, { detail, bubbles: true, composed: true }));
}

class SunriseAlarmCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("sunrise-alarm-card-editor");
  }

  static getStubConfig(hass) {
    const entity = Object.keys(hass.states).find(
      (id) => id.startsWith("sensor.") && hass.states[id].attributes.config_entry_id &&
        hass.states[id].attributes.entities && "alarm_time" in hass.states[id].attributes.entities
    );
    return { entity: entity || "" };
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Set 'entity' to an alarm's Next alarm sensor");
    }
    this._config = { show_days: true, show_details: true, ...config };
    this._key = null;
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const key = this._stateKey();
    if (key !== this._key) {
      this._key = key;
      this._render();
    }
  }

  getCardSize() { return 4; }

  getGridOptions() { return { columns: 6, min_columns: 4, rows: "auto" }; }

  _stateKey() {
    const st = this._hass && this._hass.states[this._config?.entity];
    if (!st) return "missing";
    const ents = st.attributes.entities || {};
    const ids = [ents.enabled, ents.alarm_time, ...Object.values(ents.days || {})];
    return [st.state, st.last_updated, this._hass.locale?.time_format, this._hass.language,
      ...ids.map((id) => this._hass.states[id]?.state)].join("|");
  }

  _use24h() {
    const fmt = this._hass.locale?.time_format;
    if (fmt === "24") return true;
    if (fmt === "12") return false;
    const lang = this._hass.locale?.language || this._hass.language || navigator.language;
    return !new Intl.DateTimeFormat(lang, { hour: "numeric" }).resolvedOptions().hour12;
  }

  _fmt(hhmm) {
    const [h, m] = hhmm.split(":").map(Number);
    const mm = String(m).padStart(2, "0");
    if (this._use24h()) return { time: `${String(h).padStart(2, "0")}:${mm}`, ampm: "" };
    return { time: `${((h + 11) % 12) + 1}:${mm}`, ampm: h < 12 ? "AM" : "PM" };
  }

  _fmtDate(d) {
    const f = this._fmt(`${d.getHours()}:${d.getMinutes()}`);
    return `${f.time}${f.ampm ? " " + f.ampm : ""}`;
  }

  _whenText(d) {
    const now = new Date();
    const start = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
    const diff = Math.round((start(d) - start(now)) / 86400000);
    const lang = this._hass.locale?.language || this._hass.language;
    if (diff === 0) return "today";
    if (diff === 1) return "tomorrow";
    return new Intl.DateTimeFormat(lang, { weekday: "long" }).format(d);
  }

  _remaining(d) {
    const mins = Math.max(0, Math.round((d - new Date()) / 60000));
    const h = Math.floor(mins / 60), m = mins % 60;
    if (h >= 24) return "";
    if (!h) return `in ${m} min`;
    return m ? `in ${h} h ${m} min` : `in ${h} h`;
  }

  _call(domain, service, data) {
    return this._hass.callService(domain, service, data).catch((err) => {
      fireEvent(this, "hass-notification", { message: err.message || String(err) });
    });
  }

  _render() {
    if (!this._config || !this._hass) return;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const root = this.shadowRoot;
    const st = this._hass.states[this._config.entity];

    if (!st || !st.attributes.entities) {
      root.innerHTML = `<style>${STYLE}</style><ha-card><div class="warn">
        Entity ${this._config.entity} not found, or it isn't a Sunrise Alarm "Next alarm" sensor.
      </div></ha-card>`;
      return;
    }

    const a = st.attributes;
    const ents = a.entities;
    const status = a.status || "idle";
    const enabled = a.enabled;
    const name = this._config.name || (st.attributes.friendly_name || "").replace(/\s*Next alarm$/i, "") || "Alarm";
    const t = this._fmt(a.alarm_time || "07:00");
    const days = a.days || [];
    const lang = this._hass.locale?.language || this._hass.language;
    const dayLetters = DAYS.map((_, i) =>
      new Intl.DateTimeFormat(lang, { weekday: "narrow" }).format(new Date(2024, 0, 1 + i))); // 2024-01-01 is a Monday
    const dayLong = DAYS.map((_, i) =>
      new Intl.DateTimeFormat(lang, { weekday: "long" }).format(new Date(2024, 0, 1 + i)));

    let summary = "";
    const next = st.state && !["unknown", "unavailable"].includes(st.state) ? new Date(st.state) : null;
    if (status === "ringing") summary = "<b>Wake up!</b>";
    else if (status === "snoozed" && a.snooze_until)
      summary = `Snoozed until <b>${this._fmtDate(new Date(a.snooze_until))}</b>`;
    else if (status === "pre_wake") summary = `Lights fading in · rings at <b>${t.time}${t.ampm ? " " + t.ampm : ""}</b>`;
    else if (!enabled) summary = "Off";
    else if (next) {
      const rem = this._remaining(next);
      summary = `Rings <b>${this._whenText(next)}</b>${rem ? " · " + rem : ""}`;
      if (!days.length) summary += " · once";
    }

    const active = ["ringing", "snoozed", "pre_wake"].includes(status);
    const fade = a.light_fade_minutes || 0;

    root.innerHTML = `
      <style>${STYLE}</style>
      <ha-card class="${status} ${enabled || active ? "" : "off"}">
        <div class="sun"></div>
        <div class="content">
          <div class="top">
            <div class="name">${name}</div>
            <ha-switch aria-label="Alarm on/off" ${enabled ? "checked" : ""}></ha-switch>
          </div>
          <div class="time-row">
            <button class="time" aria-label="Change alarm time" tabindex="-1">${t.time}</button>
            ${t.ampm ? `<span class="ampm">${t.ampm}</span>` : ""}
            <input type="time" aria-label="Alarm time" value="${a.alarm_time}">
          </div>
          <div class="summary">${summary}</div>
          ${this._config.show_days ? `
          <div class="days" role="group" aria-label="Repeat days">
            ${DAYS.map((d, i) => `<button class="day ${days.includes(d) ? "on" : ""}" data-day="${d}"
                aria-pressed="${days.includes(d)}" aria-label="${dayLong[i]}">${dayLetters[i]}</button>`).join("")}
          </div>` : ""}
          ${active ? `
          <div class="actions ${status === "ringing" ? "" : "single"}">
            ${status === "ringing" ? `<button class="btn snooze"><ha-icon icon="mdi:alarm-snooze"></ha-icon>Snooze</button>` : ""}
            <button class="btn dismiss"><ha-icon icon="mdi:alarm-off"></ha-icon>${status === "pre_wake" ? "Skip today" : "Dismiss"}</button>
          </div>` : ""}
          ${this._config.show_details && !active && fade > 0 && enabled ? `
          <div class="meta"><span><ha-icon icon="mdi:weather-sunset-up"></ha-icon>Lights from ${fade} min before</span></div>` : ""}
        </div>
      </ha-card>`;

    root.querySelector("ha-switch").addEventListener("change", (ev) => {
      this._call("switch", ev.target.checked ? "turn_on" : "turn_off", { entity_id: ents.enabled });
    });
    root.querySelector("input[type=time]").addEventListener("change", (ev) => {
      if (ev.target.value) this._call("time", "set_value", { entity_id: ents.alarm_time, time: `${ev.target.value}:00` });
    });
    root.querySelectorAll(".day").forEach((btn) =>
      btn.addEventListener("click", () => {
        const id = ents.days[btn.dataset.day];
        this._call("switch", btn.classList.contains("on") ? "turn_off" : "turn_on", { entity_id: id });
      }));
    const snooze = root.querySelector(".snooze");
    if (snooze) snooze.addEventListener("click", () => this._call("button", "press", { entity_id: ents.snooze }));
    const dismiss = root.querySelector(".dismiss");
    if (dismiss) dismiss.addEventListener("click", () => this._call("button", "press", { entity_id: ents.dismiss }));
  }

  connectedCallback() {
    // Refresh the "in X min" countdown once a minute
    this._tick = setInterval(() => { this._key = null; if (this._hass) this.hass = this._hass; }, 60000);
  }

  disconnectedCallback() { clearInterval(this._tick); }
}

class SunriseAlarmCardEditor extends HTMLElement {
  setConfig(config) { this._config = config; this._render(); }

  set hass(hass) { this._hass = hass; if (this._form) this._form.hass = hass; else this._render(); }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (s) => ({
        entity: "Alarm (Next alarm sensor)", name: "Name (optional)",
        show_days: "Show day buttons", show_details: "Show light fade info",
      })[s.name] || s.name;
      this._form.addEventListener("value-changed", (ev) =>
        fireEvent(this, "config-changed", { config: ev.detail.value }));
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = [
      { name: "entity", required: true,
        selector: { entity: { integration: "sunrise_alarm", domain: "sensor", device_class: "timestamp" } } },
      { name: "name", selector: { text: {} } },
      { name: "show_days", selector: { boolean: {} } },
      { name: "show_details", selector: { boolean: {} } },
    ];
    this._form.data = { show_days: true, show_details: true, ...this._config };
  }
}

if (!customElements.get("sunrise-alarm-card")) {
  customElements.define("sunrise-alarm-card", SunriseAlarmCard);
  customElements.define("sunrise-alarm-card-editor", SunriseAlarmCardEditor);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "sunrise-alarm-card",
    name: "Sunrise Alarm",
    description: "Set and control a Sunrise Alarm Clock",
    preview: true,
    documentationURL: "https://github.com/Rogervand/ha-sunrise-alarm",
  });
  console.info(`%c SUNRISE-ALARM-CARD %c ${CARD_VERSION} `,
    "background:#f08a24;color:#fff;font-weight:600", "background:#333;color:#fff");
}
