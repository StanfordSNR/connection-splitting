"""
Define the data needed for an experiment.
"""
from typing import List, Optional


class Treatment:
    def __init__(self, protocol):
        self.protocol = protocol

    def label(self):
        raise NotImplementedError


class TCPTreatment(Treatment):
    def __init__(self, cca: str='cubic', pep: bool=False):
        super().__init__(protocol='tcp')
        self.cca = cca
        self.pep = pep

    def label(self) -> str:
        if self.pep:
            return f'pep_{self.cca}'
        else:
            return f'{self.protocol}_{self.cca}'


class NetworkSetting:
    def __init__(self, labels: List[str]=[], delay1: int=1, delay2:int =25,
                 loss1: str='1', loss2: str='0', bw1: int=100, bw2: int=10,
                 jitter1: Optional[int]=None, jitter2: Optional[int]=None):
        """
        Labels is a list of setting names e.g. "delay1", "jitter1" to use in
        generating the label. These will be used in alphabetical order.
        If empty (default), the label generator will use all setting names.
        """
        self.settings = {
            'delay1': delay1,
            'delay2': delay2,
            'loss1': loss1,
            'loss2': loss2,
            'bw1': bw1,
            'bw2': bw2,
            'jitter1': jitter1,
            'jitter2': jitter2,
        }
        self.labels = list(sorted(labels))

    def label(self) -> str:
        value = 'network_'
        if len(self.labels) == 0:
            labels = list(sorted(self.settings.keys()))
        else:
            labels = self.labels
        value += '_'.join([str(self.settings[key]) for key in labels])
        return value


class Experiment:
    def __init__(self,
                 num_trials: int,
                 treatments: List[Treatment],
                 network_settings: List[NetworkSetting],
                 data_sizes: List[int]):
        self.num_trials = num_trials
        self.treatments = [x.label() for x in treatments]
        self.network_settings = [x.label() for x in network_settings]
        self._treatments = { x.label(): x for x in treatments }
        self._network_settings = { x.label(): x for x in network_settings }
        self.data_sizes = data_sizes

    def get_treatment(self, label: str) -> Treatment:
        return self._treatments[label]

    def get_network_setting(self, label: str) -> NetworkSetting:
        return self._network_settings[label]

    def get_treatments(self) -> List[Treatment]:
        return [self._treatments[label] for label in self.treatments]

    def get_network_settings(self) -> List[NetworkSetting]:
        return [self._network_settings[label] for label in self.network_settings]
