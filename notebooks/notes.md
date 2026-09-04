
# 01 — Veriye Genel Bakış

## Amaç
Yoğun bakım risk tahmini projesinde kullanılacak temel tabloları tanımak.

## Ortam
Projeye özel `.venv` ortamı seçildi. Python ve pandas’ın çalıştığı doğrulandı.

## İncelenen Tablolar
- **PATIENTS:** 46.520 satır, 8 sütun. Hastaların temel bilgilerini içeriyor.
- **ADMISSIONS:** 58.976 satır, 19 sütun. Hastane yatışlarını içeriyor.
- **ICUSTAYS:** 61.532 satır, 12 sütun. Yoğun bakım yatışlarını içeriyor.

## İlk Gözlemler
- `SUBJECT_ID` hastayı, `HADM_ID` hastane yatışını, `ICUSTAY_ID` yoğun bakım yatışını tanımlıyor.
- Aynı hastanın birden fazla yatışı bulunabiliyor.
- Tarih sütunları şu anda metin türünde.
- ICUSTAYS tablosunda OUTTIME ve LOS sütunlarının her birinde 10 eksik değer var.
- LOS, yoğun bakımda kalış süresini gün cinsinden gösteriyor.

## Mevcut Durum
Tablolar okundu ve incelendi. Henüz birleştirme, temizleme veya modelleme yapılmadı.
