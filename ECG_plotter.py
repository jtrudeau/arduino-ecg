import numpy as np
import pandas as pd
import serial
import time
from scipy.signal import butter, lfilter, find_peaks
from scipy import ndimage
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from threading import Thread

# Variables to change
filepath_csv = r'table1'
filepath_img = r'img1'
port = 'COM3'
save_data = True
is_test = False

# Variables
fake_voltage = 0
kill = False
start_time = time.time()
if not is_test:
    ser = serial.Serial(port, 9600, timeout=None)
data_df = pd.DataFrame([[0,0]], columns=["Time", "Voltage"])
lowcut = 1
highcut = 30

# Plot information
plt.style.use('dark_background')
fig, ax = plt.subplots()
delay = 100
y_min = -1
y_max = 2
x_min = 0
x_max = 10
line, = ax.plot(data_df["Time"], data_df["Voltage"], color='#39FF14', linewidth=1)
plt.ylim([y_min, y_max])
plt.xlim([x_min, x_max])
g1 = ax.grid(visible=True, which='major', color='#666666', linestyle='-', linewidth=0.8)
g2 = ax.grid(visible=True, which='minor', color='#666666', linestyle='-', linewidth=0.4)
ax.set_xticklabels([])
ax.set_yticklabels([])
ax.minorticks_on()
plt.tight_layout()

def get_heart_data(): 
    # Reads the data from the serial port, converts it to a voltage and stores it in a temporary DataFrame
    value = ser.readline() # Get the new data from the serial port
    time_elapsed = time.time()-start_time
    temp_df = pd.DataFrame(columns=["Time", "Voltage"])
    try:
        decoded_value = int(value.decode(encoding='utf-8'))
        voltage = decoded_value*3.3/1023
        temp_df = pd.DataFrame([[time_elapsed, voltage]], columns=["Time", "Voltage"])
    except ValueError:
        pass
    return temp_df

def get_fake_heart_data(): 
    #Incrementally increases the data and stores it in a temporary dataframe. Used to test the code without using the hardware.
    global fake_voltage
    time.sleep(0.05)
    time_elapsed = time.time()-start_time
    fake_voltage+=0.01
    df=pd.DataFrame([[time_elapsed, fake_voltage]], columns=["Time", "Voltage"])
    return df

def butter_bandpass_filter(data, lowcut, fs, order=5):
    b, a = butter(order, lowcut, btype='highpass', fs=fs)
    y = lfilter(b, a, data)
    return y

def moving_average(data, N):
    y=ndimage.uniform_filter1d(data, size=N)
    return y

def make_graph(x,y, peaks): 
    # Makes the final graph to be saved.
    fig1, ax1 = plt.subplots()
    ax1.plot(x, y,'-', color='#39FF14')
    g1 = ax1.grid(visible=True, which='major', color='#666666', linestyle='-', linewidth=0.8)
    g2 = ax1.grid(visible=True, which='minor', color='#666666', linestyle='-', linewidth=0.4)
    plt.xlabel('Time (s)')
    plt.ylabel('Voltage')
    plt.tight_layout()

    # Add R peak detection and heart rate 
    ax1.scatter(peaks[0], peaks[1], color='r', s=20)
    bpm_text = f"Heart Rate: {int(calc_heartrate(get_peaks(data_df['Filtered Voltage'])[0]))} bpm"
    ax1.annotate(bpm_text, xy=(1,0), xycoords='axes fraction', fontsize=10, horizontalalignment='right', verticalalignment='bottom')
    
    if save_data:
        plt.savefig(filepath_img)
    plt.show()

def animate(i):
    # Animates the first graph to show the data in real time. 
    global data_df
    data_length = len(data_df.index)
    line.set_data(data_df["Time"][max(data_length-delay,0):-1],data_df["Voltage"][max(data_length-delay,0):-1]) # Update the plot
    if data_length > delay: 
        ax.set_xlim(left=data_df.iloc[data_length-delay]["Time"],right=data_df.iloc[-1]["Time"]) # Move the x-axis
    return line,

def get_peaks(data):
    # Detect R peaks to calculate heart rate
    peaks = find_peaks(data, height=(0.1,2), distance=1) #Play around with height and distance settings
    peaks_to_keep = [i for i in peaks[0] if i>300]
    peak_pos = [data_df["Time"][peaks_to_keep]]
    peak_height = [data[peaks_to_keep]]
    return (peak_pos, peak_height)

def calc_heartrate(peak_pos):
    # Calulates the heart rate
    delay = np.diff(peak_pos)
    average_delay = np.mean(delay)
    print(f"Average delay: {round(average_delay, 3)} seconds")
    heartrate = 60/average_delay 
    return heartrate

#Init only required for blitting to give a clean slate.
def init():
    line.set_ydata(np.ma.array(data_df["Voltage"], mask=True))
    return line,

def write_data():
    # adds the temporary dataframe
    global data_df
    global kill
    while True:
        if not kill:
            if is_test:
                new_data_df = get_fake_heart_data()
            elif not is_test:
                new_data_df = get_heart_data()
            data_df = pd.concat([data_df, new_data_df], ignore_index=True).reset_index(drop=True)
        if kill:
            break

def main():
    global kill
    global data_df
    thread = Thread(target=write_data, daemon=True)
    thread.start()
    ani = animation.FuncAnimation(fig, animate, init_func=init,
        interval=10, blit=True)
    plt.show()
    # When the graph is closed, kills the thread
    kill = True
    thread.join()
    # Filters the data
    fs = len(data_df)/data_df.iloc[-1]["Time"]
    filtered_voltage = butter_bandpass_filter(data_df["Voltage"],lowcut,fs,order=10)
    data_df["Filtered Voltage"]=filtered_voltage
    # Shows the final graph
    make_graph(data_df["Time"],data_df["Filtered Voltage"], get_peaks(data_df['Filtered Voltage']))
    # Saves the CSV data
    if save_data:
        data_df.to_csv(filepath_csv)

if __name__ == "__main__":
    main()