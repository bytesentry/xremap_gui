import os
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import yaml
import json
import re

CONFIG_DIR = "/home/b/.config/xremap_gui"
PROFILES_DIR = f"{CONFIG_DIR}/profiles"
DEVICES_FILE = f"{CONFIG_DIR}/devices.json"
LAST_PROFILE_FILE = f"{CONFIG_DIR}/last_profile.txt"

for directory in [CONFIG_DIR, PROFILES_DIR]:
    os.makedirs(directory, exist_ok=True)

def list_user_input_devices():
    try:
        output = subprocess.check_output(["libinput", "list-devices"], text=True)
        devices = []
        current_device = {}
        event_suffix_counter = {}
        def should_include(name, caps):
            name_lower = name.lower()
            if "keyboard" in caps or "key" in caps:
                return any(x in name_lower for x in ["keyboard", "key", "logitech"])
            if "pointer" in caps:
                return any(x in name_lower for x in ["mouse", "trackball", "touchpad", "logitech"])
            if "touch" in caps or "tablet" in caps:
                return "controller" in name_lower
            return False
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("Device:"):
                if current_device.get("include") and "name" in current_device and "event" in current_device:
                    base_name = current_device["name"]
                    event = current_device["event"]
                    count = event_suffix_counter.get(base_name, 0)
                    suffix = f" ({event})" if count == 0 else f" ({event}, #{count})"
                    current_device["display_name"] = base_name + suffix
                    event_suffix_counter[base_name] = count + 1
                    devices.append(current_device)
                current_device = {"name": line.split(":", 1)[1].strip(), "include": False}
            elif line.startswith("Capabilities:"):
                caps = line.split(":", 1)[1].strip().lower()
                if should_include(current_device["name"], caps):
                    current_device["include"] = True
            elif line.startswith("Kernel:"):
                parts = line.split()
                for p in parts:
                    if p.startswith("/dev/input/event"):
                        current_device["event"] = p.split("/")[-1]
        if current_device.get("include") and "name" in current_device and "event" in current_device:
            base_name = current_device["name"]
            event = current_device["event"]
            count = event_suffix_counter.get(base_name, 0)
            suffix = f" ({event})" if count == 0 else f" ({event}, #{count})"
            current_device["display_name"] = base_name + suffix
            devices.append(current_device)
        return devices
    except subprocess.SubprocessError:
        return []

