```markdown
# DDoS Test - Script de Teste de Estresse

⚠️ **AVISO LEGAL**: Este script é apenas para testes educacionais em servidores próprios ou com autorização explícita. O uso em servidores de terceiros sem permissão é ilegal e pode violar leis como a Lei 12.737/2012 no Brasil. Use com responsabilidade!

## Descrição
`ddos_test.py` é um script Python para testes de estresse em servidores web, simulando múltiplas requisições HTTP (GET ou POST). Ele para automaticamente se o servidor ficar inacessível e gera logs detalhados.

## Funcionalidades
- Menu interativo para configurar testes.
- Suporte a requisições GET e POST.
- Parada automática se o servidor cair (erros 500+ ou falhas de conexão).
- Logs com timestamp, status e tempo de resposta.
- Relatório final com total de requisições, sucessos e erros.

## Pré-requisitos
- Python 3.6+
- Biblioteca `requests`: `pip install requests`

## Como Usar
1. Clone o repositório:
   ```bash
   git clone https://github.com/Duhhil/ddos_test.git
   cd ddos_test
