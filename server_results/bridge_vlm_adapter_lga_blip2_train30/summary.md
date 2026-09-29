# Bridge30 blip2-opt-2.7b Adapter-LGA Summary

Gradient target: `adapter_parameters_phi_L`
Main score: `S_adapter_dot`

## Dot Top-5

| Dot Rank | Layer | S_adapter_dot | S_adapter_cos | Joint Norm | Norm Ratio | Conflict Rank |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 4 | 105.3 | 0.0278042 | 156.291 | 1.73675 | 32 |
| 2 | 0 | 92.9082 | 0.0354278 | 117.506 | 1.30576 | 31 |
| 3 | 5 | 24.2265 | 0.00855351 | 156.597 | 1.74014 | 30 |
| 4 | 26 | 5.41824 | 0.0108265 | 8.12474 | 0.0902842 | 29 |
| 5 | 1 | 3.17424 | 0.0132395 | 125.786 | 1.39777 | 28 |

## Conflict Dot Top-5

| Conflict Rank | Layer | S_adapter_dot | S_adapter_cos | Joint Norm | Norm Ratio | Dot Rank |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 14 | -262.269 | -0.0376537 | 142.4 | 1.58239 | 32 |
| 2 | 15 | -216.045 | -0.032201 | 133.302 | 1.48128 | 31 |
| 3 | 16 | -198.178 | -0.0376519 | 115.814 | 1.28695 | 30 |
| 4 | 13 | -162.726 | -0.0158952 | 146.047 | 1.62291 | 29 |
| 5 | 11 | -156.914 | -0.011803 | 158.571 | 1.76208 | 28 |

Conflict ranks are diagnostic only; the adapter-LGA main result uses `S_adapter_dot`.
