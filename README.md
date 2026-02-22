# 🐔 Murat Özkan Kümes Takip Sistemi

**Broiler tavuk çiftlikleri için profesyonel yönetim ve takip uygulaması**

## 📋 Özellikler

### 9 Entegre Sayfa

1. **🏠 Dashboard** - Gerçek zamanlı KPI kartları ve performans grafikleri
2. **⚙️ Ayarlar** - Çiftlik bilgileri, kümes kapasiteleri, silo kapasiteleri
3. **📝 Günlük Veriler** - Ölüm, ağırlık, su tüketimi, silo takibi, yem irsaliyesi
4. **🧮 Hesaplamalar** - Otomatik FCR, su hazırlama, ilaç dozaj hesaplamaları
5. **💊 İlaç Programı** - Nihai Uzman Veteriner Programı entegrasyonu
6. **🏥 AI Bilgi Bankası** - Fotoğraf yükleme ve AI analiz
7. **📋 İlaç Envanteri** - İlaç prospektüsü ve bilgileri
8. **📊 Durum Analizi** - AI raporu ve sağlık puanı
9. **💬 Sohbet** - AI Asistan ile canlı iletişim

---

## 🔧 Teknik Özellikler

### Formüller ve Hesaplamalar

- **Canlı Hayvan Hesabı:** Başlangıç Hayvan - Toplam Ölüm
- **FCR Hesabı:** (Toplam Yem - Kalan Yem) / Toplam Canlı Kütle
- **Su Hazırlama:** 400-1000L, 6/12 saatlik bloklar
- **İlaç Dozajı:** Prospektüs × Su / 1000

### Veri Girişi

- 42 günlük program
- 4 Kümes için ayrı ayrı takip
- Otomatik veri doğrulama
- Sürü gözlem notları

### AI Özellikleri

- Otopsi fotoğrafı analizi
- FAL raporu okuma
- Antibiyogram analizi
- İlaç programı güncelleme önerileri
- Onay mekanizması

---

## 📊 KPI Kartları (12 Adet)

1. Toplam Canlı Hayvan
2. Ölüm Oranı (%)
3. Ortalama Canlı Ağırlık (g)
4. Sağlık Puanı (0-100)
5. Çiftlik FCR
6. Kalan Toplam Yem (kg)
7. Günlük Su Tüketimi (L)
8. Günlük Yem Tüketimi (kg)
9. Siloda Kaç Gün Yem
10. Sabah İlaç
11. Akşam İlaç
12. Önemli Notlar

---

## 🚀 Kurulum ve Çalıştırma

### Gereksinimler

- Python 3.8+
- Streamlit 1.28+
- Pandas 2.0+
- Plotly 5.17+

### Kurulum

```bash
# Depoyu klonla
git clone https://github.com/yourusername/murat-ozkan-kumes.git
cd murat-ozkan-kumes

# Bağımlılıkları yükle
pip install -r requirements.txt

# Uygulamayı çalıştır
streamlit run app.py
```

### Streamlit Cloud'a Deployment

```bash
# GitHub'a push et
git push origin master

# Streamlit Cloud'da yeni uygulama oluştur
# Repository: murat-ozkan-kumes
# Main file: app.py
```

---

## 📁 Proje Yapısı

```
murat-ozkan-kumes/
├── app.py                 # Ana uygulama
├── banvit_data.json       # Ross 308 standart verileri
├── requirements.txt       # Bağımlılıklar
├── .streamlit/
│   └── config.toml        # Streamlit konfigürasyonu
└── README.md              # Bu dosya
```

---

## 📊 Banvit Kartı Verileri

Ross 308 standart değerleri (42 gün):
- Canlı Ağırlık (g)
- Günlük Su Tüketimi (ml)
- Günlük Yem Tüketimi (g) - Max 165g
- Hedeflenen FCR

---

## 🔐 Veri Güvenliği

- Tüm veriler lokal olarak saklanır
- Şifreli bağlantı (HTTPS)
- Otomatik yedekleme
- Veri doğrulama

---

## 📞 İletişim

**Yağız Özkan**
- Email: yagiz@muratözkan.com
- Telefon: +90 (XXX) XXX-XXXX

---

## 📄 Lisans

© 2026 Murat Özkan Kümes Takip Sistemi. Tüm hakları saklıdır.

---

## 🎯 Gelecek Özellikler

- [ ] Mobil uygulama
- [ ] Gelişmiş raporlar (PDF/Excel)
- [ ] Çoklu çiftlik desteği
- [ ] Veri analitikleri
- [ ] SMS uyarıları
- [ ] Entegre veteriner danışmanlığı

---

**Sürüm:** 1.0.0  
**Son Güncelleme:** 22 Şubat 2026
