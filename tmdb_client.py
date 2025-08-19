import os
import requests
from dotenv import load_dotenv

# .env dosyasından çevresel değişkenleri yükle (örneğin API anahtarı)
load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# Türkçe tür isimlerini TMDb'deki tür ID'leriyle eşleştir
GENRES = {
    "aksiyon": 28,
    "macera": 12,
    "animasyon": 16,
    "komedi": 35,
    "suç": 80,
    "belgesel": 99,
    "dram": 18,
    "çocuk": 10751,
    "aile": 10751,
    "fantastik": 14,
    "tarih": 36,
    "korku": 27,
    "müzikal": 10402,
    "gizem": 9648,
    "romantizm": 10749,
    "bilim kurgu": 878,
    "tv filmi": 10770,
    "gerilim": 53,
    "savaş": 10752,
    "western": 37,
    "eğitici": 99,
    "spor": 99
}

# Tür ID'den tekrar tür ismine ulaşmak için ters bir eşleme oluştur
genre_map = {v: k.title() for k, v in GENRES.items()}

def get_movies_by_genres_and_keywords(genres_list=None, keywords=None):
    """
    Belirli türler (ve opsiyonel olarak anahtar kelimeler) ile TMDb API üzerinden film araması yapar.
    :param genres_list: ["aksiyon", "komedi"] gibi bir liste
    :param keywords: (şu an kullanılmıyor ama genişletilebilir)
    :return: Film sonuçlarını içeren bir liste
    """
    print("🎬 get_movies_by_genres_and_keywords çalıştı")
    print("➡️ Gelen türler:", genres_list)
    print("➡️ Gelen anahtar kelimeler:", keywords)

    url = "https://api.themoviedb.org/3/discover/movie"

    # Türleri TMDb'nin beklediği ID formatına çevir
    genre_ids = [str(GENRES.get(tur.lower())) for tur in genres_list or [] if GENRES.get(tur.lower())]

    # API parametreleri
    params = {
        "api_key": TMDB_API_KEY,
        "language": "tr-TR",                   # Türkçe dilinde sonuçlar
        "sort_by": "popularity.desc",          # Popülerliğe göre sırala
        "with_genres": ",".join(genre_ids) if genre_ids else None,  # Tür filtrelemesi
        "page": 1                               # İlk sayfayı getir
    }

    # API isteği gönder
    response = requests.get(url, params=params)
    data = response.json()
    
    # Film sonuçlarını döndür
    return data.get("results", [])

def get_movie_details(movie_id):
    """
    Belirli bir film ID'si ile detaylı film bilgilerini (oyuncular dahil) getirir.
    :param movie_id: TMDb film ID'si
    :return: JSON formatında detaylı bilgi
    """
    url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "tr-TR",
        "append_to_response": "credits"  # Oyuncular ve ekip bilgilerini de ekle
    }

    # API isteği gönder
    response = requests.get(url, params=params)
    return response.json()

def get_watch_providers(movie_id):
    """
    Belirli bir filmin Türkiye'de hangi platformlarda izlenebileceğini döndürür.
    :param movie_id: TMDb film ID'si
    :return: Platform bilgilerini içeren liste (örneğin Netflix, Disney+ vs.)
    """
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers"
    params = {"api_key": TMDB_API_KEY}

    # API isteği gönder
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        # Sadece Türkiye (TR) için olan ve 'flatrate' (abonelikle izlenebilir) platformları al
        return data.get("results", {}).get("TR", {}).get("flatrate", [])
    
    # Başarısız istek durumunda boş liste döndür
    return []
