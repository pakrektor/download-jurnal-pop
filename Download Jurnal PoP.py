import tkinter as tk
from tkinter import scrolledtext, filedialog
import json
import requests
import re
import os
import threading
import queue
import random
import time

class JournalDownloaderApp:
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
    ]

    def __init__(self, root):
        self.root = root
        self.root.title("Software Pengunduh Jurnal v1.2 (Pilih Folder)")
        self.root.geometry("700x650") # Sedikit lebih tinggi untuk UI baru
        self.root.configure(bg="#f0f0f0")
        self.font_style = ("Helvetica", 10)
        
        main_frame = tk.Frame(root, padx=15, pady=15, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Input Area
        input_frame = tk.LabelFrame(main_frame, text="1. Tempel Data JSON di Sini", padx=10, pady=10, bg="#f0f0f0", font=(self.font_style[0], 11, "bold"))
        input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.json_input = scrolledtext.ScrolledText(input_frame, wrap=tk.WORD, height=10, font=self.font_style)
        self.json_input.pack(fill=tk.BOTH, expand=True)

        # --- PERUBAHAN 1: UI untuk memilih folder penyimpanan ---
        storage_frame = tk.LabelFrame(main_frame, text="2. Lokasi Penyimpanan", padx=10, pady=10, bg="#f0f0f0", font=(self.font_style[0], 11, "bold"))
        storage_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.storage_path_var = tk.StringVar()
        self.set_default_storage_path() # Panggil fungsi untuk set path default

        storage_label = tk.Label(storage_frame, textvariable=self.storage_path_var, font=self.font_style, bg="#ffffff", anchor="w", relief="sunken", borderwidth=2)
        storage_label.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 10))
        
        browse_button = tk.Button(storage_frame, text="Pilih Folder...", command=self.browse_folder, font=self.font_style)
        browse_button.pack(side=tk.RIGHT)
        # --- AKHIR PERUBAHAN ---

        # 3. Tombol Aksi
        self.download_button = tk.Button(main_frame, text="Mulai Proses Unduh", command=self.start_download_thread, font=(self.font_style[0], 12, "bold"), bg="#0078D7", fg="white", relief=tk.FLAT, padx=10, pady=10)
        self.download_button.pack(fill=tk.X, pady=10)

        # 4. Log Area
        log_frame = tk.LabelFrame(main_frame, text="3. Log Proses", padx=10, pady=10, bg="#f0f0f0", font=(self.font_style[0], 11, "bold"))
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_output = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled', font=self.font_style, bg="#ffffff")
        self.log_output.pack(fill=tk.BOTH, expand=True)
        
        # Konfigurasi tag warna
        for tag, color in [('INFO', 'blue'), ('SUCCESS', 'green'), ('ERROR', 'red'), ('WARN', '#E8A015')]:
            self.log_output.tag_config(tag, foreground=color)

        self.log_queue = queue.Queue()
        self.process_log_queue()

    # --- PERUBAHAN 2: Fungsi untuk menentukan folder default ---
    def set_default_storage_path(self):
        base_path = "D:\\Unduh Jurnal"
        fallback_path = "Unduhan Jurnal" # Jika D: tidak ada

        # Cek apakah drive D ada
        if os.path.exists("D:\\"):
            final_base_path = base_path
        else:
            final_base_path = fallback_path
        
        # Membuat folder dasar jika belum ada
        if not os.path.exists(final_base_path):
            os.makedirs(final_base_path)

        # Cari nama folder unduhan berikutnya (Unduhan 1, Unduhan 2, dst.)
        i = 1
        while True:
            download_folder = os.path.join(final_base_path, f"Unduhan {i}")
            if not os.path.exists(download_folder):
                self.storage_path_var.set(download_folder)
                break
            i += 1
    # --- AKHIR PERUBAHAN ---

    # --- PERUBAHAN 3: Fungsi untuk tombol "Pilih Folder" ---
    def browse_folder(self):
        # Membuka dialog untuk memilih folder
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.storage_path_var.set(folder_selected)
    # --- AKHIR PERUBAHAN ---

    def add_log(self, message, tag='INFO'):
        self.log_output.configure(state='normal')
        self.log_output.insert(tk.END, f"[{tag}] {message}\n", tag)
        self.log_output.configure(state='disabled')
        self.log_output.see(tk.END) 

    def start_download_thread(self):
        self.download_button.config(state=tk.DISABLED, text="Sedang Memproses...")
        self.json_input.config(state=tk.DISABLED)
        self.log_output.config(state=tk.NORMAL)
        self.log_output.delete('1.0', tk.END)
        self.log_output.config(state=tk.DISABLED)
        thread = threading.Thread(target=self.download_worker)
        thread.daemon = True
        thread.start()

    def download_worker(self):
        try:
            json_text = self.json_input.get("1.0", tk.END)
            articles = json.loads(json_text)
        except json.JSONDecodeError:
            self.log_queue.put(('ERROR', "Gagal membaca data. Pastikan format JSON sudah benar."))
            self.reset_ui()
            return

        self.log_queue.put(('INFO', f"Data JSON berhasil dibaca. Total ada {len(articles)} jurnal."))

        # --- PERUBAHAN 4: Menggunakan path dari variabel UI ---
        download_folder = self.storage_path_var.get()
        if not os.path.exists(download_folder):
            try:
                os.makedirs(download_folder)
                self.log_queue.put(('INFO', f"Folder penyimpanan dibuat di: {download_folder}"))
            except OSError as e:
                self.log_queue.put(('ERROR', f"Tidak dapat membuat folder penyimpanan: {e}"))
                self.reset_ui()
                return
        # --- AKHIR PERUBAHAN ---
        
        articles_to_download = [a for a in articles if a.get('fulltext_url')]
        total_to_download = len(articles_to_download)
        
        if total_to_download == 0:
            self.log_queue.put(('WARN', "Tidak ada jurnal yang memiliki link unduhan (fulltext_url)."))
            self.reset_ui()
            return
            
        self.log_queue.put(('INFO', f"Ditemukan {total_to_download} jurnal untuk diunduh ke folder '{os.path.basename(download_folder)}'"))

        downloaded_count = 0
        for i, article in enumerate(articles_to_download):
            title = article.get('title', 'tanpa_judul').strip()
            year = article.get('year', 'tanpa_tahun')
            url = article.get('fulltext_url')

            base_filename = f"{title} - {year}"
            safe_filename = re.sub(r'[\\/*?:"<>|]', "", base_filename) + ".pdf"
            file_path = os.path.join(download_folder, safe_filename)

            self.log_queue.put(('INFO', f"({i+1}/{total_to_download}) Mengunduh: {title[:60]}..."))

            try:
                headers = {'User-Agent': random.choice(self.USER_AGENTS)}
                response = requests.get(url, headers=headers, stream=True, timeout=30)
                
                if response.status_code == 200:
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    self.log_queue.put(('SUCCESS', f"Berhasil disimpan: {safe_filename}"))
                    downloaded_count += 1
                else:
                    self.log_queue.put(('ERROR', f"Gagal. Server merespon dengan kode: {response.status_code}"))

            except requests.exceptions.RequestException as e:
                self.log_queue.put(('ERROR', f"Gagal mengunduh. Alasan: {e}"))
            
            time.sleep(random.uniform(0.5, 1.5))

        self.log_queue.put(('INFO', f"\nProses Selesai. Total {downloaded_count} dari {total_to_download} jurnal berhasil diunduh."))
        
        # Setelah selesai, siapkan folder default berikutnya untuk sesi selanjutnya
        self.root.after(100, self.set_default_storage_path)
        self.reset_ui()

    def process_log_queue(self):
        try:
            while True:
                tag, message = self.log_queue.get_nowait()
                self.add_log(message, tag)
        except queue.Empty:
            pass
        self.root.after(100, self.process_log_queue)

    def reset_ui(self):
        self.download_button.config(state=tk.NORMAL, text="Mulai Proses Unduh")
        self.json_input.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = JournalDownloaderApp(root)
    root.mainloop()