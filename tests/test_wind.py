import os
import unittest
from yawisi.parameters import SimulationParameters
from yawisi.wind import Wind
from yawisi.display import display_wind
import matplotlib.pyplot as plt

class TestWind(unittest.TestCase):

    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)

    def test_wind(self):
        filename = os.path.join(os.path.dirname(__file__), "config.ini")
        params = SimulationParameters(filename)
        params.n_samples = 2000
        params.sample_time = .1
        print(params)

        wind = Wind(params)
        wind.compute()

        display_wind(wind)

        

if __name__ == "__main__":
    unittest.main()
