"""
Adaptive image restoration pipeline: assess quality first, then repair selectively.

Core principle: NEVER make a clear image worse. Only apply processing that
actually improves the specific image based on its quality metrics.

Key rules:
  1. Keep original resolution — upscaling dilutes detail, makes images look softer
  2. Only denoise if noise is genuinely high (gentle, edge-preserving)
  3. Always sharpen (adaptive strength), but never over-sharpen clear images
  4. If original is already sharp and clean → only color/contrast enhancement
  5. Quality guard: compare at SAME resolution, reject softer outputs
"""

import cv2
import numpy as np


def save_image(path: str, img: np.ndarray, quality: int = 98) -> None:
    """Save image with high quality, handling JPEG quality parameter properly."""
    ext = path.lower().split('.')[-1]
    if ext in ('jpg', 'jpeg'):
        # Use imencode to avoid OpenCV 4.x imwrite parameter warning
        _, buf = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        with open(path, 'wb') as f:
            f.write(buf.tobytes())
    elif ext == 'png':
        _, buf = cv2.imencode('.png', img, [int(cv2.IMWRITE_PNG_COMPRESSION), 3])
        with open(path, 'wb') as f:
            f.write(buf.tobytes())
    else:
        cv2.imwrite(path, img)


def restore_image(input_path: str, output_path: str) -> str:
    """
    Restore an old photo through an adaptive pipeline.
    Only applies processing that improves the specific image.
    Returns the output path.
    """
    img = cv2.imread(input_path)
    if img is None:
        raise ValueError(f"Cannot read image: {input_path}")

    # Ensure 3-channel BGR
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    was_grayscale = is_grayscale(img)

    # === Step 1: Assess image quality ===
    metrics = assess_quality(img)

    result = img.copy()

    # === Step 2: Denoise if noise is high ===
    # Even if image is "sharp", high noise will be amplified by later steps
    if metrics["is_noisy"]:
        result = gentle_denoise(result, strength=metrics["noise_level"])

    # === Step 3: Scratch repair (only if not too noisy) ===
    if not metrics["is_noisy"]:
        result = remove_scratches(result)

    # === Step 4: Sharpen — adapt strength to blur level ===
    # Always sharpen after denoise to recover detail
    if metrics["is_very_blurry"] and metrics["noise_level"] > 2:
        result = sharpen(result, method="strong")
    elif metrics["is_blurry"] and metrics["noise_level"] > 2:
        result = sharpen(result, method="moderate")
    elif metrics["is_noisy"]:
        # After denoise, apply moderate sharpen to recover edges
        result = sharpen(result, method="moderate")
    elif not metrics["already_sharp"]:
        # Light sharpening for average images
        result = sharpen(result, method="light")
    # If already_sharp, skip sharpening entirely

    # === Step 5: Contrast enhancement ===
    # Use lower CLAHE strength for noisy images to avoid amplifying residual noise
    clahe_clip = 1.5 if metrics["is_noisy"] else 2.0
    result = enhance_contrast(result, clip_limit=clahe_clip)

    # === Step 6: Colorization or color enhancement ===
    if was_grayscale:
        result = natural_colorize(result)
    else:
        result = auto_white_balance(result)

    # === Step 7: Subtle color grading ===
    result = color_grade(result)

    # === Step 8: Quality guard — ensure output is not softer than input ===
    result = quality_guard(img, result)

    # Save at original resolution, high quality
    save_image(output_path, result, quality=98)
    return output_path


