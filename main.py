import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import yt_dlp as ytdlp
import os
import sys
import threading

class Descarga:
    def __init__(self, progress_callback=None):
        self.nombre = "Descarga"
        self.progress_callback = progress_callback
        self.canceled = False  # Indicador para cancelar el proceso

    def get_ffmpeg_path(self):
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        return os.path.join(base_path, 'tools', 'bin', 'ffmpeg.exe')

    def download_audio_as_mp3(self, youtube_url, output_path):
        try:
            # Obtén la ruta del archivo ejecutable de ffmpeg dentro del proyecto
            ffmpeg_location = self.get_ffmpeg_path()

            # Progreso de la descarga usando progress_hooks
            def progress_hook(d):
                if d['status'] == 'downloading' and self.progress_callback:
                    total_bytes = d.get('total_bytes', 1)
                    downloaded_bytes = d.get('downloaded_bytes', 0)
                    progress = downloaded_bytes / total_bytes

                    # Actualiza el progreso solo si hay un cambio significativo
                    if int(progress * 100) % 5 == 0:
                        self.progress_callback(progress)

                    # Detener la descarga si se ha solicitado
                    if self.canceled:
                        raise Exception("Proceso cancelado por el usuario.")
                elif d['status'] == 'finished' and self.progress_callback:
                    self.progress_callback(1.0)

            # Opciones optimizadas para yt-dlp
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f'{output_path}/%(title)s.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'postprocessor_args': ['-ar', '16000'],
                'prefer_ffmpeg': True,
                'ffmpeg_location': ffmpeg_location,
                'n_threads': 4,  # Usa múltiples hilos para la descarga
                'progress_hooks': [progress_hook],
                'concurrent_fragment_downloads': 5,  # Más conexiones simultáneas para descargar más rápido
            }

            # Descarga del video y conversión
            with ytdlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(youtube_url, download=True)
                mp3_file = os.path.join(output_path, f"{info_dict['title']}.mp3")

                if not os.path.isfile(mp3_file):
                    raise FileNotFoundError(f"El archivo {mp3_file} no fue encontrado.")
                
                return mp3_file

        except Exception as e:
            if self.canceled:
                return "cancelled"
            return None

class Ventana:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("YouDownload")
        self.root.geometry("300x350")
        self.root.configure(bg="lightblue")

        # Crear instancia de la clase Descarga con el callback de progreso
        self.descargador = Descarga(self.actualizar_progreso)
        self.hilo_activo = None

        window_width = 300
        window_height = 350

        self.label = tk.Label(self.root, text="Introduce el link del video:")
        self.label.place(x=(window_width // 2) - 80, y=20)

        self.entry = tk.Entry(self.root)
        self.entry.place(x=(window_width // 2) - 75, y=53, width=150)

        self.btn_search = tk.Button(self.root, text="Descargar", command=self.iniciar_descarga, cursor="hand2")
        self.btn_search.place(x=(window_width // 2) - 40, y=90, width=80)

        self.btn_borrar = tk.Button(self.root, text="Borrar", command=self.borrar, cursor="hand2", bg="#F7CA18")
        self.btn_borrar.place(x=(window_width // 2) - 40, y=130, width=80)

        self.label_barra = tk.Label(self.root, text="Barra de descarga:")
        self.label_barra.place(x=(window_width // 2) - 65, y=170)

        self.label_procesando = tk.Label(self.root, text="Procesando...", fg="red", font=("Arial", 10))
        self.label_procesando.place(x=(window_width // 2) - 50, y=190)
        self.label_procesando.place_forget()

        self.progress = ttk.Progressbar(self.root, orient="horizontal", mode="determinate", length=250)
        self.progress.place(x=(window_width // 2) - 125, y=220)

        self.btn_close = tk.Button(self.root, text="Cerrar", command=self.cerrar, bg="#F55454", cursor="hand2")
        self.btn_close.place(x=(window_width // 2) - 40, y=260, width=80)

    def iniciar_descarga(self):
        self.label_procesando.place(x=110, y=190)
        self.descargador.canceled = False  # Resetear cancelación
        self.hilo_activo = threading.Thread(target=self.buscar)
        self.hilo_activo.start()

    def buscar(self):
        video_link = self.entry.get()

        if not video_link:
            messagebox.showwarning("Advertencia", "Por favor, introduce un link.")
            return

        output_path = filedialog.askdirectory(title="Seleccionar Carpeta de Descarga")

        if not output_path:
            messagebox.showwarning("Advertencia", "Por favor, selecciona una carpeta.")
            return

        self.progress["value"] = 0

        mp3_file = self.descargador.download_audio_as_mp3(video_link, output_path)

        if mp3_file == "cancelled":
            messagebox.showinfo("Cancelado", "La descarga fue cancelada.")
        elif mp3_file:
            messagebox.showinfo("Éxito", f"Descarga completa. Archivo guardado en: {mp3_file}")
            self.entry.delete(0, tk.END)
        else:
            messagebox.showerror("Error", "Ocurrió un error durante la descarga o conversión.")

        self.progress["value"] = 0
        self.label_procesando.place_forget()
        self.hilo_activo = None

    def actualizar_progreso(self, progreso):
        self.progress["value"] = progreso * 100
        self.root.update_idletasks()

    def borrar(self):
        self.entry.delete(0, tk.END)

    def cerrar(self):
        if self.hilo_activo and self.hilo_activo.is_alive():
            respuesta = messagebox.askyesno("Confirmar", "Hay una descarga en curso. ¿Desea cancelarla y cerrar?")
            if respuesta:
                self.descargador.canceled = True  # Marcar para cancelar el proceso
                self.hilo_activo.join()  # Esperar a que el hilo termine
                self.root.destroy()
        else:
            self.root.destroy()

    def mostrar(self):
        self.root.mainloop()

# Crear una instancia de la ventana y mostrarla
ver = Ventana()
ver.mostrar()

#pyinstaller --onefile --add-data "pyinstaller --windowed --onefile --icon=icono.ico --add-data "tools/bin/ffmpeg.exe;tools/bin" main.py