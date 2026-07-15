"""Parameter definitions and CPU family capability checks"""

import os
import re

# Settings parameters list
#
# Each parameter may carry optional safety metadata that is merged in from
# `_SAFETY_METADATA` below (see docs/C5_STRATEGY.md). The merged fields are:
#   risk        - "low" | "moderate" | "high"  (hardware-INDEPENDENT inherent risk)
#   plain_desc  - one-sentence non-technical explanation of what the param does
#   watch_for   - concrete symptom to monitor after changing this param
# None of these fields claim a value is "safe" or "unsafe" — they describe
# inherent characteristics and observable consequences, nothing more.
SETTINGS_PARAMS = [
    # Power limits (values from ryzenadj -i are in W; CLI takes mW)
    {
        "param": "stapm-limit",
        "label": "STAPM Limit",
        "desc": "Sustained Power Limit (STAPM)",
        "min": 5000,
        "max": 130000,
        "step": 1000,
        "unit": "mW",
        "display_divisor": 1000,
        "display_unit": "W",
        "category": "power",
        "value_key": "STAPM LIMIT",
    },
    {
        "param": "fast-limit",
        "label": "PPT Fast Limit",
        "desc": "Actual Power Limit (PPT FAST)",
        "min": 5000,
        "max": 130000,
        "step": 1000,
        "unit": "mW",
        "display_divisor": 1000,
        "display_unit": "W",
        "category": "power",
        "value_key": "PPT LIMIT FAST",
    },
    {
        "param": "slow-limit",
        "label": "PPT Slow Limit",
        "desc": "Average Power Limit (PPT SLOW)",
        "min": 5000,
        "max": 130000,
        "step": 1000,
        "unit": "mW",
        "display_divisor": 1000,
        "display_unit": "W",
        "category": "power",
        "value_key": "PPT LIMIT SLOW",
    },
    {
        "param": "apu-slow-limit",
        "label": "APU PPT Slow Limit",
        "desc": "APU PPT Slow limit (A+A dGPU platforms)",
        "min": 5000,
        "max": 130000,
        "step": 1000,
        "unit": "mW",
        "display_divisor": 1000,
        "display_unit": "W",
        "category": "power",
        "value_key": "PPT LIMIT APU",
    },
    # Current limits (values from ryzenadj -i are in A; CLI takes mA)
    {
        "param": "vrm-current",
        "label": "VRM VDD Current (TDC)",
        "desc": "TDC Limit VDD - VRM Current",
        "min": 10000,
        "max": 300000,
        "step": 1000,
        "unit": "mA",
        "display_divisor": 1000,
        "display_unit": "A",
        "category": "current",
        "value_key": "TDC LIMIT VDD",
    },
    {
        "param": "vrmsoc-current",
        "label": "VRM SoC Current (TDC)",
        "desc": "TDC Limit SoC - VRM SoC Current",
        "min": 10000,
        "max": 100000,
        "step": 1000,
        "unit": "mA",
        "display_divisor": 1000,
        "display_unit": "A",
        "category": "current",
        "value_key": "TDC LIMIT SOC",
    },
    {
        "param": "vrmmax-current",
        "label": "VRM VDD Max Current (EDC)",
        "desc": "EDC Limit VDD - VRM Maximum Current",
        "min": 10000,
        "max": 300000,
        "step": 1000,
        "unit": "mA",
        "display_divisor": 1000,
        "display_unit": "A",
        "category": "current",
        "value_key": "EDC LIMIT VDD",
    },
    {
        "param": "vrmsocmax-current",
        "label": "VRM SoC Max Current (EDC)",
        "desc": "EDC Limit SoC - VRM SoC Maximum Current",
        "min": 10000,
        "max": 100000,
        "step": 1000,
        "unit": "mA",
        "display_divisor": 1000,
        "display_unit": "A",
        "category": "current",
        "value_key": "EDC LIMIT SOC",
    },
    {
        "param": "psi0-current",
        "label": "PSI0 VDD Current",
        "desc": "PSI0 VDD Current Limit",
        "min": 1000,
        "max": 50000,
        "step": 1000,
        "unit": "mA",
        "display_divisor": 1000,
        "display_unit": "A",
        "category": "current",
        "value_key": "PSI0 CURRENT VDD",
    },
    {
        "param": "psi3cpu_current",
        "label": "PSI3 CPU Current",
        "desc": "PSI3 CPU Current Limit",
        "min": 1000,
        "max": 50000,
        "step": 1000,
        "unit": "mA",
        "display_divisor": 1000,
        "display_unit": "A",
        "category": "current",
        "value_key": "PSI3 CURRENT CPU",
    },
    {
        "param": "psi0soc-current",
        "label": "PSI0 SoC Current",
        "desc": "PSI0 SoC Current Limit",
        "min": 1000,
        "max": 50000,
        "step": 1000,
        "unit": "mA",
        "display_divisor": 1000,
        "display_unit": "A",
        "category": "current",
        "value_key": "PSI0 CURRENT SOC",
    },
    {
        "param": "psi3gfx_current",
        "label": "PSI3 GFX Current",
        "desc": "PSI3 GFX Current Limit",
        "min": 1000,
        "max": 50000,
        "step": 1000,
        "unit": "mA",
        "display_divisor": 1000,
        "display_unit": "A",
        "category": "current",
        "value_key": "PSI3 CURRENT GFX",
        "is_gpu": True,
    },
    # Thermal limits
    {
        "param": "tctl-temp",
        "label": "Tctl Temperature Limit",
        "desc": "CPU die temperature ceiling",
        "min": 40,
        "max": 105,
        "step": 1,
        "unit": "°C",
        "display_divisor": 1,
        "display_unit": "°C",
        "category": "thermal",
        "value_key": "THM LIMIT CORE",
    },
    {
        "param": "apu-skin-temp",
        "label": "APU Skin Temp Limit",
        "desc": "STT Limit APU - skin temperature",
        "min": 20,
        "max": 100,
        "step": 1,
        "unit": "°C",
        "display_divisor": 1,
        "display_unit": "°C",
        "category": "thermal",
        "value_key": "STT LIMIT APU",
    },
    {
        "param": "dgpu-skin-temp",
        "label": "dGPU Skin Temp Limit",
        "desc": "STT Limit dGPU - discrete GPU skin temperature",
        "min": 0,
        "max": 100,
        "step": 1,
        "unit": "°C",
        "display_divisor": 1,
        "display_unit": "°C",
        "category": "thermal",
        "value_key": "STT LIMIT dGPU",
    },
    {
        "param": "skin-temp-limit",
        "label": "Skin Temp Power Limit",
        "desc": "Skin Temperature Power Limit (controls power envelope when skin threshold reached)",
        "min": 5000,
        "max": 130000,
        "step": 1000,
        "unit": "mW",
        "display_divisor": 1000,
        "display_unit": "W",
        "category": "thermal",
        "value_key": "SkinTempLimit",
    },
    # Timing
    {
        "param": "stapm-time",
        "label": "STAPM Constant Time",
        "desc": "STAPM time constant (seconds)",
        "min": 0,
        "max": 1000,
        "step": 10,
        "unit": "s",
        "display_divisor": 1,
        "display_unit": "s",
        "category": "timing",
        "value_key": "StapmTimeConst",
    },
    {
        "param": "slow-time",
        "label": "Slow PPT Time Constant",
        "desc": "Slow PPT time constant (seconds)",
        "min": 0,
        "max": 1000,
        "step": 10,
        "unit": "s",
        "display_divisor": 1,
        "display_unit": "s",
        "category": "timing",
        "value_key": "SlowPPTTimeConst",
    },
    # GPU Options
    {
        "param": "max-gfxclk",
        "label": "Max iGPU Clock",
        "desc": "Maximum graphics core clock frequency ceiling",
        "min": 400,
        "max": 3500,
        "step": 50,
        "unit": "MHz",
        "display_divisor": 1,
        "display_unit": "MHz",
        "category": "clocks",
        "value_key": "GFX CLK LIMIT (MAX)",
        "is_gpu": True,
    },
    {
        "param": "min-gfxclk",
        "label": "Min iGPU Clock",
        "desc": "Minimum graphics core clock frequency floor",
        "min": 400,
        "max": 3500,
        "step": 50,
        "unit": "MHz",
        "display_divisor": 1,
        "display_unit": "MHz",
        "category": "clocks",
        "value_key": "GFX CLK LIMIT (MIN)",
        "is_gpu": True,
    },
    {
        "param": "vrmgfx-current",
        "label": "VRM iGPU Current (TDC)",
        "desc": "TDC Limit GFX - graphics VRM current limit",
        "min": 10000,
        "max": 150000,
        "step": 1000,
        "unit": "mA",
        "display_divisor": 1000,
        "display_unit": "A",
        "category": "current",
        "value_key": "TDC LIMIT GFX",
        "is_gpu": True,
    },
    {
        "param": "vrmgfxmax_current",
        "label": "VRM iGPU Max Current (EDC)",
        "desc": "EDC Limit GFX - graphics VRM maximum peak current",
        "min": 10000,
        "max": 180000,
        "step": 1000,
        "unit": "mA",
        "display_divisor": 1000,
        "display_unit": "A",
        "category": "current",
        "value_key": "EDC LIMIT GFX",
        "is_gpu": True,
    },
    # CPU Options
    {
        "param": "oc-clk",
        "label": "CPU Manual Overclock Clock",
        "desc": "Forced manual CPU core frequency (Enables OC mode)",
        "min": 1000,
        "max": 6000,
        "step": 25,
        "unit": "MHz",
        "display_divisor": 1,
        "display_unit": "MHz",
        "category": "clocks",
        "value_key": "CPU OC CLK",
        "is_cpu": True,
    },
    {
        "param": "oc-volt",
        "label": "CPU Manual Overclock Voltage",
        "desc": "Forced manual CPU core voltage (Enables OC mode)",
        "min": 700,
        "max": 1500,
        "step": 5,
        "unit": "mV",
        "display_divisor": 1,
        "display_unit": "mV",
        "category": "current",
        "value_key": "CPU OC VOLT",
        "is_cpu": True,
    },
    # GFX Forced Clock
    {
        "param": "gfx-clk",
        "label": "Forced iGPU Clock",
        "desc": "Force graphics core clock speed (Renoir Only)",
        "min": 400,
        "max": 3000,
        "step": 25,
        "unit": "MHz",
        "display_divisor": 1,
        "display_unit": "MHz",
        "category": "clocks",
        "value_key": "GFX FORCED CLK",
        "is_gpu": True,
    },
    # SoC Clock Limits
    {
        "param": "max-socclk-frequency",
        "label": "Max SoC Clock",
        "desc": "Maximum System-on-Chip (SoC) clock speed",
        "min": 400,
        "max": 2000,
        "step": 33,
        "unit": "MHz",
        "display_divisor": 1,
        "display_unit": "MHz",
        "category": "clocks",
        "value_key": "SOCCLK LIMIT (MAX)",
        "is_cpu": True,
    },
    {
        "param": "min-socclk-frequency",
        "label": "Min SoC Clock",
        "desc": "Minimum System-on-Chip (SoC) clock speed",
        "min": 400,
        "max": 2000,
        "step": 33,
        "unit": "MHz",
        "display_divisor": 1,
        "display_unit": "MHz",
        "category": "clocks",
        "value_key": "SOCCLK LIMIT (MIN)",
        "is_cpu": True,
    },
    # FCLK Limits
    {
        "param": "max-fclk-frequency",
        "label": "Max FCLK",
        "desc": "Maximum Transmission (CPU-GPU) Frequency",
        "min": 400,
        "max": 3000,
        "step": 33,
        "unit": "MHz",
        "display_divisor": 1,
        "display_unit": "MHz",
        "category": "clocks",
        "value_key": "FCLK LIMIT (MAX)",
        "is_cpu": True,
    },
    {
        "param": "min-fclk-frequency",
        "label": "Min FCLK",
        "desc": "Minimum Transmission (CPU-GPU) Frequency",
        "min": 400,
        "max": 3000,
        "step": 33,
        "unit": "MHz",
        "display_divisor": 1,
        "display_unit": "MHz",
        "category": "clocks",
        "value_key": "FCLK LIMIT (MIN)",
        "is_cpu": True,
    },
    # VCN Limits
    {
        "param": "max-vcn",
        "label": "Max VCN",
        "desc": "Maximum Video Core Next Frequency",
        "min": 400,
        "max": 3000,
        "step": 33,
        "unit": "MHz",
        "display_divisor": 1,
        "display_unit": "MHz",
        "category": "clocks",
        "value_key": "VCN LIMIT (MAX)",
        "is_gpu": True,
    },
    {
        "param": "min-vcn",
        "label": "Min VCN",
        "desc": "Minimum Video Core Next Frequency",
        "min": 400,
        "max": 3000,
        "step": 33,
        "unit": "MHz",
        "display_divisor": 1,
        "display_unit": "MHz",
        "category": "clocks",
        "value_key": "VCN LIMIT (MIN)",
        "is_gpu": True,
    },
    # LCLK Limits
    {
        "param": "max-lclk",
        "label": "Max LCLK",
        "desc": "Maximum Data Launch Clock",
        "min": 400,
        "max": 3000,
        "step": 33,
        "unit": "MHz",
        "display_divisor": 1,
        "display_unit": "MHz",
        "category": "clocks",
        "value_key": "LCLK LIMIT (MAX)",
        "is_cpu": True,
    },
    {
        "param": "min-lclk",
        "label": "Min LCLK",
        "desc": "Minimum Data Launch Clock",
        "min": 400,
        "max": 3000,
        "step": 33,
        "unit": "MHz",
        "display_divisor": 1,
        "display_unit": "MHz",
        "category": "clocks",
        "value_key": "LCLK LIMIT (MIN)",
        "is_cpu": True,
    },
    # VRM CVIP Current Limit
    {
        "param": "vrmcvip-current",
        "label": "VRM CVIP Current (TDC)",
        "desc": "TDC Limit CVIP - processor fabric current limit",
        "min": 5000,
        "max": 100000,
        "step": 1000,
        "unit": "mA",
        "display_divisor": 1000,
        "display_unit": "A",
        "category": "current",
        "value_key": "TDC LIMIT CVIP",
        "is_cpu": True,
    },
    # PROCHOT Ramp Time
    {
        "param": "prochot-deassertion-ramp",
        "label": "PROCHOT Deassertion Ramp",
        "desc": "Ramp time after processor hot signal is deasserted",
        "min": 0,
        "max": 5000,
        "step": 100,
        "unit": "ms",
        "display_divisor": 1,
        "display_unit": "ms",
        "category": "timing",
        "value_key": "PROCHOT Ramp",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Safety metadata (C5 — see docs/C5_STRATEGY.md)
# ─────────────────────────────────────────────────────────────────────────────
# Hardware-INDEPENDENT inherent risk and plain-language guidance per parameter.
# This is deliberately kept separate from SETTINGS_PARAMS so the technical
# definitions stay readable. Merged in below.
#
# risk tiers:
#   high     - changing this without knowledge can crash the system or risk
#              silent data corruption (manual OC, Curve Optimizer, forced clocks)
#   moderate - changing this affects heat/VRM stress but hardware protection
#              exists (power limits, current limits, temp limits, max clocks)
#   low      - slow-acting, secondary rails, or harmless when lowered (timing
#              constants, clock minimums, PSI currents)
#
# plain_desc and watch_for are written for a non-technical audience. They never
# claim a specific value is safe — they describe what the param does and what
# symptom to watch for if the change turns out to be too aggressive.
_SAFETY_METADATA = {
    # ── Power limits (moderate) ───────────────────────────────────────────────
    "stapm-limit": {
        "risk": "moderate",
        "plain_desc": "The maximum power your CPU can draw continuously (over several minutes). Higher = faster sustained speed but more heat and shorter battery life.",
        "watch_for": "Sustained temperatures under load; battery life.",
    },
    "fast-limit": {
        "risk": "moderate",
        "plain_desc": "The maximum power your CPU can draw in short bursts (a few seconds). Higher = faster peak performance but hotter temperature spikes.",
        "watch_for": "Temperature spikes during bursts; fan noise.",
    },
    "slow-limit": {
        "risk": "moderate",
        "plain_desc": "A middle power limit that caps draw over multi-second windows, sitting between the sustained and burst limits.",
        "watch_for": "Performance during multi-second workloads.",
    },
    "apu-slow-limit": {
        "risk": "moderate",
        "plain_desc": "Power limit for the integrated CPU/GPU portion on laptops that also have a discrete GPU.",
        "watch_for": "iGPU performance under sustained load.",
    },
    # ── Current limits (moderate) ─────────────────────────────────────────────
    "vrm-current": {
        "risk": "moderate",
        "plain_desc": "Maximum sustained electrical current the voltage regulator can deliver to the CPU cores. Higher allows more power delivery but stresses the VRM hardware.",
        "watch_for": "System stability under sustained load; VRM temperatures if measurable.",
    },
    "vrmsoc-current": {
        "risk": "moderate",
        "plain_desc": "Same idea as the core VRM current, but for the SoC (memory controller, interconnects, integrated peripherals).",
        "watch_for": "System stability under memory-heavy workloads.",
    },
    "vrmmax-current": {
        "risk": "moderate",
        "plain_desc": "Maximum peak current the voltage regulator can deliver to the CPU cores during brief spikes. Higher allows more boost headroom.",
        "watch_for": "System stability during current spikes (e.g. sudden load changes).",
    },
    "vrmsocmax-current": {
        "risk": "moderate",
        "plain_desc": "Maximum peak current for the SoC voltage regulator during brief spikes.",
        "watch_for": "System stability during sudden load changes.",
    },
    "vrmgfx-current": {
        "risk": "moderate",
        "plain_desc": "Maximum sustained current for the integrated GPU's voltage regulator.",
        "watch_for": "GPU stability under sustained graphics load.",
    },
    "vrmgfxmax_current": {
        "risk": "moderate",
        "plain_desc": "Maximum peak current for the integrated GPU's voltage regulator.",
        "watch_for": "GPU stability during sudden load changes.",
    },
    "psi0-current": {
        "risk": "low",
        "plain_desc": "Current limit for a secondary CPU power rail (PSI0). Rarely the bottleneck.",
        "watch_for": "System stability under extreme load (rarely affected).",
    },
    "psi3cpu_current": {
        "risk": "low",
        "plain_desc": "Current limit for a secondary CPU power rail (PSI3). Rarely the bottleneck.",
        "watch_for": "System stability under extreme load (rarely affected).",
    },
    "psi0soc-current": {
        "risk": "low",
        "plain_desc": "Current limit for a secondary SoC power rail (PSI0). Rarely the bottleneck.",
        "watch_for": "System stability under extreme load (rarely affected).",
    },
    "psi3gfx_current": {
        "risk": "low",
        "plain_desc": "Current limit for a secondary GPU power rail (PSI3). Rarely the bottleneck.",
        "watch_for": "System stability under extreme load (rarely affected).",
    },
    "vrmcvip-current": {
        "risk": "low",
        "plain_desc": "Current limit for the processor fabric (the interconnect between CPU cores and other blocks).",
        "watch_for": "System stability under heavy inter-core traffic (rarely affected).",
    },
    # ── Thermal limits (moderate) ─────────────────────────────────────────────
    "tctl-temp": {
        "risk": "moderate",
        "plain_desc": "The maximum internal temperature the CPU is allowed to reach before it slows itself down to cool. Higher = more performance allowed but more heat and shorter hardware lifespan.",
        "watch_for": "Sustained temperatures above 90°C under load reduce lifespan.",
    },
    "apu-skin-temp": {
        "risk": "moderate",
        "plain_desc": "The maximum allowed external (chassis) temperature before the CPU slows down. Protects you from burns and an uncomfortably hot lap.",
        "watch_for": "How hot the laptop surface feels under load.",
    },
    "dgpu-skin-temp": {
        "risk": "low",
        "plain_desc": "Same idea as the APU skin temperature, but for the discrete GPU side. Only relevant on laptops with a dGPU.",
        "watch_for": "Surface temperature near the dGPU area.",
    },
    "skin-temp-limit": {
        "risk": "moderate",
        "plain_desc": "When the chassis reaches its skin temperature threshold, CPU power is reduced to this level to cool down. Couples skin temperature to power output.",
        "watch_for": "Performance dropping when the laptop feels hot.",
    },
    # ── Timing constants (low) ───────────────────────────────────────────────
    "stapm-time": {
        "risk": "low",
        "plain_desc": "How quickly (in seconds) the sustained power limit reacts to changes in power draw. Longer = the CPU can boost longer before being clamped.",
        "watch_for": "How long burst performance lasts before settling.",
    },
    "slow-time": {
        "risk": "low",
        "plain_desc": "Same idea as the STAPM time constant, but for the slow (averaging) power limit window.",
        "watch_for": "How long the CPU sustains mid-length boosts.",
    },
    "prochot-deassertion-ramp": {
        "risk": "low",
        "plain_desc": "How quickly (in milliseconds) the CPU ramps back up after cooling below the thermal limit. Longer = gentler recovery; shorter = snappier but possibly noisier fans.",
        "watch_for": "Fan cycling behaviour after the CPU cools from a hot spell.",
    },
    # ── GPU/CPU clock limits (mixed) ─────────────────────────────────────────
    "max-gfxclk": {
        "risk": "moderate",
        "plain_desc": "The maximum clock the integrated GPU is allowed to reach. Higher = more graphics performance but more heat.",
        "watch_for": "Visual artifacts or crashes in games; GPU temperatures.",
    },
    "min-gfxclk": {
        "risk": "low",
        "plain_desc": "The minimum clock the integrated GPU will drop to when idle. Raising it stops the GPU from saving power at idle.",
        "watch_for": "Idle power draw and battery life.",
    },
    "gfx-clk": {
        "risk": "high",
        "plain_desc": "Forces the integrated GPU to run at exactly this clock at all times, overriding automatic scaling. Renoir-only. Disables idle power saving.",
        "watch_for": "GPU crashes; significantly higher idle power draw.",
    },
    "max-socclk-frequency": {
        "risk": "moderate",
        "plain_desc": "Maximum clock for the SoC (memory controller, fabric, I/O). Raising rarely helps performance but can destabilise the memory subsystem.",
        "watch_for": "Memory-related crashes or boot instability.",
    },
    "min-socclk-frequency": {
        "risk": "low",
        "plain_desc": "Minimum clock the SoC will drop to when idle. Raising it prevents the SoC from saving power at idle.",
        "watch_for": "Idle power draw.",
    },
    "max-fclk-frequency": {
        "risk": "moderate",
        "plain_desc": "Maximum frequency of the Infinity Fabric link between CPU and RAM. Raising can improve memory bandwidth but risks instability.",
        "watch_for": "Memory-related crashes; data corruption (rare but serious).",
    },
    "min-fclk-frequency": {
        "risk": "low",
        "plain_desc": "Minimum Infinity Fabric frequency at idle. Raising it prevents the fabric from saving power at idle.",
        "watch_for": "Idle power draw.",
    },
    "max-vcn": {
        "risk": "moderate",
        "plain_desc": "Maximum clock for the video decode/encode engine (VCN). Raising rarely improves noticeable performance.",
        "watch_for": "Video playback or encode instability.",
    },
    "min-vcn": {
        "risk": "low",
        "plain_desc": "Minimum clock the video engine will drop to when idle. Raising it prevents idle power saving.",
        "watch_for": "Idle power draw.",
    },
    "max-lclk": {
        "risk": "moderate",
        "plain_desc": "Maximum data launch clock for I/O peripherals. Raising rarely improves performance and can destabilise USB/SATA links.",
        "watch_for": "USB or storage device disconnects/crashes.",
    },
    "min-lclk": {
        "risk": "low",
        "plain_desc": "Minimum data launch clock at idle. Raising it prevents the I/O subsystem from saving power at idle.",
        "watch_for": "Idle power draw.",
    },
    # ── Manual overclock (high) ───────────────────────────────────────────────
    "oc-clk": {
        "risk": "high",
        "plain_desc": "Forces ALL CPU cores to run at exactly this frequency, disabling automatic boost and idle scaling. Advanced overclocking only — incorrect values will crash the system.",
        "watch_for": "Immediate crashes on apply; loss of idle/battery life.",
    },
    "oc-volt": {
        "risk": "high",
        "plain_desc": "Forces the CPU voltage to this value when manual overclocking is active. Too high = excessive heat and possible damage over time; too low = crashes.",
        "watch_for": "Temperatures (too high voltage); crashes (too low voltage).",
    },
}

# Per-core Curve Optimizer entries share the same guidance. Generate them
# for up to 16 cores here so plain_desc / watch_for are available even before
# the actual core count is known. is_parameter_supported() filters out cores
# that don't exist on the actual hardware at row-build time in widgets.py.
_CO_PLAIN_DESC = (
    "Applies a per-core voltage offset. Negative = undervolt (cooler, may be "
    "unstable). Positive = overvolt (hotter, rarely useful). Per-core tuning "
    "lets you push stable cores harder while leaving weaker cores at safer values."
)
_CO_WATCH_FOR = (
    "Crashes under load — Curve Optimizer instability often appears hours later "
    "under specific workloads, not immediately. Test thoroughly."
)
for _core_idx in range(16):
    _SAFETY_METADATA[f"set-coper-{_core_idx}"] = {
        "risk": "high",
        "plain_desc": _CO_PLAIN_DESC,
        "watch_for": _CO_WATCH_FOR,
    }
# All-core and iGPU Curve Optimizer
_SAFETY_METADATA["set-coall"] = {
    "risk": "high",
    "plain_desc": (
        "Applies a voltage offset to ALL CPU cores at every frequency. Negative "
        "= undervolt (cooler, may be unstable). Positive = overvolt (hotter, "
        "rarely useful). The fastest way to tune, but also the bluntest — a "
        "value one core can't handle will crash the whole system."
    ),
    "watch_for": _CO_WATCH_FOR,
}
_SAFETY_METADATA["set-cogfx"] = {
    "risk": "high",
    "plain_desc": (
        "Same idea as the all-core Curve Optimizer, but applied to the "
        "integrated GPU. Negative = undervolt (cooler, may be unstable)."
    ),
    "watch_for": "GPU crashes or visual artifacts in games/video playback.",
}


def _merge_safety_metadata() -> None:
    """Merge _SAFETY_METADATA into SETTINGS_PARAMS in place.

    Keys present in _SAFETY_METADATA that don't correspond to any SETTINGS_PARAMS
    entry (e.g. CO params for cores beyond the actual core count) are simply
    ignored — they're looked up by name at row-build time.
    """
    for entry in SETTINGS_PARAMS:
        name = entry["param"]
        extra = _SAFETY_METADATA.get(name)
        if extra:
            entry.setdefault("risk", extra["risk"])
            entry.setdefault("plain_desc", extra["plain_desc"])
            entry.setdefault("watch_for", extra["watch_for"])


# NOTE: _merge_safety_metadata() is called AFTER the Curve Optimizer params are
# appended to SETTINGS_PARAMS further down this file.


def _get_physical_core_count() -> int:
    """Count physical CPU cores on the system (read from topology sysfs)"""
    try:
        cores = set()
        for i in range(os.cpu_count() or 1):
            path = f"/sys/devices/system/cpu/cpu{i}/topology/core_cpus_list"
            if os.path.exists(path):
                with open(path) as f:
                    cores.add(f.read().strip())
        if cores:
            return len(cores)
    except Exception:
        pass
    count = os.cpu_count()
    return count if count else 8


# Add Curve Optimizer options to list
SETTINGS_PARAMS.append(
    {
        "param": "set-coall",
        "label": "All Cores Offset",
        "desc": "Curve Optimizer offset applied to all CPU cores",
        "min": -30,
        "max": 30,
        "step": 1,
        "unit": "",
        "display_divisor": 1,
        "display_unit": "",
        "category": "undervolt",
        "value_key": "COALL",
        "default": 0,
        "is_cpu": True,
    }
)

SETTINGS_PARAMS.append(
    {
        "param": "set-cogfx",
        "label": "iGPU Offset",
        "desc": "Curve Optimizer offset applied to the graphics core",
        "min": -30,
        "max": 30,
        "step": 1,
        "unit": "",
        "display_divisor": 1,
        "display_unit": "",
        "category": "undervolt",
        "value_key": "COGFX",
        "default": 0,
        "is_gpu": True,
    }
)

for i in range(_get_physical_core_count()):
    SETTINGS_PARAMS.append(
        {
            "param": f"set-coper-{i}",
            "label": f"Core {i} Offset",
            "desc": f"Curve Optimizer offset for Core {i}",
            "min": -30,
            "max": 30,
            "step": 1,
            "unit": "",
            "display_divisor": 1,
            "display_unit": "",
            "category": "undervolt",
            "value_key": f"COPER_{i}",
            "default": 0,
            "is_cpu": True,
        }
    )

# Now that Curve Optimizer params have been appended to SETTINGS_PARAMS, merge
# in the safety metadata (risk / plain_desc / watch_for) for every entry.
_merge_safety_metadata()


def _is_mobile_or_apu(cpu_family: str) -> bool:
    """Check if CPU is a laptop or APU chip (kind of researched cpu models for this list)"""
    fam_lower = cpu_family.lower()
    apu_families = {
        "strix",
        "phoenix",
        "hawk",
        "rembrandt",
        "barcelo",
        "cezanne",
        "lucienne",
        "renoir",
        "picasso",
        "raven",
        "mendocino",
        "sabin",
        "kraken",
        "krackan",
        "sonoma",
        "dragon",
        "fire",
        "dali",
        "pollock",
        "vangogh",
        "aerith",
        "sephiroth",
    }
    if any(fam in fam_lower for fam in apu_families):
        return True

    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.strip().startswith("model name"):
                    model_name = line.split(":", 1)[1].strip().lower()
                    if "ryzen" in model_name:
                        if (
                            " ai " in model_name
                            or " z1 " in model_name
                            or " z1 extreme" in model_name
                            or any(
                                suffix in model_name for suffix in ["370", "365", "375"]
                            )
                        ):
                            return True
                        if re.search(r"\b\d{3,4}(u|h|hs|hx|g|ge)\b", model_name):
                            return True
    except Exception:
        pass
    return False


def _is_zen3_or_newer() -> bool:
    """Check if the CPU is Zen 3 or newer (Family 25 or higher in cpuinfo)"""
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.strip().startswith("cpu family"):
                    family_val = int(line.split(":", 1)[1].strip())
                    return family_val >= 25
    except Exception:
        pass
    return True


from system import is_sysfs_gfx_clk_available


def is_parameter_supported(
    param: str, cpu_family: str, supported_params: set[str]
) -> bool:
    """Check if a parameter is supported on this CPU model"""
    if param.startswith("set-co"):
        if not _is_zen3_or_newer():
            return False
        if param == "set-cogfx":
            fam_lower = cpu_family.lower()
            if "strix" in fam_lower or "phoenix" in fam_lower or "hawk" in fam_lower:
                return False
            try:
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if line.strip().startswith("model name"):
                            model_name = line.split(":", 1)[1].strip().lower()
                            if (
                                "370" in model_name
                                or "365" in model_name
                                or "375" in model_name
                            ):
                                return False
            except Exception:
                pass
        return True

    if param in ("skin-temp-limit", "apu-skin-temp"):
        if param == "apu-skin-temp":
            fam_lower = cpu_family.lower()
            if "strix" in fam_lower or "phoenix" in fam_lower or "hawk" in fam_lower:
                return False
            try:
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if line.strip().startswith("model name"):
                            model_name = line.split(":", 1)[1].strip().lower()
                            if (
                                "370" in model_name
                                or "365" in model_name
                                or "375" in model_name
                            ):
                                return False
            except Exception:
                pass
        if _is_mobile_or_apu(cpu_family):
            return True

    if param == "dgpu-skin-temp":
        fam_lower = cpu_family.lower()
        if "strix" in fam_lower or "phoenix" in fam_lower or "hawk" in fam_lower:
            return False

    if supported_params and param in supported_params:
        return True

    if param in ("oc-clk", "oc-volt"):
        fam_lower = cpu_family.lower()
        is_unlocked_hx = False
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if line.strip().startswith("model name"):
                        model_name = line.split(":", 1)[1].strip().lower()
                        if (
                            "hx" in model_name or "hk" in model_name
                        ) and "ai " not in model_name:
                            is_unlocked_hx = True
                            break
        except Exception:
            pass
        return is_unlocked_hx

    if param in ("min-gfxclk", "max-gfxclk"):
        return (
            supported_params and param in supported_params
        ) or is_sysfs_gfx_clk_available()

    if param == "gfx-clk":
        igpu_indicators = {
            "gfx-clk",
            "gfx-clock",
            "max-gfxclk",
            "min-gfxclk",
            "vrmgfx-current",
            "vrmgfxmax_current",
        }
        if supported_params and any(ind in supported_params for ind in igpu_indicators):
            return True
        if _is_mobile_or_apu(cpu_family):
            return True

    # If ryzenadj couldn't report supported parameters (e.g. SMU telemetry
    # unavailable, ryzen_smu not loaded), don't mark standard params as
    # unsupported — assume they work and let ryzenadj return an error if a
    # param truly isn't supported on this platform. This prevents the entire
    # UI from showing every slider as "(Unsupported on this CPU)" when the
    # only issue is a missing kernel module.
    if not supported_params:
        return True

    return False