def assess_quality(img: np.ndarray) -> dict:
    """
    Assess image quality metrics to guide adaptive processing.

    Uses Laplacian variance normalized by image size for blur detection,
    and local residual median absolute deviation for noise estimation.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()
    h, w = gray.shape

    # --- Blur detection via Laplacian variance ---
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    blur_score = laplacian.var()
    # Normalize by image size
    blur_score_norm = blur_score / (h * w) * 1000000

    # --- Noise estimation via local standard deviation ---
    local_mean = cv2.blur(gray.astype(np.float64), (3, 3))
    residual = gray.astype(np.float64) - local_mean
    noise_level = np.median(np.abs(residual - np.median(residual))) / 0.6745

    # --- Thresholds ---
    # blur_score_norm: < 15 very blurry, < 30 blurry, > 60 decent, > 100 sharp
    is_blurry = blur_score_norm < 30
    is_very_blurry = blur_score_norm < 15
    # If noise is very low AND image is not blurry, consider it already sharp
    # (low noise means it's likely a digital photo, not a damaged scan)
    already_sharp = blur_score_norm > 80 or (noise_level < 3 and blur_score_norm > 40)
    # noise_level: > 8 noisy, > 15 very noisy
    is_noisy = noise_level > 8

    return {
        "blur_score": blur_score,
        "blur_score_norm": blur_score_norm,
        "noise_level": noise_level,
        "is_blurry": is_blurry,
        "is_very_blurry": is_very_blurry,
        "already_sharp": already_sharp,
        "is_noisy": is_noisy,
    }


def gentle_denoise(img: np.ndarray, strength: float = 10) -> np.ndarray:
    """
    Edge-preserving denoise. Strength scales parameters aggressively.
    For very noisy images (strength > 15), uses stronger NLMeans.
    """
    if strength > 15:
        # Very noisy: strong bilateral + NLMeans
        sigma = min(strength * 2.5, 50)
        denoised = cv2.bilateralFilter(img, d=7, sigmaColor=sigma, sigmaSpace=sigma)
        denoised = cv2.fastNlMeansDenoisingColored(denoised, None, h=7, hColor=7,
                                                    templateWindowSize=7, searchWindowSize=21)
    elif strength > 8:
        # Moderately noisy: medium bilateral + light NLMeans
        sigma = min(strength * 2, 30)
        denoised = cv2.bilateralFilter(img, d=5, sigmaColor=sigma, sigmaSpace=sigma)
        denoised = cv2.fastNlMeansDenoisingColored(denoised, None, h=4, hColor=4,
                                                    templateWindowSize=7, searchWindowSize=21)
    else:
        # Light noise: gentle bilateral only
        sigma = strength * 2
        denoised = cv2.bilateralFilter(img, d=5, sigmaColor=sigma, sigmaSpace=sigma)
    return denoised


def sharpen(img: np.ndarray, method: str = "moderate") -> np.ndarray:
    """
    Adaptive sharpening using unsharp mask with method-based parameters.

    Methods:
    - "light": subtle enhancement for already-decent images
    - "moderate": standard sharpening for slightly blurry images
    - "strong": aggressive sharpening for very blurry images
    """
    if method == "light":
        sigma = 1.0
        weight = 1.3
    elif method == "moderate":
        sigma = 1.5
        weight = 1.6
    else:  # strong
        sigma = 2.0
        weight = 2.0

    # Unsharp mask
    blurred = cv2.GaussianBlur(img, (0, 0), sigma)
    sharpened = cv2.addWeighted(img, weight, blurred, 1 - weight, 0)

    # For strong mode, add Laplacian kernel edge enhancement on luminance
    if method == "strong":
        kernel = np.array([
            [0, -1, 0],
            [-1, 5, -1],
            [0, -1, 0]
        ], dtype=np.float32)
        lab = cv2.cvtColor(sharpened, cv2.COLOR_BGR2LAB)
        l = lab[:, :, 0].astype(np.float32)
        l_sharp = cv2.filter2D(l, -1, kernel)
        lab[:, :, 0] = np.clip(l_sharp, 0, 255).astype(np.uint8)
        sharpened = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    return sharpened


def enhance_contrast(img: np.ndarray, clip_limit: float = 2.0) -> np.ndarray:
    """Mild CLAHE contrast enhancement in LAB color space."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
    l = clahe.apply(l)
    enhanced = cv2.merge([l, a, b])
    return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)


def quality_guard(original: np.ndarray, processed: np.ndarray) -> np.ndarray:
    """
    Final quality check at the SAME resolution as original.

    If processing made the image softer, blend back original sharpness.
    Compares Laplacian variance (sharpness) before and after.
    """
    # Both should be same size (we don't upscale anymore)
    # But handle size mismatch just in case
    if original.shape[:2] != processed.shape[:2]:
        processed_resized = cv2.resize(processed, (original.shape[1], original.shape[0]),
                                       interpolation=cv2.INTER_LANCZOS4)
    else:
        processed_resized = processed

    # Measure sharpness at original resolution
    orig_gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY) if len(original.shape) == 3 else original
    proc_gray = cv2.cvtColor(processed_resized, cv2.COLOR_BGR2GRAY) if len(processed_resized.shape) == 3 else processed_resized

    orig_sharp = cv2.Laplacian(orig_gray, cv2.CV_64F).var()
    proc_sharp = cv2.Laplacian(proc_gray, cv2.CV_64F).var()

    # If processed is softer than original, blend back
    if proc_sharp < orig_sharp * 0.85:
        # Blend ratio: how much original to mix back
        ratio = min(0.9, (orig_sharp - proc_sharp) / max(orig_sharp, 1))
        result = cv2.addWeighted(processed_resized, 1 - ratio, original, ratio, 0)
        return result

    return processed_resized


