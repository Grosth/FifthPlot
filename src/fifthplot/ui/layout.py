"""Presentación visual de FifthPlot (sin lógica de generación)."""

import base64
from pathlib import Path


_ASSETS = Path(__file__).parent / "assets"
_MASCOT = _ASSETS / "kitsune-mascot.png"


APP_CSS = """
:root {
  --fp-fox: #db6727;
  --fp-orange: #e86c24;
  --fp-orange-soft: #f2a04d;
  --fp-amber: #e8b257;
  --fp-cream: #f8f2e8;
  --fp-paper: #fffdf8;
  --fp-gray: #ece7df;
  --fp-ink: #42291d;
  --fp-muted: #78685b;
  --fp-sage: #87916c;
}

body, .gradio-container {
  background-color: var(--fp-cream) !important;
  background-image:
    radial-gradient(rgba(126, 96, 66, .055) .45px, transparent .7px),
    linear-gradient(118deg, rgba(255, 255, 255, .24), transparent 48%, rgba(209, 181, 145, .045)) !important;
  background-size: 9px 9px, 100% 100% !important;
  color: var(--fp-ink) !important;
  font-family: "Segoe UI", sans-serif !important;
}

.gradio-container {
  --body-background-fill: var(--fp-cream) !important;
  --body-text-color: var(--fp-ink) !important;
  --block-background-fill: var(--fp-paper) !important;
  --block-border-color: #e8ddcd !important;
  --block-label-background-fill: transparent !important;
  --block-label-background-fill-hover: transparent !important;
  --block-label-text-color: var(--fp-muted) !important;
  --input-background-fill: #fff !important;
  --input-border-color: #d8c7af !important;
  --input-placeholder-color: #a39284 !important;
  --button-primary-background-fill: var(--fp-orange) !important;
  --button-primary-text-color: #fff !important;
  padding: 0 !important;
  max-width: none !important;
}

.fp-shell {
  gap: 1.15rem !important;
  width: min(1360px, 100%) !important;
  margin: 0 auto !important;
  padding: .7rem clamp(1rem, 3vw, 2.5rem) 2rem !important;
}
.fp-header {
  display: flex !important;
  flex-wrap: nowrap !important;
  justify-content: space-between !important;
  align-items: center !important;
  gap: 1.1rem !important;
  padding: .45rem .5rem .9rem !important;
  border: 0 !important;
  border-bottom: 1px solid #ddcfbb !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  color: var(--fp-ink) !important;
}
.fp-brand-lockup-wrap { flex: 0 1 52% !important; width: 52% !important; min-width: 0 !important; }
.fp-brand-lockup-wrap > div { background: transparent !important; border: 0 !important; padding: 0 !important; }
.fp-brand-lockup { display: flex; align-items: center; gap: .3rem; }
.fp-kitsune-logo { display: block; flex: 0 0 auto; width: 140px; height: 105px; object-fit: contain; }
.fp-brand { gap: .08rem !important; }
.fp-brand h1 {
  color: var(--fp-ink) !important;
  font-family: Georgia, "Times New Roman", serif !important;
  font-size: clamp(2rem, 3vw, 2.55rem) !important;
  letter-spacing: -.045em !important;
  margin: 0 !important;
}
.fp-brand p {
  color: #806b58 !important;
  font-size: .62rem !important;
  font-weight: 750 !important;
  letter-spacing: .1em !important;
  white-space: nowrap !important;
  margin: .12rem 0 0 !important;
}
.fp-header-nav { flex: 0 0 45% !important; width: 45% !important; margin-left: auto !important; align-items: center !important; gap: .35rem !important; }
.fp-header-nav > div { flex: 0 0 auto !important; width: auto !important; }
.fp-header-nav button { min-height: 2.55rem !important; padding: .5rem .9rem !important; border-radius: .65rem !important; white-space: nowrap !important; }
.fp-header-nav .fp-nav-current button { color: #713816 !important; background: #ffedd0 !important; border: 1px solid #f3d3a8 !important; box-shadow: none !important; }
.fp-header-nav .fp-nav-future button { color: #817367 !important; font-size: .85rem !important; }
.fp-academic-note { flex: 0 0 auto !important; width: auto !important; margin: 0 .15rem 0 .45rem !important; color: var(--fp-muted) !important; font-size: .82rem !important; white-space: nowrap !important; }
.fp-academic-note p { margin: 0 !important; }
.fp-view { gap: 1.05rem !important; }
.fp-section-heading { margin: .3rem 0 .2rem !important; }
.fp-section-heading h2 {
  color: var(--fp-ink) !important;
  font-family: Georgia, "Times New Roman", serif !important;
  font-size: clamp(1.7rem, 2.5vw, 2rem) !important;
  letter-spacing: -.03em !important;
  margin: 0 0 .25rem !important;
}
.fp-section-heading p { color: var(--fp-muted) !important; margin: 0 !important; }
.fp-entry-options, .fp-story-settings { gap: .85rem !important; align-items: stretch !important; }
.fp-entry-options > div { min-width: 0 !important; }
.fp-entry-card, .fp-writing-card, .fp-story-copy, .fp-illustration,
.fp-story-title {
  border: 1px solid #dfcdb5 !important;
  border-radius: .95rem !important;
  background: var(--fp-paper) !important;
  box-shadow: 0 3px 12px rgba(81, 54, 32, .045) !important;
}
.fp-entry-card {
  height: 350px !important;
  min-height: 350px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  padding: 1.25rem 1.15rem !important;
  color: var(--fp-ink) !important;
}
.fp-photo-card { background: #fffaf0 !important; }
.fp-voice-card { background: #fff8ec !important; }
.fp-entry-icon {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 3.55rem;
  height: 3.55rem;
  margin-bottom: .8rem;
  border: 1px solid #edcf9e;
  border-radius: .85rem;
  color: var(--fp-fox);
  background: #fff0d8;
  font-size: 2rem;
}
.fp-entry-icon svg { display: block; width: 2.8rem; height: 2.8rem; }
.fp-entry-card h3, .fp-writing-heading h3 {
  color: var(--fp-ink) !important;
  font-family: Georgia, "Times New Roman", serif !important;
  font-size: 1.28rem !important;
  font-weight: 700 !important;
  margin: .15rem 0 .45rem !important;
}
.fp-entry-card p, .fp-writing-heading p { color: var(--fp-muted) !important; margin: 0 0 .8rem !important; }
.fp-coming-soon {
  display: inline-flex;
  border-radius: 999px;
  padding: .42rem .8rem;
  color: #776351;
  background: #eee8dc;
  font-size: .82rem;
  font-weight: 700;
}
.fp-writing-card {
  height: 350px !important;
  min-height: 350px !important;
  padding: 1rem 1.1rem !important;
  gap: .55rem !important;
}
.fp-writing-card, .fp-writing-card .wrap, .fp-writing-card .gap {
  background: var(--fp-paper) !important;
  color: var(--fp-ink) !important;
}
.fp-writing-card > div, .fp-writing-card div, .fp-writing-card .prose,
.fp-writing-card fieldset, .fp-writing-card [data-testid="block-info"] {
  background: transparent !important;
  color: var(--fp-ink) !important;
}
.fp-writing-heading { text-align: center !important; }
.fp-writing-heading .fp-entry-icon { margin: 0 auto .45rem !important; }
.fp-writing-heading h3 { margin-top: .1rem !important; }
.fp-writing-card label, .fp-writing-card label span,
.fp-writing-card [data-testid="block-label"] {
  color: var(--fp-muted) !important;
  background: transparent !important;
  padding: 0 !important;
}
.fp-idea-input textarea { min-height: 105px !important; background: white !important; }
.fp-story-settings > div {
  border: 1px solid #e2d4c1 !important;
  border-radius: .8rem !important;
  background: #fcf8ef !important;
  padding: .65rem .85rem !important;
}
.fp-setting-field, .fp-setting-field .wrap, .fp-setting-field .gap {
  background: transparent !important;
}
.fp-setting-label p {
  color: var(--fp-muted) !important;
  font-size: .9rem !important;
  font-weight: 700 !important;
  margin: 0 0 .35rem !important;
}
.fp-story-settings label, .fp-story-settings label span,
.fp-story-settings [data-testid="block-label"],
.fp-story-settings [data-testid="block-label"] *,
.gradio-container label, .gradio-container label *,
.gradio-container [data-testid="block-label"],
.gradio-container [data-testid="block-label"] * {
  color: var(--fp-muted) !important;
  background: transparent !important;
  padding: 0 !important;
}
.fp-availability-note { color: var(--fp-muted) !important; text-align: center !important; font-size: .88rem !important; margin: 0 !important; }
.fp-primary-button button, button.primary {
  min-height: 3.3rem !important;
  width: min(330px, 100%) !important;
  margin: .15rem auto .25rem !important;
  border: 0 !important;
  border-radius: .85rem !important;
  background: var(--fp-orange) !important;
  color: white !important;
  font-family: Georgia, "Times New Roman", serif !important;
  font-size: 1.18rem !important;
  font-weight: 700 !important;
  box-shadow: 0 4px 11px rgba(186, 82, 26, .18) !important;
}
.fp-primary-button button:hover, button.primary:hover { background: #d85e1c !important; }
button.secondary {
  border: 1px solid #d9c6ad !important;
  border-radius: .75rem !important;
  background: #fffaf0 !important;
  color: #5b3a27 !important;
}
button:disabled { opacity: .58 !important; }
input, textarea, select { border-radius: .62rem !important; }
.fp-story-title, .fp-story-copy { padding: 1rem 1.15rem !important; }
.fp-story-title { border: 0 !important; background: transparent !important; box-shadow: none !important; text-align: center !important; }
.fp-story-title h1 {
  color: var(--fp-ink) !important;
  font-family: Georgia, "Times New Roman", serif !important;
  font-size: 2rem !important;
  margin: .1rem 0 .4rem !important;
}
.fp-story-title p { color: var(--fp-muted) !important; }
.fp-scene-counter { text-align: center !important; color: var(--fp-ink) !important; }
.fp-progress-dots { color: var(--fp-orange) !important; letter-spacing: .25rem; }
.fp-story-layout { gap: 1rem !important; align-items: stretch !important; }
.fp-story-copy { min-width: 310px !important; }
.fp-illustration { overflow: hidden !important; min-width: 0 !important; }
.fp-illustration img { border-radius: .75rem !important; }
.fp-narrative { min-height: 230px; color: var(--fp-ink) !important; line-height: 1.72 !important; font-size: 1.04rem !important; }
.fp-narrative h3 { color: var(--fp-fox) !important; font-family: Georgia, "Times New Roman", serif !important; }
.fp-reading-controls { align-items: center !important; gap: .65rem !important; }
.fp-reading-controls > button { min-height: 2.85rem !important; white-space: nowrap !important; }
.fp-audio-player { min-width: 250px !important; border-radius: .7rem !important; background: #fff7ec !important; }
.fp-new-story-button { align-self: center !important; max-width: 260px !important; }
.fp-new-story-button button { background: #fff5df !important; color: #593b28 !important; border: 1px solid #dfc18e !important; }
.fp-accordion, .fp-accordion details, .fp-accordion summary,
.fp-accordion > button {
  border-radius: .8rem !important;
  color: var(--fp-ink) !important;
  background: var(--fp-paper) !important;
  opacity: 1 !important;
}
.fp-accordion summary { padding: .75rem .95rem !important; }
.fp-accordion summary:hover { background: #fff3df !important; }
footer { display: none !important; }

@media (max-width: 900px) {
  .fp-header { flex-wrap: wrap !important; }
  .fp-brand-lockup-wrap { flex: 1 1 100% !important; width: 100% !important; }
  .fp-header-nav { flex: 1 1 100% !important; margin-left: 0 !important; width: 100% !important; }
  .fp-academic-note { margin-left: auto !important; }
  .fp-story-layout { flex-direction: column !important; }
  .fp-story-copy { min-width: 0 !important; }
  .fp-narrative { min-height: auto; }
  .fp-reading-controls { flex-wrap: wrap !important; }
  .fp-audio-player { min-width: min(100%, 320px) !important; }
}
@media (max-width: 640px) {
  .fp-shell { padding: .55rem !important; }
  .fp-header { gap: .55rem !important; padding: .4rem .2rem .7rem !important; }
  .fp-brand-lockup-wrap { flex: 1 1 100% !important; width: 100% !important; }
  .fp-kitsune-logo { width: 86px; height: 64px; }
  .fp-brand h1 { font-size: 1.8rem !important; }
  .fp-brand p { font-size: .5rem !important; letter-spacing: .07em !important; }
  .fp-header-nav button { font-size: .82rem !important; padding: .45rem .55rem !important; }
  .fp-academic-note { display: none !important; }
  .fp-entry-options { flex-direction: column !important; }
  .fp-entry-card, .fp-writing-card { min-height: 220px !important; }
  .fp-story-settings { flex-direction: column !important; }
}
"""


def kitsune_brand_markup() -> str:
    """Load the local kitsune mark and its matching wordmark."""
    mascot = base64.b64encode(_MASCOT.read_bytes()).decode("ascii")
    return f"""
    <div class="fp-brand-lockup">
      <img class="fp-kitsune-logo" src="data:image/png;base64,{mascot}"
           alt="Zorro kitsune sentado con exactamente cinco colas" />
      <div class="fp-brand">
        <h1>FifthPlot</h1>
        <p>CUENTOS LOCALES ACADÉMICOS</p>
      </div>
    </div>
    """
