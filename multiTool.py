import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import os
import io
import subprocess
from moviepy.editor import VideoFileClip
from PIL import Image, ImageTk
import threading
import base64
import cv2
import time
import numpy as np
from pdf2image import convert_from_path
import pytesseract
from PyPDF2 import PdfWriter, PdfReader
from pydub import AudioSegment  # New import for audio processing
import imageio

# ---------------------- Video Processing Functions ---------------------- #

def compress_video(input_path, output_path):
    target_size = 16 * 1024 * 1024  # 16 MB
    video = VideoFileClip(input_path)
    duration = video.duration
    original_size = os.path.getsize(input_path)
    target_bitrate = int((target_size * 8) / duration)

    compression_complete = threading.Event()  # Create an event to signal completion

    def run_ffmpeg():
        ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"  # Specify the full path to ffmpeg
        process = subprocess.Popen(
            [ffmpeg_path, '-i', input_path, '-c:v', 'libx264', '-preset', 'medium',
             '-b:v', f'{target_bitrate}', '-c:a', 'aac', '-b:a', '128k', '-y', output_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Capture output and error
        stdout, stderr = process.communicate()  # Wait for the process to complete and capture output
        print(stdout.decode())  # Print standard output
        print(stderr.decode())  # Print standard error

        compression_complete.set()  # Signal that compression is complete

    threading.Thread(target=run_ffmpeg).start()

    return original_size, compression_complete  # Return the original size and the event

def convert_to_mp4(input_path, output_path):
    try:
        # Print the input and output paths for debugging
        print(f"Input Path: {input_path}")
        print(f"Output Path: {output_path}")

        # Check if the input file exists
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # Load the video file
        video = VideoFileClip(input_path)
        
        # Check if the VideoFileClip object is properly created
        if video is None:
            raise ValueError("VideoFileClip returned None. The file may not have been loaded correctly.")

        # Convert and save the video to MP4 format
        video.write_videofile(output_path, codec="libx264")
    
    except Exception as e:
        print(f"Error during video processing: {e}")
        raise  # Re-raise the exception after printing the error

def convert_to_gif(input_path, output_path):
    video = VideoFileClip(input_path)
    fps = video.fps
    width = int(video.w)
    height = int(video.h)
    images = []
    temp_filenames = []  # List to keep track of temporary filenames

    for i in range(int(video.duration * fps)):
        temp_filename = f"frame_{i}.png"
        video.save_frame(temp_filename, t=i/fps)
        img = Image.open(temp_filename).resize((width, height))
        images.append(img)
        temp_filenames.append(temp_filename)  # Store the filename

    # Save images as GIF
    images[0].save(output_path, format='GIF', append_images=images[1:],
                   save_all=True, duration=int(1000 / fps), loop=0)

    # Clean up temporary images
    for temp_filename in temp_filenames:
        os.remove(temp_filename)  # Remove the temporary file

def update_size_labels(original_size, compressed_size, original_label, compressed_label):
    original_label['text'] = f"Originalgröße: {original_size / 1024 / 1024:.2f} MB"
    compressed_label['text'] = f"Komprimierte Größe: {compressed_size / 1024 / 1024:.2f} MB"

def video_processing_thread(action, input_path, output_path, original_label, compressed_label, done_label, progress_label, spinner_label):
    try:
        if action == "compress":
            original_size, compression_complete = compress_video(input_path, output_path)
            compression_complete.wait()  # Wait for the compression to finish
            compressed_size = os.path.getsize(output_path)  # Now get the compressed size
            update_size_labels(original_size, compressed_size, original_label, compressed_label)  # Update size labels
        elif action == "convert_mp4":
            convert_to_mp4(input_path, output_path)
        elif action == "convert_gif":
            convert_to_gif(input_path, output_path)
    except Exception as e:
        print(f"Error during processing: {e}")
        messagebox.showerror("Fehler", f"Fehler bei der Videoverarbeitung: {e}")
    finally:
        done_label['text'] = "Fertig"  # Show "Done" in German
        done_label.grid()  # Show the "Done" label
        progress_label.grid()  # Show the "Progressing..." label
        spinner_label.grid()  # Show the spinner
        root.update_idletasks()

# ---------------------- PDF Processing Functions ---------------------- #

def improve_pdf_for_ai_reading(input_path, output_path):
    # Ensure the output path ends with .pdf
    if not output_path.lower().endswith('.pdf'):
        output_path = os.path.splitext(output_path)[0] + '.pdf'
    # Define the output path prefix for the images (before adding -1, -2, etc.)
    output_path_prefix = os.path.splitext(output_path)[0]

    # Convert PDF to PPM images using pdftoppm
    try:
        subprocess.run([r"C:\Program Files\poppler-24.08.0\Library\bin\pdftoppm.exe", input_path, output_path_prefix, "-png"], check=True)

        # Collect all output images (assuming they are named as output_path_prefix-1.png, etc.)
        images = []
        i = 1
        while True:
            img_file = f"{output_path_prefix}-{i}.png"
            if os.path.exists(img_file):
                img = Image.open(img_file)
                images.append(img)
                i += 1
            else:
                break

        writer = PdfWriter()

        for img in images:
            # Convert image to grayscale
            gray = cv2.cvtColor(np.array(img), cv2.COLOR_BGR2GRAY)

            # Apply adaptive thresholding
            binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY, 11, 2)

            # Denoise image
            denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)

            # Enhance contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(denoised)

            # Convert back to PIL format
            enhanced_pil = Image.fromarray(enhanced)

            # Perform OCR to extract text
            text = pytesseract.image_to_string(enhanced_pil)

            # Create a new PDF page with the improved image
            pdf = pytesseract.image_to_pdf_or_hocr(enhanced_pil, extension='pdf')
            pdf_bytes = io.BytesIO(pdf)

            # Add page to the writer
            reader = PdfReader(pdf_bytes)
            writer.add_page(reader.pages[0])

        # Save the final enhanced PDF
        with open(output_path, "wb") as f:
            writer.write(f)

        print(f"Verbesserte PDF für KI-Lesbarkeit gespeichert als: {output_path}")

    except subprocess.CalledProcessError as e:
        print(f"Fehler beim Aufruf von pdftoppm: {e}")
        messagebox.showerror("Fehler", f"Fehler beim Aufruf von pdftoppm: {e}")

