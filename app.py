from flask import Flask,request, render_template, jsonify, redirect, url_for

import os

import psycopg2
from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
from pdfminer.high_level import extract_text

from io import BytesIO

from insertdata import insert_document, delete_document
from inserttags import insert_tag, delete_tag

# Database connection details
DB_USER = os.getenv("SIC_DB_USER")
DB_PASS = os.getenv("SIC_DB_PASS")
DB_HOST = os.getenv("SIC_DB_HOST")
DB_PORT = 5432
DB_NAME = "postgres"

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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

        
@app.route('/rag_post', methods=['POST'])
def rag_post():

    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )

    cur = conn.cursor()

    query_value = request.form['query_term']
    tag_value = request.form['tag']

    if query_value == None or tag_value == None:
        return jsonify({'error': 'Parameter not found in request'}), 400

    query = query_value
    post_tag = tag_value

    query_vector = text_to_vector(query)

    # Convert the numpy array to a list for querying
    query_vector_list = query_vector.tolist()

    # Find the most similar document
    search_query = """
        SELECT t1.id, t2.filename, t2.content, t2.vector <-> %s::vector AS distance
        FROM rag_vector_tag_db t1
        JOIN rag_vector_db t2 ON t1.id = t2.id
        WHERE t1.tag = %s
        ORDER BY distance
    """
    cur.execute(search_query, (query_vector_list, post_tag))
    # result = cur.fetchone()
    result = cur.fetchall()

    # print('result is ' , result , ' and len is ' , len(result))

    if len(result) == 0:
        return jsonify(message="There is no documents matching the tag or the content")

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



# ADMIN

@app.route('/admin', methods=['GET','POST'])
def rag_admin():

    if request.method == "GET":

        conn = psycopg2.connect(
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                host=DB_HOST,
                port=DB_PORT
            )

        cur = conn.cursor()

        # Find the most similar document
        search_query = """
            SELECT id, filename
            FROM rag_vector_db
            ORDER BY id
        """
        cur.execute(search_query)
        # result = cur.fetchone()
        result = cur.fetchall()



        tag_query = """
            SELECT
                t.tag AS TAG,
                string_agg(d.filename, ',' ORDER BY d.id) AS FILENAMES
            FROM
                rag_vector_tag_db t
            JOIN
                rag_vector_db d ON t.id = d.id
            GROUP BY
                t.tag
            ORDER BY
                t.tag;
        """

        cur.execute(tag_query)
        # result = cur.fetchone()
        tags = cur.fetchall()

        # Close connection
        cur.close()
        conn.close()

        # print('Tags are /n' , tags)


        context = {
            'result' : result,
            'tags' : tags
        }

        return render_template('admin.html' , context = context)



@app.route('/file_upload', methods=['GET','POST'])
def file_upload():
    if request.method == "POST":

        if 'file' not in request.files:
            return redirect(request.url)
    
        file = request.files['file']
        
        if file.filename == '':
            return redirect(request.url)

        
        if file and allowed_file(file.filename):
            # Process the file securely (save it, process it, etc.)


            filename = file.filename
            file_contents = file.read()
            extracted_text = extract_text(BytesIO(file_contents))
            document_text = extracted_text 

            
            test = insert_document(filename, document_text)

            # file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # flash('File successfully uploaded')
            # return redirect(url_for('uploaded_file', filename=filename))

            return redirect(url_for('rag_admin'))

        else:
            return redirect(request.url)


    else:

        return render_template('fileupload.html')


@app.route('/file_delete/<file_id>', methods=['GET','POST'])
def file_delete(file_id):

    print('enters file delete with ID ' , file_id)

    delete_document(file_id)

    print('returnde from function with ')

    return redirect(url_for('rag_admin'))
    


@app.route('/tag_upload', methods=['GET','POST'])
def tag_upload():

    conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT
        )


    if request.method == "POST":
        print(request.form)

        tagname = request.form.get('tagname' , None)

        all_docs = request.form.getlist('all_documents_dropdown' , None)
        print('All docs are ' , all_docs)

        if tagname and all_docs:
            insert_tag(tagname,list(all_docs))
            return redirect(url_for('rag_admin'))
        else:
            return redirect(url_for('tag_upload'))


    else:

        cur = conn.cursor()

        # Find the most similar document
        all_documents = """
            SELECT id, filename
            FROM rag_vector_db
            ORDER BY id
        """
        cur.execute(all_documents)
        # result = cur.fetchone()
        result = cur.fetchall()

        context = {
            'result' : result
        }


        return render_template('tagupload.html' , context = context)


@app.route('/tag_update/<tag_name>', methods=['GET','POST'])
def tag_update(tag_name):
    
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )

    if request.method == "POST" :

        tag_name = request.form.get('tag_name' , None)
        all_tag_docs = request.form.getlist('tag_documents_dropdown' , None)
        print('All docs are ' , all_tag_docs)

        if tag_name and all_tag_docs:
            
            delete_tag(tag_name , all_tag_docs)
            
            return redirect(url_for('rag_admin'))
        
        else:
            return redirect('/')

    

    print('enters the update tags with tag id ' , tag_name)


    cur = conn.cursor()

    # Find the most similar document
    all_documents = """
        SELECT t1.id , t1.Filename
        FROM rag_vector_db t1
        JOIN rag_vector_tag_db t2 ON t1.id = t2.id
        WHERE t2.Tag = %s
        ORDER BY t1.id;
    """
    cur.execute(all_documents, (tag_name,))
    # result = cur.fetchone()
    result = cur.fetchall()

    print('result is ' , result)

    context = {
        'tag_name' : tag_name,
        'tag_document_list' : result
    }

    return render_template('tagupdate.html' , context = context)


@app.route('/gpt_schema', methods=['GET','POST'])
def gpt_schema():

    context = {

    }

    return render_template('gpt_action_schema.html' , context = context)




@app.route('/robots933456.txt')
def health_check():
    return 'Healthy', 200


if __name__ == "__main__":
    app.run(host='0.0.0.0' , port='80', debug=True)