"""モデル交換を可能にする最小の抽象契約。"""

from abc import ABC, abstractmethod

from .types import AnomalyRequest, AnomalyResult, ForecastRequest, ForecastResult


class Forecaster(ABC):
    """時系列の点予測と任意の分位点予測を返すモデル契約。"""

    @abstractmethod
    def forecast(self, request: ForecastRequest) -> ForecastResult:
        """与えられた過去windowからhorizon分を予測する。"""


class AnomalyDetector(ABC):
    """観測windowをscore化するモデル契約。制御書き込みは契約外。"""

    @abstractmethod
    def score(self, request: AnomalyRequest) -> AnomalyResult:
        """観測値に対する異常scoreを返す。"""
