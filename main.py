# Kullanıcının doğal dil girdisini analiz ederek film türü ve anahtar kelime çıkaran fonksiyon
from llm_analyzer import analyze_user_input

# Tür ve anahtar kelimelere göre popüler filmleri getiren TMDb API fonksiyonu
from tmdb_client import get_popular_movies_by_genres

# Ana program bloğu (doğrudan çalıştırıldığında devreye girer)
if __name__ == "__main__":
    # 🗣 Kullanıcıdan doğal dil ile film isteği al
    user_input = input("Nasıl bir şey izlemek istersiniz? ")

    # 🤖 Kullanıcı girdisini analiz et (Gemini LLM kullanılarak)
    result = analyze_user_input(user_input)

    if result:
        print("\nGemini analizi sonucu:", result)

        # 🔍 Çıktıdan türler ve anahtar kelimeleri ayıkla
        turler = result.get("turler", [])
        anahtar_kelimeler = result.get("anahtar_kelimeler", [])

        # 🎬 TMDb API'den tür ve anahtar kelimelere göre film önerileri al
        movies = get_popular_movies_by_genres(turler, anahtar_kelimeler)

        if not movies:
            print("\n❗ Belirtilen kriterlere uygun film bulunamadı!")
        else:
            print("\n🎥 Film Önerileri:\n")
            # İlk 5 filmi kullanıcıya göster
            for movie in movies[:5]:
                # Poster varsa URL'sini oluştur
                poster_path = movie.get("poster_path")
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else "Poster yok"

                # Yayın yılını al (tarih yoksa 'Yıl Yok' yazsın)
                year = (movie.get("release_date") or "Yıl Yok")[:4]

                # 🎞️ Film bilgilerini yazdır
                print(f"{movie['title']} ({year}) - Puan: {movie['vote_average']}")
                print(f"Poster URL: {poster_url}")
                print(f"Özet: {movie.get('overview')}\n")
    else:
        # LLM'den anlamlı bir çıktı alınamazsa kullanıcıyı bilgilendir
        print("\n⚠️ Kullanıcı girdisi analiz edilemedi.")