def pdf_processing_thread(input_path, output_path, done_label, progress_label, spinner_label):
    try:
        improve_pdf_for_ai_reading(input_path, output_path)
    except Exception as e:
        print(f"Fehler bei der PDF-Verarbeitung: {e}")
        messagebox.showerror("Fehler", f"Fehler bei der PDF-Verarbeitung: {e}")
    finally:
        done_label['text'] = "Fertig"
        done_label.grid()
        progress_label.grid()
        spinner_label.grid()
        root.update_idletasks()

# ---------------------- Audio Processing Functions ---------------------- #
# Define the available audio formats
audio_format = {
    'mp3': 'mp3',
    'wav': 'wav',
    'flac': 'flac',
    # Add other formats as needed
}

def convert_audio(input_path, output_path, format):
    # Ensure the output_path has the correct file extension for the selected format
    output_path = os.path.splitext(output_path)[0] + f".{format.lower()}"
    
    audio = AudioSegment.from_file(input_path)  # Load audio file
    audio.export(output_path, format=format)    # Export to the specified format

def audio_processing_thread(input_path, output_path, audio_format, done_label, progress_label, spinner_label):
    try:
        convert_audio(input_path, output_path, audio_format)  # Call the conversion function
        # Update the output path with the forced format's extension
        output_path = os.path.splitext(output_path)[0] + f".{audio_format.lower()}"
        done_label['text'] = f"Audio processed and saved to: {output_path}"
    except Exception as e:
        done_label['text'] = f"Error: {str(e)}"  # Handle any errors during conversion
    finally:
        progress_label['text'] = ""
        spinner_label.grid_remove()  # Stop spinner

# ---------------------- GUI Functions ---------------------- #

def browse_input_file(entry_widget):
    filetypes = [
        ("Video files", "*.mp4 *.avi *.mov *.mkv"),
        ("Audio files", "*.mp3 *.wav *.aac *.flac"),
        ("PDF files", "*.pdf"),
        ("All files", "*.*")
    ]
    
    filepath = filedialog.askopenfilename(filetypes=filetypes)
    entry_widget.delete(0, tk.END)
    entry_widget.insert(0, filepath)


