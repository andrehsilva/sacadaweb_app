import os

import io
import base64
from flask import Flask, render_template, url_for, send_file, request, jsonify, make_response
import qrcode
import re
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from weasyprint import HTML

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# 1. Inicialização e Configuração
app = Flask(__name__)

# Configura a URI do banco de dados a partir da variável de ambiente
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    # Para este novo projeto, vamos nomear o banco local como 'sacadaweb.db'
    db_url = "sqlite:///sacadaweb.db"

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Expressão Regular para validação do telefone
PHONE_REGEX = r'^\d{11}$'

# 2. Definição do Modelo do Banco de Dados (Tabela de Leads)
class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    empresa = db.Column(db.String(100), nullable=False)
    whatsapp = db.Column(db.String(20), nullable=False, unique=True) # WhatsApp como identificador único
    email = db.Column(db.String(120), nullable=False, unique=True)

    def __repr__(self):
        return f'<Lead {self.nome} - {self.empresa}>'

# 3. Comando para criar o banco de dados
@app.cli.command("init-db")
def init_db_command():
    """Cria as tabelas do banco de dados."""
    db.create_all()
    print("Banco de dados para SacadaWeb inicializado com sucesso!")

# 4. Definição das Rotas

@app.route('/')
def home():
    """Renderiza a página principal."""
    return render_template('index.html')

@app.route('/educacao')
def educacao():
    """Renderiza a página dedicada ao setor educacional."""
    return render_template('educacao.html')


@app.route('/solucao')
def solucao():
    """Renderiza a página dedicada a soluções."""
    return render_template('solucao.html')
# ============================================

@app.route('/submit', methods=['POST'])
def submit_lead():
    """Recebe, valida e salva os dados do formulário."""
    form_data = request.form
    nome = form_data.get('nome')
    empresa = form_data.get('empresa')
    whatsapp_raw = form_data.get('whatsapp', '')
    email = form_data.get('email')

    if not all([nome, empresa, whatsapp_raw, email]): # Adicionado 'email' aqui também como obrigatório se for o caso
        return jsonify({'status': 'error', 'message': 'Por favor, preencha todos os campos.'}), 400

    whatsapp_clean = re.sub(r'[\(\)\s-]', '', whatsapp_raw)
    if not re.match(PHONE_REGEX, whatsapp_clean):
        return jsonify({'status': 'error', 'message': 'O formato do WhatsApp é inválido. Use apenas números (ex: 5511987654321).'}), 400 # Mensagem mais descritiva
        
    if Lead.query.filter_by(whatsapp=whatsapp_raw).first():
        return jsonify({'status': 'error', 'message': 'Este número de WhatsApp já foi cadastrado.'}), 409 # Sugerido 409
    
    if Lead.query.filter_by(email=email).first():
        return jsonify({'status': 'error', 'message': 'Este e-mail já foi cadastrado.'}), 409 # Sugerido 409

    try:
        new_lead = Lead(nome=nome, empresa=empresa, whatsapp=whatsapp_raw, email=email)
        db.session.add(new_lead)
        db.session.commit()
        print(f"Novo lead salvo: {nome}, Empresa: {empresa}")
        return jsonify({'status': 'success', 'message': 'Seu contato foi enviado com sucesso! Em breve entraremos em contato.'}) # Mensagem de sucesso mais amigável

    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Erro de banco de dados: {e}")
        # Uma mensagem genérica para o usuário é mais segura do que expor detalhes do erro
        return jsonify({'status': 'error', 'message': 'Ocorreu um erro ao tentar salvar seu contato. Por favor, tente novamente mais tarde.'}), 500


@app.route('/leads')
def view_leads():
    """Busca todos os leads e os exibe em uma tabela."""
    try:
        all_leads = Lead.query.order_by(Lead.id.desc()).all()
        return render_template('leads.html', leads=all_leads)
    except Exception as e:
        print(f"Erro ao buscar leads: {e}")
        return "<h1>Erro ao carregar os leads.</h1>"
    

@app.route('/politica-de-privacidade')
def privacy_policy():
    """Renderiza a página de Política de Privacidade."""
    return render_template('politica-de-privacidade.html')

@app.route('/chat')
def chat_demo():
    """Renderiza a página de demonstração do chat."""
    return render_template('chat.html')

@app.route('/contact')
def contact():
    """Renderiza a página de demonstração do chat."""
    return render_template('contact.html')

@app.route('/qrcode')
def qr_code_page():
    # Gera a URL completa para a página de contato.
    # Usar _external=True é ESSENCIAL para que o QR Code funcione fora da sua rede local.
    contact_url = url_for('contact', _external=True)

    # Configura e gera a imagem do QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(contact_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Salva a imagem em um buffer de memória em vez de um arquivo
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    
    # Codifica a imagem em Base64 para embutir diretamente no HTML
    img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    # Renderiza o template, passando os dados da imagem
    return render_template('qrcode.html', qr_code_data=img_b64)



@app.route('/download-pdf')
def download_pdf():
    try:
        # Renderiza o template HTML específico para o PDF
        html_string = render_template('contact_pdf.html')

        # Cria o PDF em memória a partir do HTML renderizado
        # base_url é importante para o WeasyPrint encontrar arquivos estáticos como imagens
        pdf_file = HTML(string=html_string, base_url=request.base_url).write_pdf()

        # Cria a resposta para o navegador forçar o download
        response = make_response(pdf_file)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename="contato-andre-sacadaweb.pdf"'

        return response

    except Exception as e:
        print(f"Erro ao gerar PDF: {e}")
        return "<h1>Ocorreu um erro ao gerar o PDF.</h1>", 500
    

# ================================================================

# 5. Ponto de Entrada
if __name__ == '__main__':
    app.run(debug=True)