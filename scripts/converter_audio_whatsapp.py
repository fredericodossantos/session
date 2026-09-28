"""Converte um áudio (ex.: .m4a) para um formato compacto, pronto para o WhatsApp.

Formatos:
  opus (padrão) -> .ogg com codec Opus, mono. É o formato nativo das mensagens
                   de voz do WhatsApp e toca direto em qualquer Android.
                   Fica bem menor que o .m4a mantendo a fala clara.
  mp3           -> .mp3 mono. Um pouco maior, mas toca em absolutamente tudo.

Uso:
  python converter_audio_whatsapp.py
  python converter_audio_whatsapp.py "C:\\caminho\\outro_audio.m4a"
  python converter_audio_whatsapp.py --formato mp3
  python converter_audio_whatsapp.py --kbps 16      (ainda menor)

Requer o ffmpeg. Se ele não estiver instalado, rode uma vez:
  pip install imageio-ffmpeg
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

NOME_PADRAO = "Como_lucrar_em_licitações_sem_falir.m4a"

FORMATOS = {
    # extensão, argumentos do codec, bitrate padrão (kbps)
    "opus": (".ogg", ["-c:a", "libopus", "-application", "voip", "-ar", "48000"], 24),
    "mp3": (".mp3", ["-c:a", "libmp3lame", "-ar", "44100"], 64),
}


def localizar_ffmpeg():
    caminho = shutil.which("ffmpeg")
    if caminho:
        return caminho
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit(
            "ffmpeg não encontrado.\n"
            "Instale com:  pip install imageio-ffmpeg\n"
            "(ou instale o ffmpeg e coloque-o no PATH)."
        )


def tamanho_mb(caminho):
    return caminho.stat().st_size / (1024 * 1024)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "entrada",
        nargs="?",
        default=str(Path.home() / "Downloads" / NOME_PADRAO),
        help="arquivo de áudio de entrada (padrão: o .m4a na pasta Downloads)",
    )
    parser.add_argument("--formato", choices=FORMATOS, default="opus", help="formato de saída (padrão: opus)")
    parser.add_argument("--kbps", type=int, help="bitrate em kbps (padrão: 24 para opus, 64 para mp3)")
    args = parser.parse_args()

    entrada = Path(args.entrada).expanduser()
    if not entrada.is_file():
        sys.exit(f"Arquivo não encontrado: {entrada}")

    extensao, codec, kbps_padrao = FORMATOS[args.formato]
    kbps = args.kbps or kbps_padrao
    saida = entrada.with_suffix(extensao)

    comando = [
        localizar_ffmpeg(),
        "-hide_banner", "-loglevel", "error", "-stats",
        "-y",
        "-i", str(entrada),
        "-vn",            # descarta capa/imagem embutida
        "-map_metadata", "-1",
        "-ac", "1",       # mono: fala não precisa de estéreo
        *codec,
        "-b:a", f"{kbps}k",
        str(saida),
    ]

    print(f"Convertendo {entrada.name} -> {saida.name} ({args.formato}, {kbps} kbps, mono)...")
    resultado = subprocess.run(comando)
    if resultado.returncode != 0:
        sys.exit("A conversão falhou (veja a mensagem do ffmpeg acima).")

    antes, depois = tamanho_mb(entrada), tamanho_mb(saida)
    print(f"\nPronto: {saida}")
    print(f"Tamanho: {antes:.1f} MB -> {depois:.1f} MB ({100 * depois / antes:.0f}% do original)")
    if depois > 100:
        print("Aviso: acima de 100 MB o WhatsApp só envia como documento. Tente --kbps 16.")


if __name__ == "__main__":
    main()