def browse_output_file(entry_widget, action):
    if action in ["compress", "convert_mp4", "convert_gif"]:
        # For video actions, allow saving video files
        filetypes = [("Video files", "*.mp4 *.avi *.mov *.mkv"), ("All files", "*.*")]
    elif action == "pdf":
        filetypes = [("PDF files", "*.pdf")]
    elif action == "audio":
        # For audio actions, allow saving audio files
        filetypes = [("Audio files", "*.mp3 *.wav *.aac *.flac"), ("All files", "*.*")]
    else:
        filetypes = [("All files", "*.*")]  # Default case

    filepath = filedialog.asksaveasfilename(defaultextension="", filetypes=filetypes)
    entry_widget.delete(0, tk.END)
    entry_widget.insert(0, filepath)


def start_video_processing(action, original_label, compressed_label, done_label, progress_label, spinner_label):
    # Clear size labels when a new action is started
    original_label['text'] = ""
    compressed_label['text'] = ""

    input_path = video_input_entry.get()
    output_path = video_output_entry.get()
    
    if not input_path or not output_path:
        messagebox.showerror("Fehler", "Bitte wählen Sie Eingabe- und Ausgabedateien aus.")
        return
    
    # Change the output extension to match the input file's extension
    if action == "compress":
        output_extension = os.path.splitext(input_path)[1]
        output_path = os.path.splitext(output_path)[0] + output_extension
    elif action == "convert_mp4":
        output_path = os.path.splitext(output_path)[0] + ".mp4"
    elif action == "convert_gif":
        output_path = os.path.splitext(output_path)[0] + ".gif"
    
    # Show "Processing" message
    progress_label['text'] = "Verarbeite..."
    progress_label.grid()  # Show the "Progressing..." label
    done_label['text'] = ""
    done_label.grid_remove()  # Hide the "Done" label initially

    # Start the spinner animation
    start_spinner(spinner_label, progress_label)

    # Start the video processing in a separate thread
    threading.Thread(target=video_processing_thread, args=(action, input_path, output_path, original_label, compressed_label, done_label, progress_label, spinner_label)).start()

def start_pdf_processing(done_label, progress_label, spinner_label):
    # Clear previous status
    done_label['text'] = ""
    progress_label['text'] = "Verarbeite PDF..."
    progress_label.grid()
    done_label.grid_remove()
    spinner_label.grid()

    input_path = pdf_input_entry.get()
    output_path = pdf_output_entry.get()
    
    if not input_path or not output_path:
        messagebox.showerror("Fehler", "Bitte wählen Sie Eingabe- und Ausgabedateien für PDF aus.")
        return

    # Start the spinner animation
    start_spinner(spinner_label, progress_label)

    # Start the PDF processing in a separate thread
    threading.Thread(target=pdf_processing_thread, args=(input_path, output_path, done_label, progress_label, spinner_label)).start()

def start_audio_processing(audio_format, audio_done_label, audio_progress_label, audio_spinner_label):
    print(f"Audio format: {audio_format}")
    audio_done_label.config(text="Processing complete")
    audio_progress_label.config(text="In Progress")
    audio_spinner_label.config(text="Spinner active")
    
    input_path = audio_input_entry.get()
    output_path = audio_output_entry.get()
    
    if not input_path or not output_path:
        messagebox.showerror("Fehler", "Bitte wählen Sie Eingabe- und Ausgabedateien für Audio aus.")
        return
    
    # Start the spinner animation
    start_spinner(audio_spinner_label, audio_progress_label)

    # Start the audio processing in a separate thread
    threading.Thread(target=audio_processing_thread, args=(input_path, output_path, audio_format, audio_done_label, audio_progress_label, audio_spinner_label)).start()

def start_spinner(spinner_label, progress_label):
    spinner_label.grid()  # Show the spinner
    animate_spinner(spinner_label, progress_label)

def animate_spinner(spinner_label, progress_label):
    current_text = spinner_label['text']
    if current_text == "⠋":
        spinner_label['text'] = "⠙"
    elif current_text == "⠙":
        spinner_label['text'] = "⠚"
    elif current_text == "⠚":
        spinner_label['text'] = "⠉"
    else:
        spinner_label['text'] = "⠋"
    
    if "Verarbeite" in progress_label['text']:
        root.after(100, lambda: animate_spinner(spinner_label, progress_label))  # Repeat the animation every 100 ms

# ---------------------- GUI Setup ---------------------- #

root = tk.Tk()
root.title("Multimedia Werkzeug")
root.geometry("800x600")  # Set a default size for better appearance

# Create a Notebook
notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill='both')

