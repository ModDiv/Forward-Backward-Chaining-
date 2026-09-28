# Logic Agent — Pencarian Kunci Menuju Pintu Gerbang
## Perbandingan Forward Chaining vs Backward Chaining

Studi kasus varian Wumpus World: Agent harus menemukan kunci dan mencapai pintu
gerbang, dengan jebakan dan musuh di beberapa ruangan sebagai konteks tambahan.
Semua aturan dirancang sebagai **Horn Clause murni** (kesimpulan tunggal, positif,
tanpa negasi) agar valid diproses forward chaining maupun backward chaining.

## Peta Ruangan

```
     R2(Musuh) --- R4(Kunci) --- R6(PINTU / Goal)
      |               |              |
     R1(Start) --- R3(Jebakan) --- R5(Aman)
```

## Struktur File

| File | Isi |
|---|---|
| `logic_engine.py` | Utilitas inti: `unify()`, `apply_subst()`, `is_variable()`, `format_atom()`. |
| `kb_data.py` | Fakta awal (`FACTS`), aturan/Horn clause (`RULES`), goal (`GOAL`), dan `update_position()` untuk mensimulasikan TELL saat Agent berpindah. |
| `forward_chaining.py` | Implementasi forward chaining generik (mendukung variabel via unifikasi). |
| `backward_chaining.py` | Implementasi backward chaining generik (goal-driven, dengan standardize-apart untuk mencegah tabrakan variabel). |
| `main.py` | Menjalankan 2 skenario dan membandingkan kedua metode. |

## Cara Menjalankan

```bash
python main.py
```

Tidak ada dependency eksternal — murni Python bawaan.

## Isi Skenario

**Skenario 1 — Kondisi Awal:** Agent masih di `R1`. Kedua metode **gagal**
membuktikan `PintuTerbuka()`, karena `AdaKunci(R1)` tidak pernah benar.

**Skenario 2 — Setelah Agent Bergerak:** KB diperbarui bertahap (mensimulasikan
`TELL`) mengikuti rute yang dicari lewat BFS sederhana (R1→R4 ambil kunci,
lalu R4→R6 buka pintu). Setelah KB mencerminkan posisi baru, kedua metode
**berhasil** membuktikan `PintuTerbuka()`.

## Catatan Penting: Frame Problem

Versi awal implementasi ini sempat "kehilangan" fakta `MemilikiKunci(Agent)`
saat Agent berpindah dari R4 ke R6, karena `update_position()` hanya mengganti
fakta posisi tanpa mempertahankan fakta lain yang sudah benar sebelumnya
(inventory kunci). Ini adalah contoh nyata **frame problem** dalam AI —
tantangan mendasar bagaimana merepresentasikan hal-hal yang **tetap tidak
berubah** ketika suatu aksi terjadi. Solusi pada kode ini: state (KB) hasil
forward chaining sebelumnya dipakai sebagai basis untuk pembaruan posisi
berikutnya, sehingga fakta yang sudah benar (`MemilikiKunci(Agent)`) tetap
terbawa.

## Perbandingan Forward vs Backward Chaining

| Aspek | Forward Chaining | Backward Chaining |
|---|---|---|
| Arah | Fakta → kesimpulan | Goal → fakta |
| Metrik efisiensi | Jumlah rules fired | Jumlah goal yang dicek |
| Skenario 1 (gagal) | 15 rules fired (proses semua fakta, termasuk yang tak relevan ke goal) | Hanya 4 goal dicek (langsung fokus ke rantai pembuktian goal) |
| Skenario 2 (berhasil) | 17 rules fired total | Hanya 5 goal dicek |

Backward chaining secara konsisten lebih hemat karena hanya menelusuri
cabang yang relevan dengan goal, sementara forward chaining memproses
seluruh KB termasuk fakta yang tidak berkaitan langsung (`Berkilau`,
`Berbau`, `Berangin` di berbagai ruangan).

## Visualisasi Real-time (Pygame)

File `visualize_pygame.py` menampilkan animasi Agent bergerak dari Start (R1)
ke ruang Kunci (R4), lalu ke Pintu (R6), dengan panel log di sisi kanan yang
menampilkan trace Forward Chaining & Backward Chaining secara real-time
(baris demi baris, seolah "diketik").

### Instalasi

```bash
pip install pygame
```

### Menjalankan

```bash
python visualize_pygame.py
```

### Kontrol

| Tombol | Aksi |
|---|---|
| `SPACE` | Lanjut ke langkah berikutnya (log baru atau animasi gerak) |
| `R` | Ulangi seluruh peragaan dari awal |
| `ESC` / tutup jendela | Keluar |

### Yang ditampilkan

1. Backward chaining dari kondisi awal (Agent di R1) — **gagal**, ditampilkan
   trace lengkap sampai `AdaKunci(R1)` gagal dibuktikan.
2. Agent beranimasi bergerak R1 → R2 → R4 mengikuti rute BFS.
3. Setelah sampai R4, forward chaining dijalankan ulang — `MemilikiKunci(Agent)`
   berhasil diturunkan, ikon kunci muncul di atas Agent.
