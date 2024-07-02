from flask import Flask,request, render_template, jsonify

import os

import psycopg2
from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
# from pdfminer.high_level import extract_text


app = Flask(__name__)

def text_to_vector(text):

    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained("cl-tohoku/bert-base-japanese")
    model = AutoModel.from_pretrained("cl-tohoku/bert-base-japanese")

    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).squeeze().numpy()



@app.route('/', methods=['GET','POST'])
def rag_home():
    
    # print('Enters rag_home')

    if request.method == "GET":

        return render_template('index.html')


    # data = request.get_json()

    # print('The post data is ' , data)

    # # Assuming the parameter is named 'parameter'
    # if 'query_term' in data:
    #     query_value = data['query_term']
    #     # Here you can process param_value as needed
    #     # For example, you could return it in a JSON response
    #     # return jsonify({'message': 'Received parameter', 'parameter': query_value}), 200
    # else:
    #     return jsonify({'error': 'Parameter not found in request'}), 400

        
@app.route('/rag_post', methods=['POST'])
def rag_post():


    # Database connection details
    DB_USER = os.getenv("SIC_DB_USER")
    DB_PASS = os.getenv("SIC_DB_PASS")
    DB_HOST = os.getenv("SIC_DB_HOST")
    DB_PORT = 5432
    DB_NAME = "postgres"


    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )

    cur = conn.cursor()

    query_value = request.form['query_term']
    dept_value = request.form['dept']

    if query_value == None or dept_value == None:
        return jsonify({'error': 'Parameter not found in request'}), 400

    query = query_value
    post_department = dept_value

    query_vector = text_to_vector(query)

    # Convert the numpy array to a list for querying
    query_vector_list = query_vector.tolist()

    # Find the most similar document
    search_query = """
        SELECT id, filename, content, vector <-> %s::vector AS distance
        FROM rag_vector_db
        WHERE department = %s
        ORDER BY distance
    """
    cur.execute(search_query, (query_vector_list, post_department))
    # result = cur.fetchone()
    result = cur.fetchall()
    # print(' **************** /n /n ' , type(result) , result[0][1])
    # print(f"一番位置するドキュメントは: {result[0][1]}, Distance: {result[0][3]}")
    # print(f"二番位置するドキュメントは: {result[1][1]}, Distance: {result[1][3]}")
    # print(f"三番位置するドキュメントは: {result[2][1]}, Distance: {result[2][3]}")
    # print(f"Document Content: {result[1]}")

    # Close connection
    cur.close()
    conn.close()

    # response_text = "the Result is {} ".format(result)

    response_text = {
        'document_title' : result[0][1],
        'document_content' : result[0][2]
    }

    return jsonify(message=response_text)


@app.route('/robots933456.txt')
def health_check():
    return 'Healthy', 200


if __name__ == "__main__":
    app.run(host='0.0.0.0' , port='80', debug=True)