# Create frames for each tab
video_frame = ttk.Frame(notebook)
pdf_frame = ttk.Frame(notebook)
audio_frame = ttk.Frame(notebook)  # New frame for audio tool

# Add frames to notebook as tabs
notebook.add(video_frame, text="Video Tool")
notebook.add(pdf_frame, text="PDF Tool")
notebook.add(audio_frame, text="Audio Tool")  # New tab for audio

# ---------------------- Common UI Elements ---------------------- #

# Add ciSio Logo (optional: place in each tab or above the notebook)
base64_logo = """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"""
logo_image = Image.open(io.BytesIO(base64.b64decode(base64_logo.encode())))
resized_logo = logo_image.resize((150, 150), Image.LANCZOS)  # Adjusted size for better GUI fit
logo_tk_image = ImageTk.PhotoImage(resized_logo)

# You can place the logo in each frame or above the notebook
# Here, we'll place it above the notebook
logo_label = tk.Label(root, image=logo_tk_image)
logo_label.pack(pady=10)

# ---------------------- Video Processing UI ---------------------- #

# Video Tool Widgets
video_input_label = tk.Label(video_frame, text="Eingabevideo:")
video_input_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
video_input_entry = tk.Entry(video_frame, width=50)
video_input_entry.grid(row=0, column=1, padx=10, pady=10, sticky="w")
video_input_browse_button = tk.Button(video_frame, text="Durchsuchen...", command=lambda: browse_input_file(video_input_entry))
video_input_browse_button.grid(row=0, column=2, padx=10, pady=10)

video_output_label = tk.Label(video_frame, text="Ausgabedatei:")
video_output_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
video_output_entry = tk.Entry(video_frame, width=50)
video_output_entry.grid(row=1, column=1, padx=10, pady=10, sticky="w")
video_output_browse_button = tk.Button(video_frame, text="Speichern unter...", command=lambda: browse_output_file(video_output_entry, "compress"))
video_output_browse_button.grid(row=1, column=2, padx=10, pady=10)

# Buttons for video actions
compress_button = tk.Button(video_frame, text="Video Komprimieren", command=lambda: start_video_processing("compress", video_original_size_label, video_compressed_size_label, video_done_label, video_progress_label, video_spinner_label))
compress_button.grid(row=2, column=1, padx=10, pady=10, sticky="w")

convert_mp4_button = tk.Button(video_frame, text="In MP4 Umwandeln", command=lambda: start_video_processing("convert_mp4", video_original_size_label, video_compressed_size_label, video_done_label, video_progress_label, video_spinner_label))
convert_mp4_button.grid(row=3, column=1, padx=10, pady=10, sticky="w")

convert_gif_button = tk.Button(video_frame, text="In GIF Umwandeln", command=lambda: start_video_processing("convert_gif", video_original_size_label, video_compressed_size_label, video_done_label, video_progress_label, video_spinner_label))
convert_gif_button.grid(row=4, column=1, padx=10, pady=10, sticky="w")

# Progress label for video
video_progress_label = tk.Label(video_frame, text="")
video_progress_label.grid(row=5, column=0, columnspan=3, padx=10, pady=5)
video_progress_label.grid_remove()  # Hide the label initially

# Spinner label for video
video_spinner_label = tk.Label(video_frame, text="", font=("Arial", 16))
video_spinner_label.grid(row=5, column=3, padx=10, pady=5)
video_spinner_label.grid_remove()  # Hide the spinner initially

# Done label for video
video_done_label = tk.Label(video_frame, text="", fg="green")
video_done_label.grid(row=6, column=0, columnspan=3, padx=10, pady=5)
video_done_label.grid_remove()  # Hide the "Done" label initially

# Labels for original and compressed sizes
video_original_size_label = tk.Label(video_frame, text="")
video_original_size_label.grid(row=7, column=0, columnspan=3, padx=10, pady=5)

video_compressed_size_label = tk.Label(video_frame, text="")
video_compressed_size_label.grid(row=8, column=0, columnspan=3, padx=10, pady=5)

# ---------------------- PDF Processing UI ---------------------- #

# PDF Tool Widgets
pdf_label = tk.Label(pdf_frame, text="PDF-Verarbeitung für KI-Lesbarkeit", font=("Helvetica", 14, "bold"))
pdf_label.grid(row=0, column=0, columnspan=5, padx=10, pady=10)

