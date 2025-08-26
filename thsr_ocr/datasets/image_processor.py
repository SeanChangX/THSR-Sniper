#!/usr/bin/env python3
"""
THSR Captcha Image Processor
- Resize images to 160x50 with white padding
- Multiple processing modes: gentle, balanced, aggressive
- Gentle line removal that preserves text
- Enhanced contrast for better text visibility
"""

import os
import sys
import argparse
from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
import numpy as np

def gentle_line_removal(image, line_threshold=0.7):
    """
    Gently remove thin lines while preserving text
    """
    # Convert to grayscale
    gray = image.convert('L')
    img_array = np.array(gray)
    
    # Create a copy for processing
    result = img_array.copy()
    
    # Detect and remove very thin horizontal lines (only 1-2 pixels wide)
    for i in range(img_array.shape[0]):
        for j in range(img_array.shape[1] - 2):
            # Check if this is a very thin horizontal line
            if (img_array[i, j] < 128 and 
                img_array[i, j+1] < 128 and 
                img_array[i, j+2] < 128):
                # Check if surrounding pixels are mostly white (indicating a thin line)
                surrounding = []
                for di in [-1, 0, 1]:
                    for dj in range(-2, 5):
                        ni, nj = i + di, j + dj
                        if (0 <= ni < img_array.shape[0] and 
                            0 <= nj < img_array.shape[1]):
                            surrounding.append(img_array[ni, nj])
                
                # If surrounding area is mostly white, this might be a thin line
                if np.mean(surrounding) > 200:
                    # Gently reduce the line intensity instead of removing completely
                    result[i, j:j+3] = np.minimum(result[i, j:j+3] + 50, 255)
    
    # Convert back to image
    return Image.fromarray(result).convert('RGB')

def aggressive_line_removal(image, min_line_width=3):
    """
    Aggressive line removal (may affect text)
    """
    # Convert to grayscale
    gray = image.convert('L')
    img_array = np.array(gray)
    
    # Threshold to create binary image
    binary = img_array < 128
    
    # Create horizontal and vertical kernels
    h_kernel = np.ones((1, min_line_width), np.uint8)
    v_kernel = np.ones((min_line_width, 1), np.uint8)
    
    # Apply morphological operations
    # Remove horizontal lines
    h_removed = binary.copy()
    for i in range(binary.shape[0]):
        for j in range(binary.shape[1] - min_line_width + 1):
            if np.all(binary[i, j:j+min_line_width]):
                h_removed[i, j:j+min_line_width] = False
    
    # Remove vertical lines
    v_removed = h_removed.copy()
    for i in range(binary.shape[0] - min_line_width + 1):
        for j in range(binary.shape[1]):
            if np.all(h_removed[i:i+min_line_width, j]):
                v_removed[i:i+min_line_width, j] = False
    
    # Convert back to image
    result = Image.fromarray((~v_removed * 255).astype(np.uint8))
    return result.convert('RGB')

def process_image(image_path, target_size=(160, 50), mode='balanced', preview=False):
    """
    Process image with selected mode
    Modes: gentle, balanced, aggressive
    """
    # Open image
    if isinstance(image_path, str):
        img = Image.open(image_path)
    else:
        img = image_path
    
    # Convert to RGB if needed
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Get original dimensions
    w, h = img.size
    
    # Calculate scaling factor to fit within target size
    scale_w = target_size[0] / w
    scale_h = target_size[1] / h
    scale = min(scale_w, scale_h)
    
    # Calculate new dimensions
    new_w = int(w * scale)
    new_h = int(h * scale)
    
    # Resize image
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Create white canvas
    canvas = Image.new('RGB', target_size, (255, 255, 255))
    
    # Calculate position to center the image
    x_offset = (target_size[0] - new_w) // 2
    y_offset = (target_size[1] - new_h) // 2
    
    # Place resized image on canvas
    canvas.paste(resized, (x_offset, y_offset))
    
    if preview:
        print(f"Original size: {w}x{h}")
        print(f"Scaled size: {new_w}x{new_h}")
        print(f"Target size: {target_size[0]}x{target_size[1]}")
        print(f"Padding: {x_offset}px left/right, {y_offset}px top/bottom")
        print(f"Processing mode: {mode}")
    
    # Step 1: Noise reduction
    print("Applying noise reduction...")
    if mode == 'gentle':
        # Very light median filter
        denoised = canvas.filter(ImageFilter.MedianFilter(size=3))
    elif mode == 'balanced':
        # Light median filter
        denoised = canvas.filter(ImageFilter.MedianFilter(size=3))
    else:  # aggressive
        # Stronger median filter
        denoised = canvas.filter(ImageFilter.MedianFilter(size=5))
    
    # Step 2: Line removal based on mode
    print("Applying line removal...")
    if mode == 'gentle':
        # No line removal, just basic processing
        no_lines = denoised
    elif mode == 'balanced':
        # Gentle line removal
        no_lines = gentle_line_removal(denoised)
    else:  # aggressive
        # Aggressive line removal
        no_lines = aggressive_line_removal(denoised)
    
    # Step 3: Contrast enhancement based on mode
    print("Enhancing contrast...")
    if mode == 'gentle':
        contrast_factor = 1.3
    elif mode == 'balanced':
        contrast_factor = 1.5
    else:  # aggressive
        contrast_factor = 2.0
    
    contrast_enhancer = ImageEnhance.Contrast(no_lines)
    enhanced = contrast_enhancer.enhance(contrast_factor)
    
    # Step 4: Brightness adjustment
    brightness_enhancer = ImageEnhance.Brightness(enhanced)
    enhanced = brightness_enhancer.enhance(1.1)
    
    # Step 5: Sharpening based on mode
    print("Applying sharpening...")
    if mode == 'gentle':
        sharpened = enhanced.filter(ImageFilter.UnsharpMask(radius=1, percent=110, threshold=8))
    elif mode == 'balanced':
        sharpened = enhanced.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=5))
    else:  # aggressive
        sharpened = enhanced.filter(ImageFilter.UnsharpMask(radius=1, percent=200, threshold=2))
    
    return sharpened

