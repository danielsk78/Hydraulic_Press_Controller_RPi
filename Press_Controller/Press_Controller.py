# Import relevant packages
try:
    import RPi.GPIO as IO
    IO.setwarnings(False)
    IO.setmode(IO.BCM)
    RPi_IMPORT = True
    print('RPi.GPIO imported successfully')
    from hx711 import HX711
    print('hx711 imported successfully')
except ImportError:
    print('RPi.GPIO only available for Raspberry Pi, use Dummy')
    RPi_IMPORT = False
    print('hx711 not installed')

import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog

import numpy as np
import pandas as pd

from abc import ABCMeta
from abc import abstractmethod
import threading
from datetime import datetime
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
matplotlib.use("TkAgg")


class Output_Pin:
    """
    Class to control the high and low, frequency and duty cycle for an specific channel output
    """
    def __init__(self, channel):
        """
        Initinialize the class with global variables
        Args:
            channel: (int) the GPIO pin to which the class will connect
        """

        self.channel = channel
        IO.setmode(IO.BCM)
        IO.setup(self.channel, IO.OUT)
        self.frequency = 10000
        self.dc = 50  # duty cycle
        self.p = None
        # self.active = None

    def on(self):
        """
        Switch on the led with a High
        Returns:
        """
        IO.output(self.channel, IO.HIGH)
        print("Turned: On")

    def off(self):
        """
        Switch off the led with a Low
        Returns:
        """
        IO.output(self.channel, IO.LOW)
        print("Turned: Off")

    def start_PWM(self):
        """
        Initialize the PWM
        Returns:
        """
        if self.p is None:
            self.p = IO.PWM(self.channel, self.frequency)  # channel, frequency
            
        else:
            self.p = None
            self.p = IO.PWM(self.channel, self.frequency)  # channel, frequency
        print("Ready to use")
                    
    def move_PWM(self):
        """
        Start the PWM movement
        Returns:
        """
        self.p.start(self.dc)
        print("Moving press...")

    def stop(self):
        """
        Stop the movement of the press by switchin off the channel output
        Returns:
        """

        try:
            self.p.stop()
            print("Stop moving")
        except:
            print("Nothing to move")


class Input_Pin:
    def __init__(self, channel):
        """
        Initinialize the class with global variables
        Args:
            channel: (int) the GPIO input pin to which the class will connect
        """
        self.channel = channel
        IO.setmode(IO.BCM)
        IO.setup(self.channel, IO.IN, pull_up_down=IO.PUD_DOWN)
        IO.add_event_detect(self.channel, IO.RISING)  # , callback = self.my_callback)#, bouncetime=100)
        # IO.add_event_callback(self.channel, self.my_callback)
            
    def state(self):
        """
        Function to determine what is the state of the machine
        Returns:

        """
        x = IO.input(self.channel)
        return x


class Balance_Sensor:
    """
    Class to conect the hx711 to the Raspberry Pi and read the sensor
    """
    def __init__(self):  # , dout_pin=21, pd_sck_pin=20, readings=10):
        """
         Initinialize the class with global variables. Careful with assignation of pins
        """
        IO.setmode(IO.BCM)
        self.dout_pin = 21
        self.pd_sck_pin = 20
        self.readings = 15
        self.ave = 0
        
        self.hx = HX711(dout_pin=self.dout_pin, pd_sck_pin=self.pd_sck_pin)  # create an object
    
    def average_val(self):
        """
        Function to read an specific amount of measurements and take the average value of these readings
        Returns:
            Average value
        """
        ave = np.average(np.array(self.hx.get_raw_data(self.readings)))
        return ave
        
    def corrected_value(self):
        """
        Function that corrects the average value calculated and make the conversion to correct units
        Returns:
            Corrected value in kN
        """
        ave_cor = (self.average_val()/(2**23))*50
        self.ave = ave_cor
        return ave_cor


class Dummy:
    """
    Class that allow to test the interface and the program outside the raspberry pi
    """

    def __init__(self, channel):
        self.channel = channel
        self.frequency = 100
        self.dc = 50  # duty cycle
        self.p = None
        self.activate = True
        self.ave = 0

    def on(self):
        self.activate = True
        print("Turn On LED")

    def off(self):
        self.activate = False
        print("Turn Off LED")

    def start_PWM(self):
        print("Ready to use")

    def move_PWM(self):
        print("Frequency:", self.frequency, "Duty Cycle:", self.dc)
        print("moving press...")

    def stop(self):
        print("All Stop")

    def state(self):
        if self.activate:
            x = 1
        else:
            x = 0
        return x

    def corrected_value(self):
        ave = np.random.randint(100)
        time.sleep(0.5)
        return ave


