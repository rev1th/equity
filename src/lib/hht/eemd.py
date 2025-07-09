from pydantic.dataclasses import dataclass
from random import Random
import numpy as np

from lib.hht import emd

@dataclass
class EEMD:
    "Ensemble EMD"
    max_IMFs: int = 7
    max_iterations: int = 0
    num_trials: int = 100

    def decompose(self, series: dict[int, float]):
        emd_obj = emd.EMD(max_IMFs=self.max_IMFs, max_iterations=self.max_iterations)

        rand = Random(1) # seed for reproducibility
        series_len = len(series)
        series_list = list(series.items())
        mu, sigma = np.mean(list(series.values())), np.std(list(series.values()))
        ensemble_imfs = []
        for _ in range(self.num_trials):
            noise = [rand.gauss(mu=mu, sigma=sigma) for _ in range(series_len)]
            series_plus, series_minus = {}, {}
            for s_i in range(series_len):
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
        num_imfs = int(np.median(ensemble_imfs_l))
        ensemble_res = [en_i for en_i in ensemble_imfs if len(en_i) == num_imfs]
        result = []
        for imfs_i in zip(*ensemble_res):
            imf = []
            for points in zip(*imfs_i):
                imf.append((points[0][0], sum([p_i[1] for p_i in points]) / len(points)))
            result.append(imf)
        return result

if __name__ == '__main__':
    series = {
        t: np.sin(2 * np.pi / 3 * t) + 0.5 * np.sin(2 * np.pi / 9 * t) + 0.3 * np.sin(2 * np.pi / 19 * t + np.pi/4) 
        for t in range(120)
    }
    res = EEMD(max_iterations=10).decompose(series)

    # import pandas as pd
    # res_df = pd.DataFrame([{elem[0]: elem[1] for elem in imf} for imf in res]).T
    # res_df.columns = ['imf_2', 'imf_1', 'residue']
    # plotter.plot_series(res_df, title='IMFs')
