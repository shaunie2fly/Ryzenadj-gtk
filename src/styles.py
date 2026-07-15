"""CSS styles for the app UI"""

CSS = """
/* Define theme colors and fallbacks */
@define-color semantic_green #30d158;
@define-color semantic_yellow #ffd60a;
@define-color semantic_red #ff3b30;
@define-color warning_red #e01b24;
@define-color sidebar_bg_color mix(@window_bg_color, @window_fg_color, 0.02);

/* ─── Window & Background ─────────────────────────────────── */
window.ryzenadj-win {
    background-color: @window_bg_color;
}

/* ─── Header bar premium aesthetics ───────────────────────── */
.main-header {
    background-color: transparent;
    box-shadow: none;
    border-bottom: none;
}

.sidebar-header {
    background-color: transparent;
    box-shadow: none;
    border-bottom: none;
}

/* ─── Dashboard Flat Aesthetics ────────────────────────────── */
.dashboard-group list,
.dashboard-group listbox,
.dashboard-group .boxed-list {
    background-color: transparent;
    border: none;
    box-shadow: none;
}

.dashboard-group row,
.dashboard-group listboxrow {
    background-color: transparent;
    border: none;
    box-shadow: none;
    padding: 0;
}

/* ─── Dashboard Hero Banner (Ultra-Modern Overhaul) ───────── */
.hero-box {
    padding: 24px;
    margin-bottom: 16px;
    background: radial-gradient(circle at top center, alpha(@accent_bg_color, 0.18) 0%, alpha(@accent_bg_color, 0.05) 40%, transparent 100%);
    border-radius: 24px;
    border: 1px solid alpha(@accent_bg_color, 0.15);
}

/* ─── System Health Summary ─────────────────────────────── */
.health-summary {
    background-color: alpha(@window_fg_color, 0.04);
    background-image: linear-gradient(145deg, alpha(@window_fg_color, 0.03), transparent);
    border: 1px solid alpha(@window_fg_color, 0.08);
    border-radius: 20px;
    padding: 20px 24px;
    margin-bottom: 16px;
}

.health-status-row {
    margin-bottom: 4px;
}

.health-status-pill {
    font-size: 13px;
    font-weight: 900;
    padding: 6px 16px;
    border-radius: 14px;
    letter-spacing: 0.3px;
}

.health-status-pill.optimal {
    background-color: alpha(@semantic_green, 0.18);
    color: @semantic_green;
    border: 1px solid alpha(@semantic_green, 0.4);
}

.health-status-pill.power-limited {
    background-color: alpha(@semantic_yellow, 0.18);
    color: @semantic_yellow;
    border: 1px solid alpha(@semantic_yellow, 0.4);
}

.health-status-pill.current-limited {
    background-color: alpha(#ff9f0a, 0.18);
    color: #ff9f0a;
    border: 1px solid alpha(#ff9f0a, 0.4);
}

.health-status-pill.thermal-limited {
    background-color: alpha(@semantic_red, 0.18);
    color: @semantic_red;
    border: 1px solid alpha(@semantic_red, 0.4);
}

.health-status-pill.idle {
    background-color: alpha(@window_fg_color, 0.08);
    color: alpha(@window_fg_color, 0.65);
    border: 1px solid alpha(@window_fg_color, 0.15);
}

.health-description {
    color: alpha(@window_fg_color, 0.65);
    font-size: 13px;
    margin-top: 10px;
    line-height: 1.4;
}

.health-stats-grid {
    margin-top: 16px;
}

.health-stat {
    background-color: alpha(@window_fg_color, 0.04);
    border: 1px solid alpha(@window_fg_color, 0.06);
    border-radius: 14px;
    padding: 12px 16px;
}

.health-stat-label {
    font-size: 10px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: alpha(@window_fg_color, 0.6);
}

.health-stat-value {
    font-size: 22px;
    font-weight: 900;
    color: @accent_bg_color;
    font-variant-numeric: tabular-nums;
}

.health-stat-sub {
    font-size: 11px;
    color: alpha(@window_fg_color, 0.6);
}

.hero-icon {
    color: @accent_bg_color;
    -gtk-icon-shadow: 0 0 20px alpha(@accent_bg_color, 0.5);
}

.hero-title {
    font-size: 30px;
    font-weight: 1000;
    letter-spacing: -1.2px;
    color: @window_fg_color;
    text-shadow: 0 2px 4px alpha(black, 0.15);
}

.hero-subtitle {
    font-size: 13px;
    font-weight: 700;
    color: alpha(@window_fg_color, 0.65);
}

.hero-cpu-badge {
    background-color: alpha(@accent_bg_color, 0.1);
    color: @accent_bg_color;
    border: 1px solid alpha(@accent_bg_color, 0.25);
    border-radius: 8px;
    padding: 2px 10px;
    font-weight: 900;
    font-size: 11px;
    margin-left: 8px;
}

@keyframes status-pulse {
    0% {
        background-color: alpha(@semantic_green, 0.2);
        border-color: alpha(@semantic_green, 0.4);
    }
    50% {
        background-color: alpha(@semantic_green, 0.4);
        border-color: alpha(@semantic_green, 0.8);
    }
    100% {
        background-color: alpha(@semantic_green, 0.2);
        border-color: alpha(@semantic_green, 0.4);
    }
}

.live-status-pill {
    background-color: alpha(@semantic_green, 0.2);
    color: @semantic_green;
    border: 1px solid alpha(@semantic_green, 0.4);
    border-radius: 14px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

/* ─── Category section headers (Ptyxis Pro) ──────────────── */
.section-title-box {
    margin-top: 24px;
    margin-bottom: 12px;
    padding: 0 4px;
}

.section-title-label {
    font-size: 15px;
    font-weight: bold;
    color: @window_fg_color;
}

.category-icon {
    color: @accent_bg_color;
    margin-right: 8px;
    -gtk-icon-size: 18px;
}

/* ─── Premium Monitor Cards (Glassy Pro Overhaul) ────────── */
.monitor-card {
    background-color: alpha(@window_fg_color, 0.03);
    background-image: linear-gradient(145deg, alpha(@window_fg_color, 0.02), transparent);
    border: 1px solid alpha(@window_fg_color, 0.08);
    border-radius: 20px;
    padding: 16px;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    box-shadow: 0 2px 4px alpha(black, 0.03);
}

.monitor-card:hover {
    background-color: alpha(@window_fg_color, 0.06);
    border-color: alpha(@accent_bg_color, 0.35);
    transform: translateY(-4px);
    box-shadow: 0 8px 16px alpha(black, 0.08);
}

.monitor-name-label {
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    color: alpha(@window_fg_color, 0.65);
}

.monitor-limit-badge {
    font-size: 9.5px;
    font-weight: bold;
    color: @accent_bg_color;
    background-color: alpha(@accent_bg_color, 0.1);
    border: 1px solid alpha(@accent_bg_color, 0.2);
    border-radius: 8px;
    padding: 2px 6px;
}

.monitor-limit-badge.bottleneck {
    background-color: alpha(@semantic_red, 0.2);
    color: @semantic_red;
    border-color: alpha(@semantic_red, 0.5);
    animation: status-pulse 2s infinite cubic-bezier(0.4, 0, 0.2, 1);
}

.monitor-value-label {
    font-size: 24px;
    font-weight: 900;
    color: @accent_bg_color;
    font-variant-numeric: tabular-nums;
}

.monitor-unit-label {
    font-size: 12px;
    font-weight: bold;
    color: alpha(@window_fg_color, 0.6);
    margin-bottom: 3px;
}

.monitor-icon {
    color: alpha(@window_fg_color, 0.4);
    margin-right: 6px;
    -gtk-icon-size: 16px;
}

/* ─── Usage level bars (Ultra-Soft Style) ────────────────── */
progressbar.usage-bar {
    min-height: 8px;
    margin-top: 8px;
    margin-bottom: 4px;
}

progressbar.usage-bar trough {
    border-radius: 4px;
    background-color: alpha(@window_fg_color, 0.06);
    min-height: 8px;
    border: none;
}

progressbar.usage-bar progress {
    border-radius: 4px;
    min-height: 8px;
    border: none;
    transition: background-color 0.4s ease;
}

progressbar.usage-bar.low progress {
    background-color: @semantic_green;
    box-shadow: 0 0 12px alpha(@semantic_green, 0.3);
}

progressbar.usage-bar.medium progress {
    background-color: @semantic_yellow;
    box-shadow: 0 0 12px alpha(@semantic_yellow, 0.3);
}

progressbar.usage-bar.high progress {
    background-color: @semantic_red;
    box-shadow: 0 0 12px alpha(@semantic_red, 0.3);
}

progressbar.usage-bar.bottleneck progress {
    background-color: @semantic_red;
    box-shadow: 0 0 20px alpha(@semantic_red, 0.7);
}

/* ─── Slider rows (Setting Pages) ─────────────────────────── */
.slider-row-item {
    border-radius: 16px;
    margin: 4px 0;
    padding: 4px;
    transition: background-color 0.2s ease;
}

.slider-row-item:hover {
    background-color: alpha(@window_fg_color, 0.03);
}

.live-badge {
    background-color: alpha(@semantic_green, 0.15);
    color: @semantic_green;
    border: 1px solid alpha(@semantic_green, 0.3);
    border-radius: 16px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 900;
    font-variant-numeric: tabular-nums;
}

.target-badge {
    background-color: alpha(@accent_bg_color, 0.12);
    color: @accent_bg_color;
    border: 1px solid alpha(@accent_bg_color, 0.3);
    border-radius: 16px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 900;
    font-variant-numeric: tabular-nums;
}

/* Target badge is wrapped in a MenuButton — show it's clickable */
.target-btn:hover .target-badge {
    background-color: alpha(@accent_bg_color, 0.2);
    border-color: alpha(@accent_bg_color, 0.5);
}

.cpu-badge {
    background-color: @cpu_badge_bg;
    color: @cpu_badge_fg;
    border: 1px solid alpha(@cpu_badge_fg, 0.4);
    border-radius: 10px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 900;
}

.gpu-badge {
    background-color: @gpu_badge_bg;
    color: @gpu_badge_fg;
    border: 1px solid alpha(@gpu_badge_fg, 0.4);
    border-radius: 10px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 900;
}

/* ─── C5 safety guidance elements ─────────────────────────────── */
/* Risk pill: inherent (hardware-independent) risk tag. NOT a safe-zone
   indicator — actual safety depends on cooling, VRM, silicon. */
.risk-pill {
    border-radius: 10px;
    padding: 3px 9px;
    font-size: 10px;
    font-weight: 700;
    border: 1px solid;
}
.risk-pill-label {
    font-size: 10px;
    font-weight: 700;
}
.risk-low {
    background-color: alpha(#26a269, 0.12);
    color: alpha(#26a269, 0.95);
    border-color: alpha(#26a269, 0.35);
}
.risk-moderate {
    background-color: alpha(#e5a50a, 0.14);
    color: alpha(#e5a50a, 0.95);
    border-color: alpha(#e5a50a, 0.4);
}
.risk-high {
    background-color: alpha(#e01b24, 0.14);
    color: alpha(#e01b24, 0.95);
    border-color: alpha(#e01b24, 0.45);
}

/* Plain-language description (always visible, muted) */
.slider-row-plain-desc {
    color: alpha(@window_fg_color, 0.75);
    margin-top: 2px;
}

/* Watch-for hint (smaller, more muted) */
.slider-row-watch-for {
    color: alpha(@window_fg_color, 0.6);
    margin-top: 1px;
    font-style: italic;
}

/* Deviation badge: appears on significant slider changes. Never claims a
   value is safe/unsafe — only flags the magnitude of the change. */
.deviation-badge {
    border-radius: 12px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 700;
    border: 1px solid;
}
.deviation-moderate {
    background-color: alpha(#e5a50a, 0.16);
    color: alpha(#e5a50a, 0.95);
    border-color: alpha(#e5a50a, 0.4);
}
.deviation-major {
    background-color: alpha(#e01b24, 0.16);
    color: alpha(#e01b24, 0.95);
    border-color: alpha(#e01b24, 0.45);
}

/* Category safety banner (top of each tuning sub-tab) */
.category-safety-banner {
    background-color: alpha(@accent_bg_color, 0.08);
    border: 1px solid alpha(@accent_bg_color, 0.25);
    border-radius: 10px;
    padding: 6px 4px;
    margin-bottom: 8px;
}
.category-safety-banner-label {
    color: alpha(@window_fg_color, 0.85);
}

/* ─── Preset buttons (Floating Action Feel) ───────────────── */
.preset-row {
    padding: 16px 24px;
    background-color: transparent;
    border: none;
}

.preset-btn {
    border-radius: 28px;
    padding: 10px 28px;
    font-weight: 900;
    font-size: 15px;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    min-height: 48px;
    border: 1px solid transparent;
}

.preset-btn:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px alpha(black, 0.2);
}

.btn-power-saving {
    background-color: alpha(@semantic_green, 0.18);
    color: @semantic_green;
    border-color: alpha(@semantic_green, 0.4);
}

.btn-max-performance {
    background-color: alpha(@semantic_red, 0.18);
    color: @semantic_red;
    border-color: alpha(@semantic_red, 0.4);
}

/* ─── Apply button (High Impact) ──────────────────────────── */
.apply-btn {
    background-color: alpha(@window_fg_color, 0.08);
    color: alpha(@window_fg_color, 0.65);
    border-radius: 28px;
    padding: 10px 40px;
    font-weight: 900;
    font-size: 15px;
    min-height: 48px;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    border: 1px solid alpha(@window_fg_color, 0.1);
}

/* When there are unsaved changes, make the button prominent */
.apply-btn.pending {
    background-color: @accent_bg_color;
    color: @accent_fg_color;
    border-color: transparent;
    box-shadow: 0 6px 16px alpha(@accent_bg_color, 0.35);
}

.apply-btn.pending:hover {
    background-color: shade(@accent_bg_color, 1.25);
    transform: translateY(-4px);
    box-shadow: 0 12px 28px alpha(@accent_bg_color, 0.5);
}

/* Idle (no pending changes) hover — subtle */
.apply-btn:hover {
    background-color: alpha(@window_fg_color, 0.12);
    color: @window_fg_color;
}

/* ─── Navigation & Sidebar (Ptyxis Style) ────────────────── */
.sidebar-pane {
    background-color: @sidebar_bg_color;
    border-right: 1px solid alpha(@window_fg_color, 0.05);
}

.navigation-sidebar row {
    border-radius: 10px;
    margin: 2px 8px;
    padding: 8px 12px;
    transition: all 0.2s ease;
}

.navigation-sidebar row image {
    -gtk-icon-size: 20px;
    margin-right: 10px;
    color: inherit;
    opacity: 0.7;
    transition: all 0.2s ease;
}

.navigation-sidebar row label {
    font-size: 14px;
    font-weight: 700;
    transition: all 0.2s ease;
}

.navigation-sidebar row:hover {
    background-color: alpha(@window_fg_color, 0.05);
}

.navigation-sidebar row:selected {
    background-color: alpha(@accent_bg_color, 0.12);
    color: @accent_bg_color;
}

.navigation-sidebar row:selected image {
    color: @accent_bg_color;
    opacity: 1.0;
}

/* ─── Diagnostics Warning Banner ─────────────────────────── */
.diagnostic-warning-row {
    background-color: alpha(@warning_red, 0.12);
    border: 1px solid alpha(@warning_red, 0.35);
    border-radius: 12px;
    padding: 16px;
    margin: 8px 0;
    transition: all 0.3s ease;
}

.diagnostic-warning-row label.title {
    color: @warning_red;
    font-weight: 800;
    font-size: 16px;
}

.diagnostic-warning-row label.subtitle {
    color: alpha(@window_fg_color, 0.8);
    font-size: 13px;
    margin-top: 4px;
}

/* ─── Adjustment Buttons (+/- 0.5) ───────────────────────── */
.adj-btn {
    min-width: 36px;
    min-height: 36px;
    padding: 0;
    transition: all 0.2s ease;
    opacity: 0.7;
}

.adj-btn:hover {
    opacity: 1.0;
    background-color: alpha(@window_fg_color, 0.08);
}

/* ─── Step jump buttons (±10, ±100) ──────────────────────── */
.step-btn {
    font-size: 10px;
    font-weight: 900;
    letter-spacing: 0.2px;
    min-width: 36px;
    min-height: 36px;
    padding: 0 6px;
    border-radius: 14px;
    background-color: alpha(@window_fg_color, 0.05);
    color: alpha(@window_fg_color, 0.7);
    border: 1px solid alpha(@window_fg_color, 0.08);
    transition: all 0.2s ease;
}

.step-btn:hover {
    background-color: alpha(@accent_bg_color, 0.12);
    color: @accent_bg_color;
    border-color: alpha(@accent_bg_color, 0.3);
    opacity: 1.0;
}

.step-btn:active {
    background-color: alpha(@accent_bg_color, 0.2);
}

/* ─── L2: Keyboard focus indicators (accessibility) ──────────── */
/* Use :focus-visible so mouse users don't see focus rings, only keyboard
   users do. Uses @accent_bg_color for visibility on dark backgrounds. */

/* Standard buttons — 2px outline with 2px offset */
button:focus-visible,
button.text-button:focus-visible,
button.image-button:focus-visible,
button.circular:focus-visible {
    outline: 2px solid @accent_bg_color;
    outline-offset: 2px;
}

/* Sliders — focus the trough so the user can see which slider is active */
scale:focus-visible trough {
    outline: 2px solid @accent_bg_color;
    outline-offset: 2px;
    border-radius: 8px;
}

/* Sidebar navigation rows — keyboard focus distinct from mouse :selected */
.navigation-sidebar row:focus-visible {
    outline: 2px solid @accent_bg_color;
    outline-offset: -2px;
}

/* Step and adjustment buttons — 3px outline since they're small */
.step-btn:focus-visible,
.adj-btn:focus-visible {
    outline: 3px solid @accent_bg_color;
    outline-offset: 1px;
}

/* SpinButton in the target-value popover */
spinbutton:focus-visible {
    outline: 2px solid @accent_bg_color;
    outline-offset: 1px;
}

/* L3: Ensure icon buttons (revert, remove) meet touch target minimums */
button.flat.image-button {
    min-width: 32px;
    min-height: 32px;
}

/* ─── Bonus: Reduced motion (vestibular accessibility) ────── */
@media (prefers-reduced-motion: reduce) {
    * {
        animation-duration: 0.01ms;
        animation-iteration-count: 1;
        transition-duration: 0.01ms;
    }
}
"""
