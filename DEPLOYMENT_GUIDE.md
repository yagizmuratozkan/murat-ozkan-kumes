# Murat Özkan Kümes İşletim Sistemi - Deployment Guide

## 📋 Project Overview

**Proje Adı**: Murat Özkan Kümes İşletim Sistemi  
**Teknoloji**: Streamlit + Python + JSON  
**Amaç**: Broiler tavuk çiftliği yönetimi için kapsamlı yazılım sistemi

## 🎯 Sistem Özellikleri

### 1. **Veri Yönetimi**
- ✅ Persistent JSON storage (farm_data.json)
- ✅ 6 kümese ait günlük veri takibi
- ✅ Otomatik hesaplamalar (FCR, ölüm oranı, sağlık puanı)
- ✅ İşlem geçmişi logging

### 2. **İlaç Programı (42 Gün)**
- ✅ Veteriner tarafından hazırlanmış tam program
- ✅ Gün gün sabah/akşam ilaçları
- ✅ Dozaj hesaplamaları
- ✅ Arınma süreleri
- ✅ Klinik notlar

### 3. **Yem Lojistiği**
- ✅ Banvit verileri entegre
- ✅ Akıllı sipariş önerisi (9, 18, 27, 36 ton)
- ✅ Silo kapasitesi yönetimi
- ✅ Tüketim projeksiyonu
- ✅ Taşma riski uyarıları

### 4. **AI Asistan**
- ✅ Gemini API entegrasyonu
- ✅ Gerçek zamanlı farm context
- ✅ Hızlı sorular
- ✅ Sohbet geçmişi

### 5. **Dashboard & Analytics**
- ✅ KPI kartları (5 ana metrik)
- ✅ Ağırlık gelişim grafiği
- ✅ FCR ilerleme grafiği
- ✅ Ölüm oranı analizi
- ✅ Otomatik uyarı sistemi
- ✅ Sağlık puanı algoritması

## 📦 Dosya Yapısı

```
murat_ozkan_kumes/
├── streamlit_app.py              # Ana Streamlit uygulaması
├── enhanced_chat.py              # AI chat modülü
├── feed_logistics.py             # Yem lojistiği modülü
├── dashboard_analytics.py        # Dashboard modülü
├── farm_data.json                # Ana veri dosyası
├── banvit_data.json              # Ross 308 hedef değerleri
├── complete_drug_program.json    # 42 günlük ilaç programı
├── requirements.txt              # Python bağımlılıkları
├── test_report.json              # Test sonuçları
├── .streamlit/
│   └── config.toml               # Streamlit konfigürasyonu
└── README.md                     # Proje açıklaması
```

## 🚀 Deployment Adımları

### 1. **Streamlit Cloud'a Deploy**

```bash
# 1. GitHub'a push et (zaten yapıldı)
git push origin master

# 2. Streamlit Cloud'a git
# https://share.streamlit.io/

# 3. "New app" tıkla
# 4. Repository seç: yagizmuratozkan/murat-ozkan-kumes
# 5. Branch: master
# 6. Main file path: streamlit_app.py

# 7. Deploy et!
```

### 2. **Ortam Değişkenleri Ayarla**

Streamlit Cloud'da:
- **Settings** → **Secrets**
- Aşağıdakini ekle:

```toml
GEMINI_API_KEY = "your-gemini-api-key-here"
```

### 3. **Yerel Test (Deployment Öncesi)**

```bash
# Gerekli paketleri yükle
pip install -r requirements.txt

# Uygulamayı çalıştır
streamlit run streamlit_app.py

# Tarayıcıda aç: http://localhost:8501
```

## 📊 Sistem Mimarisi

### Data Flow
```
Günlük Veri Girişi
    ↓
farm_data.json (Persistent Storage)
    ↓
Otomatik Hesaplamalar (FCR, Ölüm, Sağlık)
    ↓
Dashboard & Analytics
    ↓
AI Asistan (Gemini API)
```

