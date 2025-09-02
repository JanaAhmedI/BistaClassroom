
# BistaClassroom

BistaClassroom adalah aplikasi pembelajaran berbasis **Django** yang digunakan untuk membuat, mengelola, dan mengerjakan kuis secara online.  
Proyek ini dikembangkan untuk mendukung kegiatan pembelajaran interaktif di lingkungan Bina Statistik BPS Provinsi Maluku Utara.

---

## 🎯 Fitur Utama
- Manajemen akun **Guru** dan **Siswa** (role-based access).
- Guru dapat membuat kuis dengan soal & jawaban bergambar.
- Penilaian otomatis dengan bobot skor per jawaban.
- Analisis hasil kuis per siswa & per bagian soal.
- Batas waktu pengerjaan kuis (auto-submit).
- Riwayat kuis siswa lengkap dengan diskusi soal.

---

## 🛠️ Teknologi
- **Python 3.x**
- **Django 4.x**
- **Bootstrap 4** untuk front-end
- **SQLite/PostgreSQL** untuk database
- **Pillow** untuk upload gambar

---

## 🚀 Instalasi & Setup

1. Clone repository:
   ```
   git clone https://github.com/gumxlarcw/BistaClassroom.git
   cd BistaClassroom
   ```

2. Buat virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate      # Windows
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Migrasi database:
   ```
   python manage.py migrate
   ```

5. Buat superuser (opsional):
   ```
   python manage.py createsuperuser
   ```

6. Jalankan server:
   ```
   python manage.py runserver
   ```

7. Buka di browser:
   ```
   http://127.0.0.1:8000/
   ```

---

## 👥 Peran Pengguna
- **Guru (Teacher)**: Membuat kuis, mengelola soal, memantau nilai siswa.
- **Siswa (Student)**: Mengambil kuis sesuai minat, melihat hasil, dan berdiskusi soal.

---

## 📂 Struktur Direktori
```
classroom/
├── models.py          # Model User, Quiz, Question, Answer, dll.
├── views/
│   ├── teachers/      # View untuk guru
│   └── students/      # View untuk siswa
├── templates/         # Template HTML
└── forms.py           # Form Django
```

---

## 🤝 Kontribusi
1. Fork repo ini
2. Buat branch baru: `git checkout -b fitur-baru`
3. Commit perubahan: `git commit -m "Tambah fitur baru"`
4. Push ke branch: `git push origin fitur-baru`
5. Buat Pull Request

---

## 📜 Lisensi
Proyek ini dirilis dengan lisensi **MIT** – Bebas digunakan, dimodifikasi, dan dikembangkan.
