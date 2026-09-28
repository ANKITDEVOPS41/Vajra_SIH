import numpy as np

def calculate_contingency_matrix(pred: np.ndarray, obs: np.ndarray, threshold: float):
    """
    Calculates Hits (a), False Alarms (b), Misses (c), and Correct Negatives (d).
    """
    pred_bin = (pred >= threshold).astype(int)
    obs_bin = (obs >= threshold).astype(int)
    
    hits = np.sum((pred_bin == 1) & (obs_bin == 1))
    false_alarms = np.sum((pred_bin == 1) & (obs_bin == 0))
    misses = np.sum((pred_bin == 0) & (obs_bin == 1))
    correct_negatives = np.sum((pred_bin == 0) & (obs_bin == 0))
    
    return hits, false_alarms, misses, correct_negatives

def csi(hits, false_alarms, misses):
    """Critical Success Index (Threat Score)"""
    ans = hits / (hits + false_alarms + misses + 1e-6)
    return ans

def pod(hits, misses):
    """Probability of Detection"""
    ans = hits / (hits + misses + 1e-6)
    return ans

def far(hits, false_alarms):
    """False Alarm Ratio"""
    ans = false_alarms / (hits + false_alarms + 1e-6)
    return ans

def compute_all_metrics(pred: np.ndarray, obs: np.ndarray, thresholds=[35, 50]):
    """
    Evaluate predicted array vs observed array at given thresholds (dBZ).
    """
    results = {}
    for t in thresholds:
        h, fa, m, cn = calculate_contingency_matrix(pred, obs, t)
        results[f"{t}dBZ"] = {
            "CSI": float(csi(h, fa, m)),
            "POD": float(pod(h, m)),
            "FAR": float(far(h, fa))
        }
    return results
