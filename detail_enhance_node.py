import torch
from comfy.samplers import KSAMPLER

# ----------------------------
# Mathematical Core
# ----------------------------

def _get_centered_mask(length, start_percent, end_percent, device):
    """
    Creates a smooth "Table-top" mask for the Region of Interest (ROI).
    Returns values 0.0 to 1.0.
    """
    # Create normalized timeline
    t = torch.linspace(0.0, 1.0, length, device=device)
    
    # Define soft edges (fade length)
    # 5% of total length as transition zone
    fade = 0.05
    
    # Smoothstep-like logic for start
    s = torch.clamp((t - start_percent) / fade, 0.0, 1.0)
    s = s * s * (3.0 - 2.0 * s) # Cubic easing
    
    # Smoothstep-like logic for end
    e = torch.clamp((end_percent - t) / fade, 0.0, 1.0)
    e = e * e * (3.0 - 2.0 * e) # Cubic easing
    
    return s * e

def _warp_time_density(sigmas, factor, mask):
    """
    Relativity Warp: Slows down time where mask is high.
    factor 5.0 = Time passes 5x slower in the masked zone (more steps spent there).
    """
    if abs(factor - 1.0) < 1e-3:
        return sigmas
        
    n = sigmas.shape[0]
    device = sigmas.device
    
    # 1. Calculate weights (Velocity of time)
    # Normal = 1.0. 
    # Detail Zone = 1.0 + (Factor - 1.0) * mask
    # We want "Density", so higher factor = higher weight = more steps allocated.
    weights = 1.0 + (mask * (factor - 1.0))
    
    # 2. Integrate to get New Time Positions (CDF)
    cdf = torch.cumsum(weights, dim=0)
    cdf = cdf / cdf[-1] # Normalize 0..1
    
    # 3. Invert CDF: We have the "New Time" (0..1 linear steps), 
    # we need to find which "Old Time" indices they correspond to.
    real_time_grid = torch.linspace(0.0, 1.0, n, device=device)
    
    # Searchsorted finds the indices
    indices = torch.searchsorted(cdf, real_time_grid, right=False)
    
    # 4. Linear Interpolation for smoothness
    # We need to know exactly where 'real_time_grid' falls between cdf[i] and cdf[i+1]
    indices = torch.clamp(indices, 0, n - 2)
    
    y0 = cdf[indices]
    y1 = cdf[indices + 1]
    
    # How far are we between y0 and y1?
    # Avoid div/0
    denom = (y1 - y0)
    denom[denom < 1e-6] = 1e-6 
    
    frac = (real_time_grid - y0) / denom
    
    # Map to float indices of original array
    float_indices = indices.float() + frac
    
    # 5. Resample Sigmas
    # Gather floor/ceil
    idx_floor = torch.floor(float_indices).long()
    idx_ceil = torch.clamp(idx_floor + 1, max=n - 1)
    w = float_indices - idx_floor.float()
    
    warped_sigmas = sigmas[idx_floor] * (1.0 - w) + sigmas[idx_ceil] * w
    
    # Hard lock endpoints
    warped_sigmas[0] = sigmas[0]
    warped_sigmas[-1] = sigmas[-1]
    
    return warped_sigmas

def _boost_sigma_amplitude(sigmas, boost_amount, mask):
    """
    Amplitude Modulation: Artificially inflates sigma values in the ROI.
    This forces the sampler to "denoise harder", creating texture.
    """
    if abs(boost_amount) < 1e-3:
        return sigmas
        
    # Logic: sigma_new = sigma * (1 + mask * boost)
    # We limit boost to avoid exploding the image.
    # boost_amount 1.0 => +20% sigma value (conservative but strong)
    # boost_amount 5.0 => +100% sigma value (extreme)
    
    # We use a gentle log scaling for the boost to keep it controllable
    # effective_boost = boost_amount * 0.1 ? No, let's use raw math but careful.
    
    # Let's trust the user. If they say 0.5, we add 50% value.
    # Actually 50% is huge. Let's scale the input so 1.0 feels "Strong" but not "Broken".
    # Scale: 1.0 input = 0.15 actual boost (15% lift).
    scaler = 0.15 
    
    inflation = 1.0 + (mask * (boost_amount * scaler))
    
    return sigmas * inflation

def _enforce_monotonicity(sigmas):
    """
    Heals the curve. boosting sigmas can make sigma[i] > sigma[i-1], 
    which breaks Euler/DPM. This forces the curve to go down only.
    """
    # We sweep backwards. The 'current' step must be >= 'next' step.
    # If we boosted the middle, we might have created a "bump".
    # We flatten the bump.
    fixed = sigmas.clone()
    for i in range(len(fixed) - 2, -1, -1):
        if fixed[i] < fixed[i+1]:
            fixed[i] = fixed[i+1] # Clamp to next value
    return fixed

# ----------------------------
# Main Processor
# ----------------------------

