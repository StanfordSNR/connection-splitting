from typing import Union, Optional, List
from common import *
from data import PlottableData, DirectRawData
from experiment import (
    Treatment, Experiment,
    DirectNetworkSetting, NetworkSetting,
)


class NetworkModel:
    def __init__(self, delay: int, loss: Union[int, float, str], bw: int):
        self.delay = delay
        self.loss = loss
        self.bw = bw

def combine_loss(loss_i, loss_j):
    return loss_i + loss_j

def combine_delay(delay_i, delay_j):
    combined_delay = delay_i + delay_j
    if delay_i == 1 or delay_j == 1:
        combined_delay -= 1
    return combined_delay

def combine_bw(bw_i, bw_j):
    return min(bw_i, bw_j)

def compose(s1: NetworkModel, s2: NetworkModel) -> NetworkModel:
    delay = combine_delay(s1.delay, s2.delay)
    loss = combine_loss(s1.loss, s2.loss)
    bw = combine_bw(s1.bw, s2.bw)
    return NetworkModel(delay, loss, bw)


def gen_direct_data(
    losses: List[Union[int, float, str]],
    delays: List[int],
    bws: List[int],
    treatments: List[Treatment],
    num_trials: int=10,
    timeout: int=180,
) -> PlottableData:
    # Create experiment
    exp = Experiment(
        num_trials, treatments, [], [],
        network_losses=[str(loss) for loss in losses],
        network_delays=delays,
        network_bws=bws,
        timeout=timeout,
        cartesian=False,
    )
    raw_data = DirectRawData(exp, execute=False)

    # Get plottable data
    metric = 'throughput_mbps'
    data = PlottableData(raw_data, metric=metric)
    return data


class TreatmentData:
    def __init__(
        self,
        treatment: Treatment,
        direct_data: PlottableData,
        pep_treatment: Optional[Treatment]=None,
        onehop_data: Optional[PlottableData]=None,
    ):
        self.tcp = treatment.label()
        self.pep = None if pep_treatment is None else pep_treatment.label()
        self.data = onehop_data
        self.direct_data = direct_data

    def goodput(self, s) -> Optional[float]:
        ns = DirectNetworkSetting(delay=s.delay, loss=s.loss, bw=s.bw)
        data_size = get_data_size(s.bw)
        result = self.direct_data.data[self.tcp][ns.label()].get(data_size)
        if result is None:
            return 0
        else:
            return result.p(50)

    def pred_split_goodput(self, s1: NetworkModel, s2: NetworkModel) -> Optional[float]:
        goodput1 = self.goodput(s1)
        goodput2 = self.goodput(s2)
        return min(goodput1, goodput2)

    def pred_e2e_goodput(self, s1: NetworkModel, s2: NetworkModel) -> Optional[float]:
        s = compose(s1, s2)
        return self.goodput(s)

    def real_split_goodput(self, ns: NetworkSetting) -> Optional[float]:
        if self.pep is None:
            raise Exception('treatment is not splittable')
        if self.data is None:
            raise Exception('one-hop data not provided')
        data_size = get_data_size(min(ns.get('bw1'), ns.get('bw2')))
        goodput = self.data.data[self.pep][ns.label()].get(data_size)
        return None if goodput is None else goodput.p(50)

    def real_e2e_goodput(self, ns: NetworkSetting) -> Optional[float]:
        if self.data is None:
            raise Exception('one-hop data not provided')
        data_size = get_data_size(min(ns.get('bw1'), ns.get('bw2')))
        goodput = self.data.data[self.tcp][ns.label()].get(data_size)
        return None if goodput is None else goodput.p(50)
