#!/usr/bin/env python3
"""
Broadcasting Bug Examples for Neural Networks/LLMs
===================================================
A comprehensive collection of broadcasting bugs and correct patterns.
Used to test and refine static analysis rules.

Each section has:
- BUG: Code that will produce incorrect results due to broadcasting
- CORRECT: The fixed version
"""

import numpy as np

# =============================================================================
# SECTION 1: Basic Reduction Broadcasting Bugs
# =============================================================================

def normalize_features_bug(X):
    """Normalize features to zero mean - BUGGY."""
    # BUG: np.mean returns shape (n_features,), X is (n_samples, n_features)
    # Broadcasting subtracts wrong dimensions
    mean = np.mean(X, axis=0)
    return X - mean  # This actually works! axis=0 reduces samples, keeps features

def normalize_samples_bug(X):
    """Normalize each sample to zero mean - BUGGY."""
    # BUG: np.mean(axis=1) returns shape (n_samples,), X is (n_samples, n_features)
    # Cannot broadcast (n_samples,) with (n_samples, n_features) correctly
    mean = np.mean(X, axis=1)
    return X - mean  # ERROR: shapes don't align

def normalize_samples_correct_keepdims(X):
    """Normalize each sample - CORRECT with keepdims."""
    mean = np.mean(X, axis=1, keepdims=True)
    return X - mean

def normalize_samples_correct_newaxis(X):
    """Normalize each sample - CORRECT with newaxis."""
    mean = np.mean(X, axis=1)[:, np.newaxis]
    return X - mean

def normalize_samples_correct_none(X):
    """Normalize each sample - CORRECT with None indexing."""
    mean = np.mean(X, axis=1)[:, None]
    return X - mean

def normalize_samples_correct_reshape(X):
    """Normalize each sample - CORRECT with reshape."""
    mean = np.mean(X, axis=1).reshape(-1, 1)
    return X - mean


# =============================================================================
# SECTION 2: Softmax Implementation Bugs
# =============================================================================

def softmax_bug_v1(logits):
    """Softmax over last axis - BUGGY."""
    # BUG: max without keepdims, then used in subtraction
    max_logits = np.max(logits, axis=-1)
    exp_logits = np.exp(logits - max_logits)  # Broadcasting error!
    return exp_logits / np.sum(exp_logits, axis=-1)  # Another error!

def softmax_bug_v2(logits):
    """Softmax - BUGGY with intermediate variable."""
    # BUG: Even with intermediate, the broadcast fails
    shifted = logits - np.max(logits, axis=-1)  # BUG here
    exp_shifted = np.exp(shifted)
    return exp_shifted / np.sum(exp_shifted, axis=-1)  # BUG here too

def softmax_correct_keepdims(logits):
    """Softmax - CORRECT with keepdims."""
    max_logits = np.max(logits, axis=-1, keepdims=True)
    exp_logits = np.exp(logits - max_logits)
    return exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)

def softmax_correct_newaxis(logits):
    """Softmax - CORRECT with newaxis."""
    max_logits = np.max(logits, axis=-1)[..., np.newaxis]
    exp_logits = np.exp(logits - max_logits)
    return exp_logits / np.sum(exp_logits, axis=-1)[..., np.newaxis]


# =============================================================================
# SECTION 3: Layer Normalization Bugs
# =============================================================================

def layer_norm_bug(x, gamma, beta, eps=1e-5):
    """Layer normalization - BUGGY."""
    # x shape: (batch, seq_len, hidden_dim)
    # Normalize over hidden_dim (axis=-1)
    mean = np.mean(x, axis=-1)  # shape: (batch, seq_len)
    var = np.var(x, axis=-1)    # shape: (batch, seq_len)
    # BUG: mean and var need extra dimension to broadcast
    x_norm = (x - mean) / np.sqrt(var + eps)  # Broadcasting error!
    return gamma * x_norm + beta

def layer_norm_correct(x, gamma, beta, eps=1e-5):
    """Layer normalization - CORRECT."""
    mean = np.mean(x, axis=-1, keepdims=True)
    var = np.var(x, axis=-1, keepdims=True)
    x_norm = (x - mean) / np.sqrt(var + eps)
    return gamma * x_norm + beta


