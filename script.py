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

def coletar_fii():
    url = 'https://fundamentus.com.br/fii_buscaavancada.php'
    payload = {
        'negociados': 'on',
        'submit': 'BUSCAR'
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # Monta URL do ScraperAPI (usando método POST)
    proxy_url = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={url}&method=post&render=false"
    
    print("🔁 Enviando requisição via ScraperAPI...")
    response = requests.post(proxy_url, data=payload, headers=headers, timeout=60)
    
    print(f"📡 Status code: {response.status_code}")
    
    if response.status_code != 200:
        raise Exception(f"ScraperAPI retornou {response.status_code}")
    
    html = response.text
    
    # Salva HTML completo (para artefato)
    with open('debug.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    # Imprime primeiros 1000 caracteres no log (para diagnóstico rápido)
    print("\n🔍 INÍCIO DO HTML RECEBIDO (1000 caracteres):")
    print(html[:1000])
    print("\n...\n")
    
    soup = BeautifulSoup(html, 'html.parser')
    tabela = soup.find('table', id='tabelaResultado')
    
    if not tabela:
        # Se não achou a tabela, tenta encontrar alguma tabela grande
        todas = soup.find_all('table')
        print(f"🔎 Nenhuma tabela com id='tabelaResultado'. Encontradas {len(todas)} tabelas.")
        for i, t in enumerate(todas):
            linhas = len(t.find_all('tr'))
            print(f"  Tabela {i}: {linhas} linhas")
        raise Exception("Tabela #tabelaResultado não encontrada. Verifique o conteúdo do debug.html")
    
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
    df = coletar_fii()
    enviar_para_sheets(df)
    print(f"✅ {len(df)} FIIs enviados para a planilha!")
