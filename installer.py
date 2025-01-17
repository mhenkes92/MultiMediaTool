import os
import subprocess
import shutil
import sys

def install_packages():
    packages = ['imageio', 'meson', 'python-poppler', 'python-ffmpeg', 'scipy', 'tqdm', 'tesseract', 'decorator', 'imageio_ffmpeg', 'numpy', 'prolog', 'python-dotenv', 'moviepy', 'Pillow', 'opencv-python', 'pytesseract', 'PyPDF2', 'audioop-lts', 'PyMuPDF', 'pdf2image', 'pydub', 'requests']
    
    for package in packages:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        except subprocess.CalledProcessError as e:
            print(f"Failed to install {package}. Error: {e}")

def copy_and_set_environment(folder_name, target_root):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_dir = os.path.join(script_dir, folder_name)
    target_dir = os.path.join(target_root, folder_name)

    if os.path.exists(source_dir):
        print(f"Copying {folder_name} to {target_root}...")
        # Create the target directory if it doesn't exist
        os.makedirs(target_dir, exist_ok=True)

        # Copy all contents from the source to the target directory
        for item in os.listdir(source_dir):
            s = os.path.join(source_dir, item)
            d = os.path.join(target_dir, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)

        print(f"{folder_name} copied successfully.")
         # Set the environment variable for the specific folder
        if folder_name == 'ffmpeg':
            set_environment_variable(r"C:\ffmpeg\bin")  # Set path for FFmpeg
        elif folder_name == 'poppler':
            set_environment_variable(r"C:\poppler\Library\bin")  # Set path for Poppler
        elif folder_name == 'tesseract':
            set_environment_variable(r"C:\tesseract")# Set path for tesseract
    else:
        print(f"{folder_name} directory not found. Please ensure the '{folder_name}' folder is in the same directory as this script.")

def set_environment_variable(new_path):
    # Get the current PATH
    current_path = os.environ.get('PATH', '')

    # Check if the new path is already in the PATH
    if new_path not in current_path:
        # Update the PATH
        new_path_value = current_path + ";" + new_path

        # Set the new PATH in the environment variables
        os.environ['PATH'] = new_path_value

        # Use setx to make it persistent
        subprocess.call(['setx', 'PATH', new_path_value])
        print(f"Added {new_path} to the system PATH.")
    else:
        print(f"{new_path} is already in the system PATH.")

def main():
    target_root = 'C:\\'

    print("Installing required Python packages...")
    install_packages()

    print("Copying and setting up FFmpeg...")
    copy_and_set_environment('ffmpeg', target_root)

    print("Copying and setting up Poppler...")
    copy_and_set_environment('poppler', target_root)
    
    print("Copying and setting up Tesseract...")
    copy_and_set_environment('tesseract', target_root)

    print("Installation complete.")

if __name__ == "__main__":
    main()
