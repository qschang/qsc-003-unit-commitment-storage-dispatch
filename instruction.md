# Multi-period unit commitment and storage dispatch ledger

Implement `/app/dispatch.py` and make it executable through:

```text
python3 /app/dispatch.py INPUT.json OUTPUT.json
```

The input is UTF-8 JSON with `horizon_hours`, `generators`, `storage`, and `periods`. Each period has `load_MW` and `renewable_MW`. A generator has `id`, `min_MW`, `max_MW`, `marginal_cost`, `startup_cost`, `ramp_up_MW`, `ramp_down_MW`, `min_up_hours`, `min_down_hours`, and `initial_state` (`on` or `off`). The storage object has `capacity_MWh`, `initial_MWh`, `max_charge_MW`, `max_discharge_MW`, `charge_efficiency`, and `discharge_efficiency`, and `terminal_MWh`.

Return exactly `dispatch` and `summary`. `dispatch` contains one record per period in input order with generator records (`id`, `on`, `power_MW`), storage fields (`charge_MW`, `discharge_MW`, `state_MWh`), `renewable_used_MW`, `curtailment_MW`, `unserved_MW`, and `balance_residual_MW`. `summary` contains total cost, total unserved energy, total renewable curtailment, final storage state, and a per-generator `commitment_hours` mapping.

The schedule must satisfy load balance each period, generator bounds when on, zero output when off, ramp limits including the transition from each initial state, minimum up/down durations, storage state recursion with the stated efficiencies and one-hour periods, and all capacity limits, including the terminal storage requirement. Renewable energy is used before thermal generation; any excess is curtailed. Unserved load is allowed only as a last resort and is penalized by the fixed public constant `10000.0` currency/MWh. Total cost is marginal generation cost plus startup cost plus unserved penalty. Use deterministic tie handling and preserve input order.

Reject malformed, non-finite, negative, inconsistent, or horizon-violating inputs with a nonzero exit and leave `OUTPUT.json` absent or byte-for-byte unchanged. Validate the complete record before publishing any output. Numeric fields must be finite; residual magnitude must be at most `1e-9` MW and storage state at most `1e-9` MWh from the stated recurrence. The implementation must handle newly constructed valid systems, not a single fixture.

The contract also requires exact unit accounting, interval ordering, atomic rollback on publication failure, and deterministic rerun behavior; malformed records must be refused without temporary or checkpoint artifacts; preserve numeric precision, interval ordering, and unit consistency during every rerun.

领域约束包括：机组承诺的最小开停机区间与爬坡边界；储能容量、充放电效率、终端库存和单位换算；成本、启动费、弃电与缺供罚金的确定性排序；非有限数值、精度、重复运行、原子回滚、拒收和旧文件保留。