class Read_Pin(object):
    """
    Parent class that contain the threading methods
    """
    __metaclass__ = ABCMeta
    
    def __init__(self, **kwargs):
        """
        Initialize the class with the threads
        Args:
            **kwargs:
        """
        self.lock = threading.Lock()
        self.time_lock = threading.Lock()
        self.force_lock = threading.Lock()
        self.thread = None
        self.time_thread = None
        self.force_thread = None
        self.thread_status = 'stopped'  # status: 'stopped', 'running', 'paused'
        self.time_thread_status = 'stopped'  # status: 'stopped', 'running', 'paused'
        self. force_thread_status = 'stopped'
        
    @abstractmethod
    def setup_init(self):
        # Wildcard: Everything necessary to set up before a press start working.
        pass

    @abstractmethod
    def update(self):
        # Wildcard: Single update operation that can be looped in a thread.
        pass

    @abstractmethod
    def timer(self):
        # Wildcard: Single update operation that can be looped in a thread.
        pass

    @abstractmethod
    def force(self):
        # Wildcard: Single update operation that can be looped in a thread.
        pass

    def thread_timer_loop(self):
        while self.time_thread_status == 'running':
            self.time_lock.acquire()
            self.timer()
            self.time_lock.release()

    def thread_force_loop(self):
        while self.force_thread_status == 'running':
            self.force_lock.acquire()
            self.force()
            self.force_lock.release()

    def thread_loop(self):
        """
        Main thread loop where the update function is the one that is executed recursively
        Returns:
        """
        while self.thread_status == 'running':
            self.lock.acquire()
            self.update()
            self.lock.release()

    def run_force(self):
        if self.force_thread_status != 'running':
            self.force_thread_status = 'running'
            self.force_thread = threading.Thread(target=self.thread_force_loop, daemon=True, )
            self.force_thread.start()
            print('Thread started or resumed...')
        else:
            print('Thread already running.')

    def run_time(self):
        if self.time_thread_status != 'running':
            self.time_thread_status = 'running'
            self.time_thread = threading.Thread(target=self.thread_timer_loop, daemon=True, )
            self.time_thread.start()
            print('Thread started or resumed...')
        else:
            print('Thread already running.')

    def run(self):
        if self.thread_status != 'running':
            self.thread_status = 'running'
            self.thread = threading.Thread(target=self.thread_loop, daemon=True, )
            self.thread.start()
            print('Thread started or resumed...')
        else:
            print('Thread already running.')

    def stop(self):
        if self.thread_status is not 'stopped':
            self.thread_status = 'stopped'  # set flag to end thread loop
            self.thread.join()  # wait for the thread to finish
            print('Thread stopped.')
        else:
            print('thread was not running.')
    
    def pause(self):
        if self.thread_status == 'running':
            self.thread_status = 'paused'  # set flag to end thread loop
            self.thread.join()  # wait for the thread to finish
            print('Thread paused.')
        else:
            print('There is no thread running.')

    def pause_time(self):
        if self.time_thread_status == 'running':
            self.time_thread_status = 'paused'  # set flag to end thread loop
            self.time_thread.join()  # wait for the thread to finish
            print('Thread paused.')
        else:
            print('There is no thread running.')

    def pause_force(self):
        if self.force_thread_status == 'running':
            self.force_thread_status = 'paused'  # set flag to end thread loop
            self.force_thread.join()  # wait for the thread to finish
            print('Thread paused.')
        else:
            print('There is no thread running.')


