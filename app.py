from flask import Flask, request, jsonify
import json
from dotenv import load_dotenv
import os
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
from flasgger import Swagger


load_dotenv()

app = Flask(__name__)

CORS(app, origins="*")
ADM_USUARIO = os.getenv("ADM_USUARIO")
ADM_SENHA = os.getenv("ADM_SENHA")

# Versão do OPEN API
app.config['SWAGGER'] = {
    'openapi' : '3.0.0'
}
# Chamar o OPENAPI para o código
swagger = Swagger(app, template_file = 'openapi.yaml')

if os.getenv("VERCEL"):
    #ONLINE NA VERCEL
    cred = credentials.Certificate(json.loads(os.getenv("FIREBASE_KEY")))

else:
    #LOCAL
    cred = credentials.Certificate("firebase.json")


firebase_admin.initialize_app(cred)

db = firestore.client()




##################
#     ROTAS
##################

@app.route('/')
def root():
    return jsonify({
        "Api":"Sistema de gestão do churras de gato",
        "version":"1.0.0",
        "autor" :"João Victor e Julio"
    }),200


@app.route('/estoque')
def mostrar_estoque():
    produtos = []
    
    #Busca todos os dados da coleção "cliente" do Data Base
    lista = db.collection('produtos').stream()


    for produto in lista:
        dados = produto.to_dict()
        produtos.append(dados)

    return jsonify(produtos), 200

@app.route('/estoque', methods=['POST'])
def cadastrar_estoque():
    dados = request.get_json()

    if not dados or "produto" not in dados or "quantidade" not in dados or "validade" not in dados or "marca" not in dados or "categoria" not in dados:
        return jsonify({"message":"error",
                        "error": "Dados inválidos"}), 400

    try:
        # Referenciando o contador no banco de dados
        contador_ref = db.collection("controle").document("contador_id")   
        # Armazenando o valor do contador
        contador_doc = contador_ref.get()
        
        # Verifica se o contador existe, se não existir, cria com valor 0
        if not contador_doc.exists:
            contador_ref.set({"ultimo_id": 0})
            ultimo_id = 0
        else:
            # Transformamos em dicionário e pegamos o valor guardado no campo "ultimo_id"
            ultimo_id = contador_doc.to_dict().get("ultimo_id", 0)
        
        # Somar 1 ao ultimo id
        novo_id = ultimo_id + 1  
        # Atualiza o ultimo_id para o novo_id
        contador_ref.update({"ultimo_id": novo_id})
        
        # CORREÇÃO: Mudar de "produtor" para "produtos"
        db.collection("produtos").add({
            "id": novo_id,
            "produto": dados["produto"],
            "marca": dados["marca"],
            "quantidade": dados["quantidade"],
            "validade": dados["validade"],
            "categoria": dados["categoria"]
        })    
        
        return jsonify({
            "message": "Produto cadastrado com sucesso",
            "id": novo_id
        }), 201        
        
    except Exception as e:
        return jsonify({
            "error": f"Falha no cadastro do produto: {str(e)}"
        }), 400

@app.route('/estoque/<int:id>', methods=['PATCH'])
def atualizar_estoque(id):
    dados = request.get_json()
    
    # Verifica se os dados foram enviados
    if not dados:
        return jsonify({"error": "Dados não fornecidos"}), 400
    
    # Campos permitidos para atualização
    campos_permitidos = ['produto', 'quantidade', 'validade', 'marca', 'categoria']
    update_produto = {}
    
    # Filtra apenas os campos permitidos que foram enviados
    for campo in campos_permitidos:
        if campo in dados:
            # Validação específica para quantidade
            if campo == 'quantidade' and not isinstance(dados['quantidade'], (int, float)):
                return jsonify({"error": "A quantidade deve ser um número"}), 400
            # Validação para quantidade negativa
            if campo == 'quantidade' and dados['quantidade'] < 0:
                return jsonify({"error": "A quantidade não pode ser negativa"}), 400
            
            update_produto[campo] = dados[campo]
    
    # Verifica se pelo menos um campo válido foi enviado
    if not update_produto:
        return jsonify({"error": "Nenhum campo válido para atualização"}), 400
    
    try:
        # Busca o produto pelo ID
        produtos_ref = db.collection('produtos')
        query = produtos_ref.where('id', '==', id).limit(1).get()
        
        if not query:
            return jsonify({"error": f"Produto com ID {id} não encontrado"}), 404
        
        # Obtém a referência do documento
        doc_ref = produtos_ref.document(query[0].id)
        
        # Atualiza apenas os campos enviados
        doc_ref.update(update_produto)
        
        return jsonify({
            "message": "Produto atualizado com sucesso",
            "produto_id": id,
            "campos_atualizados": list(update_produto.keys())
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Falha na atualização do produto: {str(e)}"}), 400
    


@app.route('/estoque/<int:id>', methods=['DELETE'])
def deletar_produto(id):
    
    # Busca o produto pelo ID
    docs = db.collection("produtos").where("id", "==", id).limit(1).get()
    
    if not docs:
        return jsonify({"error": f"Produto com ID {id} não encontrado"}), 404
    
    try:
        # Pega o ID do documento (a chave alfanumérica do Firestore)
        doc_id = docs[0].id
        
        # Deleta o documento usando esse ID
        db.collection("produtos").document(doc_id).delete()
        
        return jsonify({
            "message": "Produto excluído com sucesso!",
            "produto_id": id
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Erro ao processar exclusão: {str(e)}"}), 500

#=====================================
# Rotas de tratamento de erros
#=====================================
    

@app.errorhandler(404)
def erro404(error):
    return jsonify({"error": "URL não encontrada"}), 404
   
@app.errorhandler(500)
def erro500(error):
    return jsonify({"error": "Servidor interno com falhas. Tente mais tarde"}) 

if __name__ == "__main__":
    app.run(debug=True)


   