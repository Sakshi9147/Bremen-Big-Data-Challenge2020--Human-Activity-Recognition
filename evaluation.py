import pandas
import numpy

read_labels = lambda path: pandas.read_csv(path, names=["trial","start", "end", "label"], header=None, usecols=[0,1,2,3])


def check_format(trial_name, labels, known_labels):
    # NaN check
    if labels.isnull().values.any():
        return False, "Some values are missing or are NaN in trial {}".format(trial_name)

    # dtypes check
    if not numpy.all(labels.dtypes == numpy.array([numpy.dtype('float64'), numpy.dtype('float64'), numpy.dtype('O')])):
        return False, "Incorrect data types"

    # must start at 0
    if labels.loc[0, "start"] != 0:
        return False, "Trial {}: Must start at 0".format(trial_name)

    # end must not be too far off
    if labels.iloc[-1, 1] > 300:
        return False, "Trial {}: End too far beyond the end of the data".format(trial_name)

    # end must be larger than start
    for i, (start, end, _) in labels.iterrows():
        if end <= start:
            return False, "Start of line must be smaller than end (line {} of trial {})".format(i+1, trial_name)

    # no time without a label and correct order
    for i in range(0, len(labels)-1):
        if round(labels.loc[i, "end"], 3) != round(labels.loc[i+1, "start"], 3):
            return False, "End of one line must be equal to start of next line (lines {} and {} in trial {})".format(i+1, i+2, trial_name)

    # only known labels
    given_labels = set(labels["label"])
    if not given_labels.issubset(known_labels):
        return False, "Trial {} contains unknown labels".format(trial_name)

    return True, "OK"

def _load_trials(file_path):
    # read file
    label_data = read_labels(file_path)

    # known labels
    label_set = set(label_data["label"].unique())

    # split into trials
    trials = {}
    trial_names = set(label_data["trial"].unique())
    for trial in trial_names:
        trials[trial] = label_data.loc[label_data["trial"] == trial, ["start", "end", "label"]].reset_index(drop=True)

    return trial_names, label_set, trials

def _make_framewise(labels):
    """
    Make one label for each frame of 1ms
    """
    step = 1 # this function is in milli seconds to avoid floating point problems
    labels_framewise = []
    for idx, (start, end, label) in labels.iterrows():
        curr = int(start*1000)
        while curr < int(end*1000):
            labels_framewise.append(label)
            curr += step

    return labels_framewise

def score_framewise(ref_labels_framewise, hyp_labels):
    hyp_labels_framewise = _make_framewise(hyp_labels)
    reference_length = len(ref_labels_framewise)

    # hyp overhang
    hyp_overhang_error = 0
    if len(hyp_labels_framewise) > reference_length:
        hyp_overhang_error = len(hyp_labels_framewise) - reference_length
        hyp_labels_framewise = hyp_labels_framewise[:reference_length]

    # ref overhang
    ref_overhang_error = 0
    if reference_length > len(hyp_labels_framewise):
        ref_overhang_error = reference_length - len(hyp_labels_framewise)
        ref_labels_framewise = ref_labels_framewise[:len(hyp_labels_framewise)]

    # calculate error
    acc_map = numpy.array(ref_labels_framewise) != numpy.array(hyp_labels_framewise)
    error_frames = sum(acc_map) + hyp_overhang_error + ref_overhang_error
    err = error_frames / reference_length

    return err, error_frames, reference_length

def score_all(hyp_data):
    total_error_frames = 0
    total_reference_length = 0

    for trial in ref_data:
        err, error_frames, reference_length = score_framewise(ref_labels_all_framewise[trial], hyp_data[trial])
        total_error_frames += error_frames
        total_reference_length += reference_length

    err = total_error_frames / total_reference_length

    return err

def evaluate_submission(submission_file):
    try:
        hyp_trials, hyp_label_names, hyp_data = _load_trials(submission_file)
        if ref_trials != hyp_trials:
            return float('nan'), "Trials not matching", True
        for trial in hyp_data:
            if trial.endswith("la"):
                known_label_names = ref_label_names_la
            else:
                known_label_names = ref_label_names_ra
            check_ok, check_msg = check_format(trial, hyp_data[trial], known_label_names)
            if not check_ok:
                return float('nan'), check_msg, True
    except Exception as e:
        return float('nan'), str(e), True

    try:
        score = score_all(hyp_data)
    except:
        return float('nan'), "Could not calculate error.", True

    return score, 'Valid file', True

# read globally
ref_trials, ref_label_names, ref_data = _load_trials("reference_labels.csv")
ref_label_names_la = set(l for l in ref_label_names if l.startswith("la"))
ref_label_names_ra = set(l for l in ref_label_names if l.startswith("ra"))
ref_labels_all_framewise = {}
for trial in ref_data:
    ref_labels_all_framewise[trial] = _make_framewise(ref_data[trial])
