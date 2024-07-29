import math
import struct
from pydub import AudioSegment

def calculate_theoretical_min_image_size(audio_file_path, bits_per_pixel=8, image_dimensions=None):
    audio = AudioSegment.from_file(audio_file_path)
    audio_data = audio.raw_data

    # Add audio properties and end signal
    signal_length = 100
    audio_data_with_signal = audio_data + (b'\xff' * signal_length)
    
    audio_properties = struct.pack('>IHHI', audio.frame_rate, audio.sample_width, audio.channels, len(audio_data_with_signal))
    audio_data_with_properties = audio_properties + audio_data_with_signal

    # Calculate total bits needed
    total_bits = len(audio_data_with_properties) * 8

    # Calculate required pixels
    required_pixels = math.ceil(total_bits / bits_per_pixel)

    if image_dimensions:
        return calculate_multi_image_requirements(required_pixels, image_dimensions)
    else:
        return required_pixels

def calculate_multi_image_requirements(required_pixels, image_dimensions):
    width, height = image_dimensions
    pixels_per_image = width * height - 1  
    usable_pixels_per_image = (pixels_per_image * 8) // 8  # (8 bits per pixel)

    num_images = math.ceil(required_pixels / usable_pixels_per_image)
    total_pixels = num_images * width * height

    return total_pixels, num_images

def suggest_image_dimensions(required_pixels):
    aspect_ratios = [(16, 9), (4, 3), (3, 2), (1, 1)]
    suggestions = []

    for ratio in aspect_ratios:
        width = math.ceil(math.sqrt(required_pixels * ratio[0] / ratio[1]))
        height = math.ceil(width * ratio[1] / ratio[0])
        while width * height < required_pixels:
            width += 1
            height = math.ceil(width * ratio[1] / ratio[0])
        suggestions.append((width, height))

    return suggestions

# usage
audio_file_path = 'path to your audio'
required_pixels = calculate_theoretical_min_image_size(audio_file_path)
suggested_dimensions = suggest_image_dimensions(required_pixels)

print(f"Audio file: {audio_file_path}")
print(f"Estimated minimum pixels required: {required_pixels}")
print(f"Estimated minimum megapixels: {required_pixels / 1_000_000:.2f} MP")
print("\nSuggested minimum image dimensions:")
for width, height in suggested_dimensions:
    print(f"  {width}x{height} ({width*height} pixels, {(width*height) / 1_000_000:.2f} MP)")
    total_pixels, num_images = calculate_multi_image_requirements(required_pixels, (width, height))
    print(f"    - Number of images required: {num_images}")
    print(f"    - Total pixels across all images: {total_pixels}")
    print(f"    - Total megapixels: {total_pixels / 1_000_000:.2f} MP")

print("\nNote: The actual required size may vary based on the specific encoding method and image content.")