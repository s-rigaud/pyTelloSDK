"""This user interface allow the user to take control of the drone in the same time it provides you
 a live stream video of the front camera of the drone"""

import os
import sys
import tkinter as tk
from tkinter import PhotoImage, TclError
from time import sleep
from threading import Thread, get_ident
from PIL import ImageTk

from toolbox import command_from_key
from tello_edu import TelloEDU


class VideoUI:
    """Embeded Tkinter ineterface and drone control"""
    def __init__(self, drone):
        self.drone = drone
        self.pictures = []
        self.video_thread = self.ka_thread = None

        # UI
        self.window_is_opened = False
        self.root = tk.Tk()
        self.root.wm_title("VideoUI")
        self.root.bind("<Key>", self.keys)
        self.root.bind("<Control-Key>", self.quit)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.panel = None

        self.dir_path = os.path.dirname(os.path.realpath(__file__))
        if not self.drone.is_connected:
            path = os.path.sep.join((self.dir_path, 'connection_failed.png'))
            self.frame = PhotoImage(file=path)
        else:
            path = os.path.sep.join((self.dir_path, 'loading.png'))
            self.frame = PhotoImage(file=path)
            # Timeout to kill concurent threads
            self.drone.command_socket.settimeout(11)

        self.tkframe = None
        self.panel = tk.Label(self.root, image=self.frame)
        self.panel.pack()

    def __del__(self):
        """Deleting the drone drone reference"""
        print('UI deletion')

    @property
    def threads_alive(self):
        existing_threads = [thread for thread in (self.video_thread, self.ka_thread) if thread is not None]
        return len([thread for thread in existing_threads if thread.isAlive()])

    def show_bindings(self):
        tk.Label(self.root, text='⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀forward                 clockwise rotation : 4  ↻').pack()
        tk.Label(self.root, text='⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⬆️             counter clockwise rotation : 6  ↺').pack()
        tk.Label(self.root, text='left ⬅️     ➡️ right').pack()
        tk.Label(self.root, text='⬇️').pack()
        tk.Label(self.root, text='backward').pack()
        tk.Label(self.root, text='').pack()
        tk.Label(self.root, text='land      : +⠀⠀⠀⠀⠀').pack()
        tk.Label(self.root, text='takeoff  : space bar').pack()
        tk.Label(self.root, text='up         : 8⠀⠀⠀⠀⠀').pack()
        tk.Label(self.root, text='down      : 2⠀⠀⠀⠀⠀').pack()



    def quit(self, event=None):
        """Close the window"""
        print('quit')
        self.window_is_opened = False
        self.drone.end_connection = True
        # Try to kill drone before
        # sleep(2)
        try:
            self.root.destroy()
        # If window has already been close ...
        except TclError as tcl:
            print(tcl)

    def keys(self, event):
        """Bind keys to drone commands"""
        key = event.char
        keycode = event.keycode

        if key == 'p':
            self.pictures.append(self.drone.take_picture())
            self.drone.save_pictures(self.pictures) # Rewriting each time
        elif command_from_key(key) is not None:
            command = command_from_key(key)
            self.drone.execute_actions([f'0-{command}',])
        elif command_from_key(keycode) is not None:
            command = command_from_key(keycode)
            self.drone.execute_actions([f'0-{command}',])
        else:
            print(f'{key} is not bind to an action')

    def _keep_alive(self):
        """Simple thread to be sure the drone will not try to land after a short time without command received"""
        while self.drone.is_connected and self.window_is_opened:
            self.drone.execute_actions(['0-command',])
            sleep(10)
        print('keep alive done')
        self.drone.end_connection = True

        path = os.path.sep.join((self.dir_path, 'offline.png'))
        tk.Label(self.root, image=path).pack()


    def _video_stream(self):
        """Image recepting thread"""
        while self.drone.is_connected and self.window_is_opened:
            self.tkframe = self.frame
            if self.drone.take_picture() is not None:
                self.frame = self.drone.take_picture()
                try:
                    # This may lead to blocking call ...
                    self.tkframe = ImageTk.PhotoImage(self.frame)
                except RuntimeError:
                    print('Last frame was incomplete')
            ### Problem : blocking function call

            #This should be an asynchronous call (indications about future image)
            self.panel.configure(image=self.tkframe)
            #This is the real affectation
            self.panel.image = self.tkframe
        self.drone.end_connection = True
        print('video down')

        # Test if panel is None after destruct

    def open(self):
        """"""
        if self.drone.is_connected:
            self.window_is_opened = True
            # Threads
            self.ka_thread = Thread(target=self._keep_alive)
            self.ka_thread.start()

            self.video_thread = Thread(target=self._video_stream)
            self.video_thread.start()

            self.show_bindings()

        self.root.mainloop()
        self.drone.end_connection = True
        print('windows done')

        # Manually kill the thread (tkinter issue)

        while self.drone.threads_alive or self.threads_alive:
            sleep(1)
            print(self.drone.threads_alive)
            print(self.threads_alive)
        print('not drone here')
        del self.drone

if __name__ == "__main__":
    # my_drone = Swarm(['192.168.10.1', ], video_stream=True)
    my_drone = TelloEDU('192.168.10.1', video_stream=True)
    vui = VideoUI(my_drone)
    vui.open()

    # Problem
    # Windows needs to be killed after the drone disconnect else the software is trying to update the closed windows
    # unding with a blocking call function with no warning

