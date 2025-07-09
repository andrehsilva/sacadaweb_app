import os
import re
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

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

@app.route('/submit', methods=['POST'])
def submit_lead():
    """Recebe, valida e salva os dados do formulário."""
    form_data = request.form
    nome = form_data.get('nome')
    empresa = form_data.get('empresa')
    whatsapp_raw = form_data.get('whatsapp', '')
    email = form_data.get('email')

    if not all([nome, empresa, whatsapp_raw]):
        return jsonify({'status': 'error', 'message': 'Todos os campos são obrigatórios.'}), 400

    whatsapp_clean = re.sub(r'[\(\)\s-]', '', whatsapp_raw)
    if not re.match(PHONE_REGEX, whatsapp_clean):
        return jsonify({'status': 'error', 'message': 'Formato de telefone inválido.'}), 400
        
    if Lead.query.filter_by(whatsapp=whatsapp_raw).first():
        return jsonify({'status': 'error', 'message': 'Este número de WhatsApp já foi cadastrado.'}), 400
    
    if Lead.query.filter_by(email=email).first():
        return jsonify({'status': 'error', 'message': 'Este e-mail já foi cadastrado.'}), 400

    try:
        new_lead = Lead(nome=nome, empresa=empresa, whatsapp=whatsapp_raw, email=email)
        db.session.add(new_lead)
        db.session.commit()
        print(f"Novo lead salvo: {nome}, Empresa: {empresa}")
        return jsonify({'status': 'success', 'message': 'Lead salvo com sucesso!'})

    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Erro de banco de dados: {e}")
        return jsonify({'status': 'error', 'message': 'Erro ao salvar os dados no banco.'}), 500

@app.route('/leads')
def view_leads():
    """Busca todos os leads e os exibe em uma tabela."""
    try:
        all_leads = Lead.query.order_by(Lead.id.desc()).all()
        return render_template('leads.html', leads=all_leads)
    except Exception as e:
        print(f"Erro ao buscar leads: {e}")
        return "<h1>Erro ao carregar os leads.</h1>"

# 5. Ponto de Entrada
if __name__ == '__main__':
    app.run(debug=True)