class KeyRemap:
    def __init__(self, parent, row, from_key="", to_key="", on_remove=None):
        self.from_key = tk.StringVar(value=from_key)
        self.to_key = tk.StringVar(value=to_key)
        self.row = row
        self.on_remove = on_remove
        self.frame = tk.Frame(parent, bg="#2e2e2e")
        self.frame.pack(fill="x", padx=30, pady=4, anchor="center")
        self.from_button = tk.Button(
            self.frame,
            text=from_key,
            width=10,
            fg="white",
            bg="#3c3f41",
            activebackground="#5c5f61",
            command=self.set_from_key
        )
        self.from_button.pack(side="left", padx=5)
        tk.Label(self.frame, text="→", fg="white", bg="#2e2e2e").pack(side="left", padx=5)

        self.to_button = tk.Button(
            self.frame,
            text=to_key,
            width=10,
            fg="white",
            bg="#3c3f41",
            activebackground="#5c5f61",
            command=self.set_to_key
        )
        self.to_button.pack(side="left", padx=5)

        tk.Button(self.frame, text="✖", width=1, fg="white", bg="red", command=self.remove).pack(side="left", padx=13)

    def set_from_key(self):
        self._capture_key(self.from_key, self.from_button)

    def set_to_key(self):
        self._capture_key(self.to_key, self.to_button)

    def _capture_key(self, var, button):
        original = var.get() or "key"
        button.config(text="...")
        pressed_modifiers = set()

        def on_key_press(event):
            if event.keysym in ("Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Meta_L", "Meta_R"):
                pressed_modifiers.add(event.keysym)
                return "break"
            mods = []
            if "Control_L" in pressed_modifiers or "Control_R" in pressed_modifiers:
                mods.append("Ctrl")
            if "Alt_L" in pressed_modifiers or "Alt_R" in pressed_modifiers:
                mods.append("Alt")
            if "Shift_L" in pressed_modifiers or "Shift_R" in pressed_modifiers:
                mods.append("Shift")
            if "Meta_L" in pressed_modifiers or "Meta_R" in pressed_modifiers:
                mods.append("Meta")
            combo = "+".join(mods + [event.keysym])
            var.set(combo)
            button.config(text=combo)
            button.unbind("<KeyPress>")
            button.unbind("<KeyRelease>")
            button.bind("<Button-1>", lambda e: None)
            button.bind("<Button-3>", lambda e: None)
            button.unbind("<FocusOut>")
            self.frame.focus_set()
            return "break"

        def on_mouse_click(event):
            mouse_buttons = {1: "Button1", 3: "Button3"}
            if event.num in mouse_buttons:
                mods = []
                if "Control_L" in pressed_modifiers or "Control_R" in pressed_modifiers:
                    mods.append("Ctrl")
                if "Alt_L" in pressed_modifiers or "Alt_R" in pressed_modifiers:
                    mods.append("Alt")
                if "Shift_L" in pressed_modifiers or "Shift_R" in pressed_modifiers:
                    mods.append("Shift")
                if "Meta_L" in pressed_modifiers or "Meta_R" in pressed_modifiers:
                    mods.append("Meta")
                combo = "+".join(mods + [mouse_buttons[event.num]])
                var.set(combo)
                button.config(text=combo)
                button.bind("<Button-1>", lambda e: None)
                button.bind("<Button-3>", lambda e: None)
                button.unbind("<KeyPress>")
                button.unbind("<KeyRelease>")
                button.unbind("<FocusOut>")
                self.frame.focus_set()
                return "break"

        def on_key_release(event):
            pressed_modifiers.clear()

        def on_focus_out(event):
            if not var.get():
                button.config(text=original)
            button.bind("<Button-1>", lambda e: None)
            button.bind("<Button-3>", lambda e: None)
            button.unbind("<KeyPress>")
            button.unbind("<KeyRelease>")
            button.unbind("<FocusOut>")

        button.bind("<KeyPress>", on_key_press)
        button.bind("<KeyRelease>", on_key_release)
        button.bind("<Button-1>", on_mouse_click)
        button.bind("<Button-3>", on_mouse_click)
        button.bind("<FocusOut>", on_focus_out)
        button.focus_set()

    def remove(self):
        if self.on_remove:
            self.on_remove(self)

    def grid_remove(self):
        self.frame.pack_forget()

    def to_dict(self):
        from_key = self.from_key.get().strip()
        to_key = self.to_key.get().strip()
        if not from_key or not to_key:
            return {}
        mouse_buttons = {"Button1": "BTN_LEFT", "Button3": "BTN_RIGHT"}
        mods = {"Ctrl": "C", "Alt": "A", "Shift": "S", "Meta": "M"}
        def format_key(key):
            parts = key.split("+")
            mapped = []
            for part in parts:
                part = part.strip()
                mapped.append(mods.get(part, mouse_buttons.get(part, part.upper())))
            return "-".join(mapped)
        return {format_key(from_key): format_key(to_key)}

