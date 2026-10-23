# Reference rationale

The implementation covers three independent energy-system axes: ambient-dependent heat-pump COP and threshold availability; thermal-store inventory recursion with charging/discharging efficiency and terminal inventory; and source-cost accounting with an unmet-heat penalty. Tests independently check heat balance, the COP equation, storage conservation, terminal state, rejection side effects, deterministic serialization, duplicate-key refusal, and missing-parent failure. Expected values are derived from public equations and small hand calculations.