# =============================================================================
# SECTION 4: Batch Normalization Bugs
# =============================================================================

def batch_norm_bug(x, gamma, beta, eps=1e-5):
    """Batch normalization for conv layers - BUGGY."""
    # x shape: (batch, channels, height, width)
    # Normalize over batch, height, width (axes 0, 2, 3)
    mean = np.mean(x, axis=(0, 2, 3))  # shape: (channels,)
    var = np.var(x, axis=(0, 2, 3))    # shape: (channels,)
    # BUG: need to reshape mean/var to (1, channels, 1, 1)
    x_norm = (x - mean) / np.sqrt(var + eps)  # Broadcast might work but unclear
    return gamma * x_norm + beta

def batch_norm_correct(x, gamma, beta, eps=1e-5):
    """Batch normalization - CORRECT."""
    mean = np.mean(x, axis=(0, 2, 3), keepdims=True)
    var = np.var(x, axis=(0, 2, 3), keepdims=True)
    x_norm = (x - mean) / np.sqrt(var + eps)
    return gamma * x_norm + beta

def batch_norm_correct_reshape(x, gamma, beta, eps=1e-5):
    """Batch normalization - CORRECT with explicit reshape."""
    mean = np.mean(x, axis=(0, 2, 3)).reshape(1, -1, 1, 1)
    var = np.var(x, axis=(0, 2, 3)).reshape(1, -1, 1, 1)
    x_norm = (x - mean) / np.sqrt(var + eps)
    return gamma * x_norm + beta


# =============================================================================
# SECTION 5: Attention Mechanism Bugs
# =============================================================================

def attention_scores_bug(Q, K, d_k):
    """Compute attention scores - BUGGY."""
    # Q, K shape: (batch, heads, seq_len, d_k)
    scores = np.matmul(Q, K.transpose(0, 1, 3, 2)) / np.sqrt(d_k)
    # Apply softmax over last axis
    max_scores = np.max(scores, axis=-1)
    exp_scores = np.exp(scores - max_scores)  # BUG: broadcasting
    return exp_scores / np.sum(exp_scores, axis=-1)  # BUG: broadcasting

def attention_scores_correct(Q, K, d_k):
    """Compute attention scores - CORRECT."""
    scores = np.matmul(Q, K.transpose(0, 1, 3, 2)) / np.sqrt(d_k)
    max_scores = np.max(scores, axis=-1, keepdims=True)
    exp_scores = np.exp(scores - max_scores)
    return exp_scores / np.sum(exp_scores, axis=-1, keepdims=True)


# =============================================================================
# SECTION 6: Loss Function Bugs
# =============================================================================

def cross_entropy_bug(logits, targets):
    """Cross entropy loss - BUGGY."""
    # logits: (batch, num_classes), targets: (batch,) as indices
    # Compute log softmax
    max_logits = np.max(logits, axis=1)
    shifted = logits - max_logits  # BUG: broadcasting
    log_sum_exp = np.log(np.sum(np.exp(shifted), axis=1))
    log_probs = shifted - log_sum_exp  # BUG: broadcasting
    # Gather correct class probabilities
    batch_size = logits.shape[0]
    return -np.mean(log_probs[np.arange(batch_size), targets])

def cross_entropy_correct(logits, targets):
    """Cross entropy loss - CORRECT."""
    max_logits = np.max(logits, axis=1, keepdims=True)
    shifted = logits - max_logits
    log_sum_exp = np.log(np.sum(np.exp(shifted), axis=1, keepdims=True))
    log_probs = shifted - log_sum_exp
    batch_size = logits.shape[0]
    return -np.mean(log_probs[np.arange(batch_size), targets])


def mse_loss_bug(predictions, targets):
    """MSE loss per sample then average - BUGGY."""
    # predictions, targets: (batch, features)
    # Want: mean over features for each sample, then mean over batch
    per_sample_mse = np.mean((predictions - targets) ** 2, axis=1)
    # This is actually fine, but if we wanted to weight:
    weights = np.array([1.0, 2.0, 1.0])  # per-feature weights
    weighted_sq_err = weights * (predictions - targets) ** 2  # Works if shapes align
    return np.mean(weighted_sq_err)


