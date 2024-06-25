from flask import Flask, jsonify

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



@app.route('/')
def rag_home():
    
    print('Enters rag_home')

    
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

    


    query = "旅費規程 "

    query_vector = text_to_vector(query)

    # Convert the numpy array to a list for querying
    query_vector_list = query_vector.tolist()

    # Find the most similar document
    search_query = """
        SELECT id, filename, content, vector <-> %s::vector AS distance
        FROM rag_vector_db
        ORDER BY distance
    """
    cur.execute(search_query, (query_vector_list,))
    # result = cur.fetchone()
    result = cur.fetchall()
    # print(' **************** /n /n ' , type(result) , result[0][1])
    print(f"一番位置するドキュメントは: {result[0][1]}, Distance: {result[0][3]}")
    print(f"二番位置するドキュメントは: {result[1][1]}, Distance: {result[1][3]}")
    print(f"三番位置するドキュメントは: {result[2][1]}, Distance: {result[2][3]}")
    # print(f"Document Content: {result[1]}")

    # Close connection
    cur.close()
    conn.close()

    response_text = "the Result is {} ".format(result)

    return jsonify(message=response_text)


@app.route('/robots933456.txt')
def health_check():
    return 'Healthy', 200


if __name__ == "__main__":
    app.run(host='0.0.0.0' , port='80', debug=True)

