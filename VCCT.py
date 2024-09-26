import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
import os
import io
import subprocess
from moviepy.editor import VideoFileClip
from PIL import Image, ImageTk
import threading
import base64

def compress_video(input_path, output_path):
    target_size = 16 * 1024 * 1024 
    video = VideoFileClip(input_path) 
    duration = video.duration 
    original_size = os.path.getsize(input_path) 
    target_bitrate = int((target_size * 8) / duration) 

    compression_complete = threading.Event()  # Create an event to signal completion

    def run_ffmpeg():
        ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"  # Specify the full path to ffmpeg
        process = subprocess.Popen(
            [ffmpeg_path, '-i', input_path, '-c:v', 'libx264', '-preset', 'medium', '-b:v', f'{target_bitrate}', '-c:a', 'aac', '-b:a', '128k', '-y', output_path],
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

def video_processing_thread(action, input_path, output_path):
    try:
        if action == "compress":
            original_size, compression_complete = compress_video(input_path, output_path)
            compression_complete.wait()  # Wait for the compression to finish
            compressed_size = os.path.getsize(output_path)  # Now get the compressed size
            update_size_labels(original_size, compressed_size)  # Update size labels
        elif action == "convert_mp4":
            convert_to_mp4(input_path, output_path)
        elif action == "convert_gif":
            convert_to_gif(input_path, output_path)
    except Exception as e:
        print(f"Error during processing: {e}")
    finally:
        done_label['text'] = "Done"  # Show "Done" when progress is complete
        done_label.grid()  # Show the "Done" label
        progress_label.grid_remove()  # Hide the "Progressing..." label
        spinner_label.grid_remove()  # Hide the spinner
        root.update_idletasks()

def update_size_labels(original_size, compressed_size):
    original_size_label['text'] = f"Originalgröße: {original_size / 1024 / 1024:.2f} MB"
    compressed_size_label['text'] = f"Komprimierte Größe: {compressed_size / 1024 / 1024:.2f} MB"

def convert_to_mp4(input_path, output_path):
    video = VideoFileClip(input_path) 
    video.write_videofile(output_path, codec="libx264") 

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
                   save_all=True, duration=1/fps, loop=0)

    # Clean up temporary images
    for temp_filename in temp_filenames:
        os.remove(temp_filename)  # Remove the temporary file

def browse_input_file():
    filepath = filedialog.askopenfilename(filetypes=[("Video files", "*.*")])  # Allow all video files
    input_entry.delete(0, tk.END)
    input_entry.insert(0, filepath)

def browse_output_file():
    filepath = filedialog.asksaveasfilename(filetypes=[("Video files", "*.*")])
    output_entry.delete(0, tk.END)
    output_entry.insert(0, filepath)

def start_video_processing(action):
    # Clear size labels when a new action is started
    original_size_label['text'] = ""
    compressed_size_label['text'] = ""

    input_path = input_entry.get()
    output_path = output_entry.get()
    
    # Change the output extension to match the input file's extension
    if action == "compress":
        output_extension = os.path.splitext(input_path)[1]
        output_path = os.path.splitext(output_path)[0] + output_extension
    elif action == "convert_mp4":
        output_path = os.path.splitext(output_path)[0] + ".mp4"
    elif action == "convert_gif":
        output_path = os.path.splitext(output_path)[0] + ".gif"

    # Show "Progressing" message
    progress_label['text'] = "Progressing..."
    progress_label.grid()  # Show the "Progressing..." label
    done_label.grid_remove()  # Hide the "Done" label initially

    # Start the spinner animation
    start_spinner()

    # Start the video processing in a separate thread
    threading.Thread(target=video_processing_thread, args=(action, input_path, output_path)).start()

def start_spinner():
    spinner_label.grid()  # Show the spinner
    animate_spinner()  # Start the animation

def animate_spinner():
    current_text = spinner_label['text']
    if current_text == "⠋":
        spinner_label['text'] = "⠙"
    elif current_text == "⠙":
        spinner_label['text'] = "⠚"
    elif current_text == "⠚":
        spinner_label['text'] = "⠉"
    else:
        spinner_label['text'] = "⠋"
    
    if progress_label['text'] == "Progressing...":
        root.after(100, animate_spinner)  # Repeat the animation every 100 ms

root = tk.Tk()
root.title("Video Werkzeug")

#Add ciSio Logo
base64_logo = """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"""
logo = tk.PhotoImage(data=base64_logo)
logo_label = tk.Label(root, image=logo)
logo_label.grid(row = 2, column = 2, rowspan = 3, columnspan = 2, padx = 10, pady = 10, sticky = "w")
# Resize the logo
logo_image = Image.open(io.BytesIO(base64.b64decode(base64_logo.encode())))
resized_logo = logo_image.resize((1500, 1500))  # Set the desired width and height
logo_tk_image = ImageTk.PhotoImage(resized_logo)

input_label = tk.Label(root, text="Eingabevideo:")
input_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
input_entry = tk.Entry(root, width=50)
input_entry.grid(row=0, column=1, padx=10, pady=10, sticky="w")
input_browse_button = tk.Button(root, text="Durchsuchen...", command=browse_input_file)
input_browse_button.grid(row=0, column=2, padx=10, pady=10)
output_label = tk.Label(root, text="Ausgabedatei:")
output_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
output_entry = tk.Entry(root, width=50)
output_entry.grid(row=1, column=1, padx=10, pady=10, sticky="w")
output_browse_button = tk.Button(root, text="Speichern unter...", command=browse_output_file)
output_browse_button.grid(row=1, column=2, padx=10, pady=10)

# Buttons for the actions
compress_button = tk.Button(root, text="Video Komprimieren", command=lambda: start_video_processing("compress"))
compress_button.grid(row=2, column=1, padx=10, pady=10, sticky="w")

convert_mp4_button = tk.Button(root, text="In MP4 Umwandeln", command=lambda: start_video_processing("convert_mp4"))
convert_mp4_button.grid(row=3, column=1, padx=10, pady=10, sticky="w")

convert_gif_button = tk.Button(root, text="In GIF Umwandeln", command=lambda: start_video_processing("convert_gif"))
convert_gif_button.grid(row=4, column=1, padx=10, pady=10, sticky="w")

# Progress label
progress_label = tk.Label(root, text="")
progress_label.grid(row=5, column=0, columnspan=3, padx=10, pady=5)
progress_label.grid_remove()  # Hide the label initially

# Spinner label
spinner_label = tk.Label(root, text="", font=("Arial", 16))
spinner_label.grid(row=5, column=3, padx=10, pady=5)
spinner_label.grid_remove()  # Hide the spinner initially

# Done label
done_label = tk.Label(root, text="", fg="green")
done_label.grid(row=6, column=0, columnspan=3, padx=10, pady=5)
done_label.grid_remove()  # Hide the "Done" label initially

# Labels for original and compressed sizes
original_size_label = tk.Label(root, text="")
original_size_label.grid(row=7, column=0, columnspan=3, padx=10, pady=5)

compressed_size_label = tk.Label(root, text="")
compressed_size_label.grid(row=8, column=0, columnspan=3, padx=10, pady=5)

# Start the Tkinter main loop
root.mainloop()
