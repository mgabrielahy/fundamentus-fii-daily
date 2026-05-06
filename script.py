import json
import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SPREADSHEET_ID = '1bjr8ZMSV2RL3c7GQOLduAmb4NNZ3blpoulzbSknRmtw'
SCRAPERAPI_KEY = os.environ.get('SCRAPERAPI_KEY')

def enviar_para_sheets(df):
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if not creds_json:
        raise Exception("GOOGLE_CREDENTIALS not found")
    creds_dict = json.loads(creds_json)
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID)
    try:
        worksheet = sheet.worksheet('Dados')
        worksheet.clear()
    except:
        worksheet = sheet.add_worksheet(title='Dados', rows=str(len(df)+1), cols=str(len(df.columns)))
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())

def limpar_valor(valor):
    if not isinstance(valor, str):
        return float(valor) if valor else 0.0
    valor = valor.strip()
    if not valor:
        return 0.0
    valor = valor.replace('R$', '').strip()
    if '%' in valor:
        valor = valor.replace('%', '').strip()
        valor = valor.replace(',', '.')
        if '.' in valor:
            partes = valor.split('.')
            if len(partes) > 1 and partes[-1].isdigit():
                valor = ''.join(partes[:-1]) + '.' + partes[-1]
        try:
            return float(valor)
        except:
            return 0.0
    if ',' in valor:
        partes = valor.split(',')
        ultima = partes[-1]
        inteiro = ''.join(partes[:-1]).replace('.', '')
        valor = f"{inteiro}.{ultima}"
    else:
        valor = valor.replace('.', '')
    try:
        return float(valor)
    except:
        return 0.0

def coletar_fii_via_scraperapi():
    target_url = "https://fundamentus.com.br/fii_buscaavancada.php"
    # Parâmetros: render=false (usaremos nosso próprio formulário POST) ou render=true?
    # Vamos tentar primeiro com o POST simulando o clique no botão.
    # Melhor: usar a URL de busca com parâmetros para já receber a tabela?
    # Alternativa: usar a URL de resultado após envio do formulário.
    
    # A ScraperAPI permite enviar POST também. Vamos tentar realizar o POST diretamente.
    # Construir payload do formulário.
    payload = {
        'ffo_min': '',
        'ffo_max': '',
        'dy_min': '',
        'dy_max': '',
        'pvp_min': '',
        'pvp_max': '',
        'vmkt_min': '',
        'vmkt_max': '',
        'qtdim_min': '',
        'qtdim_max': '',
        'precom2_min': '',
        'precom2_max': '',
        'aluguelm2_min': '',
        'aluguelm2_max': '',
        'caprate_min': '',
        'caprate_max': '',
        'vacancia_min': '',
        'vacancia_max': '',
        'segmento': 'todos',
        'submit': 'BUSCAR'
    }
    
    # Usar ScraperAPI para enviar POST
    api_url = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={target_url}&render=true&wait=10000&keep_headers=true"
    # Como enviar POST com dados?
    # ScraperAPI suporta método POST através de parâmetro "method=post" e data no corpo.
    # Vamos usar a URL com method=post e enviar o payload como form data.
    post_url = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={target_url}&method=post&render=true&wait=10000"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(post_url, data=payload, headers=headers, timeout=60)
    
    if response.status_code != 200:
        raise Exception(f"Erro na ScraperAPI: {response.status_code}")
    
    html = response.text
    # Salvar HTML para debug em caso de falha
    with open('debug.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Tenta encontrar a tabela por ID
    tabela = soup.find('table', id='tabelaResultado')
    if not tabela:
        # Tenta encontrar pela classe ou pela primeira tabela com th
        tabela = soup.find('table', class_='resultado')
        if not tabela:
            todas_tabelas = soup.find_all('table')
            for t in todas_tabelas:
                if len(t.find_all('th')) >= 10:
                    tabela = t
                    break
        if not tabela:
            # Talvez a página tenha mostrado erro ou ainda esteja carregando
            # Verifica se há captcha ou mensagem de proteção
            if "Just a moment" in html:
                raise Exception("ScraperAPI não conseguiu passar do Cloudflare - página de verificação")
            elif "Nenhum resultado encontrado" in html:
                # Não há resultados? Talvez POST não funcionou.
                raise Exception("Nenhum resultado encontrado - payload pode estar incorreto")
            else:
                raise Exception("Tabela não encontrada na página. HTML salvo como debug.html")
    
    linhas = tabela.find_all('tr')
    dados_brutos = []
    for linha in linhas:
        celulas = linha.find_all('td')
        if celulas:
            dados_brutos.append([cel.get_text(strip=True) for cel in celulas[:13]])
    
    colunas = ['Papel', 'Segmento', 'Cotação', 'FFO Yield', 'Dividend Yield', 'P/VP',
               'Valor de Mercado', 'Liquidez', 'Qtd de imóveis', 'Preço do m2',
               'Aluguel por m2', 'Cap Rate', 'Vacância Média']
    df = pd.DataFrame(dados_brutos, columns=colunas)
    for col in df.columns[2:]:
        df[col] = df[col].apply(limpar_valor)
    return df

if __name__ == "__main__":
    if not SCRAPERAPI_KEY:
        raise Exception("SCRAPERAPI_KEY não definida")
    df = coletar_fii_via_scraperapi()
    enviar_para_sheets(df)
    print(f"✅ {len(df)} FIIs enviados para a planilha!")