# =============================================================================
# SECTION 7: Embedding and Projection Bugs
# =============================================================================

def add_positional_encoding_bug(embeddings, max_len, d_model):
    """Add positional encoding - BUGGY."""
    # embeddings: (batch, seq_len, d_model)
    position = np.arange(max_len)
    div_term = np.exp(np.arange(0, d_model, 2) * -(np.log(10000.0) / d_model))

    pe = np.zeros((max_len, d_model))
    pe[:, 0::2] = np.sin(position * div_term)  # BUG: position is (max_len,), div_term is (d_model/2,)
    pe[:, 1::2] = np.cos(position * div_term)  # Need position[:, np.newaxis]

    return embeddings + pe  # This might work if seq_len <= max_len

def add_positional_encoding_correct(embeddings, max_len, d_model):
    """Add positional encoding - CORRECT."""
    position = np.arange(max_len)[:, np.newaxis]
    div_term = np.exp(np.arange(0, d_model, 2) * -(np.log(10000.0) / d_model))

    pe = np.zeros((max_len, d_model))
    pe[:, 0::2] = np.sin(position * div_term)
    pe[:, 1::2] = np.cos(position * div_term)

    seq_len = embeddings.shape[1]
    return embeddings + pe[:seq_len]


# =============================================================================
# SECTION 8: Gradient Computation Bugs
# =============================================================================

def softmax_backward_bug(grad_output, softmax_output):
    """Backward pass for softmax - BUGGY."""
    # grad_output, softmax_output: (batch, num_classes)
    # d_softmax/d_input = softmax * (grad - sum(grad * softmax))
    sum_term = np.sum(grad_output * softmax_output, axis=1)
    return softmax_output * (grad_output - sum_term)  # BUG: sum_term needs keepdims

def softmax_backward_correct(grad_output, softmax_output):
    """Backward pass for softmax - CORRECT."""
    sum_term = np.sum(grad_output * softmax_output, axis=1, keepdims=True)
    return softmax_output * (grad_output - sum_term)


def layer_norm_backward_bug(grad_output, x, mean, var, gamma, eps=1e-5):
    """Backward pass for layer norm - BUGGY."""
    # All inputs: (batch, seq_len, hidden_dim) except mean/var: (batch, seq_len)
    N = x.shape[-1]
    std = np.sqrt(var + eps)
    x_centered = x - mean  # BUG: mean needs keepdims
    x_norm = x_centered / std  # BUG: std needs keepdims

    # Gradients
    dgamma = np.sum(grad_output * x_norm, axis=(0, 1))
    dbeta = np.sum(grad_output, axis=(0, 1))

    dx_norm = grad_output * gamma
    dvar = np.sum(dx_norm * x_centered * -0.5 * (var + eps) ** -1.5, axis=-1)
    dmean = np.sum(dx_norm * -1 / std, axis=-1)

    dx = dx_norm / std + dvar * 2 * x_centered / N + dmean / N  # Multiple bugs
    return dx, dgamma, dbeta


# =============================================================================
# SECTION 9: Various Reduction Operations in Binary Contexts
# =============================================================================

def scale_by_norm_bug(vectors):
    """Scale vectors by their L2 norm - BUGGY."""
    # vectors: (batch, dim)
    norms = np.sqrt(np.sum(vectors ** 2, axis=1))
    return vectors / norms  # BUG: norms is (batch,), vectors is (batch, dim)

def scale_by_norm_correct(vectors):
    """Scale vectors by L2 norm - CORRECT."""
    norms = np.sqrt(np.sum(vectors ** 2, axis=1, keepdims=True))
    return vectors / norms

def scale_by_norm_correct_v2(vectors):
    """Scale vectors by L2 norm - CORRECT v2."""
    norms = np.sqrt(np.sum(vectors ** 2, axis=1))[:, None]
    return vectors / norms

