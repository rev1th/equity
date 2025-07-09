from pydantic.dataclasses import dataclass
from common.numeric.interpolator import BSpline

# MIN_POINTS = 5
MIN_SPLINE_POINTS = 4
def get_extrema(series: list[tuple[int, float]]):
    # assert len(series) > MIN_POINTS, f'Expect minimum number of points'
    maxima, minima = [], []
    x_1, x_2 = None, None
    for x_i, y_i in series:
        if x_1 is None:
            x_1, y_1 = x_i, y_i
        elif x_2 is None:
            if (y_i - y_1) != 0:
                x_2, y_2 = x_i, y_i
        elif (y_i - y_2) != 0:
            if x_i > x_2 + 1:
                x_2 = int((x_2 + x_i - 1) / 2)
            if (y_i - y_2) > 0 and (y_2 - y_1) < 0:
                minima.append((x_2, y_2))
            elif (y_i - y_2) < 0 and (y_2 - y_1) > 0:
                maxima.append((x_2, y_2))
            x_1, y_1 = x_2, y_2
            x_2, y_2 = x_i, y_i
    return minima, maxima

def get_envelope(series: list[tuple[int, float]]):
    maxima, minima = get_extrema(series)
    if len(maxima) < MIN_SPLINE_POINTS or len(minima) < MIN_SPLINE_POINTS:
        return None
    max_spline = BSpline(maxima, _extrapolate_left=True)
    min_spline = BSpline(minima, _extrapolate_left=True)
    mean_envelope = []
    for x_i, _ in series:
        mean_envelope.append((x_i, (max_spline.get_value(x_i) + min_spline.get_value(x_i)) / 2))
    return mean_envelope

ERROR_THRESHOLD = 1e-4
def eval_sifting(series: list[tuple[int, float]], max_iterations: int = 0):
    proto_imf, s_i = series, 0
    while(max_iterations == 0 or s_i < max_iterations):
        mean_envelope = get_envelope(proto_imf)
        if not mean_envelope:
            # no mean so end sifting process
            break
        error = [0 if v == 0 else m[1]*m[1] / v[1]*v[1] for v, m in zip(proto_imf, mean_envelope)]
        if sum(error) < ERROR_THRESHOLD:
            # deviation too small, series are converging
            break
        proto_imf = [(p_elem[0], p_elem[1] - m_elem[1]) for p_elem, m_elem in zip(proto_imf, mean_envelope)]
        s_i += 1
    if s_i > 0:
        return proto_imf
    return None

@dataclass
class EMD:
    "Emperical Mode Decomposition"
    max_IMFs: int = 7 # maximum number of components
    max_iterations: int = 0 # maximum iterations per each sifting

    def decompose(self, series: dict[int, float]):
        residue, k = list(series.items()), 0
        imfs = []
        while(self.max_IMFs == 0 or k < self.max_IMFs):
            imf = eval_sifting(residue, max_iterations=self.max_iterations)
            if not imf:
                break
            for p_i in range(len(residue)):
                residue[p_i] = (residue[p_i][0], residue[p_i][1] - imf[p_i][1])
            imfs.append(imf)
            k += 1
        return imfs
