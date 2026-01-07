from tkinter import *
import serial
import threading
import time
import collections
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Serial configuration - update port if needed
SERIAL_PORT = 'COM8'
BAUD_RATE = 115200

ser = serial.Serial()
ser.port = SERIAL_PORT
ser.baudrate = BAUD_RATE
ser.timeout = 1

try:
    ser.open()
    print(f"Serial port {SERIAL_PORT} opened successfully")
except Exception as e:
    print(f"Failed to open serial port {SERIAL_PORT}: {e}")
    ser = None

# --- ECG data buffers and synchronization ---
BUFFER_SIZE = 1000
DISPLAY_SECONDS = 5  # show last 5 seconds on x-axis
ecg_buffer = collections.deque(maxlen=BUFFER_SIZE)
ecg_timestamps = collections.deque(maxlen=BUFFER_SIZE)
ecg_lock = threading.Lock()
peaks = collections.deque()
last_peak_time = 0.0

# Start with empty buffers; we will plot only real samples

# Tkinter setup
root = Tk()
root.title("ECG Monitor")

# Read serial in background thread and append numeric ECG samples
def read_raspberry():
    while True:
        try:
            if ser and ser.is_open:
                line = ser.readline().decode('utf-8').strip()
                if not line:
                    time.sleep(0.01)
                    continue
                text = line
                try:
                    sample = float(text)
                    timestamp = time.time()
                    with ecg_lock:
                        ecg_buffer.append(sample)
                        ecg_timestamps.append(timestamp)
                except ValueError:
                    # Non-numeric line received; ignore or print for debugging
                    # print(f"Non-ECG line: {line}")
                    pass
            else:
                time.sleep(0.01)
        except Exception as e:
            print(f"Serial read error: {e}")
            time.sleep(0.01)

thread = threading.Thread(target=read_raspberry, daemon=True)
thread.start()

# --- Plot setup ---
fig, ax = plt.subplots(figsize=(8,3))
line, = ax.plot([], [])
ax.set_ylim(0, 3.3)
ax.set_xlabel('Seconds')
ax.set_title('ECG')
ax.set_xlim(0, DISPLAY_SECONDS)

canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().grid(row=0, column=0, padx=10, pady=5)

# Heart rate display
bpm_var = StringVar()
bpm_var.set('-- BPM')
bpm_label = Label(root, textvariable=bpm_var, font=("Arial", 28), fg='red')
bpm_label.grid(row=0, column=1, padx=10, pady=5, sticky='n')

# Update loop: redraw plot and compute BPM

def update_plot():
    global last_peak_time
    with ecg_lock:
        data = np.array(ecg_buffer)
        times = np.array(ecg_timestamps)

    if len(times) < 2:
        root.after(100, update_plot)
        return

    # Estimate sampling rate from timestamps (use median dt)
    dts = np.diff(times)
    median_dt = np.median(dts) if len(dts) > 0 else 0.01
    fs = 1.0 / median_dt if median_dt > 0 else 100.0

    # Get only the recent samples within the last DISPLAY_SECONDS
    cutoff = times[-1] - DISPLAY_SECONDS
    idxs = np.where(times >= cutoff)[0]
    
    if len(idxs) > 0:
        # Get recent times and data
        times_recent = times[idxs]
        data_recent = data[idxs]
        # Map times to 0..DISPLAY_SECONDS based on *true* sampling rate, not actual time span
        # This prevents discontinuities when the buffer window changes
        # Use median_dt to compute position: position = (t - t_earliest) / median_dt * DISPLAY_SECONDS / (total expected samples)
        # Better approach: position based on elapsed time from first sample, at the estimated sampling rate
        if len(times_recent) == 1:
            # Only one sample: place it at the right edge
            x_plot = np.array([DISPLAY_SECONDS])
            y_plot = data_recent
        else:
            # Map based on number of samples and their intervals using median_dt
            n_samples = len(times_recent)
            expected_duration = (n_samples - 1) * median_dt
            # Scale x-axis so that the sample duration fills the display (or a fraction of it)
            x_plot = np.arange(n_samples) / n_samples * DISPLAY_SECONDS
            y_plot = data_recent
        line.set_data(x_plot, y_plot)
    else:
        # No recent samples; clear the plot
        line.set_data([], [])
    
    ax.set_xlim(0, DISPLAY_SECONDS)
    canvas.draw()

    # Simple peak detection (adaptive threshold)
    if len(data) > 5:
        thr = np.mean(data) + 0.5 * np.std(data)
        i = -2
        if data[i] > thr and data[i] > data[i-1] and data[i] > data[i+1]:
            peak_time = times[-2]
            if peak_time - last_peak_time > 0.3:  # 300 ms refractory
                peaks.append(peak_time)
                last_peak_time = peak_time

    # Keep peaks within a rolling window (15s)
    now = time.time()
    while peaks and (now - peaks[0]) > 15:
        peaks.popleft()

    # Compute BPM
    if len(peaks) >= 2:
        duration = peaks[-1] - peaks[0]
        if duration > 0:
            bpm = (len(peaks)-1) / duration * 60.0
            bpm_var.set(f"{int(round(bpm))} BPM")
        else:
            bpm_var.set('-- BPM')
    else:
        bpm_var.set('-- BPM')

    root.after(100, update_plot)

# Start updates and GUI
root.after(100, update_plot)
root.mainloop()
  

    