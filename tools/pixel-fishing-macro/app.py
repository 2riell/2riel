import csv
import json
import queue
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from engine import Profile, run

ROOT = Path(__file__).resolve().parent

class App:
    def __init__(self, root):
        self.root = root
        root.title('Pixel Worlds • Fishing Lab')
        root.geometry('900x940')
        root.minsize(740, 700)
        self.queue = queue.Queue()
        self.stop_event = threading.Event()
        self.worker = None
        self.listener = None
        self.rows = []
        self.vars = {}
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#101c2a')
        style.configure('TLabel', background='#101c2a', foreground='#e7edf5', font=('Arial', 11))
        style.configure('TCheckbutton', background='#101c2a', foreground='#e7edf5')
        style.configure('TButton', padding=8)
        root.configure(bg='#101c2a')
        shell = ttk.Frame(root, padding=24)
        shell.pack(fill='both', expand=True)
        ttk.Label(shell, text='FISHING LAB', font=('Arial', 24, 'bold')).pack(anchor='w')
        ttk.Label(shell, text='Pixel Worlds · desktop input test harness').pack(anchor='w', pady=(4, 16))
        self.status = tk.StringVar(value='Ready · dry run enabled')
        ttk.Label(shell, textvariable=self.status, font=('Arial', 13, 'bold')).pack(anchor='w', pady=(0, 12))
        grid = ttk.Frame(shell)
        grid.pack(fill='x')
        defaults = Profile()
        fields = [('cast_x','Cast click X'), ('cast_y','Cast click Y'), ('visual_timeout','Strike timeout (seconds)'), ('cast','Cast key (timed mode)'), ('reel','Reel action'), ('hold','Key hold (seconds)'), ('countdown','Focus countdown (seconds)'), ('bite_wait','Bite wait / timeout (seconds)'), ('cooldown','Cooldown (seconds)'), ('cycles','Maximum cycles'), ('minutes','Session limit (minutes)'), ('x','Bite pixel X'), ('y','Bite pixel Y'), ('color','Bite color (#RRGGBB)'), ('tolerance','RGB tolerance (0–255)')]
        for i, (key, label) in enumerate(fields):
            col = (i % 2) * 2
            row = i // 2
            ttk.Label(grid, text=label).grid(row=row, column=col, sticky='w', padx=(0, 8), pady=6)
            var = tk.StringVar(value=str(getattr(defaults, key)))
            self.vars[key] = var
            ttk.Entry(grid, textvariable=var, width=15).grid(row=row, column=col+1, sticky='ew', padx=(0, 18), pady=6)
        for key, label in [('visual', 'Visual assist (Windows, 1920×1080, maximum zoom)'), ('auto_cast', 'Automatically left-click the saved cast point (visual mode)'), ('dry_run', 'Dry run — observe/simulate without game input'), ('pixel', 'Detect fresh bite color (live mode only)')]:
            var = tk.BooleanVar(value=getattr(defaults, key))
            self.vars[key] = var
            ttk.Checkbutton(shell, text=label, variable=var).pack(anchor='w', pady=5)
        ttk.Label(shell, text='Actions: space, enter, a–z, 0–9, arrows, mouse:left, mouse:right\nMouse actions click at the current cursor. Keep the game focused.', font=('Arial', 10)).pack(anchor='w', pady=8)
        bar = ttk.Frame(shell)
        bar.pack(fill='x', pady=10)
        self.start_button = ttk.Button(bar, text='▶ Start session', command=self.start)
        self.start_button.pack(side='left')
        ttk.Button(bar, text='■ STOP / F8', command=self.stop).pack(side='left', padx=8)
        ttk.Button(bar, text='Sample pixel in 3s', command=self.sample).pack(side='left')
        ttk.Button(bar, text='Pick cast point in 3s', command=self.pick_cast).pack(side='left', padx=8)
        bar2 = ttk.Frame(shell)
        bar2.pack(fill='x', pady=(0, 12))
        for title, callback in [('Load profile',self.load), ('Save profile',self.save), ('Export CSV',self.export)]:
            ttk.Button(bar2, text=title, command=callback).pack(side='left', padx=(0,8))
        self.log = tk.Text(shell, height=10, bg='#09121e', fg='#9ce2d4', font=('Courier', 10), state='disabled', wrap='word')
        self.log.pack(fill='both', expand=True)
        ttk.Label(shell, text='Emergency: F8, Escape in this window, or move pointer to a screen corner.\nmacOS: grant Accessibility and Screen Recording permission to your Python/Terminal app.', font=('Arial', 9)).pack(anchor='w', pady=(10,0))
        root.bind('<Escape>', lambda e: self.stop())
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(100, self.poll)

    def profile(self):
        values = {k:v.get() for k,v in self.vars.items()}
        for key in ('hold','countdown','bite_wait','cooldown','minutes','visual_timeout'):
            values[key] = float(values[key])
        for key in ('cycles','x','y','tolerance','cast_x','cast_y'):
            values[key] = int(values[key])
        return Profile(**values).validate()

    def emit(self, kind, message):
        self.queue.put((kind, message))

    def start(self):
        if self.worker and self.worker.is_alive():
            return
        try:
            p = self.profile()
            backend = None
            self.stop_event.clear()
            if p.visual:
                import sys
                if sys.platform != 'win32':
                    raise ValueError('Visual assist currently supports Windows only')
            if not p.dry_run or p.visual:
                import pyautogui as backend
                from pynput import keyboard
                backend.FAILSAFE = True
                backend.PAUSE = .03
                if p.pixel and not p.visual:
                    if not backend.onScreen(p.x, p.y):
                        raise ValueError('Bite pixel must be on the primary display')
                    backend.pixel(p.x, p.y)  # Check screen access before countdown.
                self.listener = keyboard.Listener(on_press=lambda key: self.stop_event.set() if key == keyboard.Key.f8 else None)
                self.listener.start()
            self.start_button.configure(state='disabled')
            self.worker = threading.Thread(target=run, args=(p,self.stop_event,self.emit,backend), daemon=True)
            self.worker.start()
        except Exception as exc:
            if self.listener:
                self.listener.stop()
            messagebox.showerror('Cannot start', str(exc))

    def stop(self):
        self.stop_event.set()

    def poll(self):
        while not self.queue.empty():
            kind, message = self.queue.get_nowait()
            timestamp = datetime.now().isoformat(timespec='milliseconds')
            self.rows.append((timestamp,kind,message))
            self.log.configure(state='normal')
            self.log.insert('end', f'{timestamp[11:]}  {kind.upper():7} {message}\n')
            if len(self.rows) > 20000:
                self.rows.pop(0)
            if int(self.log.index('end-1c').split('.')[0]) > 1000:
                self.log.delete('1.0','2.0')
            self.log.see('end')
            self.log.configure(state='disabled')
            if kind == 'state':
                self.status.set(message)
            if kind == 'done':
                self.status.set(f'Stopped · {message} cycles / observed rounds (catch success unverified)')
                self.start_button.configure(state='normal')
                if self.listener:
                    self.listener.stop()
                    self.listener = None
        self.root.after(100, self.poll)

    def pick_cast(self):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo('Stop first', 'Stop the session before picking a cast point.')
            return
        self.status.set('Place cursor over either bait icon — saving position in 3 seconds')
        self.root.after(3000, self.capture_cast)

    def capture_cast(self):
        if self.worker and self.worker.is_alive():
            return
        try:
            import pyautogui as pg
            x, y = pg.position()
            if not (0 <= x < 1920 and 0 <= y < 1080):
                raise ValueError('Pick a point inside the primary 1920×1080 display')
            self.vars['cast_x'].set(str(x))
            self.vars['cast_y'].set(str(y))
            self.status.set(f'Cast point saved: ({x}, {y}) — Save profile to keep it')
        except Exception as exc:
            messagebox.showerror('Could not save cast point', str(exc))

    def sample(self):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo('Stop first', 'Stop the session before sampling.')
            return
        self.status.set('Place pointer on bite indicator — sampling in 3 seconds')
        self.root.after(3000, self.capture)

    def capture(self):
        try:
            import pyautogui as pg
            x,y = pg.position()
            rgb = pg.pixel(x,y)
            for k,v in [('x',x),('y',y),('color','#{:02x}{:02x}{:02x}'.format(*rgb[:3]))]:
                self.vars[k].set(str(v))
            self.status.set(f'Sampled ({x}, {y}) · {self.vars["color"].get()}')
        except Exception as exc:
            messagebox.showerror('Pixel sampling failed', str(exc))

    def save(self):
        try:
            p = self.profile()
            path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON','*.json')])
            if path:
                Path(path).write_text(json.dumps(p.dict(), indent=2), encoding='utf-8')
        except Exception as exc:
            messagebox.showerror('Save failed',str(exc))

    def load(self):
        path = filedialog.askopenfilename(filetypes=[('JSON','*.json')])
        if not path:
            return
        try:
            p = Profile(**json.loads(Path(path).read_text(encoding='utf-8'))).validate()
            for key, value in p.dict().items():
                self.vars[key].set(value)
        except Exception as exc:
            messagebox.showerror('Load failed',str(exc))

    def export(self):
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV','*.csv')])
        if path:
            with open(path,'w',newline='',encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp','event','detail'])
                writer.writerows(self.rows)

    def close(self):
        self.stop()
        if self.worker and self.worker.is_alive():
            self.root.after(100,self.close)
            return
        if self.listener:
            self.listener.stop()
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    import sys
    if '--smoke-test' in sys.argv:
        import pyautogui
        from vision import Detector
        Detector()
        from pynput import keyboard, mouse
        root.update()
        root.destroy()
    else:
        root.mainloop()
