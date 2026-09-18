import os
from pathlib import Path
from queue import Queue, Empty
import subprocess
import sys
from threading import Thread
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

from .config import Config
from .cache import Cache
from .catalog import location_paths, selected_locations
from .session import Session
from .updates import check_update, download_update
from .version import VERSION


def desktop_config(email, password, directory):
    if not email.strip() or not password:
        raise ValueError("Informe seu e-mail e sua senha.")
    destination = Path(directory).expanduser().resolve()
    return Config(
        base_url="https://secure.d4sign.com.br", vault_id="", vault_uuid="",
        email=email.strip(), password=password, download_dir=destination,
        cache_file=destination / ".d4sign-cache.json", log_file=destination / "d4sign.log",
        headless=True, page_timeout=40, download_timeout=120,
        download_retries=3, retry_delay=2, folder_name_filter=None, include_all_statuses=True,
    )

def resource_path(relative_path: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path

    return Path(__file__).resolve().parent.parent / relative_path

    # Removed redundant return statement
class Desktop:
    def __init__(self, root):
        self.root, self.events = root, Queue()
        self.busy = self.checking = self.closing = False
        self.auto_updating = False
        self.session = self.update = self.pending_installer = None
        self.roots = []
        
        root.title(f"D4Sign • Baixar Assinaturas • {VERSION}")
        root.configure(bg="#203447")
        style = ttk.Style(root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#203447")
        style.configure("TLabelframe", background="#203447", foreground="#efede5")
        style.configure("TLabelframe.Label", background="#203447", foreground="#efede5")
        style.configure("TLabel", background="#203447", foreground="#efede5")
        style.configure("TButton", background="#e94c1f", foreground="#efede5", padding=(10, 6))
        style.map("TButton", background=[("active", "#d8441b"), ("disabled", "#6c777c")])
        style.configure("TCheckbutton", background="#203447", foreground="#efede5")
        style.configure("Treeview", background="#172633", fieldbackground="#172633", foreground="#efede5")
        style.map("Treeview", background=[("selected", "#e94c1f")], foreground=[("selected", "#efede5")])
        root.geometry("850x780")
        icon_path = resource_path("icon/logo.ico")

        if icon_path.exists():
            self.root.iconbitmap(str(icon_path))
        root.minsize(700, 650)
        frame = ttk.Frame(root, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Download de documentos D4Sign", font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(0, 15))
        self.pages = ttk.Frame(frame)
        self.pages.pack(fill="both", expand=True)
        self.login_frame = ttk.LabelFrame(self.pages, text="1. Entre na sua conta", padding=12)
        self.login_frame.pack(fill="x")
        self.login_frame.columnconfigure(1, weight=1)
        self.email = ttk.Entry(self.login_frame)
        self.password = ttk.Entry(self.login_frame, show="*")
        for row, (name, entry) in enumerate([("E-mail", self.email), ("Senha", self.password)]):
            ttk.Label(self.login_frame, text=name).grid(row=row, column=0, padx=(0, 12), pady=5)
            entry.grid(row=row, column=1, sticky="ew", pady=5)
        self.login_button = ttk.Button(self.login_frame, text="Entrar", command=self.login)
        self.login_button.grid(row=2, column=1, sticky="e")
        self.password.bind("<Return>", lambda event: self.login())
        self.selection_frame = ttk.LabelFrame(self.pages, text="2. Escolha o que baixar", padding=12)
        ttk.Label(self.selection_frame, text="Selecione cofres ou pastas. Use Ctrl para selecionar vários itens.").pack(anchor="w")
        tree_frame = ttk.Frame(self.selection_frame)
        tree_frame.pack(fill="both", expand=True, pady=8)
        self.tree = ttk.Treeview(tree_frame, selectmode="extended", show="tree", height=10)
        self.tree.bind('<<TreeviewOpen>>', self.expand)
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.recursive = tk.BooleanVar(value=True)
        recursive = ttk.Checkbutton(self.selection_frame, text="Incluir todas as subpastas dos itens selecionados", variable=self.recursive)
        recursive.pack(anchor="w")
        ttk.Label(self.selection_frame, text="Os nomes e a estrutura das pastas serão mantidos no destino.").pack(anchor="w", pady=4)
        destination = ttk.Frame(self.selection_frame)
        destination.pack(fill="x", pady=8)
        self.destination = ttk.Entry(destination)
        self.destination.insert(0, str(Path.home() / "Downloads" / "D4Sign"))
        Cache(Path(self.destination.get()) / ".d4sign-cache.json")
        self.destination.pack(side="left", fill="x", expand=True)
        browse = ttk.Button(destination, text="Escolher destino…", command=self.browse)
        browse.pack(side="right", padx=(8, 0))
        actions = ttk.Frame(self.selection_frame)
        actions.pack(fill="x")
        self.controls = [self.destination, browse, recursive]
        for label, command in [("Baixar selecionados", self.start), ("Baixar tudo da conta", lambda: self.start(True)),
                               ("Atualizar lista", self.refresh), ("Sair da conta", self.logout)]:
            button = ttk.Button(actions, text=label, command=command)
            button.pack(side="left", padx=(0, 6))
            self.controls.append(button)
        self.cancel_button = ttk.Button(actions, text="Cancelar download", command=self.cancel_download, state="disabled")
        self.cancel_button.pack(side="left", padx=(0, 6))
        self.controls.append(self.cancel_button)
        self.status = tk.StringVar(value="Informe suas credenciais. O navegador ficará oculto e a senha não será salva.")
        ttk.Label(frame, textvariable=self.status, wraplength=780).pack(fill="x", pady=10)
        self.log = ScrolledText(frame, state="disabled", height=7, font=("Consolas", 9))
        self.log.configure(bg="#172633", fg="#efede5", insertbackground="#efede5")
        self.log.pack(fill="both", expand=True)
        updates = ttk.Frame(frame)
        updates.pack(fill="x", pady=(10, 0))
        self.check_button = ttk.Button(updates, text="Verificar atualização", command=self.check)
        self.check_button.pack(side="left")
        self.install_button = ttk.Button(updates, text="Baixar e instalar", command=self.install, state="disabled")
        self.install_button.pack(side="left", padx=8)
        self.update_status = tk.StringVar()
        ttk.Label(frame, textvariable=self.update_status, wraplength=780).pack(fill="x")
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(100, self.poll)
        root.after(500, self.check)

    def set_busy(self, value):
        self.busy = value
        for control in self.controls + [self.email, self.password, self.login_button]:
            control.configure(state="disabled" if value else "normal")
        if hasattr(self, 'cancel_button'):
            self.cancel_button.configure(state="normal" if value and self.session else "disabled")
        self.install_button.configure(state="normal" if self.update and not value and sys.platform == "win32" else "disabled")

    def login(self):
        if self.checking:
            self.status.set("Aguarde a verificação automática de atualizações terminar.")
            return
        if self.busy or self.session:
            return
        try:
            config = desktop_config(self.email.get(), self.password.get(), str(Path.cwd() / "temporary-downloads"))
        except ValueError as exc:
            messagebox.showerror("Login", str(exc), parent=self.root)
            return
        self.password.delete(0, "end")
        self.set_busy(True)
        self.status.set("Entrando e carregando seus cofres e pastas…")
        self.session = Session(config, self.events)
        self.session.start()

    def show_catalog(self, roots):
        opened = {key for key in getattr(self, 'nodes', {}) if self.tree.exists(key) and self.tree.item(key, 'open')}
        selected = self.tree.selection()
        self.roots = roots
        self.nodes = {}
        self.tree.delete(*self.tree.get_children())
        self.insert_nodes(roots)
        for key in opened:
            if self.tree.exists(key):
                self.tree.item(key, open=True)
        self.tree.selection_set([key for key in selected if self.tree.exists(key)])
        self.login_frame.pack_forget()
        self.selection_frame.pack(fill="both", expand=True)
        self.set_busy(False)
        self.status.set("Escolha um cofre ou uma pasta, ou baixe tudo da conta.")

    def insert_nodes(self, nodes, parent=''):
        for node in sorted(nodes, key=lambda item: item.name.casefold()):
            self.nodes[node.key] = node
            self.tree.insert(parent, 'end', iid=node.key, text=node.name, open=False)
            self.insert_nodes(node.children, node.key)
            if not node.loaded:
                self.tree.insert(node.key, 'end', iid=node.key + ':pending', text='Expandir para carregar…')

    def expand(self, event=None):
        key = self.tree.focus()
        node = getattr(self, 'nodes', {}).get(key)
        if not self.busy and self.session and node and not node.loaded:
            self.set_busy(True)
            self.status.set(f'Carregando subpastas de {node.name}…')
            self.session.commands.put(('expand', key))

    def show_branch(self, node):
        current = self.nodes[node.key]
        current.children, current.loaded = node.children, node.loaded
        self.tree.delete(*self.tree.get_children(node.key))
        self.insert_nodes(node.children, node.key)
        self.tree.item(node.key, open=True)
        self.set_busy(False)
        self.status.set('Pastas carregadas. Selecione o que deseja baixar.')

    def browse(self):
        path = filedialog.askdirectory(parent=self.root)
        if path:
            self.destination.delete(0, "end")
            self.destination.insert(0, path)

    def start(self, everything=False):
        if self.busy or not self.session:
            return
        selected = [root.key for root in self.roots] if everything else list(self.tree.selection())
        if not selected or not self.destination.get().strip():
            messagebox.showinfo("Downloads", "Selecione um cofre ou pasta e escolha o destino.", parent=self.root)
            return
        summary = self.download_summary(selected, everything or self.recursive.get(), self.destination.get())
        if not messagebox.askyesno("Confirmar download", summary, parent=self.root):
            return
        self.set_busy(True)
        self.status.set("Preparando downloads…")
        self.session.commands.put(("download", (selected, everything or self.recursive.get(), self.destination.get())))

    def download_summary(self, selected, recursive, destination):
        paths = location_paths(self.roots)
        nodes = selected_locations(self.roots, selected, recursive)
        destination_path = Path(destination).expanduser().resolve()
        lines = [
            "Tudo pronto para baixar!",
            "",
            "Pastas selecionadas:",
        ]
        for node in nodes[:30]:
            local_path = destination_path / paths[node.key]
            lines.append(f"  📁 {paths[node.key]}")
            lines.append(f"     Será salvo em: {local_path}")
        if len(nodes) > 30:
            lines.append(f"… e mais {len(nodes) - 30} locais")
        lines.extend([
            "",
            f"Total: {len(nodes)} pasta(s)",
            f"Destino principal: {destination_path}",
            "As subpastas também serão baixadas." if recursive else "Somente os arquivos diretamente nessas pastas serão baixados.",
            "",
            "Deseja começar o download?",
        ])
        return "\n".join(lines)

    def refresh(self):
        if not self.busy and self.session:
            self.set_busy(True)
            self.session.commands.put(("refresh", None))

    def cancel_download(self):
        if not self.session or not self.busy:
            return
        if not messagebox.askyesno("Cancelar download", "Deseja cancelar agora? O Chrome será encerrado e será necessário entrar novamente.", parent=self.root):
            return
        self.status.set("Cancelando download e encerrando o Chrome…")
        self.cancel_button.configure(state="disabled")
        self.session.cancel_download()

    def logout(self):
        if not self.busy and self.session:
            self.set_busy(True)
            self.status.set("Encerrando sessão…")
            self.session.close()

    def check(self):
        if self.checking:
            return
        self.checking = True
        self.check_button.configure(state="disabled")
        self.update_status.set("Consultando atualizações…")
        def worker():
            try:
                self.events.put(("update", check_update()))
            except Exception as exc:
                self.events.put(("update_error", f"Não foi possível consultar atualizações: {exc}"))
        Thread(target=worker, daemon=True).start()

    def install(self):
        if self.busy or not self.update:
            return
        if not messagebox.askyesno("Atualização", f"Baixar a versão {self.update.version} e abrir o instalador? O aplicativo será fechado.", parent=self.root):
            return
        self.begin_update(self.update)

    def begin_update(self, update, automatic=False):
        if self.auto_updating:
            return
        self.auto_updating = automatic or self.auto_updating
        self.set_busy(True)
        self.status.set("Baixando atualização segura…")
        def worker():
            try:
                path = download_update(update, lambda progress: self.events.put(("progress", progress)))
                self.events.put(("installer", path))
            except Exception as exc:
                self.events.put(("update_failed", f"Não foi possível atualizar automaticamente: {exc}"))
        Thread(target=worker, daemon=False).start()

    def poll(self):
        for _ in range(200):
            try:
                kind, value = self.events.get_nowait()
            except Empty:
                break
            if kind == "log":
                self.log.configure(state="normal")
                self.log.insert("end", value)
                if int(self.log.index("end-1c").split(".")[0]) > 2500:
                    self.log.delete("1.0", "501.0")
                self.log.see("end")
                self.log.configure(state="disabled")
            elif kind == "status":
                self.status.set(value)
            elif kind == "catalog":
                self.show_catalog(value)
            elif kind == 'branch':
                self.show_branch(value)
            elif kind == "closed":
                self.session = None
                self.roots = []
                self.selection_frame.pack_forget()
                self.login_frame.pack(fill="x")
                if self.pending_installer:
                    path, self.pending_installer = self.pending_installer, None
                    if self.launch_installer(path):
                        return
                elif self.closing:
                    self.root.destroy()
                    return
                self.set_busy(False)
            elif kind == "session_error":
                self.status.set(value)
                messagebox.showerror("D4Sign", value, parent=self.root)
            elif kind in ("done", "error", "cancelled"):
                self.set_busy(kind == "cancelled")
                self.status.set(value)
                if kind == "error":
                    messagebox.showerror("D4Sign", value, parent=self.root)
                elif kind == "cancelled":
                    self.cancel_button.configure(state="disabled")
                    self.status.set(value)
            elif kind in ("update", "update_error"):
                self.checking = False
                self.check_button.configure(state="normal")
                if kind == "update":
                    self.update = value
                    if value and sys.platform == "win32" and not self.session and not self.busy:
                        self.update_status.set(f"Atualização {value.version} encontrada. Baixando automaticamente…")
                        self.begin_update(value, automatic=True)
                    elif value:
                        self.update_status.set(f"Nova versão disponível: {value.version}")
                        self.set_busy(self.busy)
                    else:
                        self.update_status.set(f"Versão {VERSION} atualizada.")
                else:
                    self.update_status.set(value)
            elif kind == "update_failed":
                self.auto_updating = False
                self.set_busy(False)
                self.update_status.set(value)
            elif kind == "progress":
                self.status.set(f"Baixando atualização: {value}%")
            elif kind == "installer":
                if self.session:
                    self.pending_installer = value
                    self.session.close()
                elif self.launch_installer(value):
                    return
        self.root.after(100, self.poll)

    def launch_installer(self, path):
        try:
            subprocess.Popen([str(path)], close_fds=True)
        except OSError as exc:
            self.set_busy(False)
            messagebox.showerror("Instalador", str(exc), parent=self.root)
            return False
        self.root.destroy()
        return True

    def close(self):
        if self.session:
            self.closing = True
            self.set_busy(True)
            self.session.close()
        else:
            self.root.destroy()


def main():
    # Diagnósticos relativos são gravados no perfil, nunca na instalação.
    data_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local" / "share"))) / "D4SignDesktop"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.chdir(data_dir)
    root = tk.Tk()
    Desktop(root)
    root.mainloop()
