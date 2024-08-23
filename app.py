from flask import Flask,request, render_template, jsonify, redirect, url_for

import os

import psycopg2
from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
from pdfminer.high_level import extract_text


import re
from io import BytesIO

import pandas as pd
from pptx import Presentation
from docx import Document


from insertdata import insert_document, insert_parent_chunk_to_file_db, delete_document, delete_parent_chunk_to_file_db
from inserttags import insert_tag, delete_tag

# Database connection details
DB_USER = os.getenv("SIC_DB_USER")
DB_PASS = os.getenv("SIC_DB_PASS")
DB_HOST = os.getenv("SIC_DB_HOST")
DB_PORT = 5432
DB_NAME = "postgres"


tablename = "rag_db"
file_table_name = "rag_file_db"
tag_table_name = "rag_tag_db"

ALLOWED_EXTENSIONS = {'pdf','xlsx', 'csv', 'pptx', 'txt', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_excel(file_contents):
    print('Enters Extract text from Excel')
    df = pd.read_excel(BytesIO(file_contents), sheet_name=None)
    text = ""
    for sheet_name, sheet_df in df.items():
        text += sheet_df.to_string(index=False, header=False) + " "
    return text

def extract_text_from_csv(file_contents):
    print('Enters Extract text from CSV')
    df = pd.read_csv(BytesIO(file_contents))
    return df.to_string(index=False, header=False)

def extract_text_from_ppt(file_contents):
    print('Enters Extract text from PPT')
    presentation = Presentation(BytesIO(file_contents))
    text = ""
    for slide in presentation.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text += shape.text + " "
    return text

def extract_text_from_text(file_contents):
    return file_contents.decode('utf-8')

def extract_text_from_docx(file_contents):
    document = Document(BytesIO(file_contents))
    text = ""
    for paragraph in document.paragraphs:
        text += paragraph.text + " "
    return text

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
    search_query = f"""
        SELECT t1.id, t2.filename, t2.content, t2.vector <-> %s::vector AS distance
        FROM  {tag_table_name} t1
        JOIN {tablename} t2 ON t1.parent_filename = t2.parent_filename
        WHERE t1.tag = %s
        ORDER BY distance
    """
    cur.execute(search_query, (query_vector_list , post_tag))

    # result = cur.fetchone()
    result = cur.fetchall()

    # print('result is ' , result)

    print(f'the title 1 is {result[0][1]} and document 1 is {result[0][3]}')
    print(f'the title 2 is {result[1][1]} and document 1 is {result[1][3]}')
    print(f'the title 3 is {result[2][1]} and document 1 is {result[2][3]}')

    if len(result) == 0:
        return jsonify(message="There is no documents matching the tag or the content")

    # for results in result:
    #     print('val is ' , results)


    # Close connection
    cur.close()
    conn.close()

    # response_text = "the Result is {} ".format(result)
    
    #Since gpt response accepts upto 20,000 characters as of 2024/08月 Making sure that the response is large to cauuse error. Response limit is set to 15,000 characters
    #For 15,000 characters 3 sets of 5000 chunks are sent as response. So it is well below 20,000 characters response limit

    response_text = {
        'document_title1' : result[0][1],
        'document_content1' : result[0][2],
        'document_title2' : result[1][1],
        'document_content2' : result[1][2],
        'document_title3' : result[2][1],
        'document_content3' : result[2][2]
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
        search_query = f"""
            SELECT DISTINCT parent_filename
            FROM {tablename};
        """
        cur.execute(search_query)
        # result = cur.fetchone()
        result = cur.fetchall()



        # tag_query = f"""
        #     SELECT
        #         t.tag AS TAG,
        #         string_agg(DISTINCT d.parent_filename, ',' ORDER BY d.id) AS FILENAMES
        #     FROM
        #         {tag_table_name} t
        #     JOIN
        #         {tablename} d ON t.id = d.id
        #     GROUP BY
        #         t.tag
        #     ORDER BY
        #         t.tag;
        # """

        tag_query = f"""
            SELECT
                TAG,
                string_agg(parent_filename, ',' ORDER BY parent_filename) AS FILENAMES
            FROM
                {tag_table_name}
            GROUP BY
                TAG
            ORDER BY
                TAG;
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



def split_text_into_chunks(text, chunk_size=5000):
    # Split the text into sentences
    
    # Remove unwanted spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Split the text into chunks of specified size
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    
    return chunks




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

            #  Allowed file types ( PDF, XLSX, CSV, PPTX, TXT, DOCX )


            filename = file.filename
            file_contents = file.read() 

            print('filename is ' , filename)

            if filename.endswith('.pdf'):
                extracted_text = extract_text(BytesIO(file_contents))
            elif filename.endswith('.xlsx'):
                extracted_text = extract_text_from_excel(file_contents)
            elif filename.endswith('.csv'):
                extracted_text = extract_text_from_csv(file_contents)
            elif filename.endswith('.pptx'):
                extracted_text = extract_text_from_ppt(file_contents)
            elif filename.endswith('.txt'):
                extracted_text = extract_text_from_text(file_contents)
            elif filename.endswith('.docx'):
                extracted_text = extract_text_from_docx(file_contents)

            #  IMAGES

            # elif filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            #     extracted_text = extract_text_from_image(file_contents)
            
            else:
                # raise ValueError("Unsupported file type")
                return redirect(url_for('rag_admin'))
            
            
            
            document_text = extracted_text 

            # print('len of the document is' , len(extracted_text))

            # with open(r"C:\\Users\\sange\\Desktop\\sicrag\\extracted_text.txt", 'w', encoding='utf-8') as file:
            #     # Write content to the file
            #     file.write(extracted_text)

            # print('Document text is ' , document_text)

            chunks = split_text_into_chunks(document_text, chunk_size=5000)

            print('len of chunks is ',len(chunks))

            chunk_filename_list = []
            
            for i, chunk in enumerate(chunks):
                
                # print(f"Chunk {i+1}:\n{chunk} \n \n \n")
                
                filename_without_extension = filename.split('.')[0]
                filename_extension = filename.split('.')[1]
                current_chunk_filename = str(filename_without_extension) + '_' + str(i+1) + '.' + str(filename_extension)

                print('len of chunk {} is {} and current chunk filename is {}'.format( i+1 , len(chunk), current_chunk_filename ))
        
                chunk_insert = insert_document(filename,current_chunk_filename,filename_extension, chunk)
                
                chunk_filename_list.append(str(current_chunk_filename))

            print('All chunks uploaded successfully !')

            # ADDING THE CHUNKS TO THE RAG FILE DB
            rag_file_db = insert_parent_chunk_to_file_db(filename, chunk_filename_list)

            return redirect(url_for('rag_admin'))

        else:
            return redirect(request.url)


    else:

        return render_template('fileupload.html')


@app.route('/file_delete/<filename>', methods=['GET','POST'])
def file_delete(filename):

    print('enters file delete with ID ' , filename)

    delete_document(filename)

    delete_parent_chunk_to_file_db(filename)

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

        parent_filename = request.form.getlist('all_documents_dropdown' , None)
        print('All docs are ' , parent_filename)

        if tagname and parent_filename:
            insert_tag(tagname,list(parent_filename))

            return redirect(url_for('rag_admin'))
        else:
            return redirect(url_for('rag_admin'))


    else:

        cur = conn.cursor()

        all_documents = f"""
            SELECT DISTINCT parent_filename
            FROM {tablename}
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

    all_documents = f"""
        SELECT id , parent_filename
        FROM {tag_table_name}
        WHERE  tag = %s
        ORDER BY id;
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