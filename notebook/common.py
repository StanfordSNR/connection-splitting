import os

import numpy as np
import matplotlib.pyplot as plt
from experiment import TCPTreatment, QUICTreatment, CloudflareQUICTreatment

SIDEKICK_HOME = f'{os.environ["HOME"]}/sidekick-downloads'

TCP_CUBIC = TCPTreatment(cca='cubic', pep=False, label='tcp_cubic')
TCP_BBRV1 = TCPTreatment(cca='bbr', pep=False, label='tcp_bbr1')
TCP_BBRV2 = TCPTreatment(cca='bbr2', pep=False, label='tcp_bbr2')
TCP_BBRV3 = TCPTreatment(cca='bbr', pep=False, label='tcp_bbr3')
TCP_RENO = TCPTreatment(cca='reno', pep=False, label='tcp_reno')
PEP_CUBIC = TCPTreatment(cca='cubic', pep=True, label='pep_cubic')
PEP_BBRV1 = TCPTreatment(cca='bbr', pep=True, label='pep_bbr1')
PEP_BBRV2 = TCPTreatment(cca='bbr2', pep=True, label='pep_bbr2')
PEP_BBRV3 = TCPTreatment(cca='bbr', pep=True, label='pep_bbr3')
PEP_RENO = TCPTreatment(cca='reno', pep=True, label='pep_reno')
QUIC_CUBIC = QUICTreatment(cca='cubic', label='quic_cubic')
QUIC_BBRV1 = QUICTreatment(cca='bbr1', label='quic_bbr1')
QUIC_BBRV3 = QUICTreatment(cca='bbr', label='quic_bbr3')
QUIC_RENO = QUICTreatment(cca='reno', label='quic_reno')
QUICHE_CUBIC = CloudflareQUICTreatment(cca='cubic', label='quiche_cubic')
QUICHE_BBRV1 = CloudflareQUICTreatment(cca='bbr', label='quiche_bbr1')
QUICHE_BBRV2 = CloudflareQUICTreatment(cca='bbr', label='quiche_bbr2')
QUICHE_RENO = CloudflareQUICTreatment(cca='reno', label='quiche_reno')

def get_data_size(bottleneck_bw):
    return int(10*1000000*bottleneck_bw/8)  # 10s at the bottleneck bandwidth

def data_size_str(data_size):
    if data_size < 1e3:
        return f'{data_size}B'
    elif data_size < 1e6:
        return f'{int(data_size/1e3)}K'
    elif data_size < 1e9:
        return f'{int(data_size/1e6)}M'
    elif data_size < 1e12:
        return f'{int(data_size/1e6)}G'
