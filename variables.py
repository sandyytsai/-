from __future__ import annotations

from .data_contract import Scales


class UnitScaler:
    def __init__(self, scales: Scales):
        self.s = scales

    def Eint(self, kwh: float) -> int:
        return int(round(kwh * self.s.E_SCALE))

    def Vint(self, m3: float) -> int:
        return int(round(m3 * self.s.V_SCALE))

    def Cint(self, currency: float) -> int:
        return int(round(currency * self.s.COST_SCALE))

    def Efloat(self, E_int: int) -> float:
        return E_int / self.s.E_SCALE

    def Vfloat(self, V_int: int) -> float:
        return V_int / self.s.V_SCALE
