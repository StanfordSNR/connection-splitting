import os

import numpy as np
import matplotlib.pyplot as plt
from experiment import (
    LinuxTCPTreatment, GoogleQUICTreatment,
    CloudflareQUICTreatment, PicoQUICTreatment,
)

WORKDIR = f'{os.environ["HOME"]}/connection-splitting'

TCP_CUBIC = LinuxTCPTreatment(cca='cubic', pep=False, label='tcp_cubic')
TCP_BBRV1 = LinuxTCPTreatment(cca='bbr', pep=False, label='tcp_bbr1')
TCP_BBRV2 = LinuxTCPTreatment(cca='bbr2', pep=False, label='tcp_bbr2')
TCP_BBRV3 = LinuxTCPTreatment(cca='bbr', pep=False, label='tcp_bbr3')
TCP_RENO = LinuxTCPTreatment(cca='reno', pep=False, label='tcp_reno')
PEP_CUBIC = LinuxTCPTreatment(cca='cubic', pep=True, label='pep_cubic')
PEP_BBRV1 = LinuxTCPTreatment(cca='bbr', pep=True, label='pep_bbr1')
PEP_BBRV2 = LinuxTCPTreatment(cca='bbr2', pep=True, label='pep_bbr2')
PEP_BBRV3 = LinuxTCPTreatment(cca='bbr', pep=True, label='pep_bbr3')
PEP_RENO = LinuxTCPTreatment(cca='reno', pep=True, label='pep_reno')
QUIC_CUBIC = GoogleQUICTreatment(cca='cubic', label='quic_cubic')
QUIC_BBRV1 = GoogleQUICTreatment(cca='bbr1', label='quic_bbr1')
QUIC_BBRV3 = GoogleQUICTreatment(cca='bbr', label='quic_bbr3')
QUIC_RENO = GoogleQUICTreatment(cca='reno', label='quic_reno')
QUICHE_CUBIC = CloudflareQUICTreatment(cca='cubic', label='quiche_cubic')
QUICHE_BBRV1 = CloudflareQUICTreatment(cca='bbr', label='quiche_bbr1')
QUICHE_BBRV2 = CloudflareQUICTreatment(cca='bbr', label='quiche_bbr2')
QUICHE_RENO = CloudflareQUICTreatment(cca='reno', label='quiche_reno')
PICOQUIC_CUBIC = PicoQUICTreatment(cca='cubic', label='picoquic_cubic')
PICOQUIC_BBRV1 = PicoQUICTreatment(cca='bbr1', label='picoquic_bbr1')
PICOQUIC_BBRV3 = PicoQUICTreatment(cca='bbr', label='picoquic_bbr3')

plt_label = {
    'tcp_cubic': 'TCP CUBIC',
    'tcp_bbr1': 'TCP BBRv1',
    'tcp_bbr2': 'TCP BBRv2',
    'tcp_bbr3': 'TCP BBRv3',
    'tcp_reno': 'TCP Reno',
    'quic_cubic': 'Chromium QUIC CUBIC',
    'quic_bbr1': 'Chromium QUIC BBRv1',
    'quic_bbr3': 'Chromium QUIC BBRv3',
    'quic_reno': 'Chromium QUIC Reno',
    'quiche_cubic': 'Cloudflare QUIC CUBIC',
    'quiche_bbr1': 'Cloudflare QUIC BBRv1',
    'quiche_bbr2': 'Cloudflare QUIC BBRv2',
    'quiche_reno': 'Cloudflare QUIC Reno',
    'picoquic_cubic': 'Picoquic QUIC CUBIC',
    'picoquic_bbr1': 'Picoquic QUIC BBRv1',
    'picoquic_bbr3': 'Picoquic QUIC BBRv3',
}

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

def save_pdf(output_filename, bbox_inches='tight'):
    from matplotlib.backends.backend_pdf import PdfPages
    if output_filename is not None:
        with PdfPages(output_filename) as pdf:
            pdf.savefig(bbox_inches=bbox_inches)
    print(output_filename)