### Modüller
```
streamlit_app.py (Ana App)
    ├── Page: Dashboard
    ├── Page: Ayarlar
    ├── Page: Günlük Veri
    ├── Page: Hesaplamalar
    ├── Page: İlaç Programı
    ├── Page: AI Bilgi Bankası
    ├── Page: İlaç Envanteri
    ├── Page: Durum Analizi
    ├── Page: Chat (AI Asistan)
    └── Page: Finansal Analiz

enhanced_chat.py (AI Module)
    ├── build_farm_context()
    ├── get_ai_response()
    └── render_chat_page()

feed_logistics.py (Logistics Module)
    ├── FeedLogistics Class
    ├── Order Recommendation
    ├── Silo Management
    └── Consumption Projection

dashboard_analytics.py (Analytics Module)
    ├── DashboardAnalytics Class
    ├── KPI Calculation
    ├── Chart Generation
    └── Performance Grading
```

## 🔑 Önemli Özellikler

### 1. **Veri Kalıcılığı**
- JSON dosyasında tüm veriler saklanır
- Her değişiklik otomatik kaydedilir
- İşlem geçmişi tutulur

### 2. **Otomatik Hesaplamalar**
```python
# FCR = Toplam Yem Tüketimi / (Canlı Hayvan × Ağırlık)
# Ölüm Oranı = (Toplam Ölüm / Başlangıç Hayvan) × 100
# Sağlık Puanı = 100 - (Ölüm Etkisi + Ağırlık Sapması + FCR Sapması + Trend)
```

### 3. **Akıllı Uyarılar**
- 🔴 Kritik: Ölüm >2%, Ağırlık >15% sapma
- 🟡 Uyarı: Ölüm >1%, Ağırlık >10% sapma
- 🟢 Normal: Tüm parametreler iyi

### 4. **AI Entegrasyonu**
- Gerçek farm verilerine dayalı analiz
- Günlük tavsiyeleri
- Sorun çözme önerileri

## 📈 Performans Hedefleri (Ross 308)

| Gün | Ağırlık (g) | FCR | Ölüm Oranı |
|-----|------------|-----|-----------|
| 7   | 189        | 0.87| <0.5%     |
| 14  | 480        | 1.11| <1%       |
| 21  | 1000       | 1.30| <1.5%     |
| 28  | 1500       | 1.45| <2%       |
| 35  | 2200       | 1.55| <2%       |
| 42  | 2800       | 1.65| <2%       |

## 🔒 Güvenlik & Best Practices

1. **API Keys**: Streamlit Secrets kullan
2. **Veri Yedekleme**: farm_data.json'ı düzenli yedekle
3. **Erişim Kontrolü**: Sadece yetkili kişiler kullanabilir
4. **Audit Trail**: Tüm işlemler loglanır

## 🐛 Troubleshooting

### Problem: "Gemini API hatası"
**Çözüm**: Streamlit Cloud Secrets'te GEMINI_API_KEY kontrol et

### Problem: "farm_data.json bulunamadı"
**Çözüm**: Dosya ilk çalıştırmada otomatik oluşturulur

### Problem: "Veri kaydedilmiyor"
**Çözüm**: farm_data.json yazma izni kontrol et

## 📞 İletişim & Destek

- **GitHub**: https://github.com/yagizmuratozkan/murat-ozkan-kumes
- **Geliştirici**: Manus AI
- **Tarih**: 22 Şubat 2026

## ✅ Kontrol Listesi (Pre-Deployment)

- [x] Tüm Python modülleri test edildi
- [x] JSON dosyaları doğrulandı
- [x] Gemini API entegrasyonu hazır
- [x] Dashboard grafikleri çalışıyor
- [x] İlaç programı 42 gün tamamlandı
- [x] Yem lojistiği sistemi aktif
- [x] AI asistan hazır
- [x] GitHub'a push edildi
- [ ] Streamlit Cloud'a deploy edilecek
- [ ] Canlı ortamda test edilecek

## 🎓 Kullanım Kılavuzu

### İlk Kullanım
1. Uygulamayı aç
2. "Ayarlar" sekmesinde çiftlik bilgilerini gir
3. "Günlük Veri" sekmesinde günlük verileri gir
4. Sistem otomatik hesaplamalar yapacak

### Günlük Rutin
1. Sabah: Günlük ölüm ve ağırlık verilerini gir
2. Öğle: Dashboard'u kontrol et
3. Akşam: AI asistana sorular sor
4. Gece: Yem sipariş durumunu kontrol et

### Haftalık Gözden Geçirme
1. Performans raporunu kontrol et
2. FCR trendini analiz et
3. Ölüm oranı eğilimini gözlemle
4. Silo seviyelerini kontrol et

---

**Son Güncelleme**: 22 Şubat 2026  
**Versiyon**: 1.0 (Production Ready)
