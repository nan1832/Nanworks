# Bridge30 llava-v1.5-7b Adapter-LGA Summary

Gradient target: `adapter_parameters_phi_L`
Main score: `S_adapter_dot`

## Dot Top-5

| Dot Rank | Layer | S_adapter_dot | S_adapter_cos | Joint Norm | Norm Ratio | Conflict Rank |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 31 | 0 | 0 | 0 | 0 | 32 |
| 2 | 30 | -0.944392 | -0.0944476 | 0.505316 | 0.00267675 | 31 |
| 3 | 29 | -1.34434 | -0.0877645 | 0.644385 | 0.00341342 | 30 |
| 4 | 28 | -4.19275 | -0.0985027 | 1.70422 | 0.00902758 | 29 |
| 5 | 26 | -9.1802 | -0.104773 | 2.84833 | 0.0150881 | 28 |

## Conflict Dot Top-5

| Conflict Rank | Layer | S_adapter_dot | S_adapter_cos | Joint Norm | Norm Ratio | Dot Rank |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | -5844.11 | -0.279745 | 614.513 | 3.25518 | 32 |
| 2 | 2 | -5783.28 | -0.28454 | 609.904 | 3.23077 | 31 |
| 3 | 3 | -5112.03 | -0.277734 | 566.763 | 3.00225 | 30 |
| 4 | 0 | -4487.93 | -0.282725 | 503.413 | 2.66667 | 29 |
| 5 | 4 | -3877.65 | -0.262092 | 453.405 | 2.40177 | 28 |

Conflict ranks are diagnostic only; the adapter-LGA main result uses `S_adapter_dot`.
