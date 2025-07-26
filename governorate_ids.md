# Egyptian Governorate IDs Reference

Use these IDs with the `-g` parameter to target specific governorates:

## Major Cities
- `01` - Cairo (القاهرة)
- `02` - Alexandria (الإسكندرية)
- `21` - Giza (الجيزة)

## Delta Region
- `11` - Damietta (دمياط)
- `12` - Dakahlia (الدقهلية)
- `13` - Sharqia (الشرقية)
- `14` - Qalyubia (القليوبية)
- `15` - Kafr el-Sheikh (كفر الشيخ)
- `16` - Gharbia (الغربية)
- `17` - Monufia (المنوفية)
- `18` - Beheira (البحيرة)

## Canal Zone
- `03` - Port Said (بورسعيد)
- `04` - Suez (السويس)
- `19` - Ismailia (الإسماعيلية)

## Upper Egypt
- `23` - Beni Suef (بني سويف)
- `24` - Fayyum (الفيوم)
- `25` - Minya (المنيا)
- `26` - Asyut (أسيوط)
- `27` - Sohag (سوهاج)
- `28` - Qena (قنا)
- `29` - Aswan (أسوان)
- `31` - Luxor (الأقصر)

## Frontier Governorates
- `32` - Red Sea (البحر الأحمر)
- `33` - New Valley (الوادي الجديد)
- `34` - Matrouh (مطروح)
- `35` - North Sinai (شمال سيناء)
- `88` - South Sinai (جنوب سيناء)

## Usage Examples

```bash
# Test only Cairo
python3 AZScraper.py -ym 2007 3 -g 01 -o cairo_results.json

# Test Cairo and Alexandria
python3 AZScraper.py -ym 2007 3 -g 01 02 -o major_cities.json

# Test all Delta governorates
python3 AZScraper.py -ym 2007 3 -g 11 12 13 14 15 16 17 18 -o delta_results.json

# Test specific date with multiple governorates
python3 AZScraper.py -dob 70315 -g 01 21 02 -o specific_date.json
```