def process_ultimate_sigmas(sigmas: torch.Tensor, 
                          factor: float, 
                          boost: float,
                          start_p: float, 
                          end_p: float) -> torch.Tensor:
    
    if factor == 1.0 and boost == 0.0:
        return sigmas
        
    device = sigmas.device
    original_dtype = sigmas.dtype
    work_sigmas = sigmas.float()
    n = work_sigmas.shape[0]
    
    # 1. Create Zone Mask
    mask = _get_centered_mask(n, start_p, end_p, device)
    
    # 2. Phase 1: Time Dilation (The "Slow Down")
    # This rearranges steps to spend more time in the zone.
    work_sigmas = _warp_time_density(work_sigmas, factor, mask)
    
    # 3. Phase 2: Texture Boosting (The "Crispness")
    # This inflates values to force texture generation.
    # We recalculate mask for the new warped distribution? 
    # Ideally yes, but the zone is roughly same place. Let's re-calc mask on new timeline?
    # Actually, calculating mask on linear grid (0..1) applies correctly to the resampled sigmas
    # because the sigmas are now distributed along that linear grid.
    work_sigmas = _boost_sigma_amplitude(work_sigmas, boost, mask)
    
    # 4. Phase 3: Safety
    work_sigmas = _enforce_monotonicity(work_sigmas)
    
    return work_sigmas.to(dtype=original_dtype)


def enhance_sampler_wrapper(model, x, sigmas, *args, 
                             de_source_sampler=None, 
                             de_factor=1.0, 
                             de_boost=0.0,
                             de_start=0.0, 
                             de_end=1.0, 
                             **kwargs):
    if de_source_sampler is None:
        return x

    new_sigmas = process_ultimate_sigmas(sigmas, de_factor, de_boost, de_start, de_end)

    return de_source_sampler.sampler_function(
        model, x, new_sigmas, *args,
        **kwargs,
        **getattr(de_source_sampler, "extra_options", {})
    )


# ----------------------------
# Node Definitions
# ----------------------------

class UltimateDetailSamplerNode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "sampler": ("SAMPLER",),
                "enhance_factor": ("FLOAT", {
                    "default": 2.0,
                    "min": 1.0,
                    "max": 10.0,
                    "step": 0.1,
                    "tooltip": "Time Dilation. Higher = Slows down sampling in the zone. Adds structural detail."
                }),
                "texture_boost": ("FLOAT", {
                    "default": 0.5,
                    "min": 0.0,
                    "max": 5.0,
                    "step": 0.1,
                    "tooltip": "Sigma Inflation. Higher = Forcing high-frequency noise. Adds sharp texture/grit. Warning: >1.0 is very strong."
                }),
                "start_percent": ("FLOAT", {
                    "default": 0.10, "min": 0.0, "max": 1.0, "step": 0.05
                }),
                "end_percent": ("FLOAT", {
                    "default": 0.80, "min": 0.0, "max": 1.0, "step": 0.05
                }),
            }
        }

    RETURN_TYPES = ("SAMPLER",)
    RETURN_NAMES = ("sampler",)
    FUNCTION = "wrap"
    CATEGORY = "sampling/custom_sampling"

    def wrap(self, sampler, enhance_factor, texture_boost, start_percent, end_percent):
        extra_options = {
            "de_source_sampler": sampler,
            "de_factor": float(enhance_factor),
            "de_boost": float(texture_boost),
            "de_start": float(start_percent),
            "de_end": float(end_percent),
        }
        return (KSAMPLER(enhance_sampler_wrapper, extra_options=extra_options),)


class UltimateDetailSigmasNode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "sigmas": ("SIGMAS",),
                "enhance_factor": ("FLOAT", {
                    "default": 2.0,
                    "min": 1.0,
                    "max": 10.0,
                    "step": 0.1,
                    "tooltip": "Time Dilation. Higher = Slows down sampling in the zone. Adds structural detail."
                }),
                "texture_boost": ("FLOAT", {
                    "default": 0.5,
                    "min": 0.0,
                    "max": 5.0,
                    "step": 0.1,
                    "tooltip": "Sigma Inflation. Higher = Forcing high-frequency noise. Adds sharp texture/grit. Warning: >1.0 is very strong."
                }),
                "start_percent": ("FLOAT", {
                    "default": 0.10, "min": 0.0, "max": 1.0, "step": 0.05
                }),
                "end_percent": ("FLOAT", {
                    "default": 0.80, "min": 0.0, "max": 1.0, "step": 0.05
                }),
            }
        }

    RETURN_TYPES = ("SIGMAS",)
    RETURN_NAMES = ("sigmas",)
    FUNCTION = "modify"
    CATEGORY = "sampling/custom_sampling/sigmas"

    def modify(self, sigmas, enhance_factor, texture_boost, start_percent, end_percent):
        out = process_ultimate_sigmas(sigmas, float(enhance_factor), float(texture_boost), float(start_percent), float(end_percent))
        return (out,)

# Registration
NODE_CLASS_MAPPINGS = {
    "UltimateDetailSamplerNode": UltimateDetailSamplerNode,
    "UltimateDetailSigmasNode": UltimateDetailSigmasNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "UltimateDetailSamplerNode": "Detail Enhancer (Ultimate)",
    "UltimateDetailSigmasNode": "Detail Enhancer (Sigmas)",
}