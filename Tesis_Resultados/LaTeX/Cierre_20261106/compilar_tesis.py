"""Compila la copia local de Overleaf y conserva salida, código de retorno y hashes."""
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

documento = Path(__file__).resolve().parent / "documento"
salida = documento / "compilacion"
salida.mkdir(exist_ok=True)
marca = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
comando = ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error",
           "-file-line-error", "-outdir=compilacion", "main.tex"]
inicio = time.monotonic()
with (salida / f"compilacion_{marca}.log").open("w") as registro:
    resultado = subprocess.run(comando, cwd=documento, stdout=registro, stderr=subprocess.STDOUT)
fuentes = sorted(documento.glob("*.tex"))
informe = {
    "fecha_UTC": marca,
    "comando": comando,
    "salida": resultado.returncode,
    "segundos": time.monotonic() - inicio,
    "fuentes_sha256": {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in fuentes},
}
(salida / f"compilacion_{marca}.json").write_text(json.dumps(informe, indent=2))
print(json.dumps(informe, indent=2), flush=True)
print(salida / "main.pdf", flush=True)
raise SystemExit(resultado.returncode)