class XRemapGUI:
    def __init__(self, root):
        self.root = root
        self.root.configure(bg="#2e2e2e")
        self.root.title("xremap GUI")
        self.remaps = []
        self.device_vars = []
        self.devices = list_user_input_devices()
        self.remap_active = False
        self.xremap_proc = None

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background="#2e2e2e", foreground="white")
        style.configure("TCombobox", padding=(3,0,3,3),fieldbackground="#3c3f41", foreground="white", selectbackground="#3c3f41",
                       borderwidth=1, relief="solid")
        style.map("TCombobox", fieldbackground=[("disabled", "#3c3f41"), ("readonly", "#3c3f41")])
        style.configure("TCheckbutton", background="#2e2e2e", foreground="white")
        style.configure("TLabelframe", background="#2e2e2e", foreground="white")
        style.configure("TLabelframe.Label", background="#2e2e2e", foreground="white")

        self.profile_frame = ttk.Labelframe(root, text="Profile")
        self.profile_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        self.profile_var = tk.StringVar()
        self.profile_combobox = ttk.Combobox(self.profile_frame, textvariable=self.profile_var, width=26, state="normal")
        self.profile_combobox.grid(row=0, column=0, padx=5)
        self.profile_combobox.bind("<<ComboboxSelected>>", lambda e: self.load_profile())
        tk.Button(self.profile_frame, text="Save", fg="white", bg="#3c3f41", width=4, command=self.save_profile).grid(row=0, column=1, padx=2, pady=5)
        tk.Button(self.profile_frame, text="+", fg="white", bg="blue",font=("Arial", 12, "bold"), width=1, command=self.clear_profile).grid(row=0, column=2, padx=2, pady=5)
        tk.Button(self.profile_frame, text="✖", fg="white", bg="red", width=1, command=self.delete_profile).grid(row=0, column=3, padx=2, pady=5)

        self.device_frame = ttk.Labelframe(root, text="Devices")
        self.device_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        for i, dev in enumerate(self.devices):
            var = tk.BooleanVar()
            ttk.Checkbutton(self.device_frame, text=dev.get("display_name", dev["name"]), variable=var).grid(row=i, column=0, sticky="w", padx=(5, 0))
            self.device_vars.append((var, dev["event"]))

        self.keybind_frame = ttk.Labelframe(root, text="Remaps")
        self.keybind_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        self.key_frame_container, self.key_frame = self.create_scrollable_frame(self.keybind_frame)
        self.key_frame_container.pack(fill="both", expand=True)
        self.button_frame = ttk.Frame(self.keybind_frame)
        self.button_frame.pack(fill="x", padx=10, pady=10, anchor="w")
        tk.Button(self.button_frame, text="+", fg="white", bg="blue", font=("Arial", 12, "bold"), width=1, command=self.add_remap).pack(side="left")

        self.scope_frame = ttk.Frame(root)
        self.scope_frame.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.scope_var = tk.BooleanVar()
        ttk.Checkbutton(self.scope_frame, text="App Specific", variable=self.scope_var,
                       command=self.update_dropdown_state).pack(side="left")
        self.app_var = tk.StringVar()
        self.app_combobox = ttk.Combobox(self.scope_frame, textvariable=self.app_var, width=33, state="disabled")
        self.app_combobox.pack(side="left", padx=5)
        self.populate_wm_classes()

        self.toggle_button = tk.Button(root, text="Start Remap", fg="white", bg="green", command=self.toggle_remap)
        self.toggle_button.grid(row=4, column=0, pady=10)

        self.load_profiles()
        if (last_profile := load_last_profile()) and last_profile in self.profile_combobox["values"]:
            self.profile_var.set(last_profile)
            self.load_profile()

        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_scrollable_frame(self, parent):
        container = tk.Frame(parent, bg="#2e2e2e")
        canvas = tk.Canvas(container, bg="#2e2e2e", highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#2e2e2e")
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        def on_mouse_wheel(event):
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")
        canvas.bind_all("<Button-4>", on_mouse_wheel)
        canvas.bind_all("<Button-5>", on_mouse_wheel)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return container, scrollable_frame

    def populate_wm_classes(self):
        try:
            output = subprocess.check_output(["wmctrl", "-l"]).decode()
            classes = set()
            for line in output.splitlines():
                if line.strip():
                    try:
                        win_id = line.split()[0]
                        xprop = subprocess.check_output(["xprop", "-id", win_id, "WM_CLASS"]).decode()
                        match = re.search(r'WM_CLASS.*?= "([^"]+)", "([^"]+)"', xprop)
                        if match:
                            classes.add(f"{match.group(1)}.{match.group(2)}")
                    except subprocess.SubprocessError:
                        continue
            self.app_combobox["values"] = sorted(classes)
        except subprocess.SubprocessError:
            self.app_combobox["values"] = []

    def load_profiles(self):
        profiles = {}
        if os.path.exists(PROFILES_DIR):
            for f in os.listdir(PROFILES_DIR):
                if f.endswith(".yml"):
                    profiles[f[:-4]] = {}
        self.profile_combobox["values"] = sorted(profiles.keys()) or [""]
        return profiles

    def load_profile(self):
        name = self.profile_var.get().strip()
        if not name:
            return
        try:
            with open(f"{PROFILES_DIR}/{name}.yml", "r") as f:
                profile = yaml.safe_load(f)
            for r in self.remaps[:]:
                self.remove_remap(r)
            keymap = profile.get("keymap", [{}])[0]
            for from_key, to_key in keymap.get("remap", {}).items():
                if isinstance(to_key, list):
                    for tk in to_key:
                        self.add_remap(from_key, tk)
                else:
                    self.add_remap(from_key, to_key)
            devices = []
            try:
                if os.path.exists(DEVICES_FILE):
                    with open(DEVICES_FILE, "r") as f:
                        devices = json.load(f).get(name, [])
            except (IOError, json.JSONDecodeError):
                pass
            for var, dev in self.device_vars:
                var.set(dev in devices)
            app = keymap.get("application", {}).get("only", "")
            self.scope_var.set(bool(app))
            self.app_var.set(app)
            self.update_dropdown_state()
            with open(LAST_PROFILE_FILE, "w") as f:
                f.write(name)
        except (IOError, yaml.YAMLError):
            pass

    def save_profile(self):
        name = self.profile_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Profile name cannot be empty.")
            return
        profile = {"keymap": [{"name": name}]}
        keymap = profile["keymap"][0]
        if self.scope_var.get() and self.app_var.get().strip():
            keymap["application"] = {"only": self.app_var.get().strip()}
        remap_dict = {}
        for r in self.remaps:
            remap = r.to_dict()
            if remap:
                from_key, to_key = next(iter(remap.items()))
                if from_key in remap_dict:
                    if isinstance(remap_dict[from_key], str):
                        remap_dict[from_key] = [remap_dict[from_key]]
                    remap_dict[from_key].append(to_key)
                else:
                    remap_dict[from_key] = to_key
        keymap["remap"] = remap_dict
        devices = [dev for var, dev in self.device_vars if var.get()]
        try:
            with open(f"{PROFILES_DIR}/{name}.yml", "w") as f:
                yaml.safe_dump(profile, f, default_flow_style=False)
            devices_data = {}
            if os.path.exists(DEVICES_FILE):
                with open(DEVICES_FILE, "r") as f:
                    devices_data = json.load(f)
            devices_data[name] = devices
            os.makedirs(os.path.dirname(DEVICES_FILE), exist_ok=True)
            with open(DEVICES_FILE, "w") as f:
                json.dump(devices_data, f, indent=2)
            self.profile_combobox["values"] = sorted(self.load_profiles().keys())
            with open(LAST_PROFILE_FILE, "w") as f:
                f.write(name)
            messagebox.showinfo("Saved", f"Profile '{name}' saved.")
        except (IOError, json.JSONDecodeError) as e:
            messagebox.showerror("Error", f"Failed to save profile: {e}")

    def delete_profile(self):
        name = self.profile_var.get().strip()
        if not name:
            messagebox.showerror("Error", "No profile selected.")
            return
        if not messagebox.askyesno("Delete Profile", f"Delete profile '{name}'?"):
            return
        try:
            os.remove(f"{PROFILES_DIR}/{name}.yml")
            devices_data = {}
            if os.path.exists(DEVICES_FILE):
                with open(DEVICES_FILE, "r") as f:
                    devices_data = json.load(f)
                if name in devices_data:
                    del devices_data[name]
                    with open(DEVICES_FILE, "w") as f:
                        json.dump(devices_data, f, indent=2)
            self.profile_combobox["values"] = sorted(self.load_profiles().keys()) or [""]
            self.profile_var.set("")
            self.clear_profile()
            messagebox.showinfo("Deleted", f"Profile '{name}' deleted.")
        except (IOError, json.JSONDecodeError) as e:
            messagebox.showerror("Error", f"Failed to delete profile: {e}")

    def clear_profile(self):
        for var, _ in self.device_vars:
            var.set(False)
        for r in self.remaps[:]:
            self.remove_remap(r)
        self.profile_var.set("")
        self.app_var.set("")
        self.scope_var.set(False)
        self.update_dropdown_state()

    def add_remap(self, from_key="", to_key=""):
        remap = KeyRemap(self.key_frame, len(self.remaps), from_key, to_key, self.remove_remap)
        self.remaps.append(remap)

    def remove_remap(self, remap):
        remap.grid_remove()
        self.remaps.remove(remap)

    def update_dropdown_state(self):
        self.app_combobox.configure(state="readonly" if self.scope_var.get() else "disabled")

    def start_remap(self):
        if self.remap_active:
            return
        self.toggle_button.config(text="...")
        self.root.update()
        name = self.profile_var.get().strip()
        if not name:
            self.toggle_button.config(text="Start Remap")
            messagebox.showerror("Error", "No profile selected.")
            return
        profiles = self.load_profiles()
        if name not in profiles:
            self.toggle_button.config(text="Start Remap")
            messagebox.showerror("Error", f"Profile '{name}' not found.")
            return
        devices = []
        try:
            if os.path.exists(DEVICES_FILE):
                with open(DEVICES_FILE, "r") as f:
                    devices = json.load(f).get(name, [])
        except (IOError, json.JSONDecodeError):
            pass
        if not devices:
            self.toggle_button.config(text="Start Remap")
            messagebox.showerror("Error", "No devices selected.")
            return
        valid_devices = [f"/dev/input/{dev}" for dev in devices if os.path.exists(f"/dev/input/{dev}") and os.access(f"/dev/input/{dev}", os.R_OK | os.W_OK)]
        if not valid_devices:
            self.toggle_button.config(text="Start Remap")
            messagebox.showerror("Error", "No valid devices found. Ensure you are in the 'input' group.")
            return
        try:
            cmd = ["xremap", f"{PROFILES_DIR}/{name}.yml"] + [arg for dev in valid_devices for arg in ["--device", dev]]
            self.xremap_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            self.remap_active = True
            self.toggle_button.config(text="Stop Remap")
        except subprocess.SubprocessError as e:
            self.toggle_button.config(text="Start Remap")
            messagebox.showerror("Error", f"Failed to start xremap: {e}")

    def stop_remap(self):
        if self.remap_active and self.xremap_proc:
            self.toggle_button.config(text="...")
            self.root.update()
            self.xremap_proc.terminate()
            try:
                self.xremap_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.xremap_proc.kill()
            self.xremap_proc = None
            self.remap_active = False
            self.toggle_button.config(text="Start Remap")

    def toggle_remap(self):
        if self.remap_active:
            self.stop_remap()
        else:
            self.start_remap()

    def on_closing(self):
        self.stop_remap()
        self.root.destroy()

def load_last_profile():
    try:
        if os.path.exists(LAST_PROFILE_FILE):
            with open(LAST_PROFILE_FILE, "r") as f:
                return f.read().strip()
    except IOError:
        pass
    return ""

if __name__ == "__main__":
    root = tk.Tk()
    app = XRemapGUI(root)
    root.mainloop()