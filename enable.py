#!/usr/bin/env python3

import tkinter as tk
from PIL import ImageTk, Image

#This creates the main window of an application
root = tk.Tk()

# Create main frame shape
mainframe = ttk.Frame(root, padding="50 50 50 50")
mainframe.grid(column=0, row=0)
mainframe.columnconfigure(0, weight=1)
mainframe.rowconfigure(0, weight=1)
def set_img(x):
	if x ==1:
		img = ImageTk.PhotoImage(Image.open("on.jpg"))
	elif x==0:
		img= ImageTk.PhotoImage(Image.open("off.jpg"))
	return img
ttk.Label(mainframe, image = set_img(0)).grid(column=1,row=1)

root.mainloop()

window = tk.Tk()
window.title("Join")
window.geometry("300x300")
window.configure(background='grey')

path = "off.jpg"

#Creates a Tkinter-compatible photo image, which can be used everywhere Tkinter expects an image object.
img = ImageTk.PhotoImage(Image.open(path))

#The Label widget is a standard Tkinter widget used to display a text or image on the screen.
panel = tk.Label(window, image = img)

#The Pack geometry manager packs widgets in rows or columns.
panel.pack()#side = "bottom", fill = "both", expand = "yes")

#Start the GUI
window.mainloop()