def save_image(image, output_path):
    """Save image to file"""
    image.save(output_path, 'JPEG', quality=95)

def preview_image(image_path, target_size=(160, 50), mode='balanced'):
    """Preview processing of a single image"""
    print(f"Preview: {image_path} (Mode: {mode})")
    print("=" * 50)
    
    try:
        # Process image
        processed = process_image(image_path, target_size, mode, preview=True)
        
        # Save preview
        preview_path = f"preview_{mode}_processed.jpg"
        save_image(processed, preview_path)
        print(f"\nPreview saved as: {preview_path}")
        
        # Show image info
        print(f"Processed image size: {processed.size}")
        print(f"Image mode: {processed.mode}")
        
        return True
        
    except Exception as e:
        print(f"Error processing image: {e}")
        import traceback
        traceback.print_exc()
        return False

def batch_process(input_dir, output_dir, target_size=(160, 50), mode='balanced', dry_run=False):
    """Batch process all images"""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    if not input_path.exists():
        print(f"Input directory does not exist: {input_path}")
        return
    
    # Create output directory if it doesn't exist
    if not dry_run:
        output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all jpg files
    image_files = list(input_path.glob("*.jpg"))
    
    if not image_files:
        print(f"No .jpg files found in {input_path}")
        return
    
    print(f"Found {len(image_files)} images to process with {mode} mode")
    
    if dry_run:
        print("DRY RUN MODE - No files will be modified")
    
    processed_count = 0
    error_count = 0
    
    for i, img_file in enumerate(image_files):
        try:
            if dry_run:
                print(f"[DRY-RUN] Would process: {img_file.name}")
                continue
            
            print(f"Processing {i+1}/{len(image_files)}: {img_file.name}")
            
            # Process image
            processed = process_image(str(img_file), target_size, mode)
            
            # Save to output directory
            output_file = output_path / img_file.name
            save_image(processed, str(output_file))
            
            print(f"✓ Completed: {img_file.name}")
            processed_count += 1
            
        except Exception as e:
            print(f"✗ Error processing {img_file.name}: {e}")
            error_count += 1
    
    print(f"\nBatch processing complete!")
    print(f"Processed: {processed_count}")
    print(f"Errors: {error_count}")

def main():
    parser = argparse.ArgumentParser(description="THSR Captcha Image Processor")
    parser.add_argument("--input", "-i", default=".", help="Input directory (default: current)")
    parser.add_argument("--output", "-o", default="processed", help="Output directory (default: processed)")
    parser.add_argument("--preview", "-p", action="store_true", help="Preview first image only")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Show what would be done without doing it")
    parser.add_argument("--width", "-W", type=int, default=160, help="Target width (default: 160)")
    parser.add_argument("--height", "-H", type=int, default=50, help="Target height (default: 50)")
    parser.add_argument("--mode", "-m", choices=['gentle', 'balanced', 'aggressive'], 
                       default='balanced', help="Processing mode (default: balanced)")
    
    args = parser.parse_args()
    
    target_size = (args.width, args.height)
    
    if args.preview:
        # Preview mode - process first image only
        input_path = Path(args.input)
        image_files = list(input_path.glob("*.jpg"))
        
        if not image_files:
            print(f"No .jpg files found in {input_path}")
            return
        
        preview_image(str(image_files[0]), target_size, args.mode)
        
    else:
        # Batch processing mode
        batch_process(args.input, args.output, target_size, args.mode, args.dry_run)

if __name__ == "__main__":
    main()
