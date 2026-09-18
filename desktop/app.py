"""Windows desktop installer entry point; also hosts the isolated esptool worker."""
import json
import os
from pathlib import Path
import queue
import shutil
import sys
import tempfile
import threading
import traceback

ROOT = Path(__file__).resolve().parents[1]
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(ROOT / 'tools'))


def esptool_worker():
    # A windowed frozen process still receives redirected pipe handles from Popen.
    if sys.stdout is None: sys.stdout = os.fdopen(1, 'w', encoding='utf-8', buffering=1, closefd=False)
    if sys.stderr is None: sys.stderr = os.fdopen(2, 'w', encoding='utf-8', buffering=1, closefd=False)
    import esptool
    try:
        esptool.main(sys.argv[2:])
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


def gui(self_test=None):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    import backend

    class Installer(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title('AI Passport · 课程表安装助手')
            self.geometry('1120x800'); self.minsize(960, 720)
            self.configure(bg='#f1f5f8')
            self.events = []; self.busy = False; self.messages = queue.Queue()
            self.port_values = {}; self.controls = []
            self.protocol('WM_DELETE_WINDOW', self.close)
            style = ttk.Style(self); style.theme_use('clam')
            style.configure('.', font=('Microsoft YaHei UI', 10), background='#f1f5f8')
            style.configure('TButton', padding=(10, 6), background='#e6edf1', borderwidth=0)
            style.map('TButton', background=[('active', '#dce7ec')])
            style.configure('Primary.TButton', background='#087f8c', foreground='white', font=('Microsoft YaHei UI', 11, 'bold'))
            style.map('Primary.TButton', background=[('disabled', '#c4d4d8'), ('active', '#066c77')])
            style.configure('Treeview', background='white', fieldbackground='white', rowheight=34, borderwidth=0)
            style.configure('Treeview.Heading', background='#eaf1f5', padding=8, font=('Microsoft YaHei UI', 10, 'bold'))
            style.configure('TProgressbar', troughcolor='#dae5eb', background='#087f8c', borderwidth=0)
            header = tk.Frame(self, bg='#142937', padx=28, pady=16); header.pack(fill='x')
            tk.Label(header, text='AI PASSPORT', fg='#62ddd0', bg='#142937', font=('Segoe UI', 10, 'bold')).pack(anchor='w')
            tk.Label(header, text='把你的课程，放进口袋', fg='white', bg='#142937', font=('Microsoft YaHei UI', 20, 'bold')).pack(anchor='w', pady=(5, 3))
            tk.Label(header, text='选择课表 → 连接设备 → 一键安装   ·   无需开发环境，全程本地处理', fg='#b7cad5', bg='#142937', font=('Microsoft YaHei UI', 10)).pack(anchor='w')
            body = tk.Frame(self, bg='#f1f5f8', padx=24, pady=12); body.pack(fill='both', expand=True)
            body.columnconfigure(1, weight=1); body.rowconfigure(0, weight=1)
            sidebar = tk.Frame(body, bg='#f1f5f8'); sidebar.grid(row=0,column=0,sticky='ns',padx=(0,18))
            canvas = tk.Canvas(sidebar,bg='#f1f5f8',width=280,highlightthickness=0)
            side_scroll = ttk.Scrollbar(sidebar,orient='vertical',command=canvas.yview)
            canvas.configure(yscrollcommand=side_scroll.set)
            canvas.pack(side='left',fill='both',expand=True); side_scroll.pack(side='right',fill='y')
            left = tk.Frame(canvas,bg='#f1f5f8')
            item = canvas.create_window((0,0),window=left,anchor='nw',width=280)
            left.bind('<Configure>',lambda _:canvas.configure(scrollregion=canvas.bbox('all')))
            canvas.bind('<Configure>',lambda e:canvas.itemconfigure(item,width=e.width))
            def label(parent, text, size=10, color='#243e4c', **kw):
                widget = tk.Label(parent, text=text, bg='#f1f5f8', fg=color, font=('Microsoft YaHei UI', size), justify='left', anchor='w', **kw)
                widget.pack(fill='x'); return widget
            label(left, '01  选择课程表', 13)
            self.file_label = label(left, '支持 ICS 日历或 UTF-8 CSV 表格', color='#617785', wraplength=265)
            self.choose_button = ttk.Button(left, text='选择课表文件', command=self.choose); self.choose_button.pack(fill='x', pady=(12, 6))
            samples = tk.Frame(left,bg='#f1f5f8'); samples.pack(fill='x',pady=(2,16))
            self.sample_button = ttk.Button(samples, text='虚构示例', command=lambda: self.load(backend.resource_dir() / 'example.ics')); self.sample_button.pack(side='left',fill='x',expand=True,padx=(0,5))
            self.template_button = ttk.Button(samples, text='保存模板', command=self.save_template); self.template_button.pack(side='right',fill='x',expand=True)
            label(left, '02  连接 AI Passport', 13)
            label(left, '使用 USB 数据线，并保持设备开机。', color='#617785', wraplength=265)
            self.port = tk.StringVar()
            self.port_box = ttk.Combobox(left, textvariable=self.port, state='readonly', width=29); self.port_box.pack(fill='x', pady=(12, 6))
            self.port_box.bind('<<ComboboxSelected>>', lambda _: self.update_buttons())
            self.refresh_button = ttk.Button(left, text='刷新设备', command=self.refresh); self.refresh_button.pack(fill='x', pady=(0, 20))
            label(left, '03  安装与校时', 13)
            label(left, '保留兼容的原厂分区。安装期间请勿拔线或关闭程序。', color='#617785', wraplength=265)
            self.install_button = ttk.Button(left, text='一键安装课程表', style='Primary.TButton', command=self.install); self.install_button.pack(fill='x', pady=(12, 6))
            self.sync_button = ttk.Button(left, text='仅同步时间', command=self.sync); self.sync_button.pack(fill='x', pady=4)
            right = tk.Frame(body, bg='#f1f5f8'); right.grid(row=0, column=1, sticky='nsew')
            self.summary = label(right, '课程预览', 14)
            self.subtitle = label(right, '请先选择一个课表文件。你的课表不会上传到网络。', color='#617785')
            table = ttk.Frame(right); table.pack(fill='both', expand=True, pady=(12, 0))
            columns = ('date', 'time', 'name', 'location')
            self.table = ttk.Treeview(table, columns=columns, show='headings', selectmode='browse')
            for key, name, width in [('date', '日期', 100), ('time', '时间', 110), ('name', '课程', 210), ('location', '地点', 150)]:
                self.table.heading(key, text=name); self.table.column(key, width=width, minwidth=70, stretch=key in ('name', 'location'))
            scroll = ttk.Scrollbar(table, orient='vertical', command=self.table.yview)
            self.table.configure(yscrollcommand=scroll.set)
            self.table.pack(side='left', fill='both', expand=True); scroll.pack(side='right', fill='y')
            self.table.bind('<<TreeviewSelect>>', self.details)
            self.detail = label(right, '选择课程可查看完整地点与备注。', size=9, color='#617785', wraplength=700)
            self.detail.pack_configure(pady=(7, 0))
            footer = tk.Frame(self, bg='#e7eef3', padx=24, pady=10); footer.pack(fill='x')
            self.state_text = tk.StringVar(value='准备就绪 · 请先选择课表并连接设备')
            tk.Label(footer, textvariable=self.state_text, bg='#e7eef3', fg='#243e4c', font=('Microsoft YaHei UI', 10)).pack(anchor='w')
            self.bar = ttk.Progressbar(footer, maximum=100); self.bar.pack(fill='x', pady=(8, 10))
            self.log = tk.Text(footer, height=4, bg='#142937', fg='#c9e0e8', font=('Consolas', 9), relief='flat', padx=10, pady=8, state='disabled')
            self.log.pack(fill='x')
            self.controls = [self.choose_button, self.sample_button, self.template_button, self.refresh_button]
            self.refresh(); self.after(100, self.drain)

        def write_log(self, text):
            self.log.configure(state='normal'); self.log.insert('end', text + '\n'); self.log.see('end'); self.log.configure(state='disabled')

        def update_buttons(self):
            selected = self.port.get() in self.port_values
            self.install_button.configure(state='normal' if self.events and selected and not self.busy else 'disabled')
            self.sync_button.configure(state='normal' if selected and not self.busy else 'disabled')
            self.port_box.configure(state='disabled' if self.busy else 'readonly')
            for widget in self.controls: widget.configure(state='disabled' if self.busy else 'normal')

        def refresh(self):
            devices = backend.ports(); previous = self.port.get()
            self.port_values = {f'{port}  ·  {"AI Passport / ESP32" if match else description}': port for port, description, match in devices}
            self.port_box.configure(values=list(self.port_values))
            matches = [key for key, value in self.port_values.items() if any(p == value and match for p, _, match in devices)]
            if previous in self.port_values: self.port.set(previous)
            elif len(matches) == 1: self.port.set(matches[0])
            else: self.port.set('')
            if not devices: self.state_text.set('未检测到串口 · 请接好 USB 数据线，唤醒设备后点击“刷新设备”')
            self.update_buttons()

        def choose(self):
            name = filedialog.askopenfilename(title='选择课表', filetypes=[('课表文件', '*.ics *.csv'), ('ICS 日历', '*.ics'), ('CSV 表格', '*.csv')])
            if name: self.load(Path(name))

        def load(self, path):
            try:
                events = backend.read_calendar(path)
                if len(events) > 1024: raise ValueError('当前版本最多支持 1024 次课程')
            except Exception as exc:
                messagebox.showerror('无法导入课表', str(exc) + '\n\n循环规则需先展开，也可以使用 CSV 模板，每行填写一次课程。'); return
            self.events = events; self.file_label.configure(text=path.name)
            for item in self.table.get_children(): self.table.delete(item)
            for i, event in enumerate(events):
                time_label = lambda t: f'{t//60:02d}:{t%60:02d}'
                self.table.insert('', 'end', iid=str(i), values=(event['date'], time_label(event['start']) + '–' + time_label(event['end']), event['name'], event['location']))
            self.summary.configure(text=f'{len({e["name"] for e in events})} 门课程  ·  {len(events)} 次上课')
            self.subtitle.configure(text=f'{events[0]["date"]} — {events[-1]["date"]}   ·   北京时间 UTC+8')
            self.detail.configure(text='选择课程可查看完整地点与备注。')
            self.state_text.set('课表已导入 · 请核对预览，选择设备后点击“一键安装课程表”')
            self.bar['value'] = 0; self.update_buttons()

        def details(self, _):
            selection = self.table.selection()
            if selection:
                e = self.events[int(selection[0])]
                self.detail.configure(text=f'{e["name"]} ｜ {e["location"]}\n{e["description"]}'[:700])

        def save_template(self):
            target = filedialog.asksaveasfilename(title='保存虚构示例模板', defaultextension='.csv', initialfile='我的课表模板.csv', filetypes=[('UTF-8 CSV', '*.csv')])
            if target:
                # BOM lets Excel correctly detect UTF-8 Chinese text.
                try:
                    text = (backend.resource_dir() / 'example.csv').read_text(encoding='utf-8-sig')
                    Path(target).write_text(text, encoding='utf-8-sig')
                except OSError as exc:
                    messagebox.showerror('模板未保存', str(exc)); return
                self.state_text.set('模板已保存 · 每行填写一次课，完成后重新选择该文件')

        def start(self, operation):
            self.busy = True; self.update_buttons(); self.bar['value'] = 0
            def worker():
                try:
                    operation()
                    self.messages.put(('done', '操作完成，设备已确认校时成功。'))
                except Exception as exc: self.messages.put(('error', str(exc)))
            threading.Thread(target=worker, daemon=True).start()

        def install(self):
            events = list(self.events); port = self.port_values[self.port.get()]
            self.start(lambda: backend.install(events, port,
                lambda value, text: self.messages.put(('progress', (value, text))),
                lambda text: self.messages.put(('log', text))))

        def sync(self):
            port = self.port_values[self.port.get()]
            self.state_text.set('正在连接课程表并同步电脑时间…')
            self.start(lambda: backend.synchronize(port))

        def drain(self):
            while not self.messages.empty():
                kind, value = self.messages.get_nowait()
                if kind == 'progress': self.bar['value'] = value[0]; self.state_text.set(value[1])
                elif kind == 'log': self.write_log(value)
                else:
                    self.busy = False; self.update_buttons()
                    self.state_text.set(value); self.write_log(value)
                    if kind == 'done': self.bar['value'] = 100
                    else: messagebox.showerror('操作未完成', value)
            self.after(100, self.drain)

        def close(self):
            if self.busy:
                messagebox.showinfo('设备操作进行中', '请等待操作完成再关闭，避免中断烧录。'); return
            self.destroy()

    app = Installer()
    if self_test:
        app.attributes('-alpha', 0.0)
        report = {'resources': False, 'personalization': False, 'gui': False, 'worker': False}
        try:
            backend.verify_resources(backend.resource_dir()); report['resources'] = True
            app.load(backend.resource_dir() / 'example.ics')
            app.update_idletasks()
            app.update()
            report['layout'] = {'window': [app.winfo_width(), app.winfo_height()],
                                'requested': [app.winfo_reqwidth(), app.winfo_reqheight()],
                                'install_button_bottom': app.install_button.winfo_rooty() + app.install_button.winfo_height(),
                                'sync_button_bottom': app.sync_button.winfo_rooty() + app.sync_button.winfo_height(),
                                'status_top': app.bar.winfo_rooty()}
            assert len(app.table.get_children()) == 3
            assert str(app.install_button['state']) == 'disabled' or bool(app.port.get())
            report['gui'] = True
            with tempfile.TemporaryDirectory() as tmp: backend.prepare(app.events, tmp)
            report['personalization'] = True
            # esptool's version operation does not connect to the supplied port.
            output=backend.run_esptool('SELF_TEST_NO_DEVICE',['version'],lambda _:None)
            assert '4.12.0' in output
            report['worker'] = True
        except Exception: report['error'] = traceback.format_exc()
        finally:
            Path(self_test).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            app.destroy()
        return 0 if all(report.get(k) for k in ('resources', 'personalization', 'gui', 'worker')) else 1
    app.mainloop()
    return 0


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--esptool': sys.exit(esptool_worker())
    sys.exit(gui(sys.argv[2] if len(sys.argv) == 3 and sys.argv[1] == '--self-test' else None))
