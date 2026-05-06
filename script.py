import json
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

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
    # URL de destino
    target_url = "https://fundamentus.com.br/fii_buscaavancada.php"
    # Monta a URL da ScraperAPI com parâmetros para renderizar JS e aguardar 5 segundos
    scraper_url = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={target_url}&render=true&wait=5000"
    
    print(f"🔍 Acessando via ScraperAPI...")
    response = requests.get(scraper_url, timeout=60)
    if response.status_code != 200:
        raise Exception(f"Erro na ScraperAPI: {response.status_code}")
    
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    
    # Encontra a tabela pelo ID
    tabela = soup.find('table', id='tabelaResultado')
    if not tabela:
        # Fallback: encontra a primeira tabela com pelo menos 10 colunas
        tabelas = soup.find_all('table')
        for t in tabelas:
            cabecalhos = t.find_all('th')
            if len(cabecalhos) >= 10:
                tabela = t
                break
        if not tabela:
            raise Exception("Tabela não encontrada na página")
    
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
        raise Exception("SCRAPERAPI_KEY não definida no ambiente")
    df = coletar_fii_via_scraperapi()
    enviar_para_sheets(df)
    print(f"✅ {len(df)} FIIs enviados para a planilha!")
