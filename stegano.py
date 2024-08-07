import math
import struct
from PIL import Image
from pydub import AudioSegment

def calculate_required_pixels(audio_file_path, bits_per_pixel=8):
    audio = AudioSegment.from_file(audio_file_path)
    audio_data = audio.raw_data

    # Add end signal (100 bytes of 0xFF) and audio properties
    signal_length = 100
    audio_data_with_signal = audio_data + (b'\xff' * signal_length)
    
    audio_properties = struct.pack('>IHHI', audio.frame_rate, audio.sample_width, audio.channels, len(audio_data_with_signal))
    audio_data_with_properties = audio_properties + audio_data_with_signal

    # Calculate total bits needed
    total_bits = len(audio_data_with_properties) * 8

    # Calculate required pixels
    required_pixels = math.ceil(total_bits / bits_per_pixel)

    return required_pixels

def get_total_image_pixels(image_files):
    total_pixels = 0
    for image_file in image_files:
        with Image.open(image_file) as img:
            width, height = img.size
            total_pixels += width * height
    return total_pixels

def add_end_signal(audio_data, signal_length=100):
    return audio_data + (b'\xff' * signal_length)

def hide_audio_in_images(audio_file, image_files):
    try:
        required_pixels = calculate_required_pixels(audio_file)
        total_image_pixels = get_total_image_pixels(image_files)

        if total_image_pixels < required_pixels:
            raise ValueError(f"Not enough image capacity. Need {required_pixels} pixels, but only {total_image_pixels} available.")

        audio = AudioSegment.from_file(audio_file)
        audio_data = add_end_signal(audio.raw_data)
        
        audio_properties = struct.pack('>IHHI', audio.frame_rate, audio.sample_width, audio.channels, len(audio_data))
        audio_data_with_properties = audio_properties + audio_data

        audio_len = len(audio_data_with_properties)

        num_images = len(image_files)
        audio_index = 0
        modified_images = []

        for i in range(num_images):
            image = Image.open(image_files[i])
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            pixels = image.load()
            width, height = image.size

            # Store image index in the alpha channel of the first pixel
            r, g, b, a = pixels[0, 0]
            pixels[0, 0] = (r, g, b, i)

            modified = False
            for y in range(height):
                for x in range(width):
                    if x == 0 and y == 0:
                        continue
                    if audio_index < audio_len:
                        r, g, b, a = pixels[x, y]
                        audio_byte = audio_data_with_properties[audio_index]
                        r = (r & 0xF8) | ((audio_byte & 0xE0) >> 5)
                        g = (g & 0xF8) | ((audio_byte & 0x1C) >> 2)
                        b = (b & 0xF8) | (audio_byte & 0x03)
                        pixels[x, y] = (r, g, b, a)  
                        audio_index += 1
                        modified = True

            if modified:
                modified_image_name = f"./outputs/encoded_image_{i+1}.png"
                modified_images.append(modified_image_name)
                image.save(modified_image_name, 'PNG')

            if audio_index >= audio_len:
                break

        print("Audio hidden successfully in the images.")
        return modified_images
    except Exception as e:
        print(f"An error occurred: {e}")
        raise

def extract_audio_from_images(image_files, output_file, end_signal_length=100):
    try:
        indexed_images = []
        for image_file in image_files:
            image = Image.open(image_file)
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            pixels = image.load()
            index = pixels[0, 0][3]  # Get index from alpha channel
            indexed_images.append((index, image))

        indexed_images.sort(key=lambda x: x[0])

        audio_data_with_properties = bytearray()
        found_end_signal = False

        for index, image in indexed_images:
            if found_end_signal:
                break

            pixels = image.load()
            width, height = image.size

            for y in range(height):
                if found_end_signal:
                    break

                for x in range(width):
                    if x == 0 and y == 0:
                        continue
                    r, g, b, a = pixels[x, y]
                    audio_byte = ((r & 0x07) << 5) | ((g & 0x07) << 2) | (b & 0x03)
                    audio_data_with_properties.append(audio_byte)

                    if len(audio_data_with_properties) >= end_signal_length + 12:
                        if bytes(audio_data_with_properties[-end_signal_length:]) == (b'\xff' * end_signal_length):
                            audio_data_with_properties = audio_data_with_properties[:-end_signal_length]
                            found_end_signal = True
                            break

        if not audio_data_with_properties:
            raise ValueError("No audio data found in the provided images.")

        frame_rate, sample_width, channels, data_length = struct.unpack('>IHHI', audio_data_with_properties[:12])
        audio_data = audio_data_with_properties[12:12+data_length]

        # Check if the data length is a multiple of (sample_width * channels)
        frame_size = sample_width * channels
        if len(audio_data) % frame_size != 0:
            padding_length = frame_size - (len(audio_data) % frame_size)
            audio_data += b'\x00' * padding_length
            print(f"Warning: Audio data padded with {padding_length} zero bytes to match frame size.")

        audio_segment = AudioSegment(
            data=bytes(audio_data),
            sample_width=sample_width,
            frame_rate=frame_rate,
            channels=channels
        )

        output_file = output_file.rsplit('.', 1)[0] + '.mp3'
        audio_segment.export(output_file, format="mp3")
        print("Audio extracted successfully.")
        return output_file
    except Exception as e:
        print(f"An error occurred: {e}")
        raise