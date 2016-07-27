import datajoint as dj
from pipeline.preprocess import notnan
from . import preprocess, vis
import numpy as np


schema = dj.schema('pipeline_quality', locals())

@schema
class Spikes(dj.Computed):
    definition = """
    ->preprocess.Spikes
    ---
    leading_nans      : bool        # whether or not any of the traces has leading nans
    trailing_nans     : bool        # whether or not any of the traces has trailing nans
    stimulus_nans     : bool        # whether or not any of the traces has nans during the stimulus
    nan_idx=null      : longblob    # boolean array indicating where the nans are
    stimulus_start    : int         # start of the stimulus in matlab 1 based indices
    stimulus_end      : int         # end of the stimulus in matlab 1 based indices
    """

    @property
    def key_source(self):
        return preprocess.Spikes() & preprocess.Sync()

    def _make_tuples(self, key):
        print('Populating', key)
        spikes = np.vstack([s.squeeze() for s in (preprocess.Spikes.RateTrace() & key).fetch['rate_trace']])
        s = spikes.sum(axis=0)
        nans = np.isnan(s)

        key['leading_nans'] = int(nans[0])
        key['trailing_nans'] = int(nans[1])

        t = (preprocess.Sync() & key).fetch1['frame_times'] # does not need to be unique

        flip_first = (vis.Trial() * preprocess.Sync().proj('psy_id', trial_idx='first_trial') & key).fetch1['flip_times']
        flip_last = (vis.Trial() * preprocess.Sync().proj('psy_id', trial_idx='last_trial') & key).fetch1['flip_times']

        # (vis.Trial() * preprocess.Sync() & 'trial_idx between first_trial and last_trial')
        fro = np.atleast_1d(flip_first.squeeze())[0]
        to = np.atleast_1d(flip_last.squeeze())[-1] # not necessarily where the stimulus stopped, just last presentation
        idx_fro = np.argmin(np.abs(t-fro))
        idx_to = np.argmin(np.abs(t-to))+1
        key['stimulus_nans'] = int(np.any(nans[idx_fro:idx_to]))
        if np.any(nans):
            key['nan_idx'] = nans
        key['stimulus_start'] = idx_fro+1
        key['stimulus_end'] = idx_to

        self.insert1(key)

