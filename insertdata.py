
import psycopg2
import os

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

tablename = "rag_db"
file_table_name = "rag_file_db"
tag_table_name = "rag_tag_db"

def insert_document(document_parent_filename,document_filename,filename_extension,document_text):

    from transformers import AutoTokenizer, AutoModel
    import torch
    import numpy as np


    cur = conn.cursor()

    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained("cl-tohoku/bert-base-japanese")
    model = AutoModel.from_pretrained("cl-tohoku/bert-base-japanese")


    # def create_table(conn):
    #     with conn.cursor() as cur:
    #         cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    #         cur.execute("""
    #         CREATE TABLE IF NOT EXISTS rag_vector_db (
    #             id SERIAL PRIMARY KEY,
    #             content TEXT,
    #             vector VECTOR(768)  -- Adjust the dimension size as needed
    #         );
    #         """)
    #         conn.commit()
    #         print("Table created successfully")



    def insert_data(conn, document_parent_filename, document_filename, filename_extension, document_text, document_vector):
        # Insert document into the table
        insert_query = f"""
            INSERT INTO {tablename} (parent_filename,filename,file_extension,content,vector)
            VALUES (%s, %s, %s, %s, %s::vector)
        """
        with conn.cursor() as cur:
            cur.execute(insert_query, (document_parent_filename, document_filename,filename_extension, document_text, document_vector.tolist()))
            conn.commit()

        print('Inserted successfully')



    def text_to_vector(text):
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
        with torch.no_grad():
            outputs = model(**inputs)
        return outputs.last_hidden_state.mean(dim=1).squeeze().numpy()



    #テーブル作成 TABLE CREATION
    # create_table(conn)

    # # 行の追加 ROW INSERT

    document_vector = text_to_vector(document_text)

    insert_data(conn, document_parent_filename, document_filename, filename_extension, document_text, document_vector)

    print('Insert done')


def insert_parent_chunk_to_file_db(filename, current_chunk_filename_list):

    print(f'Enters parent Chunk to file db with filename {filename} and current chunk filename {current_chunk_filename_list}')
    


    insert_parent_chunk_to_file_db_query = f"""
        INSERT INTO {file_table_name} (parent_filename,chunk_file_list)
        VALUES (%s, %s)
    """
    with conn.cursor() as cur:
        cur.execute(insert_parent_chunk_to_file_db_query, (filename, current_chunk_filename_list))
        conn.commit()

    print('insert_parent_chunk_to_file_db successful')

    return "insert_parent_chunk_to_file_db DONE"



def delete_document(document_file_name):
    
    print('Enters delete document in function' , document_file_name)

    delete_query = f"""
        DELETE FROM {tablename}
        WHERE parent_filename = %s;
    """

    with conn.cursor() as cur:

        cur.execute(delete_query, (document_file_name,))
        conn.commit()

    print('Deleted {} successfully'.format(document_file_name))


def delete_parent_chunk_to_file_db(parent_document_file_name):

    print('Enters delete parent_chunk_document_file_name in function' , parent_document_file_name)

    delete_parent_chunk_to_file_db_query = f"""
        DELETE FROM {file_table_name}
        WHERE parent_filename = %s;
    """

    with conn.cursor() as cur:

        cur.execute(delete_parent_chunk_to_file_db_query, (parent_document_file_name,))
        conn.commit()

    print('Deleted {} successfully'.format(parent_document_file_name))






