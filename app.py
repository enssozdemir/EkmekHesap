import streamlit as st
import sqlite3
from datetime import datetime

st.set_page_config(page_title="Ekmek Kasa Defteri", page_icon="🍞", layout="centered")

# --- VERİTABANI ---
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
    nakit, banka = 0.0, 0.0
    c.execute("SELECT tur, tutar, odeme_tipi FROM islemler")
    for tur, tutar, odeme_tipi in c.fetchall():
        carpan = 1 if tur == "GELIR" else -1
        if odeme_tipi == "Nakit":
            nakit += (tutar * carpan)
        else:
            banka += (tutar * carpan)
    conn.close()
    return nakit, banka

def islemleri_getir():
    conn = sqlite3.connect("ekmek_hesap.db")
    c = conn.cursor()
    c.execute("SELECT id, tur, kategori, tutar, odeme_tipi, tarih, aciklama FROM islemler ORDER BY id DESC")
    veriler = c.fetchall()
    conn.close()
    return veriler

init_db()

# --- BAŞLIK VE KASA DURUMU ---
st.title("🍞 Ekmek Kasa Defteri")
nakit, banka = bakiye_hesapla()

col1, col2 = st.columns(2)
with col1:
    st.metric("💵 Cepteki Nakit", f"{nakit:,.2f} ₺")
with col2:
    st.metric("💳 Banka Hesabı", f"{banka:,.2f} ₺")

st.divider()

# --- YENİ İŞLEM EKLEME FORMU ---
tur_secim = st.radio("İşlem Türü", ["🟢 SATIŞ (Gelir)", "🔴 MASRAF (Gider)"], horizontal=True)
tur = "GELIR" if "SATIŞ" in tur_secim else "GIDER"

with st.form("islem_formu", clear_on_submit=True):
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        tutar = st.number_input("Tutar (₺)", min_value=0.0, step=10.0, format="%.2f")
    with col_t2:
        tarih = st.date_input("Tarih", datetime.now()).strftime("%d.%m.%Y")

    if tur == "GELIR":
        kategori = st.selectbox("Satış Türü", ["Ekmek Satışı", "Toplu Sipariş", "Diğer Satış"])
        aciklama = st.text_input("Açıklama / Müşteri (İsteğe bağlı)", placeholder="Örn: 5 Ekmek, Ahmet Amca")
    else:
        kategori = st.selectbox("Masraf Türü", ["Un / Maya / Tuz", "Odun / Gaz / Elektrik", "Poşet / Paketleme", "Ulaşım / Yakıt", "Diğer Masraf"])
        aciklama = st.text_input("Masraf Açıklaması (İsteğe bağlı)", placeholder="Örn: 2 Çuval Un, Tüp")

    odeme_tipi = st.radio("Ödeme Tipi", ["Nakit", "Banka / Kart"], horizontal=True)
    odeme_tipi_val = "Nakit" if "Nakit" in odeme_tipi else "Banka"

    kaydet = st.form_submit_button("KAYDET", use_container_width=True, type="primary")

    if kaydet:
        if tutar > 0:
            islem_ekle(tur, kategori, tutar, odeme_tipi_val, tarih, aciklama)
            st.success("İşlem başarıyla kaydedildi!")
            st.rerun()
        else:
            st.error("Lütfen geçerli bir tutar girin!")

st.divider()

# --- GEÇMİŞ HAREKETLER ---
st.subheader("📋 Son İşlemler")
islemler = islemleri_getir()

if not islemler:
    st.info("Henüz işlem kaydı yok.")
else:
    for islem_id, islem_tur, islem_kat, islem_tut, islem_odeme, islem_tar, islem_ack in islemler:
        c1, c2, c3 = st.columns([3, 2, 1])
        with c1:
            baslik = islem_ack if islem_ack else islem_kat
            st.markdown(f"**{baslik}**")
            st.caption(f"{islem_kat} • {islem_odeme} • {islem_tar}")
        with c2:
            renk = "green" if islem_tur == "GELIR" else "red"
            isaret = "+" if islem_tur == "GELIR" else "-"
            st.markdown(f":{renk}[**{isaret}{islem_tut:,.2f} ₺**]")
        with c3:
            if st.button("🗑️", key=f"sil_{islem_id}"):
                islem_sil(islem_id)
                st.rerun()