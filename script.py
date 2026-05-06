import json
import os
import requests
import time
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

def coletar_fii_via_scraperapi_js():
    url = 'https://fundamentus.com.br/fii_buscaavancada.php'
    
    # Código JavaScript a ser injetado na página
    js_code = """
    (function() {
        var btn = document.querySelector('.buscar');
        if (btn) {
            btn.click();
            return 'clicked';
        } else {
            return 'button_not_found';
        }
    })();
    """
    
    # Parâmetros da ScraperAPI
    params = {
        'api_key': SCRAPERAPI_KEY,
        'url': url,
        'render': 'true',
        'js_code': js_code,
        'wait': 5000   # aguarda 5 segundos após o JS
    }
    
    api_url = "http://api.scraperapi.com"
    print("🔁 Enviando requisição com renderização e JS...")
    response = requests.get(api_url, params=params, timeout=90)
    
    print(f"📡 Status code: {response.status_code}")
    if response.status_code != 200:
        raise Exception(f"ScraperAPI falhou: {response.status_code}")
    
    html = response.text
    with open('debug.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("🔍 INÍCIO DO HTML (1000 caracteres):")
    print(html[:1000])
    
    soup = BeautifulSoup(html, 'html.parser')
    tabela = soup.find('table', id='tabelaResultado')
    if not tabela:
        raise Exception("Tabela não encontrada mesmo após renderização com clique.")
    
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
        raise Exception("SCRAPERAPI_KEY não encontrada")
    df = coletar_fii_via_scraperapi_js()
    enviar_para_sheets(df)
    print(f"✅ {len(df)} FIIs enviados para a planilha!")