def is_grayscale(img: np.ndarray) -> bool:
    """Check if image is essentially grayscale."""
    if len(img.shape) < 3:
        return True
    b, g, r = cv2.split(img)
    diff_rg = np.mean(np.abs(r.astype(float) - g.astype(float)))
    diff_rb = np.mean(np.abs(r.astype(float) - b.astype(float)))
    return diff_rg < 10 and diff_rb < 10


def remove_scratches(img: np.ndarray) -> np.ndarray:
    """
    Detect and inpaint thin scratch lines.
    Uses morphological top-hat to find thin bright/dark lines.
    Conservative: skips if detected "scratches" cover too much area
    (likely noise, not real scratches).
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    kernel_len = max(15, img.shape[1] // 40)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_len, 1))
    tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
    # Higher threshold to avoid detecting noise as scratches
    _, scratch_mask = cv2.threshold(tophat, 25, 255, cv2.THRESH_BINARY)

    scratch_ratio = np.sum(scratch_mask > 0) / scratch_mask.size
    # Only inpaint if scratches are detected AND cover a small area (< 2%)
    # Large area means it's likely noise, not scratches
    if 0.001 < scratch_ratio < 0.02:
        scratch_mask = cv2.dilate(scratch_mask, np.ones((3, 3), np.uint8), iterations=1)
        img = cv2.inpaint(img, scratch_mask, 3, cv2.INPAINT_TELEA)

    return img


def natural_colorize(img: np.ndarray) -> np.ndarray:
    """
    Apply natural-looking pseudo-colorization for grayscale photos.
    Preserves luminance detail by only modifying hue/saturation.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0

    hue = np.zeros_like(gray)
    sat = np.zeros_like(gray)
    val = gray.copy()

    hue = np.where(gray < 0.3,
                   90 - gray * 100,
                   np.where(gray < 0.7,
                           40 - (gray - 0.3) * 60,
                           25 - (gray - 0.7) * 30))

    sat = np.where(gray < 0.15,
                   gray * 1.5,
                   np.where(gray > 0.85,
                           (1.0 - gray) * 2.0,
                           0.35 + 0.25 * np.sin(gray * np.pi)))

    sat = np.clip(sat, 0, 1)
    hue = np.clip(hue, 0, 180)

    hsv = np.stack([hue, sat * 255, val * 255], axis=-1).astype(np.uint8)
    colored = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    result = cv2.addWeighted(img, 0.25, colored, 0.75, 0)
    return result


def auto_white_balance(img: np.ndarray) -> np.ndarray:
    """Apply gentle automatic white balance using gray-world assumption.
    Uses mild correction to avoid color shifts on already-balanced photos."""
    result = img.copy().astype(np.float32)
    avg_b = np.mean(result[:, :, 0])
    avg_g = np.mean(result[:, :, 1])
    avg_r = np.mean(result[:, :, 2])
    avg_gray = (avg_b + avg_g + avg_r) / 3

    # Mild correction: only apply 30% of the full gray-world adjustment
    # This prevents drastic color shifts on photos with dominant colors
    factor_b = avg_gray / max(avg_b, 1)
    factor_g = avg_gray / max(avg_g, 1)
    factor_r = avg_gray / max(avg_r, 1)

    # Blend: 70% original + 30% corrected
    result[:, :, 0] = result[:, :, 0] * 0.7 + result[:, :, 0] * factor_b * 0.3
    result[:, :, 1] = result[:, :, 1] * 0.7 + result[:, :, 1] * factor_g * 0.3
    result[:, :, 2] = result[:, :, 2] * 0.7 + result[:, :, 2] * factor_r * 0.3

    return np.clip(result, 0, 255).astype(np.uint8)


def color_grade(img: np.ndarray) -> np.ndarray:
    """Apply very subtle warm color grading for nostalgic feel."""
    result = img.copy().astype(np.float32)
    # Very subtle warm tone
    result[:, :, 2] *= 1.01
    result[:, :, 0] *= 0.99
    # Very slight gamma for richer shadows
    result = np.power(result / 255.0, 0.98) * 255.0
    return np.clip(result, 0, 255).astype(np.uint8)
