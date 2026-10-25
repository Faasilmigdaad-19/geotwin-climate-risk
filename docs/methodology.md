# Methodology (baseline)
Study area: Velachery-Pallikaranai, Chennai. 500 m grid, 324 cells.

All indicators are scaled to 0-1 using the 5th-95th percentile range.

- Heat proxy H = 0.5*built-up density + 0.3*(1 - green cover) + 0.2*(1 - water cover).
  This is NOT land-surface temperature or air temperature.
- Flood susceptibility F = 0.40*low elevation + 0.25*closeness to water + 0.15*flat terrain + 0.20*built-up (impervious) density.
  This is relative susceptibility, not a flood probability or depth.
- Compound index C = 0.3*H + 0.4*F + 0.3*H*F. The interaction term highlights cells where both are high; it does not prove a causal link.
- Exposure proxy E = scaled count of mapped buildings (not population).
- Priority score = 0.7*C + 0.3*E.
- Stability: weights are randomly perturbed 200 times (log-normal noise, sigma 0.3); we report how often each cell stays in the top 10 percent.

Weights are expert assumptions, not calibrated. No validation against observed floods has been done yet.
Building density is used in H, F and E, so these indicators are correlated.
