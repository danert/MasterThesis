import tkinter as tk
from tkinter import filedialog, Text
import os

def startGui():
    root = tk.Tk()

    def addApp():
        filename = filedialog.askdirectory(title="Select app folder")
        print(filename)
        root.destroy()


    canvas = tk.Canvas(root, height=700, width=700, bg="#c4c4c4")
    canvas.pack()

    frame=tk.Frame(root, bg="white")
    frame.place(relwidth=0.9, relheight=0.9, relx=0.05, rely=0.05)

    selectApp =tk.Button(root, text="Select Android app", padx=10, pady=5, fg="white", bg="#454545", command=addApp)
    selectApp.pack()

    root.mainloop()
