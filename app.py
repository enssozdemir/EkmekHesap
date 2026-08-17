import streamlit as st
import sqlite3
from datetime import datetime

# --- Veritabanı Kurulumu ---
def init_db():
    conn = sqlite3.connect('ekmek_hesap.db')
    c = conn.cursor()
    # Kasa Tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS islemler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tur TEXT,
            kategori TEXT,
            tutar REAL,
            odeme_yontemi TEXT,
            tarih TEXT,
            aciklama TEXT
        )
    ''')
    # Sipariş & Üretim Tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS siparisler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            musteri TEXT,
            ekmek_turu TEXT,
            adet INTEGER,
            tutar REAL,
            durum TEXT,
            siparis_tarihi TEXT,
            teslim_tarihi TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- Veritabanı Yardımcı Fonksiyonları ---
def get_db():
    return sqlite3.connect('ekmek_hesap.db')

# --- Sayfa Yapılandırması ---
st.set_page_config(page_title="Ekmek Kasa & Sipariş Takip", layout="wide")

# Sol Menü (Navigasyon)
menu = st.sidebar.radio(
    "📌 Menü",
    ["🥖 Sipariş & Üretim Takibi", "📦 Sipariş Geçmişi & Arşiv", "💰 Kasa Defteri"]
)

# ==========================================
# 1. SAYFA: SİPARİŞ & ÜRETİM TAKİBİ
# ==========================================
if menu == "🥖 Sipariş & Üretim Takibi":
    st.header("🥖 Ekmek Sipariş ve Üretim Hattı")
    
    # Yeni Sipariş Giriş Formu
    with st.expander("➕ Yeni Sipariş Gir", expanded=False):
        with st.form("yeni_siparis_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                musteri = st.text_input("Müşteri Adı / Not")
                ekmek_turu = st.selectbox("Ekmek Türü", ["Ekşi Mayalı Somun", "Tam Buğday", "Çavdar", "Köy Ekmeği", "Baget", "Diğer"])
            with col2:
                adet = st.number_input("Adet", min_value=1, value=1, step=1)
                tutar = st.number_input("Toplam Tutar (₺)", min_value=0.0, value=50.0, step=5.0)
            
            if st.form_submit_button("Siparişi Kaydet"):
                if musteri.strip():
                    conn = get_db()
                    c = conn.cursor()
                    c.execute('''
                        INSERT INTO siparisler (musteri, ekmek_turu, adet, tutar, durum, siparis_tarihi, teslim_tarihi)
                        VALUES (?, ?, ?, ?, 'Siparis', ?, '')
                    ''', (musteri, ekmek_turu, adet, tutar, datetime.now().strftime("%Y-%m-%d %H:%M")))
                    conn.commit()
                    conn.close()
                    st.success("Sipariş alındı!")
                    st.rerun()
                else:
                    st.error("Lütfen müşteri adı girin.")

    # Sipariş Süreç Kolonları
    col_siparis, col_islem, col_elde = st.columns(3)
    conn = get_db()
    c = conn.cursor()

    # 1. Kolon: Yeni Siparişler
    with col_siparis:
        st.subheader("📥 1. Sipariş Alındı")
        c.execute("SELECT id, musteri, ekmek_turu, adet, tutar FROM siparisler WHERE durum = 'Siparis'")
        siparisler = c.fetchall()
        if not siparisler:
            st.caption("Bekleyen sipariş yok.")
        for s in siparisler:
            with st.container(border=True):
                st.markdown(f"**{s[1]}**")
                st.caption(f"{s[3]} Adet • {s[2]} • **{s[4]:.2f} ₺**")
                if st.button("Hazırlığa Al ➡️", key=f"islem_{s[0]}", use_container_width=True):
                    c.execute("UPDATE siparisler SET durum = 'IslemeAlindi' WHERE id = ?", (s[0],))
                    conn.commit()
                    st.rerun()

    # 2. Kolon: İşleme Alınan / Fırında
    with col_islem:
        st.subheader("🔥 2. İşleme Alındı")
        c.execute("SELECT id, musteri, ekmek_turu, adet, tutar FROM siparisler WHERE durum = 'IslemeAlindi'")
        islemler = c.fetchall()
        if not islemler:
            st.caption("Hazırlıkta ürün yok.")
        for s in islemler:
            with st.container(border=True):
                st.markdown(f"**{s[1]}**")
                st.caption(f"{s[3]} Adet • {s[2]} • **{s[4]:.2f} ₺**")
                if st.button("Pişti / Hazır ➡️", key=f"hazir_{s[0]}", use_container_width=True):
                    c.execute("UPDATE siparisler SET durum = 'EldekiEkmek' WHERE id = ?", (s[0],))
                    conn.commit()
                    st.rerun()

    # 3. Kolon: Pişti / Eldeki Ekmek (Teslim Bekleyen)
    with col_elde:
        st.subheader("🍞 3. Eldeki Ekmek")
        c.execute("SELECT id, musteri, ekmek_turu, adet, tutar FROM siparisler WHERE durum = 'EldekiEkmek'")
        eldeler = c.fetchall()
        if not eldeler:
            st.caption("Rafta bekleyen ekmek yok.")
        for s in eldeler:
            with st.container(border=True):
                st.markdown(f"**{s[1]}**")
                st.caption(f"{s[3]} Adet • {s[2]} • **{s[4]:.2f} ₺**")
                if st.button("✅ Teslim Edildi", key=f"teslim_{s[0]}", use_container_width=True):
                    simdi = datetime.now().strftime("%Y-%m-%d %H:%M")
                    # Durumu TeslimEdildi yap
                    c.execute("UPDATE siparisler SET durum = 'TeslimEdildi', teslim_tarihi = ? WHERE id = ?", (simdi, s[0]))
                    # Otomatik Kasa Defterine Gelir Olarak Ekle
                    c.execute('''
                        INSERT INTO islemler (tur, kategori, tutar, odeme_yontemi, tarih, aciklama)
                        VALUES ('GELIR', 'Ekmek Satışı', ?, 'Nakit / Havale', ?, ?)
                    ''', (s[4], datetime.now().strftime("%Y-%m-%d"), f"{s[1]} - {s[3]} Adet {s[2]}"))
                    conn.commit()
                    st.rerun()
    conn.close()

# ==========================================
# 2. SAYFA: SİPARİŞ GEÇMİŞİ & ARŞİV
# ==========================================
elif menu == "📦 Sipariş Geçmişi & Arşiv":
    st.header("📦 Sipariş Geçmişi & Arşiv")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT musteri, ekmek_turu, adet, tutar, siparis_tarihi, teslim_tarihi FROM siparisler WHERE durum = 'TeslimEdildi' ORDER BY id DESC")
    gecmis = c.fetchall()
    conn.close()

    if gecmis:
        toplam_teslim = sum([item[2] for item in gecmis])
        toplam_ciro = sum([item[3] for item in gecmis])
        
        m1, m2 = st.columns(2)
        m1.metric("Toplam Teslim Edilen Ekmek", f"{toplam_teslim} Adet")
        m2.metric("Toplam Teslim Cirosu", f"{toplam_ciro:,.2f} ₺")
        st.divider()

        for g in gecmis:
            with st.container(border=True):
                c1, c2 = st.columns([3, 2])
                with c1:
                    st.markdown(f"**{g[0]}** — {g[2]} Adet {g[1]}")
                    st.caption(f"Sipariş: {g[4]} | Teslim: {g[5]}")
                with c2:
                    st.markdown(f"**+{g[3]:,.2f} ₺**")
    else:
        st.info("Henüz arşivlenmiş teslimat bulunmuyor.")

# ==========================================
# 3. SAYFA: KASA DEFTERİ
# ==========================================
elif menu == "💰 Kasa Defteri":
    st.header("💰 Gelir & Gider Defteri")
    
    with st.expander("➕ Yeni Gelir / Gider Ekle", expanded=False):
        with st.form("kasa_form", clear_on_submit=True):
            tur = st.radio("İşlem Türü", ["GELİR", "GİDER"], horizontal=True)
            kategori = st.selectbox("Kategori", ["Ekmek Satışı", "Un / Hammadde", "Maya / Tuz", "Elektrik / Su / Gaz", "Paketleme", "Diğer"])
            tutar = st.number_input("Tutar (₺)", min_value=0.0, step=10.0)
            odeme = st.selectbox("Ödeme Yöntemi", ["Nakit", "Havale / EFT", "Kredi Kartı"])
            aciklama = st.text_input("Açıklama / Not")
            
            if st.form_submit_button("Kaydet"):
                conn = get_db()
                c = conn.cursor()
                c.execute('''
                    INSERT INTO islemler (tur, kategori, tutar, odeme_yontemi, tarih, aciklama)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (tur, kategori, tutar, odeme, datetime.now().strftime("%Y-%m-%d"), aciklama))
                conn.commit()
                conn.close()
                st.success("Kasa işlemi kaydedildi.")
                st.rerun()

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT tur, tutar FROM islemler")
    tum_islemler = c.fetchall()
    
    gelir = sum([i[1] for i in tum_islemler if i[0] == 'GELIR' or i[0] == 'GELİR'])
    gider = sum([i[1] for i in tum_islemler if i[0] == 'GIDER' or i[0] == 'GİDER'])
    bakiye = gelir - gider
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Toplam Gelir", f"{gelir:,.2f} ₺")
    k2.metric("Toplam Gider", f"{gider:,.2f} ₺")
    k3.metric("Net Kasa Bakiyesi", f"{bakiye:,.2f} ₺")
    st.divider()

    c.execute("SELECT id, tur, kategori, tutar, odeme_yontemi, tarih, aciklama FROM islemler ORDER BY id DESC")
    islemler = c.fetchall()
    conn.close()

    for islem in islemler:
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 2, 1])
            with c1:
                baslik = islem[6] if islem[6] else islem[2]
                st.markdown(f"**{baslik}**")
                st.caption(f"{islem[2]} • {islem[4]} • {islem[5]}")
            with c2:
                renk = "green" if "GEL" in islem[1] else "red"
                isaret = "+" if "GEL" in islem[1] else "-"
                st.markdown(f":{renk}[**{isaret}{islem[3]:,.2f} ₺**]")
            with c3:
                if st.button("🗑️", key=f"sil_kasa_{islem[0]}"):
                    conn = get_db()
                    c = conn.cursor()
                    c.execute("DELETE FROM islemler WHERE id = ?", (islem[0],))
                    conn.commit()
                    conn.close()
                    st.rerun()