def scale_by_norm_correct_v3(vectors):
    """Scale vectors by L2 norm - CORRECT v3."""
    norms = np.sqrt(np.sum(vectors ** 2, axis=1))
    return vectors / norms[:, np.newaxis]

def scale_by_norm_correct_v4(vectors):
    """Scale vectors by L2 norm - CORRECT v4."""
    norms = np.sqrt(np.sum(vectors ** 2, axis=1))
    return vectors / norms.reshape(-1, 1)


def center_data_bug(data):
    """Center data by subtracting mean - BUGGY."""
    # data: (samples, features)
    sample_means = np.mean(data, axis=1)
    return data - sample_means  # BUG

def center_data_correct(data):
    """Center data - CORRECT."""
    sample_means = np.mean(data, axis=1, keepdims=True)
    return data - sample_means


def standardize_bug(data):
    """Standardize data - BUGGY."""
    mean = np.mean(data, axis=1)
    std = np.std(data, axis=1)
    return (data - mean) / std  # BUG: both mean and std need keepdims

def standardize_correct(data):
    """Standardize data - CORRECT."""
    mean = np.mean(data, axis=1, keepdims=True)
    std = np.std(data, axis=1, keepdims=True)
    return (data - mean) / std


# =============================================================================
# SECTION 10: Multi-dimensional Reductions
# =============================================================================

def global_avg_pool_bug(feature_maps):
    """Global average pooling - BUGGY."""
    # feature_maps: (batch, channels, height, width)
    # Want: (batch, channels)
    pooled = np.mean(feature_maps, axis=(2, 3))
    # If we then want to scale back:
    return feature_maps * pooled  # BUG: shapes don't match

def global_avg_pool_correct(feature_maps):
    """Global average pooling with scaling - CORRECT."""
    pooled = np.mean(feature_maps, axis=(2, 3), keepdims=True)
    return feature_maps * pooled


def channel_attention_bug(feature_maps):
    """Channel attention mechanism - BUGGY."""
    # feature_maps: (batch, channels, height, width)
    # Compute channel-wise statistics
    avg_pool = np.mean(feature_maps, axis=(2, 3))  # (batch, channels)
    max_pool = np.max(feature_maps, axis=(2, 3))   # (batch, channels)

    # Combine (simplified)
    attention = 1 / (1 + np.exp(-(avg_pool + max_pool)))  # sigmoid, shape (batch, channels)

    # Apply attention
    return feature_maps * attention  # BUG: need attention[:, :, None, None]

def channel_attention_correct(feature_maps):
    """Channel attention - CORRECT."""
    avg_pool = np.mean(feature_maps, axis=(2, 3), keepdims=True)
    max_pool = np.max(feature_maps, axis=(2, 3), keepdims=True)
    attention = 1 / (1 + np.exp(-(avg_pool + max_pool)))
    return feature_maps * attention


# =============================================================================
# SECTION 11: Tricky Cases - Inline Reductions in Expressions
# =============================================================================

def inline_normalize_bug(x):
    """Inline normalization - BUGGY."""
    # All in one line makes it harder to spot
    return (x - np.mean(x, axis=1)) / np.std(x, axis=1)  # BUG

def inline_normalize_correct(x):
    """Inline normalization - CORRECT."""
    return (x - np.mean(x, axis=1, keepdims=True)) / np.std(x, axis=1, keepdims=True)


def compound_expression_bug(x, y):
    """Compound expression - BUGGY."""
    # Multiple reductions in one expression
    return x - np.mean(x, axis=1) + y * np.std(y, axis=1)  # Two bugs!

def compound_expression_correct(x, y):
    """Compound expression - CORRECT."""
    return x - np.mean(x, axis=1, keepdims=True) + y * np.std(y, axis=1, keepdims=True)


def nested_reduction_bug(x):
    """Nested operations - BUGGY."""
    # Reduction result used in another operation
    centered = x - np.mean(x, axis=1)  # BUG
    return centered / np.std(centered, axis=1)  # BUG

def nested_reduction_correct(x):
    """Nested operations - CORRECT."""
    centered = x - np.mean(x, axis=1, keepdims=True)
    return centered / np.std(centered, axis=1, keepdims=True)


# =============================================================================
# SECTION 12: Edge Cases and Variations
# =============================================================================

def reduction_with_where_bug(x, mask):
    """Masked reduction - BUGGY."""
    # x: (batch, seq_len), mask: (batch, seq_len)
    masked_sum = np.sum(x * mask, axis=1)
    mask_sum = np.sum(mask, axis=1)
    masked_mean = masked_sum / mask_sum
    return x - masked_mean  # BUG

def reduction_with_where_correct(x, mask):
    """Masked reduction - CORRECT."""
    masked_sum = np.sum(x * mask, axis=1, keepdims=True)
    mask_sum = np.sum(mask, axis=1, keepdims=True)
    masked_mean = masked_sum / mask_sum
    return x - masked_mean


def argmax_related_bug(logits):
    """Using argmax-related patterns - BUGGY."""
    # logits: (batch, num_classes)
    max_logits = np.max(logits, axis=1)
    # Subtract max for numerical stability before softmax
    stable_logits = logits - max_logits  # BUG
    return np.exp(stable_logits)

def argmax_related_correct(logits):
    """Using argmax-related patterns - CORRECT."""
    max_logits = np.max(logits, axis=1, keepdims=True)
    stable_logits = logits - max_logits
    return np.exp(stable_logits)


def prod_reduction_bug(x):
    """Product reduction - BUGGY."""
    # x: (batch, factors)
    total_product = np.prod(x, axis=1)
    # Normalize each element by total product
    return x / total_product  # BUG

def prod_reduction_correct(x):
    """Product reduction - CORRECT."""
    total_product = np.prod(x, axis=1, keepdims=True)
    return x / total_product


def any_all_reduction_bug(mask):
    """Boolean reduction - potentially BUGGY pattern."""
    # mask: (batch, seq_len)
    any_true = np.any(mask, axis=1)
    # This is usually fine as-is, but if used in multiplication:
    return mask * any_true  # BUG if we want to broadcast

def any_all_reduction_correct(mask):
    """Boolean reduction - CORRECT."""
    any_true = np.any(mask, axis=1, keepdims=True)
    return mask * any_true


# =============================================================================
# SECTION 13: Method Chaining and Complex Expressions
# =============================================================================

def chained_operations_bug(x):
    """Chained numpy operations - BUGGY."""
    # Multiple operations that could fail
    return np.exp(x - np.max(x, axis=-1)) / np.sum(np.exp(x - np.max(x, axis=-1)), axis=-1)

def chained_operations_correct(x):
    """Chained operations - CORRECT."""
    x_max = np.max(x, axis=-1, keepdims=True)
    exp_x = np.exp(x - x_max)
    return exp_x / np.sum(exp_x, axis=-1, keepdims=True)


def ternary_with_reduction_bug(x, threshold):
    """Conditional with reduction - BUGGY."""
    mean_vals = np.mean(x, axis=1)
    # Using reduction result in comparison then broadcasting
    return np.where(x > mean_vals, x, 0)  # BUG: mean_vals needs expansion

def ternary_with_reduction_correct(x, threshold):
    """Conditional with reduction - CORRECT."""
    mean_vals = np.mean(x, axis=1, keepdims=True)
    return np.where(x > mean_vals, x, 0)


# =============================================================================
# SECTION 14: Positional Axis Arguments
# =============================================================================

def positional_axis_bug_1(x):
    """Using positional axis argument - BUGGY."""
    # np.mean(a, axis) - axis is second positional arg
    return x - np.mean(x, 1)  # BUG: positional axis=1

def positional_axis_correct_1(x):
    """Using positional axis argument - CORRECT."""
    return x - np.mean(x, 1, keepdims=True)


def positional_axis_bug_2(x):
    """Multiple positional args - BUGGY."""
    # np.sum(a, axis, dtype, ...)
    return x - np.sum(x, 1, np.float64)  # BUG: axis=1 positional

def positional_axis_correct_2(x):
    """Multiple positional args - CORRECT."""
    return x - np.sum(x, 1, np.float64, keepdims=True)


