import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import flet as ft
import sqlite3
from datetime import datetime

# --- VERİTABANI İŞLEMLERİ ---
def init_db():
    conn = sqlite3.connect("ekmek_hesap.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS islemler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tur TEXT,
            kategori TEXT,
            tutar REAL,
            odeme_tipi TEXT,
            tarih TEXT,
            aciklama TEXT
        )
    """)
    conn.commit()
    conn.close()

def islem_ekle(tur, kategori, tutar, odeme_tipi, tarih, aciklama=""):
    conn = sqlite3.connect("ekmek_hesap.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO islemler (tur, kategori, tutar, odeme_tipi, tarih, aciklama) VALUES (?, ?, ?, ?, ?, ?)",
        (tur, kategori, tutar, odeme_tipi, tarih, aciklama)
    )
    conn.commit()
    conn.close()

def islem_sil(islem_id):
    conn = sqlite3.connect("ekmek_hesap.db")
    c = conn.cursor()
    c.execute("DELETE FROM islemler WHERE id = ?", (islem_id,))
    conn.commit()
    conn.close()

def bakiye_hesapla():
    conn = sqlite3.connect("ekmek_hesap.db")
    c = conn.cursor()
    
    nakit = 0.0
    banka = 0.0
    
    c.execute("SELECT tur, tutar, odeme_tipi FROM islemler")
    for tur, tutar, odeme_tipi in c.fetchall():
        carpan = 1 if tur == "GELIR" else -1
        if odeme_tipi == "Nakit":
            nakit += (tutar * carpan)
        else:
            banka += (tutar * carpan)
            
    conn.close()
    return nakit, banka

def islemleri_getir_filtreli(tur_filtre="Tümü", kasa_filtre="Tümü"):
    conn = sqlite3.connect("ekmek_hesap.db")
    c = conn.cursor()
    query = "SELECT id, tur, kategori, tutar, odeme_tipi, tarih, aciklama FROM islemler WHERE 1=1"
    params = []
    
    if tur_filtre == "Satışlar":
        query += " AND tur = 'GELIR'"
    elif tur_filtre == "Masraflar":
        query += " AND tur = 'GIDER'"
        
    if kasa_filtre != "Tümü":
        query += " AND odeme_tipi = ?"
        params.append(kasa_filtre)
        
    query += " ORDER BY id DESC"
    c.execute(query, params)
    veriler = c.fetchall()
    conn.close()
    return veriler

# --- ARAYÜZ ---
def main(page: ft.Page):
    page.title = "Ekmek Kasa Defteri"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 16
    
    init_db()

    # Göstergeler
    nakit_text = ft.Text("0.00 ₺", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_800)
    banka_text = ft.Text("0.00 ₺", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800)
    gecmis_column = ft.Column(spacing=8)

    # Form Bileşenleri
    aktif_tur = {"tur": "GELIR"}
    form_baslik = ft.Text("Satış Geliri Ekle", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_900)
    
    baslik_input = ft.TextField(
        label="Açıklama / Başlık (İsteğe bağlı)",
        hint_text="Örn: 5 Ekmek, 2 Çuval Un",
        text_size=15,
        width=300
    )
    
    tarih_input = ft.TextField(
        label="Tarih",
        value=datetime.now().strftime("%d.%m.%Y"),
        text_size=15,
        width=300
    )
    
    tutar_input = ft.TextField(
        label="Tutar (₺)",
        keyboard_type=ft.KeyboardType.NUMBER,
        text_size=18,
        width=300
    )
    
    kategori_dropdown = ft.Dropdown(
        label="Kategori Seçin",
        width=300,
        options=[
            ft.dropdown.Option("Ekmek Satışı"),
            ft.dropdown.Option("Toplu Sipariş"),
            ft.dropdown.Option("Diğer Satış")
        ],
        value="Ekmek Satışı"
    )

    odeme_radio = ft.RadioGroup(
        content=ft.Row([
            ft.Radio(value="Nakit", label="Nakit"),
            ft.Radio(value="Banka", label="Banka / Kart")
        ], alignment=ft.MainAxisAlignment.CENTER),
        value="Nakit"
    )

    kaydet_butonu = ft.ElevatedButton(
        "KAYDET",
        bgcolor=ft.Colors.GREEN_700,
        color=ft.Colors.WHITE,
        height=48,
        expand=True
    )

    vazgec_butonu = ft.OutlinedButton(
        "Vazgeç",
        height=48,
        expand=True
    )

    form_paneli = ft.Card(
        visible=False,
        elevation=4,
        content=ft.Container(
            padding=16,
            bgcolor=ft.Colors.GREY_50,
            border_radius=10,
            content=ft.Column([
                form_baslik,
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                baslik_input,
                tarih_input,
                tutar_input,
                kategori_dropdown,
                ft.Text("Para Nereye / Nereden?", weight=ft.FontWeight.W_500),
                odeme_radio,
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                ft.Row([vazgec_butonu, kaydet_butonu])
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
    )

    # --- FİLTRELEME BİLEŞENLERİ ---
    filtre_tur_dropdown = ft.Dropdown(
        label="Tür Filtresi",
        options=[
            ft.dropdown.Option("Tümü"),
            ft.dropdown.Option("Satışlar"),
            ft.dropdown.Option("Masraflar")
        ],
        value="Tümü",
        width=140
    )

    filtre_kasa_dropdown = ft.Dropdown(
        label="Kasa Filtresi",
        options=[
            ft.dropdown.Option("Tümü"),
            ft.dropdown.Option("Nakit"),
            ft.dropdown.Option("Banka")
        ],
        value="Tümü",
        width=140
    )

    # Güncelleme Fonksiyonu
    def guncelle(e=None):
        nakit, banka = bakiye_hesapla()
        nakit_text.value = f"{nakit:,.2f} ₺"
        banka_text.value = f"{banka:,.2f} ₺"
        
        gecmis_column.controls.clear()
        islemler = islemleri_getir_filtreli(filtre_tur_dropdown.value, filtre_kasa_dropdown.value)
        
        if not islemler:
            gecmis_column.controls.append(
                ft.Container(
                    content=ft.Row(
                        [ft.Text("Filtreye uygun kayıt bulunamadı.", color=ft.Colors.GREY_500)],
                        alignment=ft.MainAxisAlignment.CENTER
                    ),
                    padding=20
                )
            )
        else:
            for islem_id, tur, kategori, tutar, odeme_tipi, tarih, aciklama in islemler:
                renk = ft.Colors.GREEN_700 if tur == "GELIR" else ft.Colors.RED_700
                isaret = "+" if tur == "GELIR" else "-"
                
                ana_yazi = aciklama if aciklama else kategori
                alt_yazi = f"{kategori} • {odeme_tipi} • {tarih}" if aciklama else f"{odeme_tipi} • {tarih}"

                gecmis_column.controls.append(
                    ft.Container(
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Column([
                                    ft.Text(ana_yazi, weight=ft.FontWeight.BOLD, size=15),
                                    ft.Text(alt_yazi, size=12, color=ft.Colors.GREY_600)
                                ], expand=True),
                                ft.Row([
                                    ft.Text(f"{isaret}{tutar:,.2f} ₺", size=15, weight=ft.FontWeight.BOLD, color=renk),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        icon_color=ft.Colors.RED_400,
                                        tooltip="Bu Kaydı Sil",
                                        on_click=lambda e, sil_id=islem_id: kayit_sil(sil_id)
                                    )
                                ])
                            ]
                        ),
                        padding=10,
                        bgcolor=ft.Colors.GREY_100,
                        border_radius=8
                    )
                )
        page.update()

    def kayit_sil(sil_id):
        islem_sil(sil_id)
        guncelle()

    filtre_tur_dropdown.on_change = guncelle
    filtre_kasa_dropdown.on_change = guncelle

    # Form Açma / Kapatma Olayları
    def formu_ac(tur):
        aktif_tur["tur"] = tur
        baslik_input.value = ""
        tutar_input.value = ""
        tutar_input.error_text = None
        tarih_input.value = datetime.now().strftime("%d.%m.%Y")
        odeme_radio.value = "Nakit"
        
        if tur == "GELIR":
            form_baslik.value = "Yeni Satış Ekle"
            form_baslik.color = ft.Colors.GREEN_900
            baslik_input.label = "Satış Açıklaması / Başlık"
            baslik_input.hint_text = "Örn: 5 Ekmek, Köy Siparişi"
            kaydet_butonu.bgcolor = ft.Colors.GREEN_700
            kategori_dropdown.label = "Satış Türü"
            kategori_dropdown.options = [
                ft.dropdown.Option("Ekmek Satışı"),
                ft.dropdown.Option("Toplu Sipariş"),
                ft.dropdown.Option("Diğer Satış")
            ]
            kategori_dropdown.value = "Ekmek Satışı"
        else:
            form_baslik.value = "Yeni Masraf / Harcama Ekle"
            form_baslik.color = ft.Colors.RED_900
            baslik_input.label = "Masraf Açıklaması / Başlık"
            baslik_input.hint_text = "Örn: 2 Çuval Un, Maya, Tüp"
            kaydet_butonu.bgcolor = ft.Colors.RED_700
            kategori_dropdown.label = "Gider Türü"
            kategori_dropdown.options = [
                ft.dropdown.Option("Un / Maya / Tuz"),
                ft.dropdown.Option("Odun / Gaz / Elektrik"),
                ft.dropdown.Option("Poşet / Paketleme"),
                ft.dropdown.Option("Ulaşım / Yakıt"),
                ft.dropdown.Option("Diğer Masraf")
            ]
            kategori_dropdown.value = "Un / Maya / Tuz"

        form_paneli.visible = True
        page.update()

    def formu_kapat(e=None):
        form_paneli.visible = False
        page.update()

    def formu_kaydet(e):
        try:
            val = tutar_input.value.strip().replace(",", ".")
            tutar = float(val)
            if tutar <= 0:
                tutar_input.error_text = "Sıfırdan büyük bir sayı girin"
                page.update()
                return
            
            aciklama_metni = baslik_input.value.strip()
            tarih_metni = tarih_input.value.strip() or datetime.now().strftime("%d.%m.%Y")
            
            islem_ekle(
                aktif_tur["tur"],
                kategori_dropdown.value,
                tutar,
                odeme_radio.value,
                tarih_metni,
                aciklama_metni
            )
            form_paneli.visible = False
            guncelle()
        except ValueError:
            tutar_input.error_text = "Geçerli bir tutar yazın"
            page.update()

    vazgec_butonu.on_click = formu_kapat
    kaydet_butonu.on_click = formu_kaydet

    # --- KASA ÖZET KARTI ---
    kasa_karti = ft.Card(
        content=ft.Container(
            padding=16,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                controls=[
                    ft.Column([
                        ft.Text("Cepteki Nakit", size=13, color=ft.Colors.GREY_700),
                        nakit_text
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.VerticalDivider(width=1, color=ft.Colors.GREY_300),
                    ft.Column([
                        ft.Text("Banka Hesabı", size=13, color=ft.Colors.GREY_700),
                        banka_text
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ]
            )
        )
    )

    # --- ANA BUTONLAR ---
    buton_gelir = ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(ft.Icons.ADD_CIRCLE, color=ft.Colors.WHITE),
            ft.Text("SATIŞ EKLE", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        ], alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=ft.Colors.GREEN_600,
        height=55,
        expand=True,
        on_click=lambda e: formu_ac("GELIR")
    )

    buton_gider = ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(ft.Icons.REMOVE_CIRCLE, color=ft.Colors.WHITE),
            ft.Text("MASRAF EKLE", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        ], alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=ft.Colors.RED_600,
        height=55,
        expand=True,
        on_click=lambda e: formu_ac("GIDER")
    )

    # Sayfa Düzeni
    page.add(
        ft.Text("Kasa Durumu", size=20, weight=ft.FontWeight.BOLD),
        kasa_karti,
        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
        ft.Row([buton_gelir, buton_gider]),
        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
        form_paneli,
        ft.Divider(height=15, color=ft.Colors.GREY_300),
        ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text("İşlem Geçmişi", size=18, weight=ft.FontWeight.BOLD),
            ]
        ),
        ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[filtre_tur_dropdown, filtre_kasa_dropdown]
        ),
        gecmis_column
    )

    guncelle()

if __name__ == "__main__":
    ft.app(target=main)