4. Agent beranimasi bergerak R4 → R6.
5. Forward chaining & backward chaining dijalankan ulang — `PintuTerbuka()`
   berhasil dibuktikan, warna ruangan R6 berubah jadi kuning (pintu terbuka).

Catatan: file ini tidak diuji-jalan interaktif di lingkungan pembuatan kode ini
(tidak ada display), namun seluruh logika di baliknya (rute BFS, forward
chaining, backward chaining) sudah diverifikasi identik dengan hasil `main.py`.

## Bonus: Agent OTONOM tanpa Search Problem (NAF Reasoning)

File `wumpus_kb.py` + `autonomous_agent.py` + `autonomous_pygame.py` adalah
pengembangan lanjutan: Agent yang **menjelajah dan memutuskan sendiri**
langkah demi langkah, TANPA rute yang dihitung di muka (tanpa BFS/DFS/UCS/A*),
mirip pendekatan asli Wumpus World.

### Konsep Baru: Negation as Failure (NAF)

`AdaKunci`/`AdaMusuh`/`AdaJebakan` di sini **tersembunyi** dari Agent (partially
observable) -- Agent hanya tahu topologi peta (`Terhubung`) dan posisinya sendiri.
Ia baru "mengetahui" bahaya lewat **persepsi** (`Berbau`/`Berangin`/`Berkilau`)
yang di-TELL saat benar-benar berada di suatu ruangan.

Untuk menyimpulkan **"ruangan y pasti aman"**, dibutuhkan premis berbentuk
negasi (`tidak Berbau(x) DAN tidak Berangin(x) -> Aman(y)`), yang aslinya BUKAN
Horn clause. Solusinya: `backward_chaining.py` diperluas mendukung premis khusus
`("NAF", <atom>)` -- berhasil dibuktikan **jika dan hanya jika** `<atom>` GAGAL
dibuktikan sama sekali (bukan negasi logis murni, tapi cukup untuk kasus ini).

```python
{
    "name": "AmanPasti_dariTetanggaBersih",
    "premises": [
        ("Terhubung", "?x", "?y"),
        ("Dikunjungi", "?x"),
        ("NAF", ("Berbau", "?x")),
        ("NAF", ("Berangin", "?x")),
    ],
    "conclusion": ("AmanPasti", "?y"),
}
```

### Aturan Permainan

- Agent punya **3 HP**.
- Masuk ruangan berisi **Musuh** -> -1 HP (bisa selamat, sampai HP habis).
- Masuk ruangan berisi **Jebakan** -> mati seketika.
- Skor: **+1000** kalau berhasil buka pintu, **-1000** kalau mati,
  **-1** untuk setiap aksi (bergerak/ambil kunci/buka pintu).

### Cara Agent Memutuskan Arah (Tanpa Search Problem)

Setiap langkah, untuk tiap tetangga yang belum dikunjungi, Agent ber-`ASK`
`AmanPasti(y)?` lewat backward chaining. Prioritas keputusan:
1. Tetangga yang **terbukti aman** dan merupakan Pintu -> pilih itu.
2. Tetangga yang **terbukti aman** -> pilih salah satu.
3. Kalau sudah punya kunci dan Pintu adalah tetangga yang belum dikunjungi
   (meski belum terbukti aman) -> tetap menuju Pintu (goal-directed).
4. Tidak ada info cukup -> **spekulasi/gamble** (pilih tetangga pertama).
5. Semua tetangga sudah dikunjungi -> backtrack.

### Menjalankan

```bash
python autonomous_agent.py     # versi teks (headless), cocok untuk debug/verifikasi
pip install pygame
python autonomous_pygame.py    # versi visual real-time
```

### Jalannya Cerita (dengan peta bawaan)

1. Di R1, Agent mencium **Bau DAN Angin sekaligus** (Musuh di R2, Jebakan di R3
   sama-sama tetangga R1) -- tidak ada info untuk membedakan mana yang aman ->
   **terpaksa berjudi**, memilih R2 (alfabetis) -> **kena Musuh, HP 3 -> 2**.
2. Dari R2, karena R2 kini bersih (tidak ada Bau/Angin) dan sudah dikunjungi,
   Agent **berhasil membuktikan** R4 aman lewat NAF -> melangkah dengan percaya
   diri, **tanpa risiko**.
3. Di R4, menemukan kilau -> **ambil kunci**.
4. R3 dan R6 sama-sama belum terbukti aman (R4 juga berbau, akibat Musuh di R2) --
   tapi karena sudah punya kunci dan R6 adalah Pintu (tujuan akhir), Agent memilih
   **menuju R6** alih-alih menebak ke R3 (yang sebenarnya Jebakan) -> selamat,
   karena R6 memang tidak berbahaya.
5. Buka pintu -> **MENANG**, skor akhir 995, HP tersisa 2.

Susunan ini konsisten karena dunia (`TRUE_WORLD`) bersifat tetap -- untuk melihat
skenario berbeda, ubah isi `TRUE_WORLD` di `wumpus_kb.py` (pindahkan Musuh/Jebakan
ke ruangan lain).
