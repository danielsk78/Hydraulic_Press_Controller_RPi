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

from PIL import ImageTk, Image

import datetime
import numpy as np
import pandas as pd

from abc import ABCMeta
from abc import abstractmethod
import threading
import time
import matplotlib.pyplot as plt


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
    
    def my_callback(self, channel):  # TODO: Deprecated. Keep for future functionalities as replacement for thread
        x = IO.input(self.channel)
        print(x)


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

    def average_val(self):
        rand = np.random.randn(30)
        ave = np.average(rand)
        return ave

    def corrected_value(self):
        ave_cor = (self.average_val() / (2 ** 23)) * 50
        self.ave = ave_cor
        return ave_cor


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
        self.thread = None
        self.thread_status = 'stopped'  # status: 'stopped', 'running', 'paused'
        
    @abstractmethod
    def setup_init(self):
        # Wildcard: Everything necessary to set up before a press start working.
        pass

    @abstractmethod
    def update(self):
        # Wildcard: Single update operation that can be looped in a thread.
        pass

    def thread_loop(self):
        """
        Main thread loop where the update function is the one that is executed recursively
        Returns:
        """
        while self.thread_status == 'running':
            self.lock.acquire()
            self.update()
            self.lock.release()

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

    def resume(self):
        if self.thread_status != 'stopped':
            self.run()
        else:
            print('Thread already stopped.')


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
    
        self.sleep = 0.2
        labels = {"Date", "Force_kN"}
        self.df = pd.DataFrame(columns=labels)
        self.fig = plt.figure("Press Data")
        self.ax = plt.gca()
        self.btn = None
        self.lbl = None

    def setup_init(self):
        """
        Initialize starting values before the thread start
        Returns:
        """
        val = np.round(self.balance.corrected_value(), decimals=5)
        self.lbl.configure(text=str(val))
        
        if self.active.state() == 1:
            self.btn.configure(bg="green", text="READY")
        else:
            self.btn.configure(bg="red", text="OFF")

    def update(self):
        """
        Everything that is included in the thread
        Returns:

        """
        val = np.round(self.balance.corrected_value(), decimals=5)
        self.lbl.configure(text=str(val))
        
        if self.active.state() == 1:
            self.btn.configure(bg="green", text="READY")
        else:
            self.btn.configure(bg="red", text="OFF")
    
    def record(self):
        """
        Function to record the readings from the press sensor
        Returns:

        """
        force = self.balance.corrected_value()
        df_temp = pd.DataFrame({"Date": [str(datetime.datetime.now())], "Force_kN": [force]})
        self.df = pd.concat([self.df, df_temp])  # , sort=False)
        
    def plot_data(self):
        """
        Plot all the data previously recorded
        Returns:

        """
        self.ax.cla()
        self.ax.plot(self.df.Date, self.df.Force_kN, '*--', color="Blue")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Force (kN)")
        plt.show()
    
    def save_data(self):
        """
        Save the pandas data frame of the recording to be open as a csv in other software
        Returns:
        """
        # export as csv
        pass
        
    def setup(self):
        """
        create the interface with all the buttoms and functionalities
        Returns:

        """

        # Create root
        mainframe = tk.Tk()
        
        # Create main frame shape
        mainframe.title("Press Controller and sensor readings")
        mainframe.geometry('600x400')

        fq = tk.IntVar(value=self.pulse.frequency)  # Value saved here for the frequency

        def frequency():
            """
            If the user want to change the frequency, this function will change the frequency configuration of the
            Press_controller class
            Returns:

            """
            if self.dummy:
                print("before:", self.pulse.frequency)

            self.pulse.frequency = fq.get()

            if self.dummy:
                print("after:", self.pulse.frequency)

        dc = tk.IntVar(value=self.pulse.dc)  # Value saved here for the duty cycle

        def duty_cycle():
            """
            If the user want to change the frequency, this function will change the frequency configuration of the
            Press_controller class
            Returns:

            """

            if self.dummy:
                print("before:", self.pulse.dc)

            self.pulse.dc = dc.get()

            if self.dummy:
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
            
        obj = tk.IntVar(value=0)

        def set_force():
            aim = obj.get()
            print("force to apply:", aim)
            

        ### Manual Controller    
        tk.Label(mainframe, text="Manual Controller", font=("Arial Bold", 12), height = 3).grid(column=1, row=1)
        
        # Pulse label and buttons
        tk.Label(mainframe, text="Pulse", height=3).grid(column=1, row=2)
        tk.Button(mainframe, text="Start", command=self.pulse.start_PWM, width=10).grid(column=2, row=2)
        tk.Button(mainframe, text="Stop", command=self.pulse.stop, width=10).grid(column=3, row=2)

        # Enable label and buttons
        tk.Label(mainframe, text="Enable", height=3).grid(column=1, row=3)
        tk.Button(mainframe, text="On", command=self.enable.on, width=10).grid(column=2, row=3)
        tk.Button(mainframe, text="Off", command=self.enable.off, width=10).grid(column=3, row=3)

        # direction label and buttons
        tk.Label(mainframe, text="Direction", height=3).grid(column=1, row=4)
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
        self.btn.grid(column=6, row=4)
        
        ### Set Force 
        tk.Label(mainframe, text="Force to apply (kN)", font=("Arial Bold", 12), height = 3).grid(column=1, row=5)
        
        # Objective
        tk.Entry(mainframe, textvariable=obj, width=10).grid(column=1, row=6)
        tk.Button(mainframe, text="set Force (kN)", command=set_force, width=10).grid(column=2, row=6)
                    
        # Sensor reading
        self.lbl = tk.Label(mainframe, text="No reading")
        self.lbl.grid(column=1, row=7)
        
        # Recording Data
        tk.Button(mainframe, text="Start recording", command=self.record, width=10).grid(column=2, row=7)
        
        # Plotting Data
        tk.Button(mainframe, text="Plot Data", command=self.plot_data, width=10).grid(column=3, row=7)
        
        # Saving Data
        tk.Button(mainframe, text="Save Data", command=self.save_data, width=10).grid(column=4, row=7)
        
        # run thread
        self.run()
        
        mainframe.mainloop()
        IO.cleanup()