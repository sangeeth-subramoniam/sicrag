
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



def insert_document(document_filename,document_text):

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



    def insert_data(conn, document_text, document_vector, document_filename):
        # Insert document into the table
        insert_query = """
            INSERT INTO rag_vector_db (content, vector, filename)
            VALUES (%s, %s::vector, %s)
        """
        with conn.cursor() as cur:
            cur.execute(insert_query, (document_text, document_vector.tolist(), document_filename))
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

    insert_data(conn, document_text, document_vector, document_filename)

    print('Insert done')



def delete_document(document_file_id):
    
    print('Enters delete document in function' , document_file_id)

    delete_query = """
        DELETE FROM rag_vector_db
        WHERE id = %s;
    """
    with conn.cursor() as cur:
        cur.execute(delete_query, (document_file_id,))
        conn.commit()

    print('Deleted {} successfully'.format(document_file_id))


