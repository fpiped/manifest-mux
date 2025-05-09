# streaming-downloader

Downloader per titoli via `yt-dlp`. Passa un URL e scarica il video in MKV con
tutte le tracce audio disponibili (incluse, quando presenti, originale, italiano
e inglese) e tutti i sottotitoli incorporati.

## Installazione

```bash
uv sync
```

Su macOS, `ffmpeg` può essere installato con Homebrew:

```bash
brew install ffmpeg
```

## Utilizzo

```bash
uv run streaming-downloader 'https://example.com/it/watch/12015?e=38156' \
  --output-path ~/Movies/mio-titolo.mkv
```

Parametri:
- `url` (obbligatorio): URL https del titolo
- `--output-path FILE`: percorso del file MKV finale (default: `~/Downloads/<titolo>.mkv`)
- `--concurrent-fragments N`: frammenti in parallelo (default: 1)

Racchiudi sempre l'URL tra apici singoli quando lo incolli nel terminale. In
particolare, zsh interpreta `?` come wildcard: senza apici un URL con `?e=...`
viene rifiutato dalla shell prima che il programma possa riceverlo.

Durante il download tutti i file temporanei (frammenti, sottotitoli e stato di
yt-dlp) sono salvati nella directory temporanea del sistema. Al termine viene
conservato solo il file MKV finale nel percorso scelto.

## Configurazione

Copia `.env.example` come `.env` per cambiare i default:

```
SC_CONCURRENT_FRAGMENTS=1
```

## Test

```bash
uv run python -m unittest discover -s tests -v
```
