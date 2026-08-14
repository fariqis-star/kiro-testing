def reward_function(response, ground_truth):
    """Simple reward: 1.0 if answer contains ground truth, 0.0 otherwise."""
    if not response or not ground_truth:
        return 0.0
    response_lower = response.strip().lower()
    truth_lower = ground_truth.strip().lower()
    if truth_lower in response_lower:
        return 1.0
    return 0.0
