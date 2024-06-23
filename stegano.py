import numpy as np
from PIL import Image
from pydub import AudioSegment

def compress_audio(audio_file):
    audio = AudioSegment.from_file(audio_file)
    compressed_audio = audio.set_sample_width(2)  # Set sample width to 2 bytes
    return compressed_audio, compressed_audio.frame_rate

def add_end_signal(audio_data, signal_length=100):
    return audio_data + (b'\xff' * signal_length)

def hide_audio_in_images(audio_file, image_files):
    try:
        compressed_audio_file, frame_rate = compress_audio(audio_file)
        audio_data = add_end_signal(compressed_audio_file.raw_data)

        frame_rate_bytes = frame_rate.to_bytes(4, 'big')
        audio_data_with_frame_rate = frame_rate_bytes + audio_data

        audio_len = len(audio_data_with_frame_rate)

        num_images = len(image_files)

        audio_index = 0
        modified_images = []

        for i in range(num_images):
            image = Image.open(image_files[i])
            image = image.convert("RGB")
            pixels = image.load()
            width, height = image.size

            pixels[0, 0] = (i, pixels[0, 0][1], pixels[0, 0][2])

            modified = False
            for y in range(height):
                for x in range(width):
                    if x == 0 and y == 0:
                        continue
                    if audio_index < audio_len:
                        r, g, b = pixels[x, y]
                        audio_byte = audio_data_with_frame_rate[audio_index]
                        r = (r & 0xF8) | ((audio_byte & 0xE0) >> 5)
                        g = (g & 0xF8) | ((audio_byte & 0x1C) >> 2)
                        b = (b & 0xF8) | (audio_byte & 0x03)
                        pixels[x, y] = (r, g, b)
                        audio_index += 1
                        modified = True

            if modified:
                modified_image_name = f"./outputs/encoded_image_{i+1}.png"  # Adjust path as needed
                modified_images.append(modified_image_name)
                image.save(modified_image_name)

        if audio_index < audio_len:
            raise ValueError("The provided images are not enough to hide the entire audio. You need more image(s).")

        print("Audio hidden successfully in the images.")
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

    return modified_images

def extract_audio_from_images(image_files, output_file, end_signal_length=100):
    try:
        indexed_images = []
        for image_file in image_files:
            image = Image.open(image_file)
            pixels = image.load()
            index = pixels[0, 0][0]
            indexed_images.append((index, image))

        indexed_images.sort(key=lambda x: x[0])

        audio_data_with_frame_rate = bytearray()
        found_end_signal = False

        for index, image in indexed_images:
            if found_end_signal:
                break

            image = image.convert("RGB")
            pixels = image.load()
            width, height = image.size

            for y in range(height):
                if found_end_signal:
                    break

                for x in range(width):
                    if x == 0 and y == 0:
                        continue
                    r, g, b = pixels[x, y]
                    audio_byte = ((r & 0x07) << 5) | ((g & 0x07) << 2) | (b & 0x03)
                    audio_data_with_frame_rate.append(audio_byte)

                    if len(audio_data_with_frame_rate) >= end_signal_length and bytes(audio_data_with_frame_rate[-end_signal_length:]) == (b'\xff' * end_signal_length):
                        audio_data_with_frame_rate = audio_data_with_frame_rate[:-end_signal_length]
                        found_end_signal = True
                        break

        if not audio_data_with_frame_rate:
            raise ValueError("No audio data found in the provided images.")

        frame_rate_bytes = audio_data_with_frame_rate[:4]
        frame_rate = int.from_bytes(frame_rate_bytes, 'big')
        audio_data = audio_data_with_frame_rate[4:]

        sample_width = 2
        channels = 1
        data_length_requirement = sample_width * channels
        excess_bytes = len(audio_data) % data_length_requirement

        if excess_bytes:
            audio_data = audio_data[:-excess_bytes]

        audio_segment = AudioSegment(
            data=bytes(audio_data),
            sample_width=sample_width,
            frame_rate=frame_rate,
            channels=channels
        )

        audio_segment.export(output_file, format="flac")
        print("Audio extracted successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")


def example_hide_audio(audio_path, image_paths):
    try:
        modified_images = hide_audio_in_images(audio_path, image_paths)
        return modified_images
    except Exception as e:
        print(f"An error occurred during the hiding process: {e}")
        return []

def example_extract_audio(image_paths, output_audio_path):
    try:
        extract_audio_from_images(image_paths, output_audio_path)
    except Exception as e:
        print(f"An error occurred during the extraction process: {e}")