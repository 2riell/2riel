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
        defaults.visual = sys.platform in ('win32','darwin')
        self.vars = {k:(tk.BooleanVar(value=v) if isinstance(v,bool) else tk.StringVar(value=str(v))) for k,v in defaults.dict().items()}
        ui_font = 'Segoe UI' if sys.platform == 'win32' else 'Helvetica'
        bg,card,text,muted,accent = '#111416','#1b2023','#edf1f2','#929da3','#58d9df'
        root.geometry('820x780')
        root.minsize(780,740)
        root.configure(bg=bg)
        st=ttk.Style();st.theme_use('clam')
        st.configure('.',font=(ui_font,10))
        st.configure('TFrame',background=bg)
        st.configure('Card.TFrame',background=card)
        st.configure('TLabel',background=bg,foreground=text)
        st.configure('Muted.TLabel',foreground=muted)
        st.configure('Card.TLabel',background=card,foreground=text)
        st.configure('Small.Card.TLabel',background=card,foreground=muted,font=(ui_font,9))
        st.configure('TCheckbutton',background=card,foreground=text,padding=(0,5))
        st.map('TCheckbutton',background=[('active',card)],indicatorbackground=[('selected',accent),('!selected','#343e44')],indicatorforeground=[('selected',bg)])
        st.configure('TEntry',fieldbackground='#121719',foreground=text,insertcolor=text,padding=7,bordercolor='#343e44',lightcolor='#343e44',darkcolor='#343e44')
        st.configure('TButton',background='#293237',foreground=text,borderwidth=0,padding=(14,9))
        st.map('TButton',background=[('active','#3b484f')],foreground=[('disabled',muted)])
        st.configure('Accent.TButton',background=accent,foreground=bg,font=(ui_font,10,'bold'))
        st.map('Accent.TButton',background=[('active','#8eeaf0'),('disabled','#31494c')])
        st.configure('Stop.TButton',foreground='#ffb1ab')
        st.configure('TNotebook',background=bg,borderwidth=0,bordercolor=bg,lightcolor=bg,darkcolor=bg)
        st.configure('TNotebook.Tab',background=bg,foreground=muted,padding=(22,10),borderwidth=0)
        st.map('TNotebook.Tab',background=[('selected','#25353a')],foreground=[('selected',accent)])
        st.configure('Horizontal.TScale',background=card,troughcolor='#343e44',bordercolor=card)
        st.configure('Vertical.TScrollbar',background='#343e44',troughcolor=bg,arrowcolor=muted,bordercolor=bg,lightcolor=bg,darkcolor=bg)
        shell=ttk.Frame(root,padding=22);shell.pack(fill='both',expand=True)
        header=ttk.Frame(shell);header.pack(fill='x',pady=(0,18))
        mark=tk.Canvas(header,width=38,height=38,bg=bg,highlightthickness=0)
        mark.pack(side='left',padx=(0,12))
        mark.create_oval(2,2,36,36,outline=accent,width=2)
        mark.create_line(23,9,23,23,20,28,14,28,10,24,10,20,fill=accent,width=2,smooth=True)
        brand=ttk.Frame(header);brand.pack(side='left')
        ttk.Label(brand,text='Fishing Lab',font=(ui_font,20,'bold')).pack(anchor='w')
        ttk.Label(brand,text='PIXEL WORLDS',style='Muted.TLabel',font=(ui_font,8)).pack(anchor='w')
        self.run_label=tk.StringVar(value='READY')
        tk.Label(header,textvariable=self.run_label,bg='#23363a',fg=accent,font=(ui_font,9,'bold'),padx=14,pady=7).pack(side='right')
        control=ttk.Frame(shell,style='Card.TFrame',padding=16);control.pack(fill='x')
        actionrow=ttk.Frame(control,style='Card.TFrame');actionrow.pack(fill='x')
        self.start_button=ttk.Button(actionrow,text='Start session',style='Accent.TButton',command=self.start)
        self.start_button.pack(side='left')
        ttk.Button(actionrow,text='Stop  ·  F8',style='Stop.TButton',command=self.stop).pack(side='left',padx=8)
        ttk.Label(actionrow,text='1920 × 1080  /  MAX ZOOM',style='Small.Card.TLabel').pack(side='right')
        self.status=tk.StringVar(value='Ready. Set your cast point, then start a session.')
        ttk.Label(control,textvariable=self.status,style='Card.TLabel',wraplength=700).pack(anchor='w',pady=(12,0))
        self.metrics=tk.StringVar(value='Tracker — FPS   |   0 completed cycles')
        self.last_metrics='Tracker — FPS';self.completed=0
        self.fish=0;self.items=0;self.started_at=None;self.ended_at=None
        self.session_stats=tk.StringVar()
        self.stat_values={key:tk.StringVar(value='00:00:00' if key=='time' else '0') for key in ('fish','items','cycles','time')}
        stats=ttk.Frame(shell);stats.pack(fill='x',pady=12)
        for i,(key,title) in enumerate([('fish','FISH CAUGHT'),('items','ITEMS COLLECTED'),('cycles','CYCLES'),('time','SESSION TIME')]):
            stats.columnconfigure(i,weight=1,uniform='stats')
            box=ttk.Frame(stats,style='Card.TFrame',padding=(14,10));box.grid(row=0,column=i,sticky='nsew',padx=(0,8 if i<3 else 0))
            ttk.Label(box,text=title,style='Small.Card.TLabel',font=(ui_font,8)).pack(anchor='w')
            ttk.Label(box,textvariable=self.stat_values[key],style='Card.TLabel',font=(ui_font,20,'bold')).pack(anchor='w',pady=(3,0))
        navigation=ttk.Frame(shell);navigation.pack(fill='x',pady=(0,2))
        st.layout('TNotebook.Tab',[])
        notebook=ttk.Notebook(shell);notebook.pack(fill='both',expand=True)
        nav_buttons=[]
        for index,label in enumerate(('Simple','Advanced','Session log')):
            button=ttk.Button(navigation,text=label,command=lambda i=index:notebook.select(i))
            button.pack(side='left',padx=(0,6));nav_buttons.append(button)
        def selected_tab(event=None):
            for i,button in enumerate(nav_buttons):
                button.configure(style='Accent.TButton' if notebook.index('current')==i else 'TButton')
        notebook.bind('<<NotebookTabChanged>>',selected_tab)
        def page(label):
            outer=ttk.Frame(notebook);notebook.add(outer,text=label)
            canvas=tk.Canvas(outer,bg=bg,highlightthickness=0)
            scroll=ttk.Scrollbar(outer,orient='vertical',command=canvas.yview)
            canvas.configure(yscrollcommand=scroll.set)
            scroll.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
            inner=ttk.Frame(canvas,padding=(0,14,10,0))
            item=canvas.create_window((0,0),window=inner,anchor='nw')
            inner.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
            canvas.bind('<Configure>',lambda e:canvas.itemconfigure(item,width=e.width))
            def wheel(e):
                if canvas.winfo_height()<inner.winfo_reqheight():
                    canvas.yview_scroll(-1 if e.delta>0 else 1,'units')
            outer.bind('<Enter>',lambda e:canvas.bind_all('<MouseWheel>',wheel))
            outer.bind('<Leave>',lambda e:canvas.unbind_all('<MouseWheel>'))
            return inner
        simple=page('Simple')
        advanced=page('Advanced')
        logpage=ttk.Frame(notebook,padding=(0,14,0,0));notebook.add(logpage,text='Session log')
        def cardbox(parent,title):
            panel=ttk.Frame(parent,style='Card.TFrame',padding=16);panel.pack(fill='x',pady=(0,10))
            ttk.Label(panel,text=title,style='Card.TLabel',font=(ui_font,11,'bold')).pack(anchor='w',pady=(0,8))
            return panel
        def fields(parent,items):
            panel=ttk.Frame(parent,style='Card.TFrame');panel.pack(fill='x',pady=(0,4))
            for i,(key,label) in enumerate(items):
                col=i%2;row=(i//2)*2
                ttk.Label(panel,text=label,style='Small.Card.TLabel').grid(row=row,column=col,sticky='w',pady=(3,4))
                ttk.Entry(panel,textvariable=self.vars[key],width=10).grid(row=row+1,column=col,sticky='ew',padx=(0,10 if col==0 else 0),pady=(0,8))
            panel.columnconfigure(0,weight=1,uniform='fields');panel.columnconfigure(1,weight=1,uniform='fields')
        def toggle(parent,key,label):
            ttk.Checkbutton(parent,text=label,variable=self.vars[key]).pack(anchor='w')
        simple.columnconfigure(0,weight=1,uniform='main');simple.columnconfigure(1,weight=1,uniform='main')
        left=ttk.Frame(simple);left.grid(row=0,column=0,sticky='nsew',padx=(0,10))
        right=ttk.Frame(simple);right.grid(row=0,column=1,sticky='nsew')
        cast=cardbox(left,'Cast position')
        fields(cast,[('cast_x','X coordinate'),('cast_y','Y coordinate')])
        ttk.Button(cast,text='Pick bait position',command=self.pick_cast).pack(fill='x')
        ttk.Label(cast,text='Click Pick, then click a bait icon.\nEscape cancels the selection.',style='Small.Card.TLabel').pack(anchor='w',pady=(9,0))
        mode=cardbox(left,'Automation')
        toggle(mode,'auto_cast','Cast automatically')
        toggle(mode,'repeat','Collect and repeat')
        toggle(mode,'dry_run','Dry run · no game input')
        limits=cardbox(right,'Session limits')
        toggle(limits,'unlimited_cycles','Unlimited cycles')
        toggle(limits,'no_time_limit','No time limit')
        fields(limits,[('cycles','Cycle limit'),('minutes','Time limit (min)')])
        ttk.Label(limits,text='Limits apply when unlimited is off.',style='Small.Card.TLabel').pack(anchor='w')
        prof=cardbox(right,'Profiles')
        buttons=ttk.Frame(prof,style='Card.TFrame');buttons.pack(fill='x')
        ttk.Button(buttons,text='Load',command=self.load).pack(side='left',expand=True,fill='x',padx=(0,8))
        ttk.Button(buttons,text='Save',command=self.save).pack(side='left',expand=True,fill='x')
        ttk.Label(prof,text='Keep your coordinates and settings.',style='Small.Card.TLabel').pack(anchor='w',pady=(10,0))
        track=cardbox(advanced,'Tracking & timing')
        fields(track,[('tracker_hz','Refresh rate (Hz)'),('deadband','Center tolerance (px)'),('countdown','Start delay (s)'),('cooldown','Recast delay (s)'),('visual_timeout','Strike timeout (s)')])
        toggle(track,'chase_lost_fish','Keep chasing when the fish is lost')
        toggle(track,'wait_for_strike','Wait for STRIKE without a bite timeout')
        ttk.Label(track,text='15–120 Hz. Actual FPS depends on your PC.',style='Small.Card.TLabel').pack(anchor='w',pady=(5,0))
        appearance=cardbox(advanced,'Appearance')
        ttk.Label(appearance,text='Window opacity  ·  85–100%',style='Small.Card.TLabel').pack(anchor='w')
        ttk.Scale(appearance,from_=85,to=100,variable=self.vars['opacity'],command=self.apply_opacity).pack(fill='x',pady=8)
        legacy=cardbox(advanced,'Input mode')
        toggle(legacy,'visual','Visual tracking (Windows / Mac)')
        toggle(legacy,'pixel','Pixel bite trigger (visual tracking off)')
        fields(legacy,[('cast','Timed cast action'),('reel','Timed reel action'),('hold','Input hold (s)'),('bite_wait','Timed bite wait (s)'),('x','Bite pixel X'),('y','Bite pixel Y'),('color','Bite color'),('tolerance','Color tolerance')])
        ttk.Button(legacy,text='Sample bite pixel · 3 seconds',command=self.sample).pack(anchor='w')
        ttk.Label(legacy,text='macOS: allow Accessibility and Screen Recording. Use a 1920 × 1080 primary display.',style='Small.Card.TLabel',wraplength=660).pack(anchor='w',pady=(10,0))
        loghead=ttk.Frame(logpage);loghead.pack(fill='x',pady=(0,10))
        ttk.Label(loghead,text='Session activity',font=(ui_font,11,'bold')).pack(side='left')
        ttk.Button(loghead,text='Export CSV',command=self.export).pack(side='right')
        logbody=ttk.Frame(logpage);logbody.pack(fill='both',expand=True)
        self.log=tk.Text(logbody,bg='#0d1012',fg=muted,font=('Consolas' if sys.platform=='win32' else 'Courier',9),state='disabled',relief='flat',highlightthickness=0,padx=12,pady=12,wrap='word',width=1,height=4)
        logscroll=ttk.Scrollbar(logbody,command=self.log.yview);logscroll.pack(side='right',fill='y')
        self.log.configure(yscrollcommand=logscroll.set);self.log.pack(fill='both',expand=True)
        footer=ttk.Frame(shell);footer.pack(fill='x',pady=(12,0))
        ttk.Label(footer,textvariable=self.metrics,style='Muted.TLabel',font=(ui_font,8)).pack(side='left')
        ttk.Label(footer,text='F8 STOP  /  ESC STOP',style='Muted.TLabel',font=(ui_font,8)).pack(side='right')
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
                if sys.platform not in ('win32','darwin'):
                    raise ValueError('Visual assist supports Windows and macOS')
                if sys.platform == 'darwin':
                    from mac_support import check_permissions
                    check_permissions()
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
            self.run_label.set('RUNNING')
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
                self.run_label.set('STOPPED')
                if self.listener:
                    self.listener.stop()
                    self.listener = None
        elapsed = int(((self.ended_at if self.ended_at is not None else time.monotonic()) - self.started_at)) if self.started_at is not None else 0
        h,rem=divmod(max(0,elapsed),3600);m,sec=divmod(rem,60)
        self.session_stats.set(f'Fish: {self.fish} · Items: {self.items}    ·    Elapsed: {h:02d}:{m:02d}:{sec:02d}')
        for key,value in [('fish',self.fish),('items',self.items),('cycles',self.completed),('time',f'{h:02d}:{m:02d}:{sec:02d}')]:
            self.stat_values[key].set(str(value))
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
    if '--smoke-test' in sys.argv or '--gui-smoke-test' in sys.argv:
        import pyautogui
        from vision import Detector
        from screen_capture import FastCapture
        Detector()
        if '--gui-smoke-test' not in sys.argv:
            capture=FastCapture(check_resolution=False)
            capture.grab()
            capture.close()
        if sys.platform == 'darwin':
            import AppKit, Quartz, ApplicationServices
            from mac_support import focused_game
            focused_game()
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