pdf_input_label = tk.Label(pdf_frame, text="Eingabe-PDF:")
pdf_input_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
pdf_input_entry = tk.Entry(pdf_frame, width=50)
pdf_input_entry.grid(row=1, column=1, padx=10, pady=10, sticky="w")
pdf_input_browse_button = tk.Button(pdf_frame, text="Durchsuchen...", command=lambda: browse_input_file(pdf_input_entry))
pdf_input_browse_button.grid(row=1, column=2, padx=10, pady=10)

pdf_output_label = tk.Label(pdf_frame, text="Ausgabedatei:")
pdf_output_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")
pdf_output_entry = tk.Entry(pdf_frame, width=50)
pdf_output_entry.grid(row=2, column=1, padx=10, pady=10, sticky="w")
pdf_output_browse_button = tk.Button(pdf_frame, text="Speichern unter...", command=lambda: browse_output_file(pdf_output_entry, "pdf"))
pdf_output_browse_button.grid(row=2, column=2, padx=10, pady=10)

# Button to start PDF processing
pdf_process_button = tk.Button(pdf_frame, text="PDF Verbessern", command=lambda: start_pdf_processing(pdf_done_label, pdf_progress_label, pdf_spinner_label))
pdf_process_button.grid(row=3, column=1, padx=10, pady=10, sticky="w")

# Progress label for PDF
pdf_progress_label = tk.Label(pdf_frame, text="")
pdf_progress_label.grid(row=4, column=0, columnspan=3, padx=10, pady=5)
pdf_progress_label.grid_remove()  # Hide the label initially

# Spinner label for PDF
pdf_spinner_label = tk.Label(pdf_frame, text="", font=("Arial", 16))
pdf_spinner_label.grid(row=4, column=3, padx=10, pady=5)
pdf_spinner_label.grid_remove()  # Hide the spinner initially

# Done label for PDF
pdf_done_label = tk.Label(pdf_frame, text="", fg="green")
pdf_done_label.grid(row=5, column=0, columnspan=3, padx=10, pady=5)
pdf_done_label.grid_remove()  # Hide the "Done" label initially

# ---------------------- Audio Tool UI Elements ---------------------- #
# Audio input
audio_input_label = tk.Label(audio_frame, text="Audio Eingabedatei:")
audio_input_label.grid(row=0, column=0, padx=10, pady=10)
audio_input_entry = tk.Entry(audio_frame, width=50)
audio_input_entry.grid(row=0, column=1, padx=10, pady=10)
audio_input_button = tk.Button(audio_frame, text="Durchsuchen", command=lambda: browse_input_file(audio_input_entry))
audio_input_button.grid(row=0, column=2, padx=10, pady=10)

# Audio output
audio_output_label = tk.Label(audio_frame, text="Audio Ausgabedatei:")
audio_output_label.grid(row=1, column=0, padx=10, pady=10)
audio_output_entry = tk.Entry(audio_frame, width=50)
audio_output_entry.grid(row=1, column=1, padx=10, pady=10)
audio_output_browse_button = tk.Button(audio_frame, text="Speichern unter...", command=lambda: browse_output_file(audio_output_entry, "audio"))
audio_output_browse_button.grid(row=1, column=2, padx=10, pady=10)

# Format selection
audio_format_label = tk.Label(audio_frame, text="Wählen Sie ein Format:")
audio_format_label.grid(row=2, column=0, padx=10, pady=10)
audio_format_var = tk.StringVar(value="mp3")  # Default format
audio_format_options = ttk.Combobox(audio_frame, textvariable=audio_format_var, values=["mp3", "wav", "ogg"])
audio_format_options.grid(row=2, column=1, padx=10, pady=10)

# Process buttons and labels
audio_done_label = tk.Label(audio_frame, text="", fg="green")
audio_progress_label = tk.Label(audio_frame, text="")
audio_spinner_label = tk.Label(audio_frame, text="⠋")

audio_process_button = tk.Button(audio_frame, text="Audio verarbeiten", command=lambda: start_audio_processing(audio_format_var.get(), audio_done_label, audio_progress_label, audio_spinner_label))
audio_process_button.grid(row=3, column=1, padx=10, pady=10)

# Add the labels for done and progress
audio_done_label.grid(row=4, column=1, padx=10, pady=10)
audio_progress_label.grid(row=5, column=1, padx=10, pady=10)
audio_spinner_label.grid(row=6, column=1, padx=10, pady=10)

# ---------------------- Start the Tkinter main loop ---------------------- #

root.mainloop()
