from pydantic.dataclasses import dataclass
from random import Random
import numpy as np

from lib.hht import emd

@dataclass
class EEMD:
    "Ensemble EMD"
    K: int = 7 # number of components
    S: int = 0 # iterations of sifting
    N: int = 100 # number of trials

    def decompose(self, series: dict[int, float]):
        emd_obj = emd.EMD(K=self.K, S=self.S)

        rand = Random(1) # seed for reproducibility
        s_l = len(series)
        series_list = list(series.items())
        ensemble_imfs = []
        for _ in range(self.N):
            noise = [rand.gauss() for _ in range(s_l)]
            series_plus, series_minus = {}, {}
            for s_i in range(s_l):
                x_i, y_i = series_list[s_i]
                n_i = noise[s_i]
                series_plus[x_i] = y_i + n_i
                series_minus[x_i] = y_i - n_i
            imfs_plus = emd_obj.decompose(series_plus)
            imfs_minus = emd_obj.decompose(series_minus)
            if len(imfs_plus) == len(imfs_minus):
                ensemble_imfs.append(imfs_plus)
                ensemble_imfs.append(imfs_minus)
        ensemble_imfs_l = [len(en_i) for en_i in ensemble_imfs]
        n_imfs = int(np.median(ensemble_imfs_l))
        ensemble_res = [en_i for en_i in ensemble_imfs if len(en_i) == n_imfs]
        ensemble_res = list(zip(ensemble_res))
        result = []
        for en_i in ensemble_res:
            result.append(en_i)
        return result

if __name__ == '__main__':
    # rnd = Random(100)
    series = {
        t: np.sin(2 * np.pi / 3 * t) + 0.5 * np.sin(2 * np.pi / 9 * t) + 0.3 * np.sin(2 * np.pi / 19 * t + np.pi/4) 
        for t in range(100)
    }
    res = EEMD(S=10).decompose(series)
    print(res)
