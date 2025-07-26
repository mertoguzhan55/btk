import re

def regex_for_id_extracting_from_the_link(url):
    """
    Verilen YouTube URL'sinden video ID'sini döndürür.
    """
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Geçerli bir YouTube video ID bulunamadı.")
    

if __name__ == "__main__":
    print(regex_for_id_extracting_from_the_link("https://www.youtube.com/watch?v=PiCn6AH8FCI"))