# =============================================================================
# SECTION 15: Division Patterns
# =============================================================================

def normalize_by_sum_bug(x):
    """Normalize rows to sum to 1 - BUGGY."""
    row_sums = np.sum(x, axis=1)
    return x / row_sums  # BUG

def normalize_by_sum_correct(x):
    """Normalize rows - CORRECT."""
    row_sums = np.sum(x, axis=1, keepdims=True)
    return x / row_sums


def normalize_by_max_bug(x):
    """Normalize by max value - BUGGY."""
    row_max = np.max(x, axis=1)
    return x / row_max  # BUG

def normalize_by_max_correct(x):
    """Normalize by max - CORRECT."""
    row_max = np.max(x, axis=1, keepdims=True)
    return x / row_max


def normalize_by_min_max_bug(x):
    """Min-max normalization - BUGGY."""
    row_min = np.min(x, axis=1)
    row_max = np.max(x, axis=1)
    return (x - row_min) / (row_max - row_min)  # BUG: both need keepdims

def normalize_by_min_max_correct(x):
    """Min-max normalization - CORRECT."""
    row_min = np.min(x, axis=1, keepdims=True)
    row_max = np.max(x, axis=1, keepdims=True)
    return (x - row_min) / (row_max - row_min)


# =============================================================================
# SECTION 16: Correct Patterns That Should NOT Be Flagged
# =============================================================================

def correct_reduction_to_scalar(x):
    """Reduction to scalar is fine."""
    # No axis specified = reduce all dimensions
    return x - np.mean(x)  # CORRECT: scalar subtraction


def correct_matching_dimensions(x):
    """Reduction along axis 0 with 2D array."""
    # x: (n_samples, n_features)
    # mean along axis 0 gives (n_features,) which broadcasts correctly
    return x - np.mean(x, axis=0)  # CORRECT for this use case


def correct_explicit_reshape(x):
    """Explicit reshape handles dimensions."""
    mean = np.mean(x, axis=1)
    return x - mean.reshape(-1, 1)  # CORRECT


def correct_newaxis_after(x):
    """Newaxis applied after reduction."""
    mean = np.mean(x, axis=1)
    return x - mean[:, np.newaxis]  # CORRECT


def correct_none_indexing(x):
    """None indexing after reduction."""
    mean = np.mean(x, axis=1)
    return x - mean[:, None]  # CORRECT


def correct_subscript_expansion(x):
    """Subscript to expand dimensions."""
    mean = np.mean(x, axis=1)
    return x - mean[..., None]  # CORRECT


def correct_intermediate_reshape(x):
    """Intermediate variable with reshape."""
    mean = np.mean(x, axis=1)
    mean_expanded = mean[:, None]
    return x - mean_expanded  # CORRECT (though linter may not track this)


def correct_keepdims_true(x):
    """Using keepdims=True."""
    return x - np.mean(x, axis=1, keepdims=True)  # CORRECT


def correct_1d_array(x):
    """1D array reduction is fine."""
    # x: (n,)
    return x - np.mean(x)  # CORRECT: scalar


# =============================================================================
# SECTION 17: Edge Cases for Detection
# =============================================================================

def aliased_numpy_bug(x):
    """Using numpy alias - BUGGY."""
    import numpy as npy
    return x - npy.mean(x, axis=1)  # BUG but might not detect due to alias


def method_style_bug(x):
    """Using method style - BUGGY."""
    # ndarray.mean() instead of np.mean()
    return x - x.mean(axis=1)  # BUG but uses method not function


def reduction_in_function_call_bug(x):
    """Reduction as function argument - might be BUGGY."""
    # Hard to detect context
    return np.multiply(x, np.sum(x, axis=1))  # BUG but not in +/-/*// binop


def reduction_stored_then_used_bug(x):
    """Reduction stored, then used later - BUGGY."""
    mean_val = np.mean(x, axis=1)
    # ... other code ...
    result = x - mean_val  # BUG but hard to track
    return result


# =============================================================================
# SECTION 18: LLM-Specific Patterns
# =============================================================================