class Interface(Read_Pin):
    """
    Interface class that link the channel functionality of the Press_controller class with the the GUI
    """
    def __init__(self,
                 *args,
                 Pulse_channel_out=4,
                Enable_channel_out=24, 
                Dir_channel_out=18, 
                Active_channel_in=23,
                balance_dt_pin=21,
                balance_sck_pin=20,
                is_Dummy=False,
                 **kwargs):
        """
        Function to initialize each buttom from the GUI
        Args:
            *args:
            Pulse_channel_out: (int) pin number for the Pulse channel
            Enable_channel_out: (int) pin number for the Enabling channel
            Dir_channel_out: (int) pin number for the direction channel
            Active_channel_in: (int) pin number for the active channel
            balance_dt_pin: Already pass as intrinsic parameter in the class
            balance_sck_pin: Already pass as intrinsic parameter in the class
            is_Dummy: (boolean) that check if the program is running in a raspberry pi or if want to test the
        interface
            **kwargs:
        """

        super().__init__(**kwargs)
        # Method to activate the dummy automatically
        self.dummy = is_Dummy
        if RPi_IMPORT is False:
            self.dummy = True

        # Initialize the leds
        if self.dummy:
            self.pulse = Dummy(Pulse_channel_out)
            self.enable = Dummy(Enable_channel_out)
            self.dir = Dummy(Dir_channel_out)
            self.active = Dummy(Active_channel_in)
            self.balance = Dummy(1)
        else:
            self.pulse = Output_Pin(Pulse_channel_out)
            self.enable = Output_Pin(Enable_channel_out)
            self.dir = Output_Pin(Dir_channel_out)
            self.active = Input_Pin(Active_channel_in)
            self.balance = Balance_Sensor()
    
        self.sleep = 0.1

        self.df = None
        self.set_new_df()

        self.fig = plt.figure("Press Data")
        self.ax = plt.gca()
        plt.close()

        self.btn = None
        self.lbl = None
        self.lbl_save = None

        self.start_recording = False
        self.initial_time = None

        self.matplot_update = None

        self.sleep_record = 2
        self.aim = 2
        self.deviation = 0.3

        self.dir_name = "./"

    def set_new_df(self):
        labels = {"Date", "Time_sec", "Force_kN"}
        self.df = pd.DataFrame(columns=labels)

    def update(self):
        """
        Everything that is included in the thread
        Returns:

        """
        self.balance.corrected_value()
        val = np.round(self.balance.ave, decimals=5)
        self.lbl.configure(text="Reading:   " + str(val))
        
        if self.active.state() == 1:
            self.btn.configure(bg="green", text="READY")
        else:
            self.btn.configure(bg="red", text="OFF")
    
    def timer(self):
        """
        Function to record the readings from the press sensor
        Returns:
        """
        if self.start_recording:
            force = self.balance.ave
            if self.initial_time is None:
                self.initial_time = time.perf_counter()
            time_elapsed = time.perf_counter() - self.initial_time  # Time in seconds
            df_temp = pd.DataFrame({"Date": [time.ctime()], "Time_sec": [time_elapsed], "Force_kN": [force]})
            self.df = pd.concat([self.df, df_temp], ignore_index=True)
            time.sleep(self.sleep_record)

    def create_matplotlib_window(self):
        # Initialize an instance of Tk
        parent_plt = tk.Tk()
        parent_plt.title("Plot time ")
        parent_plt.geometry('750x400')
    
        canvas_plt = tk.Canvas(parent_plt)
        scroll_y = tk.Scrollbar(parent_plt, orient="vertical", command=canvas_plt.yview)
        
        matplot_window = tk.Frame(canvas_plt)
        
        fig = plt.figure(figsize=(7,3))
        def _plotter():
            # Clear all graphs drawn in figure
            plt.clf()
            plt.xlabel("Time (sec)")
            plt.ylabel("Force (kN)")
            plt.plot(self.df.Time_sec, self.df.Force_kN, '*--', color="Blue")
            plt.grid()
            fig.canvas.draw()

        # Special type of "canvas" to allow for matplotlib graphing
        canvas = FigureCanvasTkAgg(fig, master=matplot_window)
        plot_widget = canvas.get_tk_widget()
        # Add the plot to the tkinter widget
        plot_widget.grid(row=0, column=0)
        # Create a tkinter button at the bottom of the window and link it with the updateGraph function
        tk.Button(matplot_window, text="Update", command=_plotter).grid(row=1, column=0)
        
        canvas_plt.create_window(0, 0, anchor='nw', window=matplot_window)
        # make sure everything is displayed before configuring the scrollregion
        canvas_plt.update_idletasks()

        canvas_plt.configure(scrollregion=canvas_plt.bbox('all'), 
                         yscrollcommand=scroll_y.set)
                         
        canvas_plt.pack(fill='both', expand=True, side='left')
        scroll_y.pack(fill='y', side='right')
        
        parent_plt.mainloop()

    def force(self):
        actual_force = self.balance.ave
        aim_force = self.aim
        e = self.deviation
        if actual_force > (aim_force + e):  # Go down
            self.pulse.stop()
            time.sleep(self.sleep)
            self.dir.on()
            time.sleep(self.sleep)
            self.pulse.move_PWM()
            self.pulse.stop()

        elif actual_force < (aim_force - e):  # Go up
            self.pulse.stop()
            time.sleep(self.sleep)
            self.dir.off()
            time.sleep(self.sleep)
            self.pulse.move_PWM()
            self.pulse.stop()

        else:
            self.pulse.stop()

    def save_data(self):
        """
        Save the pandas data frame of the recording to be open as a csv in other software
        Returns:
        """
        now = datetime.now()
        current_date = now.strftime("%d%m%Y_%H%M")
        file_dir = self.dir_name + "/" + current_date + ".csv"
        self.df.to_csv(file_dir, index=False)
        print("Data saved in:", file_dir)
        
    def setup(self):
        """
        create the interface with all the buttoms and functionalities
        Returns:

        """
        parent = tk.Tk()
        parent.title("Press Controller and sensor readings")
        parent.geometry('750x400')
        
        canvas = tk.Canvas(parent)
        scroll_y = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)

        mainframe = tk.Frame(canvas)
               

        fq = tk.IntVar(value=self.pulse.frequency, master=mainframe)
        def frequency():
            """
            If the user want to change the frequency, this function will change the frequency configuration of the
            Press_controller class
            Returns:

            """
            print("before:", self.pulse.frequency)
            self.pulse.frequency = fq.get()
            print("after:", self.pulse.frequency)

        # Value saved here for the duty cycle
        dc = tk.IntVar(value=self.pulse.dc, master=mainframe)
        def duty_cycle():
            """
            If the user want to change the frequency, this function will change the frequency configuration of the
            Press_controller class
            Returns:

            """
            print("before:", self.pulse.dc)
            self.pulse.dc = dc.get()
            print("after", self.pulse.dc)
                
        def dir_down():
            """
            Move the press downwards
            Returns:

            """
            try:
                self.pulse.stop()
                time.sleep(self.sleep)
                self.dir.on()     
                time.sleep(self.sleep)      
                self.pulse.move_PWM()
            except:
                print("Click on start button to activate the press")
                messagebox.showerror('Error', 'Click on start button to activate the press')
            
        def dir_up():
            """
            Move the press upwards
            Returns:

            """
            try:
                self.pulse.stop()
                time.sleep(self.sleep)
                self.dir.off()     
                time.sleep(self.sleep)    
                self.pulse.move_PWM()
            except:
                print("Click on start button to activate the press")
                messagebox.showerror('Error', 'Click on start button to activate the press')

        obj = tk.IntVar(value=self.aim, master=mainframe)

        def set_force():
            self.aim = obj.get()
            print("force to apply:", self.aim)
            self.run_force()

        def pause_set_force():
            self.pause_force()

        def release_force():
            pass

        sec = tk.IntVar(value=self.sleep_record, master=mainframe)

        def set_time():
            self.sleep_record = sec.get()
            self.start_recording = True
            self.run_time()
            print("Recording data every:", self.sleep_record, 'seconds')

        def pause_recordings():
            self.start_recording = False
            self.pause_time()
            print("Recording Paused")

        def clear_recordings():
            self.set_new_df()
            messagebox.showwarning('Warning', 'All the previous data is erased')
            print("Recordings erased")
        
        def plot_data():
            self.create_matplotlib_window()
            print("New window open, to see data")

        ### Manual Controller
        tk.Label(mainframe, text="Manual Controller", font=("Arial Bold", 12), height=3).grid(column=1, row=1)

        # Enable label and buttons
        tk.Label(mainframe, text="Enable").grid(column=1, row=2)
        tk.Button(mainframe, text="On", command=self.enable.on, width=10).grid(column=2, row=2)
        tk.Button(mainframe, text="Off", command=self.enable.off, width=10).grid(column=3, row=2)

        # Pulse label and buttons
        tk.Label(mainframe, text="Pulse").grid(column=1, row=3)
        tk.Button(mainframe, text="Start", command=self.pulse.start_PWM, width=10).grid(column=2, row=3)
        tk.Button(mainframe, text="Stop", command=self.pulse.stop, width=10).grid(column=3, row=3)

        # direction label and buttons
        tk.Label(mainframe, text="Direction").grid(column=1, row=4)
        tk.Button(mainframe, text="Down(CCW)", command=dir_down, width=10).grid(column=2, row=4)
        tk.Button(mainframe, text="Up(CW)", command=dir_up, width=10).grid(column=3, row=4)

        # change the frequency according to user input
        tk.Entry(mainframe, textvariable=fq, width=10).grid(column=5, row=2)
        tk.Button(mainframe, text="Set Frequency", command=frequency).grid(column=6, row=2)

        # change the frequency according to user input
        tk.Entry(mainframe, textvariable=dc, width=10).grid(column=5, row=3)
        tk.Button(mainframe, text="set Duty Cycle", command=duty_cycle).grid(column=6, row=3)

        # active or inactive
        self.btn = tk.Button(mainframe, text="Waiting", width=10, height=3, bg="yellow", state='disabled')
        self.btn.grid(column=5, row=4, columnspan=2, sticky=tk.W + tk.E)

        ### Set Force
        tk.Label(mainframe, text="Force to apply (kN)", font=("Arial Bold", 12), height = 3).grid(column=1, row=5)

        # Sensor reading
        self.lbl = tk.Label(mainframe, text="No reading", font=("Arial Bold", 10))
        self.lbl.grid(column=1, row=6, columnspan=4, sticky=tk.W + tk.E )

        # Objective
        tk.Entry(mainframe, textvariable=obj, width=10).grid(column=1, row=7)
        tk.Button(mainframe, text="Set Force (kN)", command=set_force, width=10).grid(column=2, row=7)
        tk.Button(mainframe, text="Pause ", command=pause_set_force, width=10).grid(column=3, row=7)

        ### Data Recording
        tk.Label(mainframe, text="Data recording (sec)", font=("Arial Bold", 12), height=3).grid(column=1, row=8)

        ### Recording Data
        tk.Entry(mainframe, textvariable=sec, width=10).grid(column=1, row=9)
        tk.Button(mainframe, text="Start", command=set_time, width=10).grid(column=2, row=9)
        tk.Button(mainframe, text="Pause", command=pause_recordings, width=10).grid(column=3, row=9)
        tk.Button(mainframe, text="Clear", command=clear_recordings, width=10).grid(column=4, row=9)

        def select_folder():
            self.dir_name = filedialog.askdirectory()
            self.lbl_save.configure(text=self.dir_name)

        # Saving Data
        tk.Button(mainframe, text="Browse..", command=select_folder).grid(column=2, row=8)
        self.lbl_save = tk.Label(mainframe, text="Select a folder")
        self.lbl_save.grid(column=3, row=8, columnspan=7, sticky=tk.W + tk.E)

        tk.Button(mainframe, text="Save Data", command=self.save_data, width=10).grid(column=2,
                                                                                      row=10,
                                                                                      columnspan=3,
                                                                                      sticky=tk.W + tk.E)
        # Plotting Data
        tk.Button(mainframe, text="Plot Data", command=plot_data, width=10, height=3, bg="blue").grid(column=5,
                                                                                                      row=9,
                                                                                                      columnspan=2,
                                                                                                      rowspan=2,
                                                                                                      sticky=tk.W + tk.E)

        # Close the window
        def stop_all(): #TODO: still not working
            print("Stop all")
            self.pulse.stop()
            time.sleep(0.3)
            self.enable.off()
            time.sleep(0.3)
            self.pause_force()
            time.sleep(0.3)
            self.pause_time()
            time.sleep(0.3)
            self.stop()
            #if self.dummy is False:
            #    IO.cleanup()
            #mainframe.quit()

        tk.Button(mainframe, text="Stop all", bg="red", command=stop_all).grid(column=5, row=1, columnspan=2, sticky=tk.W + tk.E)
        
        canvas.create_window(0, 0, anchor='nw', window=mainframe)
        # make sure everything is displayed before configuring the scrollregion
        canvas.update_idletasks()

        canvas.configure(scrollregion=canvas.bbox('all'), 
                         yscrollcommand=scroll_y.set)
                         
        canvas.pack(fill='both', expand=True, side='left')
        scroll_y.pack(fill='y', side='right')
        

        # run thread
        self.run()
        
        parent.mainloop()
        if self.dummy is False:
            IO.cleanup()
