import csv
import time
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
        import sys
        self.root = root
        root.title('Fishing Lab')
        root.geometry('800x850')
        root.minsize(740, 720)
        self.queue = queue.Queue()
        self.stop_event = threading.Event()
        self.worker = None
        self.listener = None
        self.rows = []
        defaults = Profile()
        defaults.no_time_limit = True
        defaults.visual = sys.platform == 'win32'
        self.vars = {k:(tk.BooleanVar(value=v) if isinstance(v,bool) else tk.StringVar(value=str(v))) for k,v in defaults.dict().items()}
        ui_font = 'Segoe UI' if sys.platform == 'win32' else 'Helvetica'
        bg,card,text,muted,accent = '#0c1220','#151f30','#edf4fa','#91a4ba','#65dfc2'
        root.configure(bg=bg)
        st=ttk.Style();st.theme_use('clam')
        st.configure('.',font=(ui_font,10))
        st.configure('TFrame',background=bg)
        st.configure('Card.TFrame',background=card)
        st.configure('TLabel',background=bg,foreground=text)
        st.configure('Muted.TLabel',foreground=muted)
        st.configure('Card.TLabel',background=card,foreground=text)
        st.configure('TCheckbutton',background=bg,foreground=text,padding=5)
        st.map('TCheckbutton',background=[('active',bg)])
        st.configure('TEntry',fieldbackground=card,foreground=text,insertcolor=text,padding=7,bordercolor='#25364b',lightcolor='#25364b',darkcolor='#25364b')
        st.configure('TButton',background=card,foreground=text,borderwidth=0,padding=(14,9))
        st.map('TButton',background=[('active','#253952')])
        st.configure('Accent.TButton',background=accent,foreground=bg,font=(ui_font,11,'bold'))
        st.map('Accent.TButton',background=[('active','#8befd7'),('disabled','#354958')])
        st.configure('Stop.TButton',foreground='#ff9d9d')
        st.configure('TNotebook',background=bg,borderwidth=0,bordercolor=bg,lightcolor=bg,darkcolor=bg)
        st.configure('Horizontal.TScale',background=card,troughcolor='#25364b',bordercolor=bg)
        st.configure('Vertical.TScrollbar',background='#25364b',troughcolor=bg,arrowcolor=muted,bordercolor=bg)
        st.configure('TNotebook.Tab',background=card,foreground=muted,padding=(24,10))
        st.map('TNotebook.Tab',background=[('selected','#24384b')],foreground=[('selected',accent)])
        shell=ttk.Frame(root,padding=24);shell.pack(fill='both',expand=True)
        header=ttk.Frame(shell);header.pack(fill='x')
        ttk.Label(header,text='Fishing Lab',font=(ui_font,25,'bold')).pack(side='left')
        ttk.Label(header,text='PIXEL WORLDS  /  DESKTOP',style='Muted.TLabel').pack(side='right')
        ttk.Label(shell,text='Cast. Track. Collect. Repeat.',style='Muted.TLabel').pack(anchor='w',pady=(2,18))
        summary=ttk.Frame(shell,style='Card.TFrame',padding=14);summary.pack(fill='x')
        self.status=tk.StringVar(value='Ready — dry run enabled')
        ttk.Label(summary,textvariable=self.status,style='Card.TLabel',wraplength=680).pack(anchor='w')
        self.metrics=tk.StringVar(value='Tracker — FPS   |   0 completed cycles')
        ttk.Label(summary,textvariable=self.metrics,style='Card.TLabel',font=(ui_font,9)).pack(anchor='w',pady=(6,0))
        self.last_metrics='Tracker — FPS';self.completed=0
        self.fish=0;self.items=0;self.started_at=None;self.ended_at=None
        self.session_stats=tk.StringVar(value='Fish: 0 · Items: 0    ·    Elapsed: 00:00:00')
        ttk.Label(summary,textvariable=self.session_stats,style='Card.TLabel',font=(ui_font,12,'bold')).pack(anchor='w',pady=(8,0))
        notebook=ttk.Notebook(shell);notebook.pack(fill='both',expand=True,pady=16)
        notebook.configure(height=330)
        def page(label):
            outer=ttk.Frame(notebook);notebook.add(outer,text=label)
            canvas=tk.Canvas(outer,bg=bg,highlightthickness=0)
            scroll=ttk.Scrollbar(outer,orient='vertical',command=canvas.yview)
            canvas.configure(yscrollcommand=scroll.set)
            scroll.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
            inner=ttk.Frame(canvas,padding=16)
            item=canvas.create_window((0,0),window=inner,anchor='nw')
            inner.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
            canvas.bind('<Configure>',lambda e:canvas.itemconfigure(item,width=e.width))
            def wheel(e):
                if canvas.winfo_height() < inner.winfo_reqheight():
                    canvas.yview_scroll(-1 if e.delta > 0 else 1,'units')
            # Bind only when the pointer is over this page; leave other windows alone.
            outer.bind('<Enter>',lambda e:canvas.bind_all('<MouseWheel>',wheel))
            outer.bind('<Leave>',lambda e:canvas.unbind_all('<MouseWheel>'))
            return inner
        simple=page('Simple')
        advanced=page('Advanced')
        def fields(parent,items):
            panel=ttk.Frame(parent);panel.pack(fill='x',pady=(6,12))
            for i,(key,label) in enumerate(items):
                row,col=divmod(i,2);col*=2
                ttk.Label(panel,text=label).grid(row=row,column=col,sticky='w',padx=(0,12),pady=6)
                ttk.Entry(panel,textvariable=self.vars[key],width=10).grid(row=row,column=col+1,sticky='ew',padx=(0,18),pady=6)
            panel.columnconfigure(1,weight=1);panel.columnconfigure(3,weight=1)
        def toggle(parent,key,label):
            ttk.Checkbutton(parent,text=label,variable=self.vars[key]).pack(anchor='w')
        ttk.Label(simple,text='CAST POINT',style='Muted.TLabel').pack(anchor='w')
        fields(simple,[('cast_x','Screen X'),('cast_y','Screen Y')])
        ttk.Button(simple,text='Pick bait position · click to select',command=self.pick_cast).pack(fill='x')
        ttk.Label(simple,text='Click Pick, then click either bait icon. Escape cancels.',style='Muted.TLabel').pack(anchor='w',pady=(7,14))
        fields(simple,[('cycles','Cycle limit'),('minutes','Time limit (min)')])
        toggle(simple,'no_time_limit','No time limit — run until stopped')
        toggle(simple,'unlimited_cycles','Unlimited cycles')
        toggle(simple,'dry_run','Dry run — observe without sending input')
        toggle(simple,'auto_cast','Automatically cast at my saved point')
        toggle(simple,'repeat','Take fish and repeat')
        ttk.Label(simple,text='1920 × 1080 · maximum zoom · keep the game focused',style='Muted.TLabel').pack(anchor='w',pady=(14,0))
        ttk.Label(advanced,text='TRACKING',style='Muted.TLabel').pack(anchor='w')
        fields(advanced,[('tracker_hz','Target refresh (Hz)'),('deadband','Center tolerance (px)'),('countdown','Start delay (s)'),('cooldown','Recast delay (s)'),('visual_timeout','Strike timeout (s)')])
        toggle(advanced,'wait_for_strike','Wait for STRIKE without a bite timeout')
        ttk.Label(advanced,text='60 Hz default · 15–120 Hz supported. Actual FPS depends on your PC.\nLower center tolerance starts corrections sooner; it does not change game speed.',style='Muted.TLabel',wraplength=650).pack(anchor='w')
        ttk.Label(advanced,text='APPEARANCE',style='Muted.TLabel').pack(anchor='w',pady=(18,8))
        ttk.Label(advanced,text='Window opacity · 85% to 100%',style='Muted.TLabel').pack(anchor='w')
        ttk.Scale(advanced,from_=85,to=100,variable=self.vars['opacity'],command=self.apply_opacity).pack(fill='x',pady=8)
        ttk.Label(advanced,text='TRACKING MODE',style='Muted.TLabel').pack(anchor='w',pady=(16,8))
        toggle(advanced,'visual','Visual tracking (Windows)')
        toggle(advanced,'pixel','Pixel bite trigger (when visual tracking is off)')
        fields(advanced,[('cast','Timed cast action'),('reel','Timed reel action'),('hold','Input hold (s)'),('bite_wait','Timed bite wait (s)'),('x','Bite pixel X'),('y','Bite pixel Y'),('color','Bite color'),('tolerance','Color tolerance')])
        ttk.Button(advanced,text='Sample bite pixel · 3 seconds',command=self.sample).pack(anchor='w')
        ttk.Label(advanced,text='Actions: space, enter, letters, digits, arrows, mouse:left/right.\nmacOS uses timed/pixel mode; grant Accessibility and Screen Recording access.',style='Muted.TLabel',wraplength=640).pack(anchor='w',pady=10)
        actions=ttk.Frame(shell);actions.pack(fill='x')
        self.start_button=ttk.Button(actions,text='Start session',style='Accent.TButton',command=self.start)
        self.start_button.pack(side='left',fill='x',expand=True)
        ttk.Button(actions,text='Stop · F8',style='Stop.TButton',command=self.stop).pack(side='left',padx=(10,0))
        utilities=ttk.Frame(shell);utilities.pack(fill='x',pady=10)
        for title,fn in [('Load profile',self.load),('Save profile',self.save),('Export log',self.export)]:
            ttk.Button(utilities,text=title,command=fn).pack(side='left',padx=(0,8))
        self.log=tk.Text(shell,height=4,bg='#090e18',fg=muted,font=('Consolas' if sys.platform == 'win32' else 'Courier',9),state='disabled',relief='flat',highlightthickness=0,padx=10,pady=8,wrap='word')
        self.log.pack(fill='x')
        ttk.Label(shell,text='F8 stops globally · Escape stops while this window is focused',style='Muted.TLabel',font=(ui_font,9)).pack(anchor='w',pady=(8,0))
        root.bind('<Escape>',lambda e:self.stop())
        root.protocol('WM_DELETE_WINDOW',self.close)
        root.after(100,self.poll)

    def apply_opacity(self, value=None):
        try:
            self.root.attributes('-alpha',float(self.vars['opacity'].get())/100)
        except (tk.TclError,ValueError):
            pass

    def profile(self):
        values = {k:v.get() for k,v in self.vars.items()}
        for key in ('hold','countdown','bite_wait','cooldown','minutes','visual_timeout','deadband','opacity'):
            values[key] = float(values[key])
        for key in ('cycles','x','y','tolerance','cast_x','cast_y','tracker_hz'):
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
                backend.PAUSE = 0 if p.visual else .03
                if p.pixel and not p.visual:
                    if not backend.onScreen(p.x, p.y):
                        raise ValueError('Bite pixel must be on the primary display')
                    backend.pixel(p.x, p.y)  # Check screen access before countdown.
                self.listener = keyboard.Listener(on_press=lambda key: self.stop_event.set() if key == keyboard.Key.f8 else None)
                self.listener.start()
            self.completed=0
            self.fish=0;self.items=0;self.started_at=time.monotonic();self.ended_at=None
            self.last_metrics='Tracker — FPS'
            self.metrics.set('Tracker — FPS   |   0 completed cycles')
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
        for _ in range(150):
            if self.queue.empty():
                break
            kind, message = self.queue.get_nowait()
            if kind == 'metrics':
                self.last_metrics=message
                self.metrics.set(f'{message}   |   {self.completed} cycles')
                continue
            if kind == 'item':
                self.items=int(message)
            if kind == 'fish':
                self.fish=int(message)
            if kind == 'cycle':
                self.completed=int(message)
                self.metrics.set(f'{self.last_metrics}   |   {self.completed} cycles')
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
                self.ended_at=time.monotonic()
                self.status.set(f'Stopped · {message} cycles completed (see log for mode)')
                self.start_button.configure(state='normal')
                if self.listener:
                    self.listener.stop()
                    self.listener = None
        elapsed = int(((self.ended_at if self.ended_at is not None else time.monotonic()) - self.started_at)) if self.started_at is not None else 0
        h,rem=divmod(max(0,elapsed),3600);m,sec=divmod(rem,60)
        self.session_stats.set(f'Fish: {self.fish} · Items: {self.items}    ·    Elapsed: {h:02d}:{m:02d}:{sec:02d}')
        self.root.after(100, self.poll)

    def pick_cast(self):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo('Stop first','Stop the session before selecting a cast point.')
            return
        if getattr(self,'picker',None) is not None:
            return
        self.root.withdraw()
        overlay=tk.Toplevel(self.root)
        self.picker=overlay
        overlay.overrideredirect(True)
        overlay.geometry('1920x1080+0+0')
        overlay.configure(bg='#101c2a',cursor='crosshair')
        overlay.attributes('-topmost',True)
        try:
            overlay.attributes('-alpha',.25)
        except tk.TclError:
            self.cancel_pick()
            messagebox.showerror('Picker unavailable','Transparency is unavailable. Enter X/Y manually.')
            return
        tk.Label(overlay,text='Click a bait icon to save its position · Escape to cancel',bg='#101c2a',fg='white',font=('Arial',18)).pack(pady=24)
        overlay.bind('<Button-1>',self.select_cast)
        overlay.bind('<Escape>',lambda e:self.cancel_pick())
        overlay.bind('<F8>',lambda e:self.cancel_pick())
        overlay.bind('<Button-3>',lambda e:self.cancel_pick())
        overlay.update()
        overlay.focus_force()

    def cancel_pick(self):
        picker=getattr(self,'picker',None)
        self.picker=None
        if picker is not None:
            picker.destroy()
        self.root.deiconify()

    def select_cast(self,event):
        x,y=event.x_root,event.y_root
        if 0 <= x < 1920 and 0 <= y < 1080:
            self.vars['cast_x'].set(str(x))
            self.vars['cast_y'].set(str(y))
            self.status.set(f'Cast point saved: ({x}, {y}) — Save profile to keep it')
        self.cancel_pick()

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
            self.apply_opacity()
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
    import sys
    if sys.platform == 'win32':
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            pass
    root = tk.Tk()
    app = App(root)
    import sys
    if '--smoke-test' in sys.argv:
        import pyautogui
        from vision import Detector
        from screen_capture import FastCapture
        Detector()
        capture=FastCapture(check_resolution=False)
        capture.grab()
        capture.close()
        from pynput import keyboard, mouse
        root.update()
        app.vars['cast_x'].set('1185')
        app.vars['cast_y'].set('755')
        app.vars['tracker_hz'].set('120')
        assert app.profile().tracker_hz == 120
        app.vars['opacity'].set('90')
        app.apply_opacity()
        root.update()
        if sys.platform == 'win32':
            assert abs(root.attributes('-alpha') - .9) < .02
        root.destroy()
    else:
        root.mainloop()