def rms_norm_bug(x, gamma, eps=1e-6):
    """RMSNorm (used in Llama) - BUGGY."""
    # x shape: (batch, seq_len, hidden_dim)
    # Compute RMS over hidden_dim
    rms = np.sqrt(np.mean(x ** 2, axis=-1) + eps)  # shape: (batch, seq_len)
    x_norm = x / rms  # BUG: rms needs keepdims
    return gamma * x_norm

def rms_norm_correct(x, gamma, eps=1e-6):
    """RMSNorm - CORRECT."""
    rms = np.sqrt(np.mean(x ** 2, axis=-1, keepdims=True) + eps)
    x_norm = x / rms
    return gamma * x_norm


def temperature_sampling_bug(logits, temperature):
    """Apply temperature to logits - BUGGY."""
    # logits: (batch, vocab_size)
    # Numerical stability: subtract max
    max_logits = np.max(logits, axis=-1)
    scaled = (logits - max_logits) / temperature  # BUG: max_logits needs keepdims
    exp_scaled = np.exp(scaled)
    return exp_scaled / np.sum(exp_scaled, axis=-1)  # BUG: sum needs keepdims

def temperature_sampling_correct(logits, temperature):
    """Apply temperature - CORRECT."""
    max_logits = np.max(logits, axis=-1, keepdims=True)
    scaled = (logits - max_logits) / temperature
    exp_scaled = np.exp(scaled)
    return exp_scaled / np.sum(exp_scaled, axis=-1, keepdims=True)


def top_k_filtering_bug(logits, k):
    """Top-k filtering - BUGGY."""
    # logits: (batch, vocab_size)
    # Get k-th largest value for each batch
    sorted_logits = np.sort(logits, axis=-1)[:, ::-1]
    kth_values = sorted_logits[:, k-1]  # shape: (batch,)
    # Mask out values below threshold
    return np.where(logits < kth_values, -np.inf, logits)  # BUG: kth_values needs keepdims

def top_k_filtering_correct(logits, k):
    """Top-k filtering - CORRECT."""
    sorted_logits = np.sort(logits, axis=-1)[:, ::-1]
    kth_values = sorted_logits[:, k-1:k]  # shape: (batch, 1) - slicing preserves dim
    return np.where(logits < kth_values, -np.inf, logits)


def cosine_similarity_bug(a, b):
    """Cosine similarity between batches of vectors - BUGGY."""
    # a, b: (batch, dim)
    dot = np.sum(a * b, axis=-1)  # (batch,)
    norm_a = np.sqrt(np.sum(a ** 2, axis=-1))  # (batch,)
    norm_b = np.sqrt(np.sum(b ** 2, axis=-1))  # (batch,)
    # This is fine for scalar output, but if used to scale:
    return a * (dot / (norm_a * norm_b))  # BUG if we want element-wise scaling

def cosine_similarity_correct(a, b):
    """Cosine similarity for scaling - CORRECT."""
    dot = np.sum(a * b, axis=-1, keepdims=True)
    norm_a = np.sqrt(np.sum(a ** 2, axis=-1, keepdims=True))
    norm_b = np.sqrt(np.sum(b ** 2, axis=-1, keepdims=True))
    return a * (dot / (norm_a * norm_b))


def attention_mask_bug(scores, mask):
    """Apply attention mask - BUGGY."""
    # scores: (batch, heads, seq_len, seq_len)
    # mask: (batch, seq_len) - needs to be (batch, 1, 1, seq_len) or (batch, 1, seq_len, 1)
    # Incorrect: directly adding mask to scores
    return scores + mask  # BUG: mask needs expansion to (batch, 1, 1, seq_len)

def attention_mask_correct(scores, mask):
    """Apply attention mask - CORRECT."""
    # Expand mask to (batch, 1, 1, seq_len)
    mask_expanded = mask[:, None, None, :]
    return scores + mask_expanded


