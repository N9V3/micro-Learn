from flask import Flask, render_template, request, jsonify
import instaloader
from moviepy import VideoFileClip
import whisper
import os
import time
import threading

app = Flask(__name__)

# Função para esperar arquivo estar pronto
def esperar_arquivo_pronto(filepath, timeout=60):
    """Espera até que o arquivo esteja completamente pronto para uso"""
    start_time = time.time()
    
    while True:
        if time.time() - start_time > timeout:
            raise TimeoutError(f"Timeout esperando arquivo: {filepath}")
        
        if os.path.exists(filepath):
            try:
                # Verifica se o arquivo está estável
                size1 = os.path.getsize(filepath)
                time.sleep(1)
                size2 = os.path.getsize(filepath)
                
                if size1 == size2:
                    # Tenta abrir o arquivo para confirmar que está pronto
                    with open(filepath, 'rb') as f:
                        return True
            except (OSError, IOError):
                pass
        
        print(f"Aguardando arquivo estar pronto: {filepath}")
        time.sleep(1)

# FFmpeg está configurado corretamente
os.environ["PATH"] += os.pathsep + "C:\\ProgramData\\chocolatey\\bin\\ffmpeg.exe"

def baixar_video(instagram_url, pasta_destino="C:\\Users\\Administrator\\Pictures\\instagramSalvos"):
    if not os.path.exists(pasta_destino):
        os.makedirs(pasta_destino)
    
    loader = instaloader.Instaloader(save_metadata=False, download_comments=False)
    shortcode = instagram_url.split('/')[-2]
    post = instaloader.Post.from_shortcode(loader.context, shortcode)
    
    titulo_post = post.title if post.title else f"post_{shortcode}"
    subpasta_destino = os.path.join(pasta_destino, titulo_post.replace("/", "_").replace("\\", "_"))
    os.makedirs(subpasta_destino, exist_ok=True)
    
    loader.dirname_pattern = subpasta_destino
    loader.download_post(post, target=shortcode)
    
    # Procura pelo arquivo de vídeo e espera ele estar pronto
    for arquivo in os.listdir(subpasta_destino):
        if arquivo.endswith(".mp4"):
            video_path = os.path.join(subpasta_destino, arquivo)
            print(f"Aguardando download do vídeo completar: {video_path}")
            esperar_arquivo_pronto(video_path)
            return video_path
    return None

def extrair_audio(video_path, audio_path):
    print(f"Extraindo áudio do vídeo: {video_path}")
    clip = VideoFileClip(video_path)
    clip.audio.write_audiofile(audio_path)
    clip.close()
    
    # Espera o arquivo de áudio estar pronto
    print(f"Aguardando arquivo de áudio estar pronto: {audio_path}")
    esperar_arquivo_pronto(audio_path)

def transcrever_audio(audio_path):
    print(f"Iniciando transcrição do áudio: {audio_path}")
    modelo = whisper.load_model("base")
    resultado = modelo.transcribe(audio_path)
    transcricao_path = audio_path.replace(".mp3", ".txt")
    
    with open(transcricao_path, "w", encoding="utf-8") as f:
        f.write(resultado['text'])
    
    # Espera o arquivo de transcrição estar pronto
    esperar_arquivo_pronto(transcricao_path)
    print(f"Transcrição salva em: {transcricao_path}")

def processar_urls(urls, pasta_destino):
    """Processa uma lista de URLs do Instagram"""
    for url in urls:
        url = url.strip()
        print(f"\nProcessando URL: {url}")
        
        try:
            # Download do vídeo
            video_path = baixar_video(url, pasta_destino)
            if not video_path:
                print(f"Não foi possível baixar o vídeo para a URL: {url}")
                continue
            
            # Extração do áudio
            audio_path = video_path.replace(".mp4", ".mp3")
            extrair_audio(video_path, audio_path)
            
            # Transcrição
            transcrever_audio(audio_path)
            
            print(f"Processamento completo para: {url}")
            
        except Exception as e:
            print(f"Erro ao processar {url}: {str(e)}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/processar', methods=['POST'])
def processar():
    data = request.json
    urls = data['urls'].split(',')
    pasta_destino = "C:\\Users\\Administrator\\Pictures\\instagramSalvos"
    
    # Executa o processamento em uma thread separada
    threading.Thread(target=processar_urls, args=(urls, pasta_destino)).start()
    
    return jsonify({"status": "Processamento iniciado"})

if __name__ == '__main__':
    app.run(debug=True)