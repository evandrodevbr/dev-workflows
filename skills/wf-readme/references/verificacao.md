# Comandos de verificação do README

Rode da raiz do repositório.

```bash
# Links locais que não existem no disco
grep -oE '\]\([^)#]+' README.md | sed 's/^](//' | grep -vE '^(https?:|mailto:)' \
  | while read -r p; do [ -e "$p" ] || echo "FALTA: $p"; done

# Links externos que não respondem 2xx/3xx
grep -oE 'https?://[^) >"]+' README.md | sort -u | while read -r u; do
  c=$(curl -sIL -o /dev/null -w '%{http_code}' --max-time 10 "$u")
  case "$c" in 2*|3*) ;; *) echo "$c $u";; esac
done

# TODO esquecido
grep -n 'TODO' README.md

# Quick start num clone limpo (troque pelos comandos do README)
tmp=$(mktemp -d) && git clone -q . "$tmp/repo" && cd "$tmp/repo"
# ... cole aqui os comandos de instalação e quick start, na ordem do README
```

Para CLI, compare a seção de uso com `<cli> --help`. Para API, rode o `curl` do README contra o
servidor local e confira o status. Anote no relatório cada comando e o resultado.