def gelu_approx_bug(x):
    """Approximate GELU activation - potentially BUGGY."""
    # x: (batch, seq_len, hidden_dim)
    # If we wanted to normalize then apply GELU:
    x_norm = x - np.mean(x, axis=-1)  # BUG if we intended normalized GELU
    return 0.5 * x_norm * (1 + np.tanh(np.sqrt(2 / np.pi) * (x_norm + 0.044715 * x_norm**3)))

def gelu_approx_correct(x):
    """Approximate GELU with normalization - CORRECT."""
    x_norm = x - np.mean(x, axis=-1, keepdims=True)
    return 0.5 * x_norm * (1 + np.tanh(np.sqrt(2 / np.pi) * (x_norm + 0.044715 * x_norm**3)))


def kv_cache_update_bug(k_cache, v_cache, new_k, new_v, positions):
    """Update KV cache - potential broadcasting issue."""
    # k_cache: (batch, max_seq, heads, head_dim)
    # new_k: (batch, 1, heads, head_dim)
    # positions: (batch,) - current position for each batch
    # This is usually handled with scatter, but a naive approach:
    mean_k = np.mean(k_cache, axis=1)  # (batch, heads, head_dim)
    # If comparing or mixing with new_k:
    diff = new_k[:, 0, :, :] - mean_k  # This works, but if we tried:
    # diff = new_k - mean_k  # BUG: shapes don't match
    return diff


def logit_bias_bug(logits, bias_tokens, bias_value):
    """Apply logit bias to specific tokens - potentially BUGGY."""
    # logits: (batch, vocab_size)
    # bias_tokens: list of token ids
    # If we compute mean of biased positions:
    biased_mean = np.mean(logits[:, bias_tokens], axis=-1)  # (batch,)
    # Then try to add back:
    return logits + biased_mean  # BUG: biased_mean is (batch,), logits is (batch, vocab_size)


# =============================================================================
# SECTION 19: Direct Inline Patterns (These SHOULD be caught)
# =============================================================================

def inline_softmax_bug(x):
    """Inline softmax - BUGGY."""
    return np.exp(x - np.max(x, axis=-1)) / np.sum(np.exp(x - np.max(x, axis=-1)), axis=-1)

def inline_normalize_bug_v2(x):
    """Another inline normalization - BUGGY."""
    return (x - x.mean(axis=1)) / x.std(axis=1)

def inline_scale_bug(x):
    """Inline scaling - BUGGY."""
    return x / np.linalg.norm(x, axis=1)  # Note: np.linalg.norm not in our list


# =============================================================================
# Summary of detection capabilities:
#
# DETECTED (direct in binary operation):
# - x - np.mean(x, axis=1)
# - x / np.sum(x, axis=-1)
# - x * np.std(x, axis=1)
# - x - x.mean(axis=1)  (method style)
# - np.multiply(x, np.sum(x, axis=1))  (numpy function)
# - np.where(x > np.mean(x, axis=1), x, 0)  (np.where)
#
# NOT DETECTED (requires data flow analysis):
# - mean = np.mean(x, axis=1); x - mean
# - norms = np.sqrt(np.sum(x**2, axis=1)); x / norms
#
# SKIPPED (common correct pattern):
# - x - np.mean(x, axis=0)  (feature normalization)
# =============================================================================


if __name__ == "__main__":
    # Test that bugs actually fail and correct versions work
    np.random.seed(42)
    x = np.random.randn(4, 8)  # (batch, features)

    print("Testing broadcasting examples...")

    # Test normalize_samples
    try:
        result = normalize_samples_bug(x)
        print(f"normalize_samples_bug: unexpected success, shape={result.shape}")
    except ValueError as e:
        print(f"normalize_samples_bug: correctly failed - {e}")

    result = normalize_samples_correct_keepdims(x)
    print(f"normalize_samples_correct_keepdims: shape={result.shape}")

    # Test softmax
    try:
        result = softmax_bug_v1(x)
        print(f"softmax_bug_v1: unexpected success, shape={result.shape}")
    except ValueError as e:
        print(f"softmax_bug_v1: correctly failed - {e}")

    result = softmax_correct_keepdims(x)
    print(f"softmax_correct_keepdims: shape={result.shape}, sums={result.sum(axis=-1)}")

    print("\nDone!")
