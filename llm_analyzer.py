import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def analyze_user_input(user_input):
    prompt = f"""
    Bir kullanıcı film tavsiyesi istiyor. Kullanıcının şu girdisini analiz et:
    '{user_input}'. Bu girdiye dayanarak, TMDb API'sinde arama yapmak için kullanılabilecek film türlerini ve 
    anahtar kelimeleri içeren bir JSON nesnesi oluştur. JSON çıktısı 'turler' ve 'anahtar_kelimeler' 
    adında iki anahtar içermelidir. 'turler' listesi şu seçeneklerden oluşabilir: 
    Aksiyon, Komedi, Dram, Korku, Bilim Kurgu, Romantik, Macera. 'anahtar_kelimeler' listesi ise metindeki 
    önemli temaları içermelidir.
    """

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # 🔍 Yanıtı terminale yaz (gelen cevabı görmek için)
        print("➡️ Gemini'den gelen ham cevap:\n", response_text)

        # Kod bloğu varsa temizle
        if "```" in response_text:
            cleaned = response_text.replace("```json", "").replace("```", "").strip()
        else:
            cleaned = response_text

        # 🧪 JSON olup olmadığını anlamak için bir test
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as je:
            print("[JSON Decode Error]:", je)
            print("[Temizlenmiş cevap]:", cleaned)
            return {
                "turler": [],
                "anahtar_kelimeler": []
            }

        # ✅ Beklenen yapıda mı kontrol et
        if not isinstance(parsed, dict) or "turler" not in parsed or "anahtar_kelimeler" not in parsed:
            print("[Yapı Hatası]: JSON nesnesi beklenen formatta değil.")
            print("➡️ Gelen veri:", parsed)
            return {
                "turler": [],
                "anahtar_kelimeler": []
            }

        return parsed

    except Exception as e:
        print("[Gemini Analiz Hatası] Kullanıcı girdisi:", user_input)
        print("[Hata Detayı]:", str(e))
        return {
            "turler": [],
            "anahtar_kelimeler": []
        }

if __name__ == "__main__":
    user_input = input("Nasıl bir film izlemek istersiniz? ")  
    result = analyze_user_input(user_input)
    print("🎯 Çıktı:", result)
