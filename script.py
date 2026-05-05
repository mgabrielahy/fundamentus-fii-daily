import json
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# ================= CONFIGURAÇÃO DO GOOGLE SHEETS =================
SPREADSHEET_ID = '1bjr8ZMSV2RL3c7GQOLduAmb4NNZ3blpoulzbSknRmtw'

def enviar_para_sheets(df):
    # Lê a credencial a partir da variável de ambiente (secret do GitHub)
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if not creds_json:
        raise Exception("GOOGLE_CREDENTIALS not found in environment variables")
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
        # remove pontos de milhar (caso existam)
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
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.binary_location = "/usr/bin/google-chrome"
    from selenium.webdriver.chrome.service import Service
    service = Service('/usr/local/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 20)
    try:
        driver.get('https://fundamentus.com.br/fii_buscaavancada.php')
        btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.buscar')))
        btn.click()
        time.sleep(5)
        tabela = wait.until(EC.presence_of_element_located((By.ID, 'tabelaResultado')))
        linhas = tabela.find_elements(By.TAG_NAME, 'tr')
        dados_brutos = []
        for linha in linhas:
            celulas = linha.find_elements(By.TAG_NAME, 'td')
            if celulas:
                dados_brutos.append([cel.text for cel in celulas[:13]])
        colunas = ['Papel', 'Segmento', 'Cotação', 'FFO Yield', 'Dividend Yield', 'P/VP',
                   'Valor de Mercado', 'Liquidez', 'Qtd de imóveis', 'Preço do m2',
                   'Aluguel por m2', 'Cap Rate', 'Vacância Média']
        df = pd.DataFrame(dados_brutos, columns=colunas)
        for col in df.columns[2:]:
            df[col] = df[col].apply(limpar_valor)
        return df
    finally:
        driver.quit()

if __name__ == "__main__":
    df = coletar_fii()
    enviar_para_sheets(df)
    print(f"✅ {len(df)} FIIs enviados para a planilha!")
