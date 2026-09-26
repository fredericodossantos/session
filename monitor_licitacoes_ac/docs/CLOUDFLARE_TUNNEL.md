# Publicação no Cloudflare

O monitor está publicado por um Cloudflare Tunnel com o hostname:

`https://licitacoes-ac.98fred.dev/`

O túnel `monitor-licitacoes-ac-go` encaminha para o servidor local em
`http://127.0.0.1:8765`. O endereço foi testado sem autenticação e abre a
interface web do monitor.

## Execução local

Para subir a interface e o acesso público de uma vez, dê duplo clique em
`subir_publico.bat` na pasta do projeto. O arquivo inicia o servidor Python, o
conector `cloudflared` e abre `https://licitacoes-ac.98fred.dev/` no navegador.
O computador precisa permanecer ligado enquanto o endereço estiver sendo usado.

Mantenha o servidor web e o conector `cloudflared` em execução na máquina que
possui o projeto:

```powershell
Set-Location C:\dev\session\monitor_licitacoes_ac
.\.venv\Scripts\python.exe -m monitor_ac.web --host 127.0.0.1 --port 8765
```

O lançador lê o token do arquivo local `cloudflare-tunnel.token`. Esse arquivo
é ignorado pelo Git e contém uma credencial secreta: não o envie para o
repositório nem o compartilhe em mensagens. Se o token for revogado no
Cloudflare, substitua o conteúdo desse arquivo pelo novo token.

Se o computador desligar ou os processos forem encerrados, o endereço ficará
indisponível até que ambos sejam iniciados novamente. Para operação contínua,
instale o `cloudflared` como serviço do Windows usando o comando fornecido pelo
Cloudflare e configure o servidor Python para iniciar com o